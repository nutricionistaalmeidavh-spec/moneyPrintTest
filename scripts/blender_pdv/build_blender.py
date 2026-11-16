#!/usr/bin/env python3
"""MoneyPrint Blender: 3D characters, reusable rigs, props and REAL PDV video textures.

Run: blender -b --python scripts/build_blender.py -- --scene 05 --still --quality preview
This script needs Blender 4.2+. Dry-run uses stdlib, without bpy.
Proprietary and paid plugins are not used. Nothing auto-publishes.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve()
ROOT=HERE.parents[2] if HERE.parent.name=='blender_pdv' else HERE.parents[1]
CONFIG=ROOT/'projects'/'pdv-artisys-blender-v1.json'


def parse_args():
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    p=argparse.ArgumentParser(description='Build 3D scenes; render MP4/stills only when explicitly requested')
    p.add_argument('--scene',default='05',help='Scene ID 01-12 or all')
    p.add_argument('--quality',choices=['preview','final'],default='preview')
    p.add_argument('--character-mode',choices=['quaternius_standard','procedural_preview'],default=None)
    p.add_argument('--animation-clip',default=None,help='Optional actual Quaternius Standard clip name (never invents missing clip)')
    p.add_argument('--still',action='store_true',help='Render one PNG preview at mid-scene')
    p.add_argument('--animate',action='store_true',help='Render full scene MP4 (CPU intensive)')
    p.add_argument('--dry-run',action='store_true',help='Validate assets/contract without bpy')
    p.add_argument('--contract-only',action='store_true',help='Validate schema without requiring user-owned private MP4 files (CI only)')
    p.add_argument('--output-dir',default=str(ROOT/'outputs'))
    p.add_argument('--project',default=str(CONFIG))
    return p.parse_args(argv)


def validate_plan(project,folder=ROOT,*,require_media=True):
    if project.get('fps')!=30 or project.get('aspect')!='9:16' or project.get('total_frames')!=2460:
        raise ValueError('Project must be 12 scenes, 30 fps, 82 seconds, 9:16')
    seen=set();cursor=0
    scenes=project.get('scenes',[])
    if len(scenes)!=12:raise ValueError('Expected 12 scenes')
    valid_actions={'present','confused','waiting','check','relief','walk_point','scan','phone_tap','notification','cook','checkout','assign_roles','nod','confirm','point','type','wave'}
    roles={'desenvolvedor','garcom','cliente','cozinheiro','caixa','gerente'}
    devices={'laptop','phone','tablet','monitor'}
    for s in scenes:
        if s['id'] in seen or s['start_frame']!=cursor or s['end_frame']!=cursor+s['duration_frames']:
            raise ValueError('Duplicate ID, timeline gap or overlap')
        seen.add(s['id']);cursor=s['end_frame']
        if s.get('kind') not in {'full_3d','hybrid_3d','transition_3d'}:raise ValueError('Invalid shot kind')
        for a in s['actors']:
            if a['role'] not in roles or a['action'] not in valid_actions:raise ValueError('Unknown actor/action')
            if a['animation']['end_frame']>s['duration_frames']:raise ValueError('Actor keyframes exceed scene')
        v=s.get('video_texture')
        if v:
            rel=Path(v['file'])
            if rel.is_absolute() or '..' in rel.parts or rel.parts[0]!='assets':raise ValueError('Unsafe video path')
            if require_media and not (folder/rel).is_file():raise ValueError(f'Missing video: {rel}')
            if v['device'] not in devices:raise ValueError('Unsupported device')
    if cursor!=2460:raise ValueError('Incorrect frame total')
    return {'scenes':12,'duration_s':82,'frames':cursor,'actors':sum(len(s['actors']) for s in scenes),
            'video_textures':sum(bool(s.get('video_texture')) for s in scenes)}


def make_blender_scene(project,scene_data,quality,output_dir,still=False,animate=False,*,character_mode=None,selected_animation=None):
    try:import bpy
    except ModuleNotFoundError as e:raise RuntimeError('Blender is required to create .blend and render output') from e
    from mathutils import Vector

    # Build one independent timeline at frame 1 for every shot: no edits to the existing MoneyPrint renderer.
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for m in list(bpy.data.materials):
        if m.users==0:bpy.data.materials.remove(m)
    shot=scene_data['id']
    scene=bpy.context.scene
    w,h=project['resolution'][quality]
    scene.render.resolution_x=w;scene.render.resolution_y=h;scene.render.resolution_percentage=100
    scene.render.film_transparent=False
    scene.render.image_settings.color_mode='RGBA'
    scene.render.film_transparent=False
    scene.render.fps=project['fps'];scene.frame_start=1;scene.frame_end=scene_data['duration_frames']
    scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='AgX'
    scene.render.image_settings.color_mode='RGBA'
    scene.world.color=(0.018,0.02,0.033)
    scene.render.film_transparent=False
    for engine_name in ('BLENDER_EEVEE_NEXT','BLENDER_EEVEE','CYCLES'):
        try:
            scene.render.engine=engine_name
            break
        except (TypeError, ValueError):
            continue

    # Materials
    def mat(name,hexcode,metal=0.0,rough=0.65,emission=0):
        rgb=[int(hexcode[i:i+2],16)/255 for i in (1,3,5)]
        m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.diffuse_color=(*rgb,1);m.use_nodes=True
        n=m.node_tree.nodes.get('Principled BSDF')
        n.inputs['Base Color'].default_value=(*rgb,1)
        n.inputs['Roughness'].default_value=rough
        n.inputs['Metallic'].default_value=metal
        if emission:
            n.inputs['Emission Color'].default_value=(*rgb,1)
            n.inputs['Emission Strength'].default_value=emission
        return m
    navy=mat('MAT_Backdrop','#0B1020');purple=mat('MAT_ArtisysPurple','#864DD0',rough=.43)
    white=mat('MAT_White','#F7F2ED');warm=mat('MAT_Amber','#C8874D',emission=.15)
    charcoal=mat('MAT_Black','#101626',metal=.3,rough=.32)
    floor_mat=mat('MAT_FloorWood','#25232C',rough=.53)
    brass=mat('MAT_Copper','#B18A55',metal=.65,rough=.3)
    skin_a=mat('MAT_SkinWarm','#D9A27A',rough=.83)
    skin_b=mat('MAT_SkinMedium','#C99169',rough=.82)
    hair_dark=mat('MAT_Hair','#261A22',rough=.85)
    eyes=mat('MAT_Eyes','#1E2435',rough=.52)
    hair_brown=mat('MAT_HairBrown','#4A3028',rough=.88)
    shirt=mat('MAT_Shirt','#E2E7E5');shirt2=mat('MAT_ShirtPurple','#724B9F')
    table=mat('MAT_Table','#4B302B',rough=.42)
    teal=mat('MAT_Teal','#3F998C')

    def cube(name,location,dimensions,material,bevel=0):
        bpy.ops.mesh.primitive_cube_add(size=1,location=location)
        o=bpy.context.object;o.name=name;o.dimensions=dimensions
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        if bevel:
            mod=o.modifiers.new('SmoothEdges','BEVEL');mod.width=bevel;mod.segments=3
            norm=o.modifiers.new('WeightedNormals','WEIGHTED_NORMAL')
        o.data.materials.append(material)
        return o
    def sphere(name,location,scale,material,segments=24):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=12,location=location)
        o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(material)
        for p in o.data.polygons:p.use_smooth=True
        return o
    def cyl(name,a,b,r,material,vertices=16):
        a,b=Vector(a),Vector(b);mid=(a+b)/2;delta=b-a
        bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=delta.length,location=mid)
        o=bpy.context.object;o.name=name;o.rotation_euler=delta.to_track_quat('Z','Y').to_euler();o.data.materials.append(material)
        for p in o.data.polygons:p.use_smooth=True
        return o
    def rig_parts(role,index,x,y,scale=1):
        # An actual Blender Armature: torso, head and separate joint chains, not a PNG sprite.
        bpy.ops.object.armature_add(enter_editmode=True,location=(x,y,0))
        rig=bpy.context.object;rig.name=f'RIG_{role}_{index}';rig.scale=(scale,)*3
        arm=rig.data;arm.name=f'ARM_{role}_{index}'
        eb=arm.edit_bones
        for bone in tuple(eb):eb.remove(bone)
        defs={
            'hips':((0,0,1.20),(0,0,1.68),None),
            'torso':((0,0,1.68),(0,0,2.35),'hips'),
            'head':((0,0,2.35),(0,0,3.12),'torso'),
            'upper_arm.L':((-.35,0,2.25),(-.58,0,1.80),'torso'),
            'lower_arm.L':((-.58,0,1.80),(-.70,-.02,1.45),'upper_arm.L'),
            'upper_arm.R':((.35,0,2.25),(.58,0,1.80),'torso'),
            'lower_arm.R':((.58,0,1.80),(.70,-.02,1.45),'upper_arm.R'),
            'upper_leg.L':((-.19,0,1.25),(-.20,0,.65),'hips'),
            'lower_leg.L':((-.20,0,.65),(-.20,-.06,.20),'upper_leg.L'),
            'upper_leg.R':((.19,0,1.25),(.20,0,.65),'hips'),
            'lower_leg.R':((.20,0,.65),(.20,-.06,.20),'upper_leg.R')}
        for name,(head,tail,parent) in defs.items():
            b=eb.new(name);b.head=head;b.tail=tail
            if parent:b.parent=eb[parent];b.use_connect=False
        bpy.ops.object.mode_set(mode='OBJECT')
        for pb in rig.pose.bones:pb.rotation_mode='XYZ'
        def part(obj,bone):
            world=obj.matrix_world.copy()
            obj.parent=rig;obj.parent_type='BONE';obj.parent_bone=bone
            obj.matrix_world=world
        def at(p):return (x+p[0]*scale,y+p[1]*scale,p[2]*scale)
        skin=skin_b if role in ('cozinheiro','gerente') else skin_a
        torso_mat=shirt2 if role in ('desenvolvedor','gerente','cliente','caixa') else shirt
        if role=='cozinheiro':torso_mat=white
        part(sphere(f'{role}_torso',at((0,0,1.92)),(.40*scale,.23*scale,.59*scale),torso_mat),'torso')
        part(sphere(f'{role}_head',at((0,-.03,2.86)),(.30*scale,.27*scale,.35*scale),skin),'head')
        part(sphere(f'{role}_haircap',at((0,.03,3.13)),(.31*scale,.27*scale,.18*scale),hair_brown if role in ('cliente','caixa') else hair_dark),'head')
        if role in ('cozinheiro',):
            part(cyl(f'{role}_chef_hat',at((0,.06,3.15)),at((0,.06,3.57)),.27*scale,white),'head')
            part(sphere(f'{role}_chef_hat_top',at((0,.06,3.55)),(.32*scale,.30*scale,.12*scale),white),'head')
        if role in ('garcom','caixa'):
            part(cube(f'{role}_apron',at((0,-.24,1.86)),(.53*scale,.04*scale,.65*scale),charcoal,bevel=.03*scale),'torso')
        if role=='gerente':
            part(cube('gerente_clipboard',at((.19,-.28,1.88)),(.36*scale,.06*scale,.50*scale),brass,bevel=.03*scale),'torso')
        for side,xs in [('L',-.13),('R',.13)]:
            part(sphere(f'{role}_eyewhite_{side}',at((xs,-.283,2.90)),(.077*scale,.035*scale,.063*scale),white),'head')
            part(sphere(f'{role}_pupil_{side}',at((xs,-.316,2.90)),(.029*scale,.017*scale,.037*scale),eyes),'head')
            part(sphere(f'{role}_eyebrow_{side}',at((xs,-.283,3.03)),(.075*scale,.025*scale,.023*scale),hair_dark),'head')
        part(sphere(f'{role}_nose',at((0,-.302,2.82)),(.05*scale,.075*scale,.045*scale),skin),'head')
        part(sphere(f'{role}_mouth',at((0,-.286,2.70)),(.08*scale,.017*scale,.018*scale),hair_dark),'head')
        if role in ('gerente','desenvolvedor','cozinheiro'):
            part(sphere(f'{role}_beard',at((0,-.17,2.64)),(.24*scale,.13*scale,.105*scale),hair_dark),'head')
        for side,sgn in [('L',-1),('R',1)]:
            part(cyl(f'{role}_upper_arm_{side}',at((sgn*.35,0,2.22)),at((sgn*.58,0,1.82)),.11*scale,torso_mat),'upper_arm.'+side)
            part(cyl(f'{role}_forearm_{side}',at((sgn*.58,0,1.78)),at((sgn*.70,-.02,1.48)),.082*scale,skin),'lower_arm.'+side)
            part(sphere(f'{role}_hand_{side}',at((sgn*.71,-.02,1.42)),(.11*scale,.09*scale,.12*scale),skin),'lower_arm.'+side)
            part(cyl(f'{role}_thigh_{side}',at((sgn*.19,0,1.15)),at((sgn*.20,0,.67)),.15*scale,charcoal),'upper_leg.'+side)
            part(cyl(f'{role}_shin_{side}',at((sgn*.20,0,.65)),at((sgn*.20,-.05,.20)),.12*scale,charcoal),'lower_leg.'+side)
            part(sphere(f'{role}_shoe_{side}',at((sgn*.20,-.14,.16)),(.17*scale,.27*scale,.13*scale),charcoal),'lower_leg.'+side)
        # For player rig/animation inspection in Blender.
        rig['role']=role;rig['licensing']='procedural proof; production characters must use licensed rigged assets'
        return rig

    def keypose(rig,bone,frame,rotation=(0,0,0)):
        pb=rig.pose.bones.get(bone)
        if pb:
            pb.rotation_euler=rotation
            pb.keyframe_insert(data_path='rotation_euler',frame=frame,group='CharacterAction')
    def action(rig,typ,frames):
        f0,f1=1,frames;mid=max(10,frames//2);end=max(mid+1,frames-8)
        keypose(rig,'head',f0,(0,0,0));keypose(rig,'torso',f0,(0,0,0))
        gestures={
         'present': ('upper_arm.R',(-.75,-.18,.24)),
         'confused':('upper_arm.R',(-1.22,-.1,.32)),
         'waiting':('upper_arm.L',(-.5,0,-.18)),
         'check':('lower_arm.R',(-.95,0,.10)),
         'relief':('upper_arm.R',(-.32,0,.24)),
         'walk_point':('upper_arm.R',(-.84,0,.38)),
         'scan':('lower_arm.R',(-.78,0,.12)),
         'phone_tap':('lower_arm.R',(-1.1,0,.12)),
         'notification':('upper_arm.R',(-1.0,0,.20)),
         'cook':('lower_arm.R',(-.9,0,.16)),
         'checkout':('lower_arm.L',(-.9,0,-.10)),
         'assign_roles':('upper_arm.R',(-.85,0,.30)),
         'nod':('head',(.19,0,0)),
         'confirm':('lower_arm.R',(-.7,0,.20)),
         'point':('upper_arm.R',(-.86,0,.28)),
         'type':('lower_arm.R',(-1.13,0,.30)),
         'wave':('upper_arm.R',(-1.35,.04,.3))}
        bone,move=gestures.get(typ,gestures['present'])
        keypose(rig,bone,f0)
        keypose(rig,bone,mid,move)
        keypose(rig,bone,end,(move[0]*.72,move[1]*.8,move[2]*1.10))
        if typ in ('cook','phone_tap','type','wave'):
            for phase,t in enumerate(range(max(10,frames//3),min(frames-8,frames//3+60),10)):
                keypose(rig,bone,t,(move[0]+(.16 if phase%2 else -.11),move[1],move[2]+(.08 if phase%2 else -.08)))
        if typ in ('scan','check','notification','confused','nod'):
            keypose(rig,'head',mid,(.13,0,.16))
            keypose(rig,'head',end,(-.03,0,-.08))
        elif typ in ('present','relief','assign_roles','walk_point'):
            keypose(rig,'head',mid,(-.10,0,-.14))
        if typ in ('walk_point',):
            x,y,z=rig.location
            for i in range(5):
                fr=1+i*max(1,(frames//2)//4)
                keypose(rig,'upper_leg.L',fr,((-.18 if i%2==0 else .19),0,0))
                keypose(rig,'upper_leg.R',fr,((.17 if i%2==0 else -.17),0,0))
            rig.location=(x-.35,y,z);rig.keyframe_insert(data_path='location',frame=1)
            rig.location=(x,y,z);rig.keyframe_insert(data_path='location',frame=max(3,frames//2))
        if typ in ('confused','waiting','relief'):
            keypose(rig,'torso',mid,(.05,0,.07 if typ=='confused' else -.05))
        keypose(rig,'head',f1,(0,0,0))

    def light(name,kind,loc,energy,color=(1,1,1),size=4):
        data=bpy.data.lights.new(name,kind);data.energy=energy;data.color=color
        if kind=='AREA':data.shape='DISK';data.size=size
        ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);ob.location=loc
        ob.rotation_euler=(Vector((0,0,1.7))-ob.location).to_track_quat('-Z','Y').to_euler()
        return ob

    # Set in a real 3D set rather than a flat visual layer.
    cube('STAGE_floor',(0,0,-.11),(12,10,.22),floor_mat,bevel=.04)
    cube('STAGE_back_wall',(0,3.15,2.9),(12,.22,6.1),navy,bevel=.07)
    cube('STAGE_wall_panel',(0,2.97,2.9),(9.2,.11,4.9),charcoal,bevel=.04)
    for i in range(5):
        x=-4+i*2
        cube('STAGE_panel_trim',(x,2.84,2.9),(.045,.07,4.9),brass,bevel=.02)
    if scene_data['background']=='restaurant':
        for i,x in enumerate((-3.2,3.1)):
            cube(f'PROP_tabletop_{i}',(x,.6,1.04),(2,1,.12),table,bevel=.12)
            cyl(f'PROP_table_leg_{i}',(x,.6,0),(x,.6,1.0),.10,brass)
            for z in [4.4]:
                cyl(f'PROP_lamp_cable_{i}',(x,1,z),(x,1,z+.65),.025,brass)
                sphere(f'PROP_lamp_{i}',(x,1,z),(.26,.26,.17),warm)
        cube('PROP_counter',(-.1,2.5,.65),(5.8,1.0,1.2),table,bevel=.09)
        cube('PROP_counter_top',(-.1,2.5,1.32),(6.3,1.18,.13),brass,bevel=.08)
    else:
        cube('PROP_desk',(0,1,.92),(5,1.5,.2),table,bevel=.1)
        cube('PROP_desk_leg',(-1.7,1,.45),(.12,.12,.9),charcoal)
        cube('PROP_desk_leg',(1.7,1,.45),(.12,.12,.9),charcoal)
        cube('PROP_wall_art',(0,2.85,3.25),(3,.1,1.7),purple,bevel=.1)

    light('LIGHT_key_warm','AREA',(-3.2,-4.5,6.0),600,(1,.72,.51),5)
    light('LIGHT_blue_fill','AREA',(3.5,-3.0,4.0),400,(.67,.68,1),4)
    light('LIGHT_rim','AREA',(0,2.1,6.3),700,(.84,.69,1),4)
    light('LIGHT_practical','POINT',(2.4,1.8,4.2),100,(1,.69,.36))

    # Actor positions share a consistent stage and can be retargeted to CC0 skinned rigs later.
    actors=scene_data['actors'];count=len(actors)
    mode=character_mode or project.get('character_mode','procedural_preview')
    if mode not in ('quaternius_standard','procedural_preview'):
        raise ValueError('Unknown character mode')
    actor_x={1:[-1.45],2:[-1.65,-.1],3:[-1.65,-.2,1.30]}[count]
    for i,(spec,x) in enumerate(zip(actors,actor_x)):
        if mode=='quaternius_standard':
            if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
            from importlib import import_module
            package = 'scripts.blender_pdv' if HERE.parent.name == 'blender_pdv' else 'scripts'
            import_quaternius_actor = import_module(package + '.quaternius_blender').import_quaternius_actor
            import_quaternius_actor(root=ROOT,role=spec['role'],index=i,x=x,
                y=.2 if count==1 else 0,scale=.97 if count<3 else .85,
                frame_count=scene_data['duration_frames'],action_name=spec['action'],
                selected_animation=selected_animation)
        else:
            rig=rig_parts(spec['role'],i,x,.2 if count==1 else 0,scale=.97 if count<3 else .85)
            action(rig,spec['action'],scene_data['duration_frames'])

    def make_video_material(path,offset_seconds):
        from subprocess import check_output
        name=f'MAT_RealPDV_{path.stem}'
        m=bpy.data.materials.new(name);m.use_nodes=True
        nodes=m.node_tree.nodes;nodes.clear()
        tex=nodes.new('ShaderNodeTexImage');tex.label='REAL PDV VIDEO — NOT RECONSTRUCTED'
        video=bpy.data.images.load(str(path),check_existing=True)
        video.source='MOVIE'
        tex.image=video;tex.interpolation='Linear'
        tex.image_user.use_auto_refresh=True
        tex.image_user.use_cyclic=False
        tex.image_user.frame_start=1
        tex.image_user.frame_offset=int(round(offset_seconds*30))
        tex.image_user.frame_duration=10000
        em=nodes.new('ShaderNodeEmission');em.inputs['Strength'].default_value=1.1
        out=nodes.new('ShaderNodeOutputMaterial')
        m.node_tree.links.new(tex.outputs['Color'],em.inputs['Color'])
        m.node_tree.links.new(em.outputs[0],out.inputs['Surface'])
        return m

    def screen(name,x,y,z,w,h,material):
        mesh=bpy.data.meshes.new(name+'_mesh')
        verts=[(-w/2,0,-h/2),(w/2,0,-h/2),(w/2,0,h/2),(-w/2,0,h/2)]
        mesh.from_pydata(verts,[],[(0,1,2,3)]);mesh.update()
        uv=mesh.uv_layers.new()
        for loop,pt in zip(mesh.polygons[0].loop_indices,[(0,0),(1,0),(1,1),(0,1)]):uv.data[loop].uv=pt
        o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o)
        o.location=(x,y,z);o.data.materials.append(material)
        return o

    def make_device(device,video,seconds):
        isphone=device=='phone';isdesktop=device in ('laptop','monitor')
        if isphone:
            w,h=1.55,2.85;x,y,z=1.20,-.45,2.05
        elif isdesktop:
            w,h=2.65,1.55;x,y,z=1.08,-.22,2.2
        else:
            w,h=2.48,1.75;x,y,z=1.13,-.45,2.1
        shell=cube(f'DEVICE_{device}_bezel',(x,y+.025,z),(w+.16,.13,h+.18),charcoal,bevel=.13 if isphone else .06)
        matte=make_video_material(video,seconds)
        disp=screen(f'SCREEN_REAL_PDV_{scene_data["id"]}',x,y-.075,z,w,h,matte)
        disp['glb_insert_name']='DISPLAY_VIDEO_INSERT'
        disp['source_file']=video.name
        disp['is_original_recording']=True
        if isdesktop:
            cube('DEVICE_base',(x,y+.13,z-h/2-.55),(.45,.5,.82),brass,bevel=.05)
            cube('DEVICE_foot',(x,y-.10,z-h/2-.96),(1.4,.7,.08),charcoal,bevel=.05)
            if device=='laptop':
                cube('DEVICE_keyboard',(x,y-.44,z-h/2-.17),(2.95,1.12,.10),charcoal,bevel=.04)
        if isphone:
            sphere('DEVICE_camera',(x,y-.095,z+h/2+.018),(.060,.012,.012),eyes)
            cube('DEVICE_floor_shadow',(x,.1,-.02),(.8,1.7,.025),charcoal,bevel=.04)
        return shell,disp

    v=scene_data.get('video_texture')
    if v:
        p=(ROOT/v['file']).resolve()
        make_device(v['device'],p,v['offset_seconds'])
    elif count>1:
        for i in range(3):
            cube(f'PROP_disconnected_board_{i}',(-1.3+i*1.25,.90,3.8),(.8,.09,.48),[purple,warm,teal][i],bevel=.10)

    bpy.ops.object.camera_add(location=(0,-10,4.3))
    camera=bpy.context.object;camera.name=f'CAMERA_{shot}';scene.camera=camera
    camera.data.type='ORTHO';camera.data.ortho_scale=6.2 if shot=='05' else 7.8
    target=Vector((0,0,2.05))
    for f,position in [(1,(-.10,-10.2,4.36)),(max(2,scene_data['duration_frames']//2),(0,-9.7,4.22)),(scene_data['duration_frames'],(.10,-9.3,4.13))]:
        camera.location=position
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.keyframe_insert(data_path='location',frame=f,group='CameraMotion')
        camera.keyframe_insert(data_path='rotation_euler',frame=f,group='CameraMotion')
    scene.frame_set(1)
    output_dir.mkdir(parents=True,exist_ok=True)
    # Save Blender-editable files, one per scene, no merged dependency or publication.
    filename=output_dir/f'pdv_artisys_scene_{shot}.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(filename))
    if still:
        scene.frame_set(max(1,scene_data['duration_frames']//2))
        scene.render.image_settings.file_format='PNG'
        scene.render.filepath=str(output_dir/f'pdv_artisys_scene_{shot}_still.png')
        bpy.ops.render.render(write_still=True)
    if animate:
        scene.frame_set(1)
        scene.render.image_settings.file_format='FFMPEG'
        scene.render.image_settings.color_mode='RGB'
        scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264';scene.render.ffmpeg.constant_rate_factor='MEDIUM'
        scene.render.filepath=str(output_dir/f'pdv_artisys_scene_{shot}.mp4')
        bpy.ops.render.render(animation=True)
    return str(filename)


def main():
    opt=parse_args();project=json.loads(Path(opt.project).read_text(encoding='utf8'))
    info=validate_plan(project,ROOT,require_media=not opt.contract_only)
    if opt.contract_only and not opt.dry_run:raise SystemExit('--contract-only cannot be used for actual render')
    scenes=project['scenes'] if opt.scene=='all' else [s for s in project['scenes'] if s['id']==opt.scene]
    if not scenes:raise SystemExit(f'Unknown scene: {opt.scene}')
    character_mode=opt.character_mode or project.get('character_mode','procedural_preview')
    if character_mode=='quaternius_standard' and not opt.contract_only:
        if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
        from importlib import import_module
        package = 'scripts.blender_pdv' if HERE.parent.name == 'blender_pdv' else 'scripts'
        assetmod = import_module(package + '.quaternius_assets')
        find_standard_assets, select_animation = assetmod.find_standard_assets, assetmod.select_animation
        library=find_standard_assets(ROOT/'assets/quaternius')
        clip=select_animation(library['clips'],[opt.animation_clip] if opt.animation_clip else ['Sitting_Idle','Sit_Idle','Idle'])
        print('Verified Quaternius Standard assets. Base:',library['model'],'Animation:',library['animation'],'Clip:',clip)
    if opt.dry_run:
        print(json.dumps({'valid':True,'plan':info,'selected':[s['id'] for s in scenes],
          'blender_required_for_blend_and_render':True,'character_mode':character_mode,
          'media_checked':not opt.contract_only,'paid_services':False},indent=2))
        return
    for s in scenes:
        print('Building Blender scene',s['id'],flush=True)
        print(make_blender_scene(project,s,opt.quality,Path(opt.output_dir),opt.still,opt.animate,
            character_mode=character_mode,selected_animation=opt.animation_clip),flush=True)

if __name__=='__main__':main()
