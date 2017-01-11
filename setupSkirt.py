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

bl_info = {
    "name": "Setup skirt bone",
    "author": "dskjal",
    "version": (1, 0),
    "blender": (2, 78, 0),
    "location": "Properties Shelf",
    "description": "Setup skirt bones",
    "warning": "",
    "support": "TESTING",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Rigging"
}

class DskjalSetupSkirtUI(bpy.types.Panel):
    bl_label = "Setup skirt bones"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    @classmethod
    def poll(self, context):
        try:
            return context.active_object.type == 'MESH'
        except:
            return 0

    def draw(self, context):
        self.layout.operator("dskjal.setupskirtbutton")

class DskjalSetupSkirtButton(bpy.types.Operator):
    bl_idname = "dskjal.setupskirtbutton"
    bl_label = "Setup skirt bones"
  
    def execute(self, context):
        ob = bpy.context.active_object

        #get bmesh
        bpy.ops.object.mode_set(mode='OBJECT')
        if ob.data.is_editmode:
            bm = bmesh.from_edit_mesh(ob.data)
        else:
            bm = bmesh.new()
            bm.from_mesh(ob.data)

        #assign vertex groups
        vgNameHeader = "skirt_t."
        for v in bm.verts:
            vg = ob.vertex_groups.new(vgNameHeader + "%03d" % v.index)
            vg.add([v.index], 1, 'REPLACE')

        #get armature
        bpy.ops.object.add(type='ARMATURE', enter_editmode=True ,location=ob.location)
        amt = bpy.context.object
        amt.name = "AutoSetupedSkirt"

        #-----------------------create bones----------------------------
        bpy.ops.object.mode_set(mode='EDIT')

        #get roop start
        terminalVerts = [v for v in bm.verts if len(v.link_edges)==3]
        meanPos = mathutils.Vector((0.0,0.0,0.0))
        weight = 1/len(terminalVerts)
        for v in terminalVerts:
            meanPos += v.co * weight
        heads = [v for v in terminalVerts if v.co.z > meanPos.z]

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
                    if bottom.co.z > other.co.z:
                        bottom = other
                    elif top.co.z < other.co.z:
                        top = other

                #append tail(i.e. next head)
                b.tail = bottom.co
                tailIndexTable[v.index] = bottom.index
                if len(bottom.link_edges) > 3:
                    tails.append(bottom)

                #parenting
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
            ik.subtarget = vgNameHeader + "%03d" % tailIndexTable[int(b.name[-2:])]
            ik.chain_count = 1
            ik.use_stretch = 1

            #enable stretch
            b.ik_stretch = 1

        bpy.ops.object.mode_set(mode='OBJECT')

        return{'FINISHED'}

def register():
    bpy.utils.register_module(__name__)

def unregister():
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()
