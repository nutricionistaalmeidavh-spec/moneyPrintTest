#!/usr/bin/env python3
"""Export 3D reference props as portable GLB for Blender (CC0-independent)."""
import trimesh
import numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DEST=ROOT/'assets'/'models';DEST.mkdir(exist_ok=True,parents=True)

def color(hexcode):return np.array([int(hexcode[i:i+2],16) for i in (1,3,5)]+[255],dtype=np.uint8)

def addbox(s,name,extents,xyz,hexcode):
 m=trimesh.creation.box(extents=extents);m.apply_translation(xyz);m.visual.vertex_colors=color(hexcode);s.add_geometry(m,geom_name=name)

def addsphere(s,name,radii,xyz,hexcode):
 m=trimesh.creation.icosphere(subdivisions=2,radius=1.0)
 m.apply_scale(radii);m.apply_translation(xyz);m.visual.vertex_colors=color(hexcode)
 s.add_geometry(m,geom_name=name)

def cylinder(s,name,rad,height,xyz,hexcode):
 m=trimesh.creation.cylinder(radius=rad,height=height,sections=22)
 m.apply_translation(xyz);m.visual.vertex_colors=color(hexcode);s.add_geometry(m,geom_name=name)

def export(name,components):
 s=trimesh.Scene()
 for kind,params in components:
  {'box':addbox,'ball':addsphere,'cylinder':cylinder}[kind](s,*params)
 path=DEST/(name+'.glb');s.export(path)
 return path

items={
'phone':[('box',('body',(0.88,0.1,1.68),(0,0,.85),'#141C30')),
          ('box',('DISPLAY_VIDEO_INSERT',(0.77,.012,1.47),(0,-.058,.85),'#B0D9F2')),
          ('ball',('lens',(.04,.016,.022),(0,-.064,1.61),'#384050'))],
'laptop':[('box',('lid',(2.15,.08,1.42),(0,.45,1.55),'#1B2334')),
          ('box',('DISPLAY_VIDEO_INSERT',(1.99,.012,1.24),(0,.403,1.55),'#B0D9F2')),
          ('box',('keyboard',(2.34,1.3,.06),(0,-.3,.79),'#161D2C'))],
'tablet':[('box',('body',(1.65,.1,1.2),(0,0,.85),'#1B2233')),
          ('box',('DISPLAY_VIDEO_INSERT',(1.52,.01,1.09),(0,-.056,.85),'#B0D9F2'))],
'kds_monitor':[('box',('body',(2.4,.10,1.38),(0,0,1.67),'#131925')),
          ('box',('DISPLAY_VIDEO_INSERT',(2.27,.01,1.25),(0,-.056,1.67),'#B0D9F2')),
          ('box',('stand',(.16,.22,.53),(0,.1,.75),'#505865')),
          ('box',('base',(1.0,.75,.1),(0,0,.48),'#242A33'))],
'mesa':[('box',('top',(2,1.15,.12),(0,0,1.02),'#70422F')),
         ('cylinder',('pedestal',.09,1.0,(0,0,.50),'#494047')),
         ('box',('base',(0.85,.7,.07),(0,0,.04),'#343039'))],
'balcao':[('box',('base',(3,1.03,1.02),(0,0,.51),'#4C3035')),
           ('box',('countertop',(3.25,1.25,.13),(0,0,1.06),'#9A654E'))],
'prato':[('cylinder',('dish',.55,.055,(0,0,.08),'#EBEBE7')),
          ('ball',('bread',(.34,.33,.115),(0,0,.19),'#ECA047')),
          ('ball',('lettuce',(.36,.34,.033),(0,0,.12),'#6C8E49'))],
'comanda':[('box',('paper',(.53,.015,.86),(0,0,.6),'#F1EFE9')),
            ('box',('row_1',(.36,.018,.02),(0,-.02,.86),'#757B83')),
            ('box',('row_2',(.36,.018,.02),(0,-.02,.75),'#757B83'))],
'qr_table_card':[('box',('card',(.66,.06,.88),(0,0,.56),'#F5F2F2')),
                 ('box',('qr_placeholder',(.43,.018,.43),(0,-.036,.62),'#172235'))],
'cadeira':[('box',('seat',(1,.9,.1),(0,0,.75),'#48343C')),
            ('box',('back',(1,.13,.92),(0,.42,1.24),'#48343C')),
            ('cylinder',('leg_1',.05,.7,(-.38,-.33,.36),'#272936')),
            ('cylinder',('leg_2',.05,.7,(.38,-.33,.36),'#272936'))],
'luminaria':[('cylinder',('stem',.035,.65,(0,0,1.05),'#9E8D77')),
             ('ball',('shade',(.42,.42,.23),(0,0,1.48),'#DAB687'))],
'planta':[('cylinder',('pot',.33,.45,(0,0,.23),'#79675F')),
          ('ball',('leaf_cluster',(.57,.45,.66),(0,0,1.02),'#396A57'))]
}
for k,v in items.items():print(export(k,v))
