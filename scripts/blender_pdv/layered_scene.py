"""Build genuine editable layered Blender scenes for MoneyPrint PDV ArtiSys.

Requires locally installed Blender and Quaternius Standard CC0 assets; does not
substitute flattened sprites or fake the final 3D render. Layered `.blend` scenes
are generated individually, with independent character, prop, screen, camera,
lighting and background collections. Optional transparent PNG sequences allow
recomposition in MoneyPrint without rerendering unaffected passes.

Usage:
 blender -b --factory-startup --python scripts/layered_scene.py -- \
    --scene 05 --quality preview --output-dir outputs/blender
"""
from __future__ import annotations
from pathlib import Path
import argparse
import hashlib
import json
import sys

HERE=Path(__file__).resolve()
ROOT=HERE.parents[2] if HERE.parent.name=='blender_pdv' else HERE.parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

COLORS={'navy':(0.035,0.050,0.103,1),'black':(.032,.035,.067,1)}
COLLECTIONS=(
    '00_WORLD',
    '10_RESTAURANT_SET',
    '20_ACTORS_QUATERNIUS_CC0',
    '30_HAND_PROPS',
    '40_DEVICES_3D',
    '41_REAL_PDV_MOVIE_TEXTURES',
    '50_FLOATING_INFO',
    '60_LIGHTS',
    '70_CAMERA',
    '90_SOURCE_ANIMATIONS_HIDDEN',
)


def read_project(path):
    project=json.loads(Path(path).read_text(encoding='utf-8'))
    if HERE.parent.name=='blender_pdv':
        from scripts.blender_pdv.build_blender import validate_plan
    else:
        from scripts.build_blender import validate_plan
    validate_plan(project, ROOT,require_media=True)
    if project.get('character_mode')!='quaternius_standard':
        raise ValueError('Only actual Quaternius Standard skinned actors permitted')
    return project


def bone_match(rig,part):
    if HERE.parent.name=='blender_pdv':
        from scripts.blender_pdv.rig_acting import find_bone
    else:
        from scripts.rig_acting import find_bone
    return find_bone(rig.pose.bones,part)


def armature_related(ob,rig):
    cur=ob
    while cur is not None:
        if cur==rig:return True
        cur=cur.parent
    return any(m.type=='ARMATURE' and m.object==rig for m in ob.modifiers)


def clean_collections(bpy):
    for co in list(bpy.data.collections):
        if co.name in COLLECTIONS or co.name.startswith('CHAR_'):
            bpy.data.collections.remove(co)


def get_collection(bpy,scene,name,parent=None):
    existing=bpy.data.collections.get(name)
    if existing:return existing
    collection=bpy.data.collections.new(name)
    (parent or scene.collection).children.link(collection)
    return collection


def reassign(ob,dest):
    if dest in list(ob.users_collection):return
    dest.objects.link(ob)
    for old in list(ob.users_collection):
        if old !=dest:old.objects.unlink(ob)


def classify_and_group(bpy,scene):
    """Object data stay independently editable; no flattening/merging."""
    groups={name:get_collection(bpy,scene,name) for name in COLLECTIONS}
    rigs=sorted((o for o in scene.objects if o.type=='ARMATURE' and
                 o.name.startswith('RIG_QUATERNIUS_')),key=lambda o:o.name)
    actor_groups={rig:get_collection(bpy,scene,'CHAR_'+rig.name,groups['20_ACTORS_QUATERNIUS_CC0'])
                  for rig in rigs}
    counts={name:0 for name in COLLECTIONS}
    for ob in list(scene.objects):
        label=ob.name
        if label.startswith('LIGHT_') or ob.type=='LIGHT':key='60_LIGHTS'
        elif ob.type=='CAMERA' or label.startswith('CAMERA_'):key='70_CAMERA'
        elif label.startswith('SCREEN_REAL_') or label.startswith('SCREEN_MOVIE_'):key='41_REAL_PDV_MOVIE_TEXTURES'
        elif label.startswith('DEVICE_') or label.startswith('DEVICE_EXTRA_'):key='40_DEVICES_3D'
        elif label.startswith('HAND_PROP_'):key='30_HAND_PROPS'
        elif label.startswith('FLOAT_'):key='50_FLOATING_INFO'
        elif label.startswith('STAGE_') or label.startswith('PROP_table') or label.startswith('PROP_counter') or label.startswith('PROP_desk') or label.startswith('PROP_wall') or label.startswith('PROP_lamp'):key='10_RESTAURANT_SET'
        elif label.startswith('RIG_QUATERNIUS_'):key='20_ACTORS_QUATERNIUS_CC0'
        elif ob.type=='ARMATURE' or ob.hide_render:key='90_SOURCE_ANIMATIONS_HIDDEN'
        else:key='10_RESTAURANT_SET'
        owner=next((rig for rig in rigs if armature_related(ob,rig)),None)
        if owner:
            reassign(ob,actor_groups[owner]);counts['20_ACTORS_QUATERNIUS_CC0']+=1
        else:
            reassign(ob,groups[key]);counts[key]+=1
    groups['90_SOURCE_ANIMATIONS_HIDDEN'].hide_render=True
    for rig in rigs:
        rig['motion_source']='Quaternius Universal Animation Library Standard CC0'
        rig['editable_bones']=True
        rig['original_mesh']='Universal Base Characters Standard CC0'
    return counts


def movie_material(bpy,path,offset,scene_id,device_type):
    if not Path(path).is_file():raise FileNotFoundError(path)
    mat=bpy.data.materials.new(f'MAT_REAL_{scene_id}_{device_type}')
    mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear()
    tex=nodes.new('ShaderNodeTexImage');tex.name='SOURCE_REAL_PDV_VIDEO'
    image=bpy.data.images.load(str(path),check_existing=True)
    image.source='MOVIE';image.filepath=str(path)
    tex.image=image;tex.image_user.use_auto_refresh=True
    tex.image_user.frame_start=1
    tex.image_user.frame_duration=10000
    tex.image_user.frame_offset=int(round(offset*30))
    emission=nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=1.35
    result=nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(tex.outputs['Color'],emission.inputs['Color'])
    mat.node_tree.links.new(emission.outputs['Emission'],result.inputs['Surface'])
    return mat


def additional_screen(bpy,scene,meta,index):
    """Extra actual video textures, from local original MP4, on 3D devices."""
    from mathutils import Vector
    device=meta['device'];scene_id=meta['scene_id']
    video=(ROOT/meta['file']).resolve()
    if ROOT not in video.parents:raise ValueError('Unsafe video source')
    width,height={'phone':(1.00,1.92),'tablet':(1.60,1.03),
                  'laptop':(1.65,1.06),'monitor':(2.0,1.25),'wall_panel':(2.50,1.54)}[device]
    x,y,z=meta['position']
    mat=movie_material(bpy,video,float(meta.get('offset_seconds',0)),scene_id,device)
    mesh=bpy.data.meshes.new(f'SCREEN_MOVIE_{scene_id}_{index}_mesh')
    mesh.from_pydata([(-width/2,0,-height/2),(width/2,0,-height/2),
                      (width/2,0,height/2),(-width/2,0,height/2)],[],[(0,1,2,3)])
    mesh.update();uv=mesh.uv_layers.new()
    for loop,coord in zip(mesh.polygons[0].loop_indices,((0,0),(1,0),(1,1),(0,1))):
        uv.data[loop].uv=coord
    ob=bpy.data.objects.new(f'SCREEN_MOVIE_{scene_id}_{device}_{index}',mesh)
    scene.collection.objects.link(ob);ob.location=(x,y-.086,z);ob.data.materials.append(mat)
    ob['source_kind']='original_pdv_tutorial';ob['device']=device
    ob['source_file']=str(meta['file']);ob['frame_offset']=int(float(meta.get('offset_seconds',0))*30)
    # Physical device bezel remains separate from the screen video mesh.
    shellmat=bpy.data.materials.new(f'MAT_BEZEL_{scene_id}_{index}')
    shellmat.diffuse_color=(.035,.041,.07,1)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x,y+.016,z))
    shell=bpy.context.object;shell.name=f'DEVICE_EXTRA_{device}_{index}'
    shell.dimensions=(width+.12,.14,height+.14)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    shell.data.materials.append(shellmat)
    bevel=shell.modifiers.new('ScreenBezelRound','BEVEL');bevel.width=.055;bevel.segments=3
    # The screen sits slightly in front of the housing and remains editable.
    return ob,shell


def attach_hand_prop(bpy,scene,rig,role,index):
    """Simple true 3D hand props attached to actual animated bones."""
    action=rig.get('acting_action','')
    if action not in {'phone_tap','scan','notification','check','confirm','checkout','type','deliver_plate','cook'}:
        return None
    hand=bone_match(rig,'wrist') or bone_match(rig,'elbow')
    if not hand:return None
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,0))
    o=bpy.context.object
    kind='phone' if action in {'phone_tap','scan','notification','check','confirm'} else (
        'plate' if action=='deliver_plate' else 'tablet' if action in {'checkout','type'} else 'spatula')
    o.name=f'HAND_PROP_{kind}_{role}_{index}'
    o.dimensions={'phone':(.20,.045,.37),'plate':(.45,.45,.06),
                  'tablet':(.38,.045,.27),'spatula':(.07,.5,.035)}[kind]
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    # Parent to the deforming animated hand, separate from character meshes.
    o.parent=rig;o.parent_type='BONE';o.parent_bone=hand.name
    o.location=(0,.12,.08);o.rotation_euler=(0,0,0)
    mat=bpy.data.materials.new(f'MAT_HANDED_{kind}_{index}')
    mat.diffuse_color=(.08,.07,.12,1) if kind!='plate' else (.95,.91,.84,1)
    o.data.materials.append(mat)
    o['prop_type']=kind;o['attached_bone']=hand.name
    return o


def enhance_stage(bpy,scene,project,entry):
    extras=[dict(item,scene_id=entry['id']) for item in entry.get('extra_video_textures',[])]
    for i,extra in enumerate(extras,1):additional_screen(bpy,scene,extra,i)
    rigs=sorted((o for o in scene.objects if o.type=='ARMATURE' and o.name.startswith('RIG_QUATERNIUS_')),
                key=lambda o:o.name)
    for idx,rig in enumerate(rigs):
        role=rig.name[len('RIG_QUATERNIUS_'):].rsplit('_',1)[0]
        attach_hand_prop(bpy,scene,rig,role,idx)
    return classify_and_group(bpy,scene)


def render_pass(bpy,scene,layer_name,out,*,full_sequence=False):
    """Render transparent independent pass; not destructive to .blend file."""
    if layer_name not in COLLECTIONS:raise ValueError('Unknown pass')
    state={co.name:co.hide_render for co in scene.collection.children}
    engine=scene.render.engine
    try:
        for co in scene.collection.children:
            if co.name in COLLECTIONS:
                co.hide_render=(co.name!=layer_name)
        scene.render.film_transparent=True
        scene.render.image_settings.file_format='PNG'
        scene.render.image_settings.color_mode='RGBA'
        out.mkdir(parents=True,exist_ok=True)
        if full_sequence:
            scene.render.filepath=str(out/'frame_')
            bpy.ops.render.render(animation=True)
        else:
            scene.frame_set(max(1,scene.frame_end//2))
            scene.render.filepath=str(out/'poster.png')
            bpy.ops.render.render(write_still=True)
    finally:
        for co in scene.collection.children:
            if co.name in state:co.hide_render=state[co.name]
        scene.render.film_transparent=False
        scene.render.engine=engine


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--scene',default='05')
    p.add_argument('--project',default=str(ROOT/'projects/pdv-artisys-quaternius-v1.json'))
    p.add_argument('--quality',choices=('preview','final'),default='preview')
    p.add_argument('--output-dir',default=str(ROOT/'output'))
    p.add_argument('--layer-posters',action='store_true')
    p.add_argument('--render-passes',action='store_true')
    p.add_argument('--render-video',action='store_true')
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
    project=read_project(args.project)
    if HERE.parent.name=='blender_pdv':
        from scripts.blender_pdv.build_blender import make_blender_scene
    else:
        from scripts.build_blender import make_blender_scene
    import bpy
    out=Path(args.output_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    selected=project['scenes'] if args.scene=='all' else [x for x in project['scenes'] if x['id']==args.scene]
    if not selected:raise ValueError('Scene ID not in project')
    manifest=[]
    for entry in selected:
        clean_collections(bpy)
        make_blender_scene(project,entry,args.quality,out,character_mode='quaternius_standard')
        scene=bpy.context.scene
        counts=enhance_stage(bpy,scene,project,entry)
        blend=out/f'pdv_artisys_scene_{entry["id"]}.blend'
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        if args.render_video:
            scene.frame_set(1)
            scene.render.image_settings.file_format='FFMPEG'
            scene.render.image_settings.color_mode='RGB'
            scene.render.ffmpeg.format='MPEG4'
            scene.render.ffmpeg.codec='H264'
            scene.render.filepath=str(out/f'pdv_artisys_scene_{entry["id"]}.mp4')
            bpy.ops.render.render(animation=True)
        if args.layer_posters or args.render_passes:
            for name in COLLECTIONS:
                if name in ('00_WORLD','90_SOURCE_ANIMATIONS_HIDDEN'):continue
                render_pass(bpy,scene,name,out/'passes'/entry['id']/name,full_sequence=args.render_passes)
        manifest.append({'scene':entry['id'],'blend':blend.name,'frames':entry['duration_frames'],
                         'media_files':([entry['video_texture']['file']] if entry.get('video_texture') else []) +
                                       [x['file'] for x in entry.get('extra_video_textures',[])],
                         'collections':counts,'rig_names':[o.name for o in scene.objects if o.type=='ARMATURE'
                                             and o.name.startswith('RIG_QUATERNIUS_')],
                         'video_screens':[o.name for o in scene.objects if o.name.startswith(('SCREEN_REAL_','SCREEN_MOVIE_'))]})
    (out/'layer_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':'blend_created','scenes':len(manifest),'output':str(out)},ensure_ascii=False))

if __name__=='__main__':main()
