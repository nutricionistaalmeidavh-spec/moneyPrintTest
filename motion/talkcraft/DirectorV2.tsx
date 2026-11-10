/**
 * MoneyPrint Director V2 — warm paper, editorial collage, proof-first software.
 * Owned by MoneyPrint; original Talkcraft camera and recipe components are
 * imported from the separately pinned noncommercial upstream runtime.
 * Never present a fabricated interface as a screenshot.
 */
import React from 'react';
import {
  AbsoluteFill, Img, Sequence, spring, interpolate, staticFile,
  useCurrentFrame, useVideoConfig
} from 'remotion';
import {CameraRig, Plane} from '../../../template/motion-systems/camera';
import {PencilDraw} from '../../../template/components/pencil';
import {card as OrbitCard} from '../cards/gen/orbit-drift';
import {card as ChatCard} from '../cards/gen/chat-message-flow';
import {card as StepCard} from '../cards/gen/numbered-step-stack';
import {card as PaperFanCard} from '../cards/gen/stack-fan-out';

type Direction={
  composition:string;kind:string;palette:string;portrait?:string|null;
  role?:string|null;effect:string;media_mode:string;headline:string;
  narrative_focus:string;protected_typography:boolean;
  connectors_avoid_labels:boolean;
  beats?:{at_s:number;action:string;layer:string}[];
};
type Scene={
  id:string;title:string;text:string;eyebrow:string;repoUrl:string;
  image:string;appImage?:string;direction?:Direction;
  startFrame:number;durationFrames:number;
};
type Cue={id:string;scene_id:string;word:string;effect:string;
  recipe:string;at:number;duration:number;method:string};
type Props={scene:Scene;cues:Cue[]};

const paper='#F6EEDB',ink='#253143',violet='#7964BC',sage='#86AC96',blue='#80A8BC';
const sans='"Lato","Inter","DejaVu Sans","Arial",sans-serif';
function natural(frame:number,at:number,fps:number){
 return frame < at ? 0 : spring({frame:frame-at,fps,config:{damping:24,stiffness:132,mass:.8}});
}
const Gr:React.FC<{children:React.ReactNode;style?:React.CSSProperties}> = ({children,style})=>
  <div style={{...style,fontFamily:sans}}>{children}</div>;

const PaperBackdrop:React.FC=()=>(
 <AbsoluteFill style={{background:paper,backgroundImage:
  'radial-gradient(ellipse at 86% 7%,rgba(180,160,222,.19),transparent 34%),'+
  'radial-gradient(ellipse at 0% 98%,rgba(132,171,168,.16),transparent 39%),'+
  'repeating-linear-gradient(0deg,rgba(111,99,85,.025) 0px,rgba(111,99,85,.025) 1px,transparent 1px,transparent 34px)'}}/>
);

// Five distinctly drawn editorial B/W portraits. Original illustrations:
// no licensed stock image, no re-use of the same silhouette for every role.
const Persona:React.FC<{id:string;frame:number;fps:number}> = ({id,frame,fps})=>{
 const variant={manager_a:0,seller_b:1,support_c:2,planner_d:3,docs_e:4}[id as
 "manager_a"|"seller_b"|"support_c"|"planner_d"|"docs_e"]??0;
 const rise=natural(frame,8,fps);
 const hair=[
  <><path d="M96 166 Q72 78 137 49 Q210 11 268 67 Q298 109 284 187 Q259 132 223 119 Q161 165 96 166Z" fill="#242b34"/><ellipse cx="269" cy="72" rx="35" ry="40" fill="#303842"/></>,
  <path d="M94 148 Q81 71 154 58 Q240 27 281 81 L270 142 Q208 123 165 130 Q135 132 94 148Z" fill="#222936"/>,
  <><path d="M86 162 Q74 90 132 59 Q212 19 273 75 L294 166 Q254 136 227 112 Q178 149 86 162Z" fill="#333a45"/><path d="M80 174 Q57 85 159 46" stroke="#20262f" strokeWidth="20" fill="none"/></>,
  <><path d="M78 148 C85 20 288 14 291 139" fill="none" stroke="#303842" strokeWidth="55" strokeDasharray="15 5" strokeLinecap="round"/><path d="M87 149 Q75 66 136 51 Q220 19 279 97 L273 143Z" fill="#3d424d"/></>,
  <><path d="M96 154 Q77 65 164 53 Q248 26 283 117 L275 162 Q210 126 96 154Z" fill="#343944"/><path d="M94 111 Q134 79 187 81" stroke="#51555f" strokeWidth="16" fill="none"/></>
 ][variant];
 const attire=[
  <><path d="M72 334 L168 290 L193 361 L219 290 L312 333 L352 513 L34 513Z" fill="#3a414c"/><path d="M157 303 L193 385 L232 301" fill="none" stroke="#c7c8c9" strokeWidth="22"/></>,
  <><path d="M45 350 Q100 304 176 302 L204 373 L237 308 Q309 314 360 361 L364 513 L38 513Z" fill="#525963"/><path d="M173 305 L205 389 L228 309" stroke="#d5d6d8" strokeWidth="17" fill="none"/></>,
  <><path d="M56 338 Q147 298 228 300 Q314 303 352 363 L369 513 L35 513Z" fill="#424b57"/><path d="M112 324 L202 414 L285 323" stroke="#bcc3cb" strokeWidth="17" fill="none"/></>,
  <><path d="M40 341 Q136 287 228 308 Q302 308 352 356 L367 515 L34 515Z" fill="#494e5a"/><path d="M137 310 L196 395 L255 310" stroke="#cfd1d5" strokeWidth="15" fill="none"/></>,
  <><path d="M48 342 Q154 283 239 311 L352 351 L361 514 L39 514Z" fill="#515765"/><path d="M145 311 L205 390 L263 310" stroke="#dddfe2" strokeWidth="19" fill="none"/></>
 ][variant];
 return <svg viewBox="0 0 400 520" style={{width:'100%',height:'100%',
   opacity:rise,transform:'translateY('+(45*(1-rise))+'px)'}}>
   <defs>
    <linearGradient id={'face'+variant} x1="0" y1="0" x2="1" y2="1">
     <stop stopColor="#d3d4d6"/><stop offset="1" stopColor="#828993"/>
    </linearGradient>
    <filter id={'shadow'+variant}><feGaussianBlur stdDeviation="8"/></filter>
   </defs>
   <ellipse cx="199" cy="507" rx="145" ry="15" fill="#6f7780" opacity=".25"
      filter={'url(#shadow'+variant+')'}/>
   {attire}
   <path d="M159 256 L165 322 Q205 340 244 312 L237 255Z" fill="#a6abb1"/>
   <ellipse cx="202" cy="168" rx="104" ry="124" fill={'url(#face'+variant+')'}/>
   <path d="M100 187 Q106 245 156 267 Q195 295 247 262 Q283 236 286 174" fill="none" stroke="#7a808b" strokeWidth="4" opacity=".45"/>
   {hair}
   <path d="M149 168 Q168 161 184 169 M223 169 Q242 163 260 169" stroke="#4c515a" strokeWidth="5" fill="none" strokeLinecap="round"/>
   <path d="M196 175 Q183 202 197 209" stroke="#777d87" strokeWidth="4" fill="none"/>
   <path d="M175 232 Q200 245 226 229" fill="none" stroke="#656b75" strokeWidth="4" strokeLinecap="round"/>
   {variant===2&&<g><path d="M98 160 Q83 59 206 55 Q328 80 305 188" stroke="#343943" strokeWidth="13" fill="none"/><rect x="73" y="153" width="30" height="72" rx="14" fill="#444b55"/><rect x="295" y="154" width="25" height="71" rx="11" fill="#444b55"/><path d="M302 222 Q301 263 248 260" stroke="#444b55" strokeWidth="6" fill="none"/></g>}
   {variant===4&&<g><rect x="124" y="165" width="69" height="39" rx="11" fill="none" stroke="#353a43" strokeWidth="8"/><rect x="211" y="165" width="69" height="39" rx="11" fill="none" stroke="#353a43" strokeWidth="8"/><path d="M193 178 H211" stroke="#353a43" strokeWidth="6"/></g>}
   <path d="M43 513 L354 513" stroke="#2e333d" strokeWidth="2"/>
 </svg>;
};

const Bubble:React.FC<{text:string;x:number;y:number;color?:string;frame:number;at:number;fps:number}> =
 ({text,x,y,color='#fff7ee',frame,at,fps})=>{
 const p=natural(frame,at,fps);
 return <div style={{position:'absolute',left:x,top:y,minWidth:144,maxWidth:270,
  background:color,padding:'17px 22px',borderRadius:25,border:'1px solid rgba(73,60,65,.12)',
  boxShadow:'0 14px 30px rgba(77,61,42,.10)',fontSize:27,fontWeight:800,color:ink,
  opacity:p,transform:'translateY('+(29*(1-p))+'px) scale('+(.83+.17*p)+')'}}>{text}</div>;
};

const DramaticChaos:React.FC<{frame:number;fps:number}> = ({frame,fps})=>{
 const paths=[
 'M46 208 C85 -65 205 445 240 122 S400 386 466 72',
 'M50 398 C186 20 351 486 480 188 S620 448 720 128',
 'M160 80 C450 480 76 448 364 55 S565 450 684 65',
 'M58 115 C186 355 400 135 525 402 S640 75 746 320',
 'M164 435 C85 175 421 -15 516 298 S698 392 750 56',
 'M31 265 Q388 93 522 430 Q670 95 787 273',
 'M100 54 Q254 350 430 98 T761 416',
 'M16 350 Q220 458 370 80 T710 220',
 'M95 432 C510 190 490 510 755 248',
 'M206 49 C250 230 750 210 601 400'
 ];
 const p=natural(frame,9,fps);
 return <AbsoluteFill style={{pointerEvents:'none'}}>
  <svg viewBox="0 0 820 530" style={{position:'absolute',left:700,top:432,width:1030,height:580}}>
   <path d="M80 75 C290 -30 582 25 728 134 Q868 298 740 427 C520 540 210 501 69 362 Q-25 217 80 75Z"
      fill="#FFF9ED" stroke="#2B303B" strokeWidth="4" strokeDasharray="10 12" opacity={p*.94}/>
   {paths.map((path,i)=><path key={i} d={path} fill="none" stroke="#242b39"
       strokeWidth={3.5+(i%4)} strokeLinecap="round" strokeLinejoin="round"
       strokeDasharray="1700" strokeDashoffset={1700*(1-natural(frame,15+i*5,fps))}/>)}
   {['?','!','?!','↗','↘','↖','○'].map((char,i)=><text key={char+i}
      x={70+(i*101)%690} y={70+(i*79)%380} fontSize={38+(i%3)*12}
      fontWeight="900" fill="#393341" opacity={natural(frame,24+i*4,fps)}>{char}</text>)}
  </svg>
 </AbsoluteFill>;
};

function pickLabels(kind:string):string[]{
 const table:Record<string,string[]>={
 order_flow:['PEDIDO','ESTOQUE','FINANCEIRO'],
 crm_orbit_explainer:['CONTATO','PROPOSTA','VENDA'],
 sales_funnel:['CONTATO','PROPOSTA','VENDA'],
 customer_support_flow:['CLIENTE','EQUIPE','RESPOSTA'],
 channels_caveat:['SISTEMA','INTEGRAÇÃO','CANAL'],
 kanban_movement:['A FAZER','EM CURSO','CONCLUÍDO'],
 pdf_search_flow:['PDF','OCR','BUSCA'],
 privacy_security:['ACESSOS','BACKUP','PROTEÇÃO'],
 before_after_erp:['PLANILHAS','PROCESSOS','GESTÃO'],
 free_not_costless:['CÓDIGO','HOSPEDAGEM','MANUTENÇÃO']
 };
 return table[kind]??['INFORMAÇÃO','PROCESSO','RESULTADO'];
}
const FlowCards:React.FC<{kind:string;frame:number;fps:number}> = ({kind,frame,fps})=>{
 const labels=pickLabels(kind);
 return <div style={{position:'absolute',left:265,top:540,width:1405,
   display:'flex',justifyContent:'space-between',alignItems:'center'}}>
  {labels.map((label,i)=><React.Fragment key={label+i}>
    <div style={{flex:1,background:'#FFFAEF',minHeight:270,
      border:'2px solid #DDD4C2',borderRadius:25,padding:'30px 31px',
      boxShadow:'0 18px 35px rgba(59,48,37,.08)',
      opacity:natural(frame,12+i*16,fps),
      transform:'translateY('+(36*(1-natural(frame,12+i*16,fps)))+'px)'}}>
      <div style={{display:'flex',justifyContent:'center',alignItems:'center',
        background:[violet,blue,sage][i],color:'#fff',width:60,height:60,
        borderRadius:19,fontWeight:900,fontSize:32}}>{i+1}</div>
      <div style={{marginTop:37,fontSize:32,fontWeight:900,color:ink}}>{label}</div>
      <div style={{height:7,width:100+i*40,background:[violet,blue,sage][i],
        borderRadius:8,opacity:.35,marginTop:22}}/>
    </div>
    {i<2&&<div style={{width:68,display:'flex',justifyContent:'center',alignItems:'center',
       fontSize:40,color:violet,opacity:natural(frame,25+i*16,fps)}}>→</div>}
  </React.Fragment>)}
 </div>;
};

const OpeningVisual:React.FC<{frame:number;fps:number}> = ({frame,fps})=>{
 const tools=[
  ['ERPNext',180,125,'#E3D9F3'],['Twenty',1160,105,'#D3E7EA'],
  ['Chatwoot',1350,530,'#D6EAD9'],['Plane',270,575,'#DCE6F6'],
  ['Paperless',960,640,'#F0E1D1']
 ] as const;
 return <div style={{position:'absolute',left:180,top:390,right:180,bottom:75}}>
  <div style={{position:'absolute',left:560,top:140,width:440,height:385,
   display:'flex',justifyContent:'center',alignItems:'center',borderRadius:55,
   background:'#FFFAF1',border:'3px solid #E0D2BE',
   boxShadow:'0 26px 55px rgba(79,65,56,.12)',
   opacity:natural(frame,4,fps),
   transform:'scale('+(.85+.15*natural(frame,4,fps))+')'}}>
   <div style={{textAlign:'center'}}>
    <div style={{fontSize:215,fontWeight:900,color:violet,lineHeight:.9}}>5</div>
    <div style={{fontSize:27,color:ink,fontWeight:900,letterSpacing:1.3}}>SISTEMAS REAIS</div>
    <div style={{fontSize:18,color:'#77818c',marginTop:10}}>CÓDIGO ABERTO · GITHUB</div>
   </div>
  </div>
  {tools.map(([name,x,y,col],i)=>{
    const p=natural(frame,14+i*9,fps);
    return <div key={name} style={{position:'absolute',left:x,top:y,
      minWidth:203,padding:'21px 27px',borderRadius:38,
      border:'2px solid #E2D5C7',background:col,
      color:ink,fontSize:27,fontWeight:900,textAlign:'center',
      opacity:p,transform:'translateY('+(35*(1-p))+'px) scale('+(.92+.08*p)+')'}}>
      {name}
    </div>;
  })}
 </div>;
};

const FiveMap:React.FC<{frame:number;fps:number}> = ({frame,fps})=>{
 const data=[['ERPNext','#d9d2f4',250,130],['Twenty CRM','#d4ebed',1030,110],
 ['Chatwoot','#dce9da',1450,300],['Plane','#d5e4f4',360,570],
 ['Paperless','#e6dcf0',1290,625]];
 return <div style={{position:'absolute',left:170,top:360,width:1580,height:620}}>
   <svg style={{position:'absolute',width:'100%',height:'100%'}} viewBox="0 0 1580 620">
    {data.map((x,i)=><line key={i} x1="790" y1="290" x2={Number(x[2])}
      y2={Number(x[3])} stroke="#A59A8C" strokeWidth="4"
      strokeDasharray="8 12" opacity={natural(frame,18+i*8,fps)}/>)}
   </svg>
   <div style={{position:'absolute',left:650,top:190,width:280,height:200,
     borderRadius:100,background:'#FFF8EC',border:'2px solid #D5C9BA',
     display:'flex',alignItems:'center',justifyContent:'center',fontSize:35,
     fontWeight:900,color:ink,zIndex:3}}>EMPRESA</div>
   {data.map(([label,color,x,y],i)=><div key={label} style={{
    position:'absolute',left:Number(x)-122,top:Number(y)-45,width:244,height:94,
    borderRadius:45,background:String(color),display:'flex',alignItems:'center',
    justifyContent:'center',fontSize:29,fontWeight:800,color:ink,zIndex:4,
    border:'2px solid #eee8da',
    opacity:natural(frame,12+i*11,fps),
    transform:'scale('+(.8+.2*natural(frame,12+i*11,fps))+')'}}>{label}</div>)}
 </div>;
};

const RepoProof:React.FC<{scene:Scene;frame:number;fps:number}> = ({scene,frame,fps})=>{
 const p=natural(frame,13,fps),q=natural(frame,34,fps);
 return <div style={{position:'absolute',left:180,top:430,right:170,bottom:85,display:'flex',gap:24}}>
  <div style={{width:scene.appImage?'54%':'100%',height:'100%',padding:12,
    background:'#FFF9EE',borderRadius:27,border:'2px solid #D9CEBD',
    boxShadow:'0 24px 55px rgba(56,48,44,.15)',
    overflow:'hidden',opacity:p,transform:'translateY('+(45*(1-p))+'px)'}}>
    <div style={{height:48,fontSize:22,fontWeight:900,color:'#75688b',padding:'8px 18px',
      display:'flex',gap:12,alignItems:'center'}}>● ● ●　 REPOSITÓRIO · GITHUB</div>
    {scene.image?<Img src={staticFile(scene.image)} style={{width:'100%',height:'91%',
      objectFit:'cover',objectPosition:'top',borderRadius:13}}/>:
      <div style={{fontSize:27,fontWeight:800,padding:30,color:ink}}>
        {scene.repoUrl.replace('https://github.com/','')}<div style={{fontSize:20,
          fontWeight:400,marginTop:25}}>Captura real indisponível. Não é uma interface simulada.</div>
      </div>}
  </div>
  {scene.appImage&&<div style={{width:'46%',height:'100%',padding:12,
      background:'#FFF9EE',borderRadius:27,border:'2px solid #D9CEBD',
      boxShadow:'0 24px 55px rgba(56,48,44,.15)',overflow:'hidden',
      opacity:q,transform:'translateY('+(60*(1-q))+'px)'}}>
      <div style={{height:48,fontSize:22,fontWeight:900,color:'#537969',padding:'8px 15px'}}>
       ● ● ●　 CAPTURA DE INTERFACE DO README</div>
      <Img src={staticFile(scene.appImage)} style={{width:'100%',height:'91%',
        objectFit:'contain',background:'#fff',borderRadius:12}}/>
    </div>}
 </div>;
};

const PaperFan:React.FC<{frame:number;fps:number}> = ({frame,fps})=>{
 const Card=PaperFanCard.component;
 const rise=natural(frame,20,fps);
 return <div style={{position:'absolute',top:435,left:650,width:1050,height:530,
  opacity:rise,transform:'translateY('+(45*(1-rise))+'px)',
  borderRadius:24,overflow:'hidden',mixBlendMode:'multiply'}}>
   <Card title="" src1={staticFile('moneyprint/paper_1.svg')}
     src2={staticFile('moneyprint/paper_2.svg')}
     src3={staticFile('moneyprint/paper_3.svg')}
     src4={staticFile('moneyprint/paper_4.svg')}
     src5={staticFile('moneyprint/paper_5.svg')}/>
  </div>;
};

const Orbit:React.FC<{frame:number;fps:number}> = ({frame,fps})=>{
 const Card=OrbitCard.component;
 const p=natural(frame,20,fps);
 return <div style={{position:'absolute',left:730,top:430,width:840,height:475,
  borderRadius:28,overflow:'hidden',boxShadow:'0 25px 60px rgba(63,55,68,.12)',
  opacity:p,transform:'scale('+(.9+.1*p)+')'}}>
  <Card appName="CRM" barTitle="Clientes e oportunidades" chip="ILUSTRAÇÃO DIDÁTICA"
    detailTitle="Relacionamento comercial" detailMeta="Conceito" kv1="Contato|Organizado"
    kv2="Vendas|Acompanhadas" ink="#2b504a"/>
 </div>;
};

const InfoCollage:React.FC<{scene:Scene;frame:number;fps:number}> = ({scene,frame,fps})=>{
 const id=scene.direction?.portrait;
 const labels=pickLabels(scene.direction?.kind||'');
 const main=scene.direction?.kind??'';
 const bubbleLabels=main.includes('support')?['CLIENTE','MENSAGEM','RESPOSTA']:
     main.includes('task')?['TAREFAS','PRAZO','EQUIPE']:
     main.includes('lost_lead')?['CLIENTES','ORÇAMENTO','VENDAS']:
     main.includes('paper')?['CONTRATOS','NOTAS','ARQUIVOS']:
     ['SISTEMAS','CLIENTES','GESTÃO'];
 return <AbsoluteFill>
   {id&&<div style={{position:'absolute',width:440,height:550,left:180,top:430,
       filter:'drop-shadow(0 16px 25px rgba(43,37,34,.13))'}}>
       <Persona id={id} frame={frame} fps={fps}/>
    </div>}
   <Bubble text={bubbleLabels[0]} x={730} y={485} color="#E8E1F5" frame={frame} at={16} fps={fps}/>
   <Bubble text={bubbleLabels[1]} x={1110} y={600} color="#DCECF2" frame={frame} at={35} fps={fps}/>
   <Bubble text={bubbleLabels[2]} x={810} y={815} color="#DFEDDF" frame={frame} at={50} fps={fps}/>
   <svg viewBox="0 0 1920 1080" style={{position:'absolute',inset:0,width:'100%',height:'100%',pointerEvents:'none'}}>
    <path d="M610 710 Q730 620 850 570" fill="none" stroke="#9A8CAC" strokeWidth="4" strokeDasharray="8 10"/>
    <path d="M620 760 Q865 895 1110 680" fill="none" stroke="#9A8CAC" strokeWidth="4" strokeDasharray="8 10"/>
   </svg>
 </AbsoluteFill>;
};

const CueInsert:React.FC<{cue:Cue}> = ({cue})=>{
 const frame=useCurrentFrame(),{fps}=useVideoConfig();
 const p=natural(frame,0,fps);
 if(cue.effect==='scribble_chaos'){
   return <div style={{position:'absolute',top:520,left:680,width:1050,height:480,
     pointerEvents:'none',opacity:p}}>
     <svg viewBox="0 0 780 420" style={{width:'100%',height:'100%'}}>
      <path d="M90 180 C210 -30 300 500 400 140 S700 450 740 80"
        fill="none" stroke="#32313D" strokeWidth="9"/>
     </svg>
   </div>;
 }
 if(cue.effect==='paper_overload')return <PaperFan frame={frame} fps={fps}/>;
 if(cue.effect==='crm_orbit')return <Orbit frame={frame} fps={fps}/>;
 const Card=cue.effect==='support_chat'?ChatCard.component:StepCard.component;
 const props:any=cue.effect==='support_chat'?
   {contactName:'Equipe',contactSub:'Atendimento ilustrativo',avatarChar:'E',
     messages:'them|Olá, preciso de ajuda.\nme|Como posso ajudar?\nthem|Obrigado!',
     ink:'#405867',themBg:'#E7EFEF'}:
   {stepsDsl:cue.effect==='sales_flow'?
      '01|Cliente\n02|Proposta\n03|Venda':
      '01|Entrada\n02|Organização\n03|Resultado',noColor:'#7964BC'};
 return <div style={{position:'absolute',left:760,top:458,width:820,height:475,
    borderRadius:27,overflow:'hidden',boxShadow:'0 23px 45px #5a463326',
    opacity:p}}>
    <Card {...props}/>
  </div>;
};

export const DirectorV2:React.FC<Props>=({scene,cues})=>{
 const frame=useCurrentFrame(),{fps}=useVideoConfig();
 const d=scene.direction!;
 const title=d.headline || scene.title;
 const camera=[{t:0,scale:1,x:0,y:0},
               {t:scene.durationFrames/fps,scale:1.025,x:-10,y:-4}];
 const intro=natural(frame,2,fps);
 // Only a short readable editorial caption is displayed; Piper narrates every
 // original word. Never show a paragraph clipped in the middle of a line.
 const sentence=scene.text.split(/[.!?]/)[0].trim();
 const subtitle=sentence.length<=104?sentence:
   sentence.slice(0,100).replace(/\s+\S*$/,'').trim()+'…';
 const isOpening=d.kind==='opening_burst';
 const isProof=d.media_mode!=='illustration';
 const isChaos=d.kind==='chaos_thought_cloud';
 const isOrbit=d.kind==='crm_orbit_explainer';
 const isPaper=d.kind==='paper_overload_collage';
 const isFive=d.kind==='five_tools_summary'||d.kind==='outro_links';
 const isPortrait=Boolean(d.portrait);
 return <CameraRig path={camera} durationSec={scene.durationFrames/fps}>
  <AbsoluteFill style={{overflow:'hidden',fontFamily:sans,color:ink}}>
   <PaperBackdrop/>
   <Plane depth={.62}>
    <div style={{position:'absolute',left:110,top:52,width:1700,
       color:'#776B85',letterSpacing:3.2,fontSize:20,fontWeight:900}}>
      MONEYPRINT · OPEN SOURCE EM PORTUGUÊS
    </div>
    <div style={{position:'absolute',left:110,top:100,right:110,height:1,background:'#D6C8B6'}}/>
   </Plane>
   <Plane depth={1.0}>
    <div style={{position:'absolute',left:113,top:156,right:95,maxWidth:1650,
      opacity:intro,transform:'translateY('+(25*(1-intro))+'px)'}}>
      <div style={{fontSize:title.length>35?58:69,fontWeight:900,
       lineHeight:1.08,letterSpacing:-1.6,maxWidth:1550}}>
        {title.toUpperCase()}
      </div>
      <div style={{width:190,height:7,background:violet,borderRadius:12,marginTop:23}}/>
      <div style={{fontSize:27,lineHeight:1.35,color:'#5F6470',maxWidth:1540,
         marginTop:25,maxHeight:84,overflow:'hidden'}}>
        {subtitle}
      </div>
    </div>
   </Plane>
   <Plane depth={1.27}>
    {isOpening?<OpeningVisual frame={frame} fps={fps}/>:
      isProof?<RepoProof scene={scene} frame={frame} fps={fps}/>:
      isChaos?<><InfoCollage scene={scene} frame={frame} fps={fps}/>
       <DramaticChaos frame={frame} fps={fps}/></>:
      isOrbit?<><InfoCollage scene={scene} frame={frame} fps={fps}/>
       <Orbit frame={frame} fps={fps}/></>:
      isPaper?<><InfoCollage scene={scene} frame={frame} fps={fps}/>
       <PaperFan frame={frame} fps={fps}/></>:
      isFive?<FiveMap frame={frame} fps={fps}/>:
      isPortrait?<InfoCollage scene={scene} frame={frame} fps={fps}/>:
      <FlowCards kind={d.kind} frame={frame} fps={fps}/>}
   </Plane>
   {/* Keyword effects are SMALL insets, never opaque full-screen slide changes. */}
   {cues.filter(c=>!(['scribble_chaos','paper_overload','crm_orbit'].includes(c.effect)
       && [d.kind].some(k=>k==='chaos_thought_cloud'||k==='paper_overload_collage'||k==='crm_orbit_explainer')))
     .slice(0,2).map((cue,i)=>{
       const from=Math.max(0,Math.round(cue.at*fps)-scene.startFrame);
       if(from>=scene.durationFrames)return null;
       const duration=Math.min(scene.durationFrames-from,Math.max(12,Math.round(cue.duration*fps)));
       return <Sequence key={cue.id} from={from} durationInFrames={duration}>
         <CueInsert cue={cue}/>
       </Sequence>;
   })}
   <div style={{position:'absolute',bottom:35,right:70,color:'#8C857A',
      fontSize:16,fontWeight:900,letterSpacing:2}}>
       {d.composition?.split('-')[0]} · ESTUDO EDUCACIONAL
   </div>
  </AbsoluteFill>
 </CameraRig>;
};
