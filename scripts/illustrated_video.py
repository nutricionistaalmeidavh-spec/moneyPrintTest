#!/usr/bin/env python3
"""PDV ArtiSys illustrated short: independent character rigs, devices and real-screen footage.
No paid APIs, no internet, no secrets. Clip-by-clip rendering and cache reuse.
"""
from __future__ import annotations
import argparse, json, math, os, random, subprocess, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'cartoon_render'
ASSETS=ROOT/'assets'/'pdv'/'personagens'
W,H=720,1280
FPS=30
DURS=[6,7,7,6,7,7,7,7,6,7,6,9]
PALETTE={'bg':'#0C101C','edge':'#414058','white':'#F9FAFC','purple':'#B28AFB','soft':'#A8A7BF','blue':'#4A80FA','orange':'#F5A24D','green':'#62D79D'}
FONT_B='/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
FONT_X='/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf'
FONT_R='/usr/share/fonts/opentype/inter/Inter-Regular.otf'
if not Path(FONT_B).is_file(): FONT_B='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
if not Path(FONT_X).is_file(): FONT_X=FONT_B
if not Path(FONT_R).is_file(): FONT_R='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

SRC=ROOT/'assets'/'pdv'
VIDEOS={
 'intro':SRC/'balcao.mp4',
 'mesa':SRC/'mesas.mp4',
 'qr':SRC/'gerar-qr.mp4',
 'cliente':SRC/'cliente-qr.mp4',
 'garcom':SRC/'garcom.mp4',
 'cozinha':SRC/'kds.mp4',
 'caixa':SRC/'caixa.mp4',
 'equipe':SRC/'equipe.mp4',
 'estoque':SRC/'ficha.mp4',
 'relatorios':SRC/'relatorio.mp4',
}
SCENES=[
 dict(id='01',title='Criei meu próprio\nsistema de PDV.',accent='Do salão à cozinha.',body='Um sistema construído para acompanhar a operação real.',hero='laptop',video='intro',chars=['desenvolvedor'],props=['BALCÃO','COZINHA']),
 dict(id='02',title='O problema',accent='Ferramentas separadas\natrasam o atendimento.',body='Caixa, comandas, cozinha e cardápio em fluxos diferentes.',hero='chaos',chars=['garcom','caixa','cozinheiro'],props=['CAIXA','COMANDAS','COZINHA']),
 dict(id='03',title='A solução',accent='Tudo em um só sistema.',body='Vendas, atendimento, equipe e gestão no mesmo lugar.',hero='laptop',video='intro',chars=['desenvolvedor'],props=['BALCÃO','CAIXA','GESTÃO']),
 dict(id='04',title='Operação no salão',accent='Mesas, comandas\ne pedidos.',body='Da abertura da mesa até o QR Code.',hero='laptop',video='mesa',chars=['garcom'],props=['MESA 01','QR CODE']),
 dict(id='05',title='Cardápio digital',accent='O cliente faz o pedido\npelo celular.',body='Navegação visual e escolha dos produtos.',hero='phone',video='cliente',chars=['cliente'],props=['X-BACON','PEDIDO']),
 dict(id='06',title='Garçom conectado',accent='Pedidos e chamados\nem tempo real.',body='O atendimento acompanha o pedido no celular.',hero='phone',video='garcom',chars=['garcom'],props=['NOVO PEDIDO','MESA 08']),
 dict(id='07',title='Cozinha organizada',accent='Da comanda ao KDS.',body='Novo, em preparo e pronto: cada etapa visível.',hero='laptop',video='cozinha',chars=['cozinheiro'],props=['NOVO','EM PREPARO','PRONTO']),
 dict(id='08',title='Do pedido ao caixa',accent='Pagamento sem\nretrabalho.',body='A comanda segue para o fechamento.',hero='laptop',video='caixa',chars=['caixa'],props=['COMANDA','PAGAMENTO']),
 dict(id='09',title='Equipe e permissões',accent='Cada pessoa,\nseu acesso.',body='Administrador, operador e garçom com funções definidas.',hero='roles',chars=['gerente','caixa','garcom'],props=['ADMIN','OPERADOR','GARÇOM']),
 dict(id='10',title='Estoque e cadastros',accent='Ficha técnica\n+ produtos.',body='Organização dos ingredientes, itens e cardápio.',hero='laptop',video='estoque',chars=['cozinheiro'],props=['RECEITA','ESTOQUE']),
 dict(id='11',title='Por trás do produto',accent='Código, testes\ne evolução.',body='Um software que continua evoluindo.',hero='laptop',video='relatorios',chars=['desenvolvedor'],props=['CÓDIGO','TESTES']),
 dict(id='12',title='Curtiu o projeto?',accent='Segue e salva para ver\nos próximos sistemas.',body='Série: sistemas que construí · ArtiSys',hero='laptop',video='intro',chars=['desenvolvedor'],props=['SEGUIR','SALVAR']),
]

def rgba(color, a=255):
 return tuple(int(color[i:i+2],16) for i in (1,3,5))+(a,)

def font(size,bold=False): return ImageFont.truetype(FONT_X if bold else FONT_R, size)

def text_lines(draw,text,ft,maxw):
 result=[]
 for part in text.split('\n'):
  pending=''
  for word in part.split():
   trial=(pending+' '+word).strip()
   if pending and draw.textbbox((0,0),trial,font=ft)[2]>maxw:
    result.append(pending);pending=word
   else: pending=trial
  result.append(pending)
 return result

def text_block(draw,text,x,y,size,color,maxw,line_spacing=1.06,bold=True):
 ft=font(size,bold);lines=text_lines(draw,text,ft,maxw)
 for line in lines:
  draw.text((x,y),line,font=ft,fill=color,stroke_width=0)
  y+=int(size*line_spacing)
 return y

def background(scene,index):
 rng=random.Random(19217+index)
 yy=np.linspace(0,1,H,dtype=np.float32)[:,None]
 xx=np.linspace(0,1,W,dtype=np.float32)[None,:]
 base=np.empty((H,W,3),dtype=np.float32)
 for c,(a,b) in enumerate([(10,18),(13,14),(24,31)]):base[:,:,c]=a+(b-a)*yy
 glow=[(85,865,(75,43,119),380),(615,855,(32,52,132),330),(620,675,(122,59,21),250)]
 X=np.arange(W)[None,:];Y=np.arange(H)[:,None]
 for gx,gy,color,r in glow:
  d=((X-gx)**2+(Y-gy)**2)/(r*r)
  intensity=np.exp(-d*2.7)*0.43
  for c in range(3):base[:,:,c]+=color[c]*intensity
 im=Image.fromarray(np.clip(base,0,255).astype('uint8'),'RGB').convert('RGBA')
 # Blurred illustrated restaurant set from the user's exact visual reference.
 # Heavy blur prevents any conceptual product UI in the artwork being mistaken for real UI.
 ref=ROOT/'assets'/'pdv'/'referencia.jpeg'
 if ref.is_file():
  grid=Image.open(ref).convert('RGB')
  tile_w,tile_h=grid.width//3,grid.height//4
  row,col=divmod(index,3)
  scene_tile=grid.crop((col*tile_w,row*tile_h+int(tile_h*.38),(col+1)*tile_w,(row+1)*tile_h))
  decor=scene_tile.resize((W,650),Image.Resampling.BICUBIC)
  decor=ImageEnhance.Brightness(decor.filter(ImageFilter.GaussianBlur(25))).enhance(.72).convert('RGBA')
  grad=Image.new('L',(W,650));g=ImageDraw.Draw(grad)
  for gy in range(650):
   norm=gy/650
   opacity=int(125*min(1,norm/.28,(1-norm)/.18))
   g.line((0,gy,W,gy),fill=max(0,opacity))
  decor.putalpha(grad)
  im.alpha_composite(decor,(0,405))
 # Warm blurred back-bar and restaurant silhouettes create a hand-painted set.
 lamps=Image.new('RGBA',(W,H));ld=ImageDraw.Draw(lamps)
 for lx in (82,315,604):
  ld.line((lx,450,lx,555),fill=(82,61,58,80),width=3)
  ld.ellipse((lx-16,546,lx+16,578),fill=(255,177,66,110))
  ld.ellipse((lx-39,528,lx+39,592),outline=(247,159,70,70),width=5)
 ld.rounded_rectangle((5,989,W-5,1046),radius=12,fill=(126,72,41,47))
 lamps=lamps.filter(ImageFilter.GaussianBlur(20))
 im=Image.alpha_composite(im,lamps)
 bokeh=Image.new('RGBA',(W,H));bd=ImageDraw.Draw(bokeh)
 for i in range(45):
  x=rng.randrange(0,W);y=rng.randrange(440,1070);r=rng.randrange(3,16)
  col=rng.choice([(233,141,54,75),(124,90,244,65),(49,101,236,75)])
  bd.ellipse((x-r,y-r,x+r,y+r),fill=col)
 bokeh=bokeh.filter(ImageFilter.GaussianBlur(15));im=Image.alpha_composite(im,bokeh)
 d=ImageDraw.Draw(im)
 d.rounded_rectangle((22,22,W-22,H-20),radius=32,outline='#38384A',width=2)
 d.text((50,57),'S I S T E M A S   Q U E   C O N S T R U Í',font=font(17,True),fill=PALETTE['purple'])
 tag=f'{index+1:02d} / 12';bb=d.textbbox((0,0),tag,font=font(21))
 d.text((W-55-(bb[2]-bb[0]),53),tag,font=font(21),fill='#EBE8F2')
 top=text_block(d,scene['title'],50,139,59,PALETTE['white'],620,1.04)
 accsize=35 if len(scene['accent'])>45 else 41
 top=text_block(d,scene['accent'],50,top+16,accsize,PALETTE['purple'],635,1.13)
 d.line((51,1069,669,1069),fill='#454354',width=2)
 text_block(d,scene['body'],51,1094,25,'#D6D3E2',620,1.25,False)
 d.line((51,1188,669,1188),fill='#343545',width=1)
 d.text((50,1206),'ARTISYS  /  PDV ARTISYS',font=font(21),fill='#BCB7D0')
 d.text((629,1198),'↗',font=font(40,True),fill=PALETTE['purple'])
 return im

def frame_card(out,where='laptop'):
 im=Image.new('RGBA',(W,H));d=ImageDraw.Draw(im)
 if where=='phone':
  x,y,w,h=(423,515,240,526)
  d.rounded_rectangle((x-8,y-8,x+w+8,y+h+8),radius=34,fill='#080C16',outline='#A28CD0',width=4)
  d.rounded_rectangle((x-2,y-2,x+w+2,y+h+2),radius=27,outline='#68718E',width=3)
  d.rounded_rectangle((x+70,y+9,x+w-70,y+24),radius=8,fill='#030710')
  return (x+10,y+34,w-20,h-50),im
 x,y,w,h=(255,605,424,294)
 d.rounded_rectangle((x-13,y-13,x+w+13,y+h+8),radius=21,fill='#080C16',outline='#A299B3',width=4)
 d.rounded_rectangle((x-1,y-1,x+w+1,y+h+1),radius=9,outline='#3E5275',width=1)
 d.ellipse((x+w//2-2,y-9,x+w//2+2,y-5),fill='#5A5A72')
 d.polygon([(x-44,y+h+5),(x+w+44,y+h+5),(x+w+66,y+h+29),(x-63,y+h+29)],fill='#252941')
 d.line([(x-62,y+h+28),(x+w+65,y+h+28)],fill='#988FB9',width=4)
 d.rounded_rectangle((x+133,y+h+8,x+w-133,y+h+17),radius=4,fill='#505574')
 return (x+8,y+9,w-16,h-14),im

def role_card(x,y,w,h,title,description,accent):
 im=Image.new('RGBA',(W,H));d=ImageDraw.Draw(im)
 d.rounded_rectangle((x,y,x+w,y+h),radius=22,fill='#19182BEA',outline=accent,width=3)
 d.text((x+18,y+19),title,font=font(24,True),fill='white')
 text_block(d,description,x+18,y+64,19,'#CDCADB',w-36,1.27,False)
 return im

def action_chip(text,idx,index):
 ft=font(22,True);tmp=Image.new('RGBA',(W,H));d=ImageDraw.Draw(tmp)
 bb=d.textbbox((0,0),text,font=ft)
 tw=bb[2]-bb[0];cw=min(W-80,tw+54)
 col=['#9961ED','#2D83DB','#EF9445','#21A68E'][idx%4]
 d.rounded_rectangle((0,0,cw,50),radius=20,fill='#201A35EB',outline=col,width=3)
 d.text((20,10),text,font=ft,fill='#F7F1FF')
 return tmp.crop((0,0,cw,53))

def render_props(scene,index):
 props=[]
 props_dir=WORK/'props';props_dir.mkdir(parents=True,exist_ok=True)
 for j,word in enumerate(scene['props']):
  png=props_dir/f'{index+1:02d}_{j}.png';action_chip(word,j,index).save(png)
  props.append(png)
 return props

def generate_character_animation(role):
 """2D cutout character with separately rotating head + breathing torso, original cartoon poses."""
 out=WORK/'rigs'/f'{role}.mov'
 if out.is_file() and out.stat().st_size>10000:return out
 frames=WORK/'rigs'/role;frames.mkdir(parents=True,exist_ok=True)
 raw=Image.open(ASSETS/f'{role}.png').convert('RGBA')
 box=(260,530);orig=raw.copy();orig.thumbnail((248,510),Image.Resampling.LANCZOS)
 xx=(box[0]-orig.width)//2; yy=(box[1]-orig.height)//2
 canvas=Image.new('RGBA',box);canvas.alpha_composite(orig,(xx,yy))
 threshold=round(yy+orig.height*.265)
 top=round(yy+orig.height*.365)
 body=canvas.copy(); bd=body.load()
 for y in range(threshold):
  for x in range(box[0]):bd[x,y]=(0,0,0,0)
 head=canvas.copy();hd=head.load()
 for y in range(top,box[1]):
  for x in range(box[0]):hd[x,y]=(0,0,0,0)
 for f in range(40):
  t=f/20.0
  wobble=math.sin(2*math.pi*t/2)
  b=body.rotate(2.2*math.sin(2*math.pi*t/2),resample=Image.Resampling.BICUBIC,
                center=(130,380),expand=False)
  h=head.rotate(6.2*math.sin(2*math.pi*(t/2+.12)),resample=Image.Resampling.BICUBIC,
                center=(132,top-3),expand=False)
  frm=Image.new('RGBA',box)
  frm.alpha_composite(b,(0,int(5.0*wobble)))
  frm.alpha_composite(h,(int(2.8*wobble),int(6*math.sin(2*math.pi*(t/2+.15)))))
  frm.save(frames/f'{f:03d}.png')
 cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-framerate','20','-i',str(frames/'%03d.png'),'-c:v','qtrle','-pix_fmt','argb',str(out)]
 subprocess.run(cmd,check=True)
 return out

def prepare_visuals():
 WORK.mkdir(parents=True,exist_ok=True)
 for i,s in enumerate(SCENES):
  f=WORK/f'plate_{i+1:02d}.png';background(s,i).save(f)
  _,border=frame_card(WORK, 'phone' if s['hero']=='phone' else 'laptop')
  border.save(WORK/f'frame_{i+1:02d}.png')
  render_props(s,i)
 for role in {r for sc in SCENES for r in sc['chars']}:
  generate_character_animation(role)

def ffprobe_video(path):
 r=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_type,width,height:format=duration','-of','json',str(path)],text=True))
 return r

def render_clip(i,force=False):
 s=SCENES[i];n=i+1;out=WORK/f'clips/scene-{n:02d}.mp4';out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists() and not force:
  try:
   if abs(float(ffprobe_video(out)['format']['duration'])-DURS[i]) <.12:return out
  except:pass
 dur=DURS[i];cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-threads','2','-filter_complex_threads','2','-loop','1','-framerate','30','-t',str(dur),'-i',str(WORK/f'plate_{n:02d}.png')]
 index=1;vid_idx=None;border_idx=None
 if s.get('video'):
  src=VIDEOS[s['video']]
  if not src.is_file():raise FileNotFoundError(f'Mídia real indispensável: {src}')
  # Seek to the real operative action, rather than beginning with setup or connection screens.
  offsets={'mesa':5,'garcom':10,'cozinha':12,'caixa':11,'estoque':9,'relatorios':8}
  offset=offsets.get(s['video'],0)
  cmd.extend(['-stream_loop','-1'])
  if offset:cmd.extend(['-ss',str(offset)])
  cmd.extend(['-i',str(src)]);vid_idx=index;index+=1
  cmd.extend(['-loop','1','-framerate','30','-t',str(dur),'-i',str(WORK/f'frame_{n:02d}.png')]);border_idx=index;index+=1
 chars=[]
 for role in s['chars']:
  cmd.extend(['-stream_loop','-1','-i',str(WORK/f'rigs/{role}.mov')]);chars.append((index,role));index+=1
 props=[]
 for j,word in enumerate(s['props']):
  cmd.extend(['-loop','1','-framerate','30','-t',str(dur),'-i',str(WORK/f'props/{n:02d}_{j}.png')]);props.append(index);index+=1
 filt=[f'[0:v]scale=740:1316,crop={W}:{H}:x=10+5*sin(t*.36):y=18+7*sin(t*.22),format=rgba[b0]']
 current='b0';num=1
 # Render real video inside the physical device before bezel and characters.
 if vid_idx is not None:
  (x,y,w,h),_=frame_card(WORK,'phone' if s['hero']=='phone' else 'laptop')
  filt.append(f'[{border_idx}:v]format=rgba[bord{n}]')
  filt.append(f'[{current}][bord{n}]overlay=x=0:y=0:shortest=1:format=auto[b{num}]');current=f'b{num}';num+=1
  # Overlay authentic screen footage on TOP of the bezel interior, not underneath its opaque fill.
  screen_crop='crop=iw:trunc(ih*0.79/2)*2:0:0,' if s['hero']=='phone' else ''
  filt.append(f'[{vid_idx}:v]fps=30,{screen_crop}scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,format=rgba,fade=t=in:st=0.45:d=0.45:alpha=1[v{n}]')
  filt.append(f'[{current}][v{n}]overlay=x={x}:y={y}:shortest=1:format=auto[b{num}]');current=f'b{num}';num+=1
 # Human illustrated characters: 2D head turn + body idle already encoded in qtrle with alpha.
 positions={
  0:[(20,560,0.98)],1:[(-42,665,0.70),(238,730,0.63),(463,667,0.7)],
  2:[(4,590,0.95)],3:[(3,605,0.88)],4:[(20,600,0.87)],
  5:[(20,615,0.88)],6:[(12,610,0.89)],7:[(15,595,0.90)],
  8:[(-17,600,0.78),(249,600,0.76),(473,600,0.76)],
  9:[(3,620,0.83)],10:[(10,618,0.84)],11:[(9,622,0.80)]}
 for j,(cidx,role) in enumerate(chars):
  x,y,sc=positions[i][j]
  cw=max(2,int(260*sc)//2*2);ch=max(2,int(530*sc)//2*2)
  filt.append(f'[{cidx}:v]fps=30,scale={cw}:{ch},format=rgba,fade=t=in:st={min(.4+j*.21,1):.2f}:d=0.45:alpha=1[char{j}]')
  # true hand-drawn puppet animation: articulated head inside the moving character, floating body in scene.
  xpos=f'{x}+7*sin(t*1.4)';ypos=f'{y}+4*sin(t*2.7)'
  filt.append(f'[{current}][char{j}]overlay=x=\'{xpos}\':y=\'{ypos}\':shortest=1:eval=frame:format=auto[b{num}]')
  current=f'b{num}';num+=1
 # Props: moving illustrated objects represent concrete actions instead of kinetic-only typography.
 for j,pidx in enumerate(props):
  if i==1:
   x=[50,290,482][j];y=[535,500,566][j]
  elif i==8:
   x=[38,275,503][j];y=[983,963,990][j]
  elif i==11:
   x=[365,524][j];y=[987,1050][j]
  else:
   x=380+(j%2)*130;y=500+j*63
  appear=.6+j*.5
  filt.append(f'[{pidx}:v]format=rgba,fade=t=in:st={appear:.2f}:d=0.35:alpha=1[prop{j}]')
  if i==1:
   # Scene 02: disconnected departments shake as the team struggles.
   xpos=f'{x}+13*sin(t*9+{j})'; ypos=f'{y}+8*sin(t*11+{j})'
  elif i==2:
   # Scene 03: the fragmented modules converge into one computer.
   xpos=f'{x}-105*max(0,1-(t-{appear})/.85)+5*sin(t*2+{j})'
   ypos=f'{y}+48*max(0,1-(t-{appear})/.85)+4*sin(t*2+{j})'
  elif i in (3,5,6,7):
   # Contextual handoff: cards travel in from different places.
   xpos=f'{x}+115*max(0,1-(t-{appear})/.8)+4*sin(t*2.4+{j})'
   ypos=f'{y}-65*max(0,1-(t-{appear})/.8)+5*sin(t*2.1+{j})'
  else:
   xpos=f'{x}+9*sin(t*2.1+{j})'
   ypos=f'{y}-24*min(max((t-{appear})/0.5,0),1)+7*sin(t*1.9+{j})'
  filt.append(f'[{current}][prop{j}]overlay=x=\'{xpos}\':y=\'{ypos}\':eval=frame:shortest=1:format=auto[b{num}]')
  current=f'b{num}';num+=1
 # Convert RGBA once at the end; no need to generate intermediary RGB movies.
 filt.append(f'[{current}]format=yuv420p,fps=30[vout]')
 cmd+=['-filter_complex',';'.join(filt),'-map','[vout]','-an','-t',str(dur),'-c:v','libx264','-preset','ultrafast','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart','-r','30',str(out)]
 (WORK/'commands').mkdir(exist_ok=True)
 (WORK/'commands'/f'scene-{n:02d}.json').write_text(json.dumps(cmd,ensure_ascii=False,indent=2))
 subprocess.run(cmd,check=True)
 return out

def make_soundtrack():
 """Original simple royalty-free synthesized instrumental bed; no imitation/copyrighted music."""
 out=WORK/'original_instrumental.wav'
 if out.exists():return out
 rate=22050;seconds=82;N=seconds*rate
 data=np.zeros(N,np.float32);BPM=112;beat=60/BPM
 chords=[[196,246.94,293.66],[174.61,220,261.63],[146.83,185,220],[164.81,207.65,246.94]]
 for section in range(math.ceil(seconds/(beat*8))):
  start=int(section*beat*8*rate);end=min(N,int((section+1)*beat*8*rate))
  if start>=N:break
  t=np.arange(end-start,dtype=np.float32)/rate
  env=.5-.5*np.cos(2*np.pi*np.minimum(t/(beat*8),1))
  env=.26+.18*env
  for f in chords[section%4]:
   data[start:end]+=.009*env*(np.sin(2*np.pi*f*t)+.25*np.sin(2*np.pi*2*f*t))
  # plucked original notes on every beat
  for k in range(8):
   idx=start+int(k*beat*rate);L=min(N-idx,int(.4*rate))
   if L<=0:continue
   ti=np.arange(L)/rate
   freq=chords[section%4][k%3]*2
   data[idx:idx+L]+=.022*np.exp(-ti*13)*np.sin(2*np.pi*freq*ti)
  # subtle kick and tick
  for k in range(8):
   idx=start+int(k*beat*rate);L=min(N-idx,int(.1*rate))
   if L>0:
    ti=np.arange(L)/rate
    data[idx:idx+L]+=.05*np.exp(-ti*43)*np.sin(2*np.pi*(72*ti-35*ti*ti))
 data[:rate]=data[:rate]*(np.arange(rate)/rate)
 data[-rate:]=data[-rate:]*(np.arange(rate)[::-1]/rate)
 data=np.clip(data,-.7,.7)
 with wave.open(str(out),'wb') as w:
  w.setframerate(rate);w.setnchannels(1);w.setsampwidth(2);w.writeframes((data*32767).astype('<i2').tobytes())
 return out

def join_clips():
 text=''.join(f"file '{(WORK / 'clips'/f'scene-{i+1:02d}.mp4').as_posix()}'\n" for i in range(12))
 listing=WORK/'concat.txt';listing.write_text(text)
 silent=WORK/'silent_video.mp4';final=ROOT/'outputs'/'MoneyPrint_PDV_Artisys_Cartoon_82s.mp4'
 subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(silent)],check=True)
 music=make_soundtrack()
 final.parent.mkdir(parents=True,exist_ok=True)
 subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(silent),'-i',str(music),'-c:v','copy','-c:a','aac','-b:a','128k','-ar','44100','-shortest','-movflags','+faststart',str(final)],check=True)
 return final

def dump_project():
 d={'name':'PDV ArtiSys — animação ilustrada','version':1,'fps':FPS,'aspect':'9:16','resolution':[W,H],
    'duration_seconds':sum(DURS),'illustration_source':'Character PNGs supplied from project storyboard',
    'voice':'not rendered - Paradee model not locally available; do not substitute robotic voice',
    'render_engine':'Pillow rig animation + FFmpeg open source','autopublish':False,'scenes':[]}
 cursor=0
 for i,(s,sec) in enumerate(zip(SCENES,DURS)):
  d['scenes'].append({**s,'start_seconds':cursor,'duration_seconds':sec,'start_frame':cursor*FPS,'duration_frames':sec*FPS,
                      'layers':['dark_restaurant_background','illustrated_character_rig','animated_action_props','real_pdv_footage' if s.get('video') else 'illustrated_character_group','typography','footer']})
  cursor+=sec
 out=WORK/'moneyprint_pdv_cartoon_layers.json';out.write_text(json.dumps(d,ensure_ascii=False,indent=2));return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--only',type=int,help='Render individual scene, 1..12');p.add_argument('--force',action='store_true');p.add_argument('--prepare-only',action='store_true');p.add_argument('--join-only',action='store_true');args=p.parse_args()
 if not args.join_only: prepare_visuals();dump_project()
 if args.prepare_only:return
 if not args.join_only:
  if args.only:render_clip(args.only-1,force=args.force)
  else:
   for i in range(len(SCENES)):
    print(f'Rendering {i+1}/12',flush=True);render_clip(i,force=args.force)
 if not args.only:print('OUTPUT:',join_clips(),flush=True)

if __name__=='__main__':main()
