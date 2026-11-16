"""Reusable, editable Quaternius pose overlays for ArtiSys PDV.

The Standard library supplies the actual base animation; this adds authored bone
keys for acting. Never replaces skinned geometry with an image or procedural rig.
Designed to run *inside* Blender 4.2+ after a retargeted animation is baked.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Beat:
    phase: float
    arm: float = 0.0
    elbow: float = 0.0
    head: float = 0.0
    torso: float = 0.0
    wrist: float = 0.0
    step: float = 0.0

# The acting timeline has three independently editable gestures per character.
# Values are small rotations in radians, layered over the real UAL pose.
ACTING = {
    'present': [Beat(0.0), Beat(.24,arm=-.72,elbow=-.28,head=-.08), Beat(.68,arm=-.60,head=-.14), Beat(1)],
    'point': [Beat(0.0),Beat(.32,arm=-.86,elbow=-.10,head=-.12),Beat(.75,arm=-.72),Beat(1)],
    'confused':[Beat(0),Beat(.28,arm=-.95,elbow=-.40,head=.20,torso=.10),Beat(.65,arm=-1.14,head=-.14),Beat(1)],
    'waiting':[Beat(0),Beat(.38,arm=-.28,head=.12,torso=.03),Beat(.75,head=-.10),Beat(1)],
    'check':[Beat(0),Beat(.25,arm=-.67,elbow=-.45,head=.21),Beat(.66,elbow=-.61,head=.03),Beat(1)],
    'relief':[Beat(0),Beat(.28,arm=-.30,head=-.12,torso=-.09),Beat(.70,head=.08),Beat(1)],
    'walk_point':[Beat(0,step=-.24),Beat(.22,arm=-.58,step=.18),Beat(.42,arm=-.88,step=-.14),Beat(.68,arm=-.75,step=.08),Beat(1)],
    'scan':[Beat(0),Beat(.24,arm=-.60,elbow=-.48,head=.15),Beat(.57,arm=-.63,elbow=-.58,head=.26),Beat(1)],
    'phone_tap':[Beat(0),Beat(.18,arm=-.50,elbow=-.64,head=.15,wrist=.04),Beat(.36,arm=-.55,elbow=-.54,wrist=-.18),Beat(.53,arm=-.55,elbow=-.64,wrist=.06),Beat(.73,arm=-.51,elbow=-.51,wrist=-.11),Beat(1)],
    'notification':[Beat(0),Beat(.22,head=-.15,arm=-.28),Beat(.40,arm=-.67,elbow=-.50,head=.18),Beat(.77,elbow=-.58),Beat(1)],
    'cook':[Beat(0),Beat(.20,arm=-.51,elbow=-.44,torso=.06),Beat(.38,arm=-.64,elbow=-.62),Beat(.56,arm=-.43,elbow=-.26),Beat(.76,arm=-.68,elbow=-.49),Beat(1)],
    'deliver_plate':[Beat(0),Beat(.21,arm=-.45,elbow=-.18,step=-.18),Beat(.47,arm=-.65,elbow=-.35,step=.17),Beat(.79,arm=-.72,elbow=-.24),Beat(1)],
    'checkout':[Beat(0),Beat(.28,arm=-.63,elbow=-.61,head=.11),Beat(.50,arm=-.58,elbow=-.39,wrist=-.15),Beat(.70,head=-.14),Beat(1)],
    'assign_roles':[Beat(0),Beat(.36,arm=-.72,elbow=-.24,head=-.10),Beat(.66,arm=-.43,head=.08),Beat(1)],
    'nod':[Beat(0),Beat(.28,head=.18),Beat(.54,head=-.09),Beat(.76,head=.15),Beat(1)],
    'confirm':[Beat(0),Beat(.28,arm=-.30,elbow=-.44,head=-.12),Beat(.70,head=.12),Beat(1)],
    'type':[Beat(0),Beat(.20,arm=-.65,elbow=-.75,wrist=.07,head=.10),Beat(.39,arm=-.66,elbow=-.66,wrist=-.11),Beat(.59,arm=-.60,elbow=-.80,wrist=.10),Beat(.78,arm=-.60,elbow=-.66,wrist=-.09),Beat(1)],
    'wave':[Beat(0),Beat(.20,arm=-1.05,elbow=-.25,wrist=.18),Beat(.44,arm=-1.18,wrist=-.30),Beat(.62,arm=-1.03,wrist=.23),Beat(.82,arm=-1.18,wrist=-.26),Beat(1)],
}

# Name-normalizing pattern match, independent of whether the rig is Mixamo-style,
# Blender suffix style, or Quaternius glTF joint naming.
ALIASES = {
    'head':('head',),
    'torso':('spine2','spine1','chest','upperchest','spine'),
    'upper_arm':('rightupperarm','upperarmr','rightarm','armr','mixamorigrightarm'),
    'elbow':('rightforearm','lowerarmr','forearmr','rightlowerarm'),
    'wrist':('righthand','handr','righthandindex'),
    'left_upper_arm':('leftupperarm','upperarml','leftarm','arml'),
    'left_elbow':('leftforearm','lowerarml','forearml','leftlowerarm'),
    'left_leg':('leftupleg','leftthigh','upperlegl','thighl'),
    'right_leg':('rightupleg','rightthigh','upperlegr','thighr'),
}

def normalize(value):
    return ''.join(ch for ch in value.casefold().split(':')[-1] if ch.isalnum())

def find_bone(pose_bones,part):
    keyed={normalize(b.name):b for b in pose_bones}
    for alias in ALIASES[part]:
        exact=keyed.get(alias)
        if exact:return exact
    for alias in ALIASES[part]:
        matches=[b for k,b in keyed.items() if alias in k]
        if matches:return sorted(matches,key=lambda b:len(b.name))[0]
    return None

def apply_acting(rig,action_name,frame_count,*,walk_distance=.42):
    """Keyframe additional acting on top of baked UAL Standard bone motions.

    Edits are stored as Quaternius_Acting keyframes in the same rig Action. Motion
    is deterministic. Fails if hands are required but rig has no arm bones.
    """
    import bpy
    from mathutils import Quaternion, Vector
    if action_name not in ACTING:
        raise ValueError(f'Ação de personagem desconhecida: {action_name}')
    arm=find_bone(rig.pose.bones,'upper_arm')
    elbow=find_bone(rig.pose.bones,'elbow')
    head=find_bone(rig.pose.bones,'head')
    torso=find_bone(rig.pose.bones,'torso')
    wrist=find_bone(rig.pose.bones,'wrist')
    l_leg=find_bone(rig.pose.bones,'left_leg')
    r_leg=find_bone(rig.pose.bones,'right_leg')
    if not arm or not elbow or not head:
        raise RuntimeError('Quaternius rig lacks right arm, elbow or head for articulated acting')
    part_bones=[('arm',arm),('elbow',elbow),('head',head),('torso',torso),('wrist',wrist)]
    for b in ACTING[action_name]:
        frame=max(1,min(frame_count,round(1+b.phase*(frame_count-1))))
        bpy.context.scene.frame_set(frame)
        for key,bone in part_bones:
            if bone is None:continue
            angle=getattr(b,key)
            if abs(angle)<1e-8 and b.phase not in (0,1):continue
            bone.rotation_mode='QUATERNION'
            base=bone.rotation_quaternion.copy()
            delta=Quaternion((1.0,0,0),angle)
            bone.rotation_quaternion=base@delta
            bone.keyframe_insert(data_path='rotation_quaternion',frame=frame,group=f'ACTING_{action_name}')
        if action_name in {'walk_point','deliver_plate'}:
            for leg,sign in ((l_leg,-1),(r_leg,1)):
                if leg:
                    leg.rotation_mode='QUATERNION'
                    leg.rotation_quaternion=leg.rotation_quaternion@Quaternion((1.,0,0),b.step*sign)
                    leg.keyframe_insert(data_path='rotation_quaternion',frame=frame,group='ACTING_walk')
    if action_name in {'walk_point','deliver_plate'}:
        origin=rig.location.copy()
        for fr,offset in ((1,-walk_distance),(max(2,round(frame_count*.48)),0.),(frame_count,0.)):
            rig.location=origin+Vector((offset,0,0))
            rig.keyframe_insert(data_path='location',frame=fr,group='ACTING_short_walk')
    rig['acting_action']=action_name
    rig['acting_keys']=len(ACTING[action_name])
    bpy.context.scene.frame_set(1)
    return {'action':action_name,'beats':len(ACTING[action_name]),'has_arm':bool(arm),'has_head':bool(head)}
