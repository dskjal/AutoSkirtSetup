# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
import bpy, bmesh, mathutils, math
from bpy.props import *

'''
bl_info = {
    "name": "Setup skirt bone",
    "author": "dskjal",
    "version": (3, 0),
    "blender": (2, 83, 0),
    "location": "Properties Shelf",
    "description": "Setup skirt bones",
    "warning": "",
    "support": "COMMUNITY",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Rigging"
}
'''

element_table = {'X':0, 'Y':1, 'Z':2}

def search_neighbor(bm_vert, elem, is_plus_direction):
    top = bottom = bm_vert.link_edges[0].other_vert(bm_vert)
    for e in bm_vert.link_edges:
        other = e.other_vert(bm_vert)
        if bottom.co[elem] > other.co[elem]:
            bottom = other
        elif top.co[elem] < other.co[elem]:
            top = other

    if is_plus_direction:
        tmp = bottom
        bottom = top
        top = tmp
    
    return (top, bottom)

def is_non_manifold_terminal(bm_vert):
    return len(bm_vert.link_edges) > len(bm_vert.link_faces)

def is_isolation_point(bm_vert):
    for e in bm_vert.link_edges:
        other = e.other_vert(bm_vert)
        if other.select:
            return False

    return True

def is_selected_terminal(bm_vert, elem, is_plus_direction):
        if bm_vert.select:
            if is_non_manifold_terminal(bm_vert):
                return True

            if is_isolation_point(bm_vert):
                return False

            top, bottom = search_neighbor(bm_vert, elem, is_plus_direction)
            return not top.select

        return False



class DSKJAL_PT_SETUP_SKIRT_UI(bpy.types.Panel):
    bl_label = "Setup skirt bones"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"

    @classmethod
    def poll(self, context):
        return context.active_object and context.active_object.type == 'MESH'

    def draw(self, context):
        my_props = context.scene.setup_skirt_props
        col = self.layout.column(align=True)
        row = col.row()
        row.prop(my_props, 'element')

        row = col.row()
        row.prop(my_props, 'direction')
        col.separator()

        col.prop(my_props, 'is_select_only', text="select only")
        col.separator()
        col.prop(my_props, "is_create_rig", text="create rig")

        col.separator()
        btn = col.operator("dskjal.setupskirtbutton")
        btn.element = element_table[list(my_props.element)[0]]
        btn.is_plus_direction = list(my_props.direction)[0] == '+'
        btn.is_select_only = my_props.is_select_only


class DSKJAL_OT_SETUP_SKIRT_BUTTON(bpy.types.Operator):
    bl_idname = "dskjal.setupskirtbutton"
    bl_label = "Setup skirt bones"
    element : bpy.props.IntProperty(default=2)
    is_plus_direction : bpy.props.BoolProperty(default=False)
    is_select_only : bpy.props.BoolProperty(default=False)
  
    def execute(self, context):
        ob = bpy.context.active_object
        is_create_rig = context.scene.setup_skirt_props.is_create_rig

        #get bmesh
        bpy.ops.object.mode_set(mode='OBJECT')
        bm = bmesh.new()
        bm.from_mesh(ob.data)

        # create vertex groups
        if is_create_rig:
            vgNameHeader = "skirt_t."
            for v in bm.verts:
                name = vgNameHeader + "%03d" % v.index
                vg = ob.vertex_groups.new(name=name) if ob.vertex_groups.find(name) == -1 else ob.vertex_groups[name] 
                vg.add([v.index], 1, 'REPLACE')

        #get roop start
        if self.is_select_only:
            terminalVerts = [v for v in bm.verts if is_selected_terminal(v, self.element, self.is_plus_direction)]
            heads = terminalVerts
        else:
            terminalVerts = [v for v in bm.verts if len(v.link_edges)==3]

        num_terminal_verts = len(terminalVerts)
        if num_terminal_verts == 0:
            return {"CANCELLED"}
        
        if not self.is_select_only:
            mean_pos = mathutils.Vector((0.0,0.0,0.0))
            weight = 1/num_terminal_verts
            for v in terminalVerts:
                mean_pos += v.co * weight

            if num_terminal_verts > 1:
                if self.is_plus_direction:
                    heads = [v for v in terminalVerts if v.co[self.element] < mean_pos[self.element]]
                else:
                    heads = [v for v in terminalVerts if v.co[self.element] > mean_pos[self.element]]

        tail_index_table = [-1]*len(bm.verts)
        boneNameHeader = "skirt."

        # add an armature
        bpy.ops.object.add(type='ARMATURE', enter_editmode=True ,location=ob.location)
        amt = bpy.context.object
        amt.name = "Auto_Setuped_Skirt"

        while len(heads) != 0:
            tails = []
            for v in heads:
                b = amt.data.edit_bones.new(boneNameHeader + "%03d" % v.index)
                b.head = v.co

                #search tail
                top, bottom = search_neighbor(v, self.element, self.is_plus_direction)
                b.tail = bottom.co

                #append tail(i.e. next head)
                if len(bottom.link_edges) > 3:
                    tails.append(bottom)
                
                if self.is_select_only:
                    if not bottom.select:
                        amt.data.edit_bones.remove(b)
                        continue

                # set roll
                angle_cos = v.normal.dot(b.z_axis)
                angle_cos = max(-1, min(angle_cos, 1)) # clamp
                roll = math.acos(angle_cos)
                if self.element == 2: # Z
                    b.roll = roll if v.normal.x >=0 else -roll
                elif self.element == 0: # X
                    if self.is_plus_direction:
                        b.roll = roll if v.normal.y < 0 else -roll
                    else:
                        b.roll = roll if v.normal.y >= 0 else -roll
                elif self.element == 1: # Y
                    if self.is_plus_direction:
                        b.roll = -roll if v.normal.x < 0 else roll
                    else:
                        b.roll = roll if v.normal.x < 0 else -roll

                # register index
                tail_index_table[v.index] = bottom.index

                # parenting if a vertex is not terminal
                if not v in terminalVerts:
                    parent_name = boneNameHeader + "%03d" % top.index
                    if amt.data.edit_bones.find(parent_name) != -1:
                        b.parent = amt.data.edit_bones[parent_name]
                        b.use_connect = True

            heads = tails


        # add constraint
        if is_create_rig:
            bpy.ops.object.mode_set(mode='POSE')
            for b in amt.pose.bones:
                #add ik
                ik = b.constraints.new(type='IK')
                ik.target = ob
                ik.subtarget = vgNameHeader + "%03d" % tail_index_table[int(b.name[-3:])]
                ik.chain_count = 1
                ik.use_stretch = 1

                #enable stretch
                b.ik_stretch = 1

        bpy.ops.object.mode_set(mode='OBJECT')

        bm.free()

        return{'FINISHED'}

class DSKJAL_Setup_Skirt_Props(bpy.types.PropertyGroup):
    element : bpy.props.EnumProperty(name='axis', description='Axis', default={'Z'}, options={'ENUM_FLAG'}, items=(('X', 'X', ''), ('Y', 'Y', ''), ('Z', 'Z', '')))
    direction : bpy.props.EnumProperty(name='direction', description='select +/-', default={'-'}, options={'ENUM_FLAG'}, items=(('+', '+', ''), ('-', '-', '')))
    is_select_only : bpy.props.BoolProperty(name='is_select_only', description='select only', default=False)
    is_create_rig : bpy.props.BoolProperty(name='is_create_rig', description='set ik to bones', default=True)


classes = (
    DSKJAL_PT_SETUP_SKIRT_UI,
    DSKJAL_OT_SETUP_SKIRT_BUTTON,
    DSKJAL_Setup_Skirt_Props
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.setup_skirt_props = bpy.props.PointerProperty(type=DSKJAL_Setup_Skirt_Props)

def unregister():
    if getattr(bpy.types.Scene, "setup_skirt_props", False): del bpy.types.Scene.setup_skirt_props
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
