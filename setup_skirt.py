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
import bpy
import bmesh
import mathutils
from bpy.props import *


bl_info = {
    "name": "Setup skirt bone",
    "author": "dskjal",
    "version": (1, 0),
    "blender": (2, 83, 0),
    "location": "Properties Shelf",
    "description": "Setup skirt bones",
    "warning": "",
    "support": "TESTING",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Rigging"
}

element_table = {'X':0, 'Y':1, 'Z':2}
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
        btn = col.operator("dskjal.setupskirtbutton")
        btn.element = element_table[list(my_props.element)[0]]
        btn.is_plus_direction = list(my_props.direction)[0] == '+'

class DSKJAL_OT_SETUP_SKIRT_BUTTON(bpy.types.Operator):
    bl_idname = "dskjal.setupskirtbutton"
    bl_label = "Setup skirt bones"
    element : bpy.props.IntProperty(default=2)
    is_plus_direction : bpy.props.BoolProperty(default=False)
  
    def execute(self, context):
        ob = bpy.context.active_object

        #get bmesh
        bpy.ops.object.mode_set(mode='OBJECT')
        bm = bmesh.new()
        bm.from_mesh(ob.data)

        # create vertex groups
        vgNameHeader = "skirt_t."
        for v in bm.verts:
            vg = ob.vertex_groups.new(name = vgNameHeader + "%03d" % v.index)
            vg.add([v.index], 1, 'REPLACE')

        # add an armature
        bpy.ops.object.add(type='ARMATURE', enter_editmode=True ,location=ob.location)
        amt = bpy.context.object
        amt.name = "AutoSetupedSkirt"

        #-----------------------create bones----------------------------
        #get roop start
        terminalVerts = [v for v in bm.verts if len(v.link_edges)==3]
        mean_pos = mathutils.Vector((0.0,0.0,0.0))
        weight = 1/len(terminalVerts)
        for v in terminalVerts:
            mean_pos += v.co * weight
        if self.is_plus_direction:
            heads = [v for v in terminalVerts if v.co[self.element] < mean_pos[self.element]]
        else:
            heads = [v for v in terminalVerts if v.co[self.element] > mean_pos[self.element]]

        tailIndexTable = [-1]*len(bm.verts)
        boneNameHeader = "skirt."

        while len(heads) != 0:
            tails = []
            for v in heads:
                b = amt.data.edit_bones.new(boneNameHeader + "%03d" % v.index)
                b.head = v.co

                #search tail
                top = bottom = v.link_edges[0].other_vert(v)
                for e in v.link_edges:
                    other = e.other_vert(v)
                    if bottom.co[self.element] > other.co[self.element]:
                        bottom = other
                    elif top.co[self.element] < other.co[self.element]:
                        top = other

                if self.is_plus_direction:
                    tmp = bottom
                    bottom = top
                    top = tmp
                    
                #append tail(i.e. next head)
                b.tail = bottom.co
                if len(bottom.link_edges) > 3:
                    tails.append(bottom)

                # register index
                tailIndexTable[v.index] = bottom.index

                # parenting if a vertex is not terminal
                if len(v.link_edges) > 3:
                    parentName = boneNameHeader + "%03d" % top.index
                    b.parent = amt.data.edit_bones[parentName]
                    b.use_connect = True

            heads = tails


        #add ik
        bpy.ops.object.mode_set(mode='POSE')
        for b in amt.pose.bones:
            ik = b.constraints.new(type='IK')
            ik.target = ob
            ik.subtarget = vgNameHeader + "%03d" % tailIndexTable[int(b.name[-3:])]
            ik.chain_count = 1
            ik.use_stretch = 1

            #enable stretch
            b.ik_stretch = 1

        bpy.ops.object.mode_set(mode='OBJECT')

        return{'FINISHED'}

class DSKJAL_Setup_Skirt_Props(bpy.types.PropertyGroup):
    element : bpy.props.EnumProperty(name='axis', description='Axis', default={'Z'}, options={'ENUM_FLAG'}, items=(('X', 'X', ''), ('Y', 'Y', ''), ('Z', 'Z', '')))
    direction : bpy.props.EnumProperty(name='direction', description='select +/-', default={'-'}, options={'ENUM_FLAG'}, items=(('+', '+', ''), ('-', '-', '')))


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
    if hasattr(bpy.types.Scene, "setup_skirt_props"): del bpy.types.Scene.setup_skirt_props
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
