"""Generate separately-editable transparent typography layers for MoneyPrint.
No text is burned onto actual PDV recordings or 3D footage.
"""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont
HERE=Path(__file__).resolve()
ROOT=HERE.parents[2] if HERE.parent.name=='blender_pdv' else HERE.parents[1]
SIZE=(1080,1920)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def font(sz,bold=False):
    try:return ImageFont.truetype(BOLD if bold else FONT,sz)
    except OSError:return ImageFont.load_default(size=sz)

def wrap(text,f,maxwidth):
    dummy=ImageDraw.Draw(Image.new('RGB',(4,4)))
    lines=[];line=''
    for word in text.split():
        next_line=(line+' '+word).strip()
        if dummy.textbbox((0,0),next_line,font=f)[2]>maxwidth and line:
            lines.append(line);line=word
        else:line=next_line
    if line:lines.append(line)
    return lines

def draw_layer(text,*,x,y,color,bold=False,size=48,letter_spacing=0):
    im=Image.new('RGBA',SIZE,(0,0,0,0));d=ImageDraw.Draw(im)
    ff=font(size,bold);lines=wrap(text,ff,900)
    yy=y
    for line in lines:
        d.text((x,yy),line,font=ff,fill=color,stroke_width=0)
        yy+=int(size*1.27)
    return im

def build():
    p=json.loads((ROOT/'projects/pdv-artisys-quaternius-v1.json').read_text())
    manifest={}
    for s in p['scenes']:
        sid=s['id'];folder=ROOT/'overlays'/('scene_'+sid);folder.mkdir(parents=True,exist_ok=True)
        meta=s['typography'];recs=[]
        elements=[
          ('eyebrow','SISTEMAS QUE CONSTRUÍ',(80,75),'#AC88EB',False,25,.0),
          ('title',meta['title'],(70,135),meta['color_title'],True,68,.3),
          ('accent',meta['accent'],(76,385),meta['color_accent'],True,48,1.25),
          ('footer','ARTISYS / PDV ARTISYS',(76,1784),'#D8D4E0',False,24,0),
          ('scene_number',sid+' / 12',(910,72),'#E5DEEA',False,23,0),
        ]
        for name,text,(x,y),color,bold,size,at in elements:
            output=folder/(name+'.png')
            draw_layer(text,x=x,y=y,color=color,bold=bold,size=size).save(output)
            recs.append({'id':name,'file':str(output.relative_to(ROOT)),
                         'start_seconds':at,'duration_seconds':s['duration_frames']/30-at,
                         'opacity_curve':[{'t':at,'v':0},{'t':at+.35,'v':1}],
                         'position':{'x':x,'y':y},'editable_text':text,'alpha':True})
        manifest[sid]=recs
    f=ROOT/'timelines/typography_layers.json'
    f.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    return manifest

if __name__=='__main__':print('Generated overlay layer files:',sum(map(len,build().values())))
