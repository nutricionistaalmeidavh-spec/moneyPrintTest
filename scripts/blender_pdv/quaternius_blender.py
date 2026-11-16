"""Blender 4.2+ adapter: genuine Quaternius skinned character + real Standard clip.

Requires downloaded CC0 Standard assets. No procedural character fallback, no paid
Source/Pro dependency. Intended for one pilot scene (05) before expanding to 12.
"""
from __future__ import annotations
from pathlib import Path
import math

from .quaternius_assets import AssetError, find_standard_assets, normalize_bone, select_animation

CLIP_FOR_ROLE = {
    'cliente':['Idle','Sitting_Idle','Sit_Idle'],
    'garcom':['Idle','Walk'],
    'cozinheiro':['Idle'],
    'caixa':['Idle'],
    'gerente':['Idle'],
    'desenvolvedor':['Idle'],
}


def import_quaternius_actor(*, root: Path, role: str, index: int, x: float,
                            y: float, scale: float, frame_count: int, action_name: str,
                            selected_animation: str|None=None):
    import bpy
    from mathutils import Quaternion, Vector

    assets=find_standard_assets(root / 'assets/quaternius',female=role in ('cliente','caixa'))
    preferred=[selected_animation] if selected_animation else CLIP_FOR_ROLE[role]
    real_clip=select_animation(assets['clips'],preferred)

    existing=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(assets['model']))
    imported=[ob for ob in bpy.data.objects if ob not in existing]
    armatures=[ob for ob in imported if ob.type=='ARMATURE']
    if not armatures:raise AssetError('Quaternius Standard glTF não criou Armature')
    target=max(armatures,key=lambda ob:len(ob.data.bones))
    target.name=f'RIG_QUATERNIUS_{role}_{index}'
    # Position complete imported hierarchy; GLB rig may include parent root nodes.
    # Scale the armature and all top-level model objects, preserving skinning.
    roots=[ob for ob in imported if ob.parent is None or ob.parent not in imported]
    for ob in roots:
        ob.scale*=scale
        ob.location+=Vector((x,y,0))

    previous=set(bpy.data.objects)
    existing_actions=set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=str(assets['animation']))
    animation_objects=[ob for ob in bpy.data.objects if ob not in previous]
    rigs=[ob for ob in animation_objects if ob.type=='ARMATURE']
    if not rigs:raise AssetError('Universal Animation Library não contém Armature importável')
    source=max(rigs,key=lambda ob:len(ob.data.bones))
    source_actions=[a for a in bpy.data.actions if a not in existing_actions]
    nla=[]
    if source.animation_data:
        for track in source.animation_data.nla_tracks:
            for strip in track.strips:
                if strip.action not in source_actions:source_actions.append(strip.action)
                nla.append((track,strip))
        if source.animation_data.action and source.animation_data.action not in source_actions:
            source_actions.append(source.animation_data.action)
    matching=[act for act in source_actions if real_clip.casefold() in act.name.casefold()]
    if not matching:
        matching=[act for act in source_actions if any(t.casefold() in act.name.casefold() for t in ('idle','sit'))]
    if not matching:
        raise AssetError('GLB possui animação declarada, mas o Blender não importou uma Action correspondente: '+real_clip)
    selected=matching[0]
    source.animation_data_create()
    for track,strip in nla:
        track.mute=True
    source.animation_data.action=selected
    # Blender 4.4+ Actions may contain separate armature animation slots.
    if hasattr(selected,'slots') and selected.slots:
        slots=[s for s in selected.slots if getattr(s,'target_id_type','')=='OBJECT']
        if slots:
            try:source.animation_data.action_slot=slots[0]
            except (AttributeError,TypeError,ValueError):pass

    src={normalize_bone(b.name):b for b in source.pose.bones}
    dst={normalize_bone(b.name):b for b in target.pose.bones}
    matches=[(src[n],dst[n]) for n in sorted(set(src)&set(dst))]
    if len(matches)<max(5,min(len(src),len(dst))*.60):raise AssetError('Retarget incompatível com a malha selecionada')
    for ob in animation_objects:
        ob.hide_render=True
        ob.hide_viewport=True
    source.hide_viewport=False  # allow dependency graph evaluation while baking
    source.hide_render=True

    fr0,fr1=(int(n) for n in selected.frame_range)
    if fr1<=fr0:raise AssetError('Action sem keyframes válidos')
    scene=bpy.context.scene
    # 30 fps: sample source clip cyclically, baking actual UAL bone pose to the
    # skinned Quaternius actor. Keyframes editable in .blend per bone.
    for fr in range(1,frame_count+1,2):
        src_f=fr0+((fr-1)%(max(2,fr1-fr0)))
        scene.frame_set(src_f)
        # bone rotation is transferred in local rest space; common skeleton
        # naming and rest orientation are expected by these matching packs.
        for source_bone,dest_bone in matches:
            dest_bone.rotation_mode='QUATERNION'
            dest_bone.rotation_quaternion=source_bone.matrix_basis.to_quaternion()
            if dest_bone.name.lower().startswith(('root','pelvis')):
                # Standard _in-place_ source; forbid root drift during camera shot.
                dest_bone.location=(0,0,0)
            dest_bone.keyframe_insert(data_path='rotation_quaternion',frame=fr,group='Quaternius UAL Standard')
    # Hand gesture overlay for scene 05: a real 3D bone animation, not sprites.
    if action_name=='phone_tap':
        lower=next((b for name,b in dst.items() if 'lowerarmr' in name or 'forearmr' in name),None)
        upper=next((b for name,b in dst.items() if 'upperarmr' in name),None)
        head=next((b for name,b in dst.items() if name in ('head','head01')),None)
        if not (lower and upper):raise AssetError('Rig sem braço direito; impossível animar uso do celular')
        for fr,angle in [(1,0.0),(16,-.22),(30,-.46),(46,-.20),(61,-.53),(76,-.27),(92,-.49),(frame_count,0.0)]:
            if fr>frame_count:continue
            for bone,amount in [(upper,angle*.45),(lower,angle)]:
                bone.rotation_mode='QUATERNION'
                base=bone.rotation_quaternion.copy()
                bone.rotation_quaternion=base@Quaternion((1,0,0),amount)
                bone.keyframe_insert(data_path='rotation_quaternion',frame=fr,group='PDV phone tap')
            if head:
                head.rotation_mode='QUATERNION'
                head.rotation_quaternion=Quaternion((1,0,0),.10)
                head.keyframe_insert(data_path='rotation_quaternion',frame=fr,group='PDV head focus')

    # Source objects kept hidden in viewport only AFTER baking, so visual shot
    # uses real character without duplicate animation mannequin.
    for ob in animation_objects:ob.hide_viewport=True
    scene.frame_set(1)
    target['quaternius_source']='Universal Base Characters [Standard]'
    target['quaternius_animation']='Universal Animation Library [Standard]'
    target['real_clip']=real_clip
    target['retargeted_bones']=len(matches)
    target['license']='CC0-1.0'
    return target
