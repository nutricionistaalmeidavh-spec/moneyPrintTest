/**
 * MoneyPrint educational explainer. Runs INSIDE the pinned ORIGINAL
 * Vincentwei1021/video-talkcraft workbench. Card components, camera rig,
 * PencilDraw and Remotion runtime are imported directly from that upstream.
 * Original author retains the PolyForm Noncommercial license.
 */
import React from 'react';
import {
  AbsoluteFill, Audio, Composition, Img, Sequence, interpolate,
  spring, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import {registerRoot} from 'remotion';
import {CameraRig, Plane} from '../../../template/motion-systems/camera';
import {PencilDraw} from '../../../template/components/pencil';
import {card as OrbitCard} from '../cards/gen/orbit-drift';
import {card as ChatCard} from '../cards/gen/chat-message-flow';
import {card as StepsCard} from '../cards/gen/numbered-step-stack';
import {card as PaperFanCard} from '../cards/gen/stack-fan-out';
import data from './MoneyPrintData.json';

type Scene = {
  id: string; title: string; text: string; eyebrow: string;
  layout: string; repoUrl: string; image: string;
  startFrame: number; durationFrames: number;
};
type Cue = {
  id: string; scene_id: string; word: string; effect: string;
  recipe: string; at: number; duration: number; method: string;
};
type Manifest = {
  fps: number; totalFrames: number; aspect: string;
  scenes: Scene[]; cues: Cue[];
};
const movie = data as Manifest;
const ink = '#192643';
const violet = '#6c57d5';
const pastel = '#f8faff';

const fontStack = '"Inter", "Arial", "DejaVu Sans", Helvetica, sans-serif';

const FlowIllustration:React.FC<{scene:Scene}> = ({scene})=>{
 const frame=useCurrentFrame();
 const {fps}=useVideoConfig();
 const key=(scene.title+' '+scene.text).toLowerCase();
 const labels=key.includes('planilha')||key.includes('erp')?['PLANILHAS','PEDIDOS','FINANCEIRO']:
   key.includes('crm')||key.includes('cliente')||key.includes('lead')?['CLIENTE','PROPOSTA','VENDA']:
   key.includes('atendimento')||key.includes('mensag')?['MENSAGEM','EQUIPE','RESPOSTA']:
   key.includes('kanban')||key.includes('tarefa')||key.includes('plane')?['A FAZER','FAZENDO','CONCLUÍDO']:
   key.includes('document')||key.includes('paperless')||key.includes('contrato')?['DOCUMENTO','INDEXAÇÃO','BUSCA']:
   ['ENTRADA','ORGANIZAÇÃO','RESULTADO'];
 const colors=['#7358df','#3b97d5','#2aab9c'];
 return <div style={{position:'absolute',left:120,top:557,right:120,
   display:'flex',justifyContent:'space-between',alignItems:'center',gap:32}}>
   {labels.map((label,i)=>{
     const p=spring({frame:Math.max(0,frame-(i*11+7)),fps,config:{damping:20,stiffness:125}});
     const pulse=1+Math.sin(frame*.036+i*.7)*.009;
     return <React.Fragment key={label}>
       <div style={{flex:1,minHeight:255,background:'#ffffff',borderRadius:28,
         border:'2px solid #e7eaf6',boxShadow:'0 24px 54px rgba(61,83,135,.10)',
         padding:'35px 34px',opacity:frame<(i*11+7)?0:p,
         transform:'translateY('+(62*(1-p))+'px) scale('+pulse+')'}}>
         <div style={{width:67,height:67,borderRadius:20,
           background:colors[i],color:'#fff',fontWeight:800,fontSize:34,
           display:'flex',alignItems:'center',justifyContent:'center'}}>{i+1}</div>
         <div style={{marginTop:40,fontSize:31,fontWeight:800,color:ink}}>{label}</div>
         <div style={{height:7,width:(90+i*35),borderRadius:10,
           marginTop:20,background:colors[i],opacity:.35}}/>
       </div>
       {i<2&&<div style={{fontSize:48,color:'#a9b2d0',
         transform:'translateX('+Math.round(Math.sin(frame*.08+i)*7)+'px)'}}>→</div>}
     </React.Fragment>;
   })}
 </div>;
};

const TextReveal: React.FC<{text: string; fontSize: number; delay?: number; color?: string}> =
  ({text, fontSize, delay=0, color=ink}) => {
    const frame=useCurrentFrame();
    const {fps}=useVideoConfig();
    const p=spring({frame:Math.max(0,frame-delay),fps,config:{damping:23,mass:.85,stiffness:160}});
    return <div style={{fontSize,fontWeight:800,letterSpacing:-1.9,lineHeight:1.12,fontFamily:fontStack,
      opacity:frame<delay?0:p,
      transform:'translateY('+(38*(1-p))+'px)',color}}>{text}</div>;
  };

const ChaosLines: React.FC = () => {
  // Original PencilDraw from video-talkcraft; paths are unique original
  // MoneyPrint illustrations, not screenshots from stock repositories.
  const strokes=[
    'M 130 170 C 240 40 280 400 440 130 S 690 380 780 95 C 590 410 390 20 190 425',
    'M 90 335 C 350 85 530 480 790 235 C 640 90 195 520 110 220',
    'M 230 95 Q 615 500 775 145 T 230 450',
  ];
  return <AbsoluteFill style={{justifyContent:'center',alignItems:'center',transform:'translateY(165px) scale(.86)'}}>
    {strokes.map((d,i)=><PencilDraw key={i} d={d} at={i*10}
       dur={54} stroke={i===1?'#b44b77':'#272947'} width={5.5}
       viewBox="0 0 960 540" pencilScale={.58} tilt={-35}
       style={{width:1030,height:580}} />)}
  </AbsoluteFill>;
};

const Recipe:React.FC<{cue:Cue;scene:Scene}> = ({cue,scene}) => {
  if(cue.effect==='scribble_chaos'){
    return <ChaosLines/>;
  }
  if(cue.effect==='paper_overload'){
    // Native VIDEO TALKCRAFT stack-fan-out recipe, not a Pillow imitation.
    // Five original educational document SVGs are supplied as card images.
    const PaperFan=PaperFanCard.component;
    return <AbsoluteFill style={{background:'transparent'}}>
      <div style={{position:'absolute',left:220,top:360,width:960,height:540,
        transform:'scale(1.45)',transformOrigin:'top left',borderRadius:20,
        boxShadow:'0 22px 65px rgba(39,57,100,.08)',overflow:'hidden'}}>
        <PaperFan title=""
          src1={staticFile('moneyprint/paper_1.svg')}
          src2={staticFile('moneyprint/paper_2.svg')}
          src3={staticFile('moneyprint/paper_3.svg')}
          src4={staticFile('moneyprint/paper_4.svg')}
          src5={staticFile('moneyprint/paper_5.svg')}/>
      </div>
      <div style={{position:'absolute',bottom:40,right:95,fontSize:18,color:'#7c87a6'}}>
        DOCUMENTOS · ILUSTRAÇÃO DIDÁTICA
      </div>
    </AbsoluteFill>;
  }
  const chosen=cue.effect==='crm_orbit'?OrbitCard:
               cue.effect==='support_chat'?ChatCard:StepsCard;
  const Card=chosen.component;
  const props:Record<string,unknown> = cue.effect==='crm_orbit'?
    {appName:'CRM',barTitle:'Clientes e oportunidades',chip:'ILUSTRAÇÃO',
     detailTitle:'Organização do funil',detailMeta:'Exemplo didático',
     kv1:'Contato|Organizado',kv2:'Etapas|Visíveis',ink:'#233e48'}:
    cue.effect==='support_chat'?
    {contactName:'Equipe de atendimento',contactSub:'Cenário ilustrativo',
     avatarChar:'E',messages:'them|Olá, preciso de atendimento.\nme|Vou encaminhar sua solicitação.\nthem|Obrigado!',
     ink:'#234c5d',themBg:'#e9f2f9'}:
    {stepsDsl: cue.effect==='sales_flow'?
       '01|Primeiro contato\n02|Enviar proposta\n03|Concluir venda':
       cue.effect==='document_flow'?
       '01|Documento recebido\n02|Indexação\n03|Pesquisa e recuperação':
       '01|Informação recebida\n02|Equipe acompanha\n03|Processo concluído',
     noColor:'#6c57d5'};
  return <AbsoluteFill style={{alignItems:'center',justifyContent:'center'}}>
    <div style={{width:960,height:540,transform:'scale(1.56)',
      transformOrigin:'center',boxShadow:'0 20px 70px rgba(42,58,96,.10)',
      borderRadius:20,overflow:'hidden'}}>
      <Card {...props}/>
    </div>
    <div style={{position:'absolute',right:75,bottom:60,fontSize:18,
      color:'#60708d'}}>ILUSTRAÇÃO DIDÁTICA · VIDEO TALKCRAFT</div>
  </AbsoluteFill>;
};

const SceneView:React.FC<{scene:Scene}> = ({scene})=>{
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const secs=scene.durationFrames/fps;
  const cameraPath=[
    {t:0,scale:1.0,x:0,y:0},
    {t:Math.max(.03,secs),scale:1.04,x:-19,y:-8}
  ];
  const cues=movie.cues.filter(c=>c.scene_id===scene.id);
  const subtitle=scene.text.length>180?scene.text.slice(0,176).trim()+'…':scene.text;
  const titleFont=scene.title.length>35?59:76;
  return <CameraRig path={cameraPath} durationSec={secs}>
    <AbsoluteFill style={{background:pastel,overflow:'hidden',fontFamily:fontStack}}>
      <Plane depth={.55}>
        <AbsoluteFill style={{background:
          'radial-gradient(ellipse at 88% 10%,#e7e0ff 0%,transparent 42%),radial-gradient(ellipse at 4% 90%,#e1f4ff 0%,transparent 42%)'}}/>
      </Plane>
      <Plane depth={1.1}>
        <AbsoluteFill style={{padding:'72px 110px'}}>
          <div style={{color:violet,fontSize:24,fontWeight:800,
            letterSpacing:3,marginBottom:55}}>ARTISYS · OPEN SOURCE EM PORTUGUÊS</div>
          <div style={{maxWidth:1500}}><TextReveal text={scene.title} fontSize={titleFont}/></div>
          <div style={{marginTop:38,marginBottom:52,height:5,width:180,
            background:'#8873f4',borderRadius:5}}/>
          <div style={{fontSize:31,color:'#54627e',lineHeight:1.35,maxWidth:1480,
            opacity:interpolate(frame,[4,20],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}>
            {subtitle}</div>
        </AbsoluteFill>
      </Plane>
      {scene.image&&<Plane depth={1.3}>
        <div style={{position:'absolute',top:520,left:760,width:1060,height:450,
          borderRadius:26,background:'#ffffff',padding:14,
          boxShadow:'0 30px 85px rgba(42,45,89,.13)',overflow:'hidden',
          transform:'translateY('+Math.round(24*Math.sin(frame*.016))+'px)'}}>
          <div style={{fontSize:16,color:'#6f7893',padding:'4px 20px 15px'}}>
            CAPTURA REAL DO REPOSITÓRIO · GITHUB</div>
          <Img src={staticFile(scene.image)} style={{width:'100%',height:'89%',
            objectFit:'cover',objectPosition:'top',borderRadius:15}}/>
        </div>
      </Plane>}
      {!scene.image&&<Plane depth={1.2}><FlowIllustration scene={scene}/></Plane>}
      {cues.map(c=>{
        const rawFrom=Math.round(c.at*fps)-scene.startFrame;
        const from=Math.max(0,Math.min(scene.durationFrames-1,rawFrom));
        const duration=Math.max(1,Math.min(scene.durationFrames-from,Math.round(c.duration*fps)));
        return <Sequence key={c.id} from={from} durationInFrames={duration}>
          <AbsoluteFill style={{background:(c.effect==='scribble_chaos'||c.effect==='paper_overload')?'transparent':'rgba(248,250,255,.94)'}}>
            <Recipe cue={c} scene={scene}/>
          </AbsoluteFill>
        </Sequence>
      })}
    </AbsoluteFill>
  </CameraRig>;
};

const Movie:React.FC=()=>{
  return <AbsoluteFill style={{background:'#f8faff',fontFamily:fontStack}}>
    {movie.scenes.map(scene=><Sequence key={scene.id} from={scene.startFrame}
      durationInFrames={scene.durationFrames} name={scene.id}>
      <SceneView scene={scene}/>
    </Sequence>)}
    <Audio src={staticFile('moneyprint/narration.wav')} />
  </AbsoluteFill>;
};
const Root:React.FC=()=>{
 const dim=movie.aspect==='9:16'?[1080,1920]:movie.aspect==='1:1'?[1080,1080]:[1920,1080];
 return <Composition id="MoneyPrintEdu" component={Movie}
    durationInFrames={movie.totalFrames} fps={movie.fps}
    width={dim[0]} height={dim[1]}/>;
};
registerRoot(Root);
