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
// P1: Five independent illustrated silhouettes, faces and props;
// sceneVariant mirrors the pose without changing a role's identity.
const Persona:React.FC<{id:string;frame:number;fps:number;sceneVariant:number}> =
({id,frame,fps,sceneVariant})=>{
 const rise=natural(frame,10,fps);
 const mirror=sceneVariant%2===0;
 const roleContours:Record<string,React.ReactNode>={
  manager_a:<g>
   <path d="M75 568 L65 395 Q66 331 151 326 L236 356 L290 321 Q389 350 391 423 L410 568Z" fill="#414b5a"/>
   <path d="M162 332 L222 393 L288 332" stroke="#d4d3d0" strokeWidth="20" fill="none"/>
   <path d="M153 209 Q132 105 209 74 Q296 68 309 196 L290 258 Q288 316 227 324 Q156 320 153 253Z" fill="#c0c3c8"/>
   <ellipse cx="231" cy="85" rx="68" ry="63" fill="#2d333f"/>
   <path d="M144 184 Q117 88 179 58 Q233 31 289 103 Q309 134 299 197 L266 152 Q207 195 144 184Z" fill="#323844"/>
   <circle cx="297" cy="58" r="46" fill="#303741"/>
   <path d="M175 222 q15 -11 31 0 M247 222 q15 -9 29 3 M204 277 q22 16 49 0" stroke="#4c545f" strokeWidth="5" fill="none" strokeLinecap="round"/>
   <path d="M290 384 L354 451 L388 427" stroke="#c0c2c6" strokeWidth="24" fill="none" strokeLinecap="round"/>
  </g>,
  seller_b:<g>
   <path d="M47 567 Q50 359 135 342 L197 381 L269 353 Q370 344 390 567Z" fill="#555e6b"/>
   <path d="M151 355 Q223 423 286 358" stroke="#d9d6d2" strokeWidth="19" fill="none"/>
   <ellipse cx="224" cy="218" rx="101" ry="111" fill="#b9bdc3"/>
   <g fill="#343945">
    <circle cx="137" cy="147" r="54"/><circle cx="190" cy="96" r="59"/>
    <circle cx="258" cy="98" r="63"/><circle cx="311" cy="156" r="53"/>
    <circle cx="131" cy="195" r="30"/><circle cx="321" cy="193" r="27"/>
   </g>
   <rect x="141" y="205" width="65" height="41" rx="16" stroke="#515762" strokeWidth="7" fill="none"/>
   <rect x="238" y="205" width="65" height="41" rx="16" stroke="#515762" strokeWidth="7" fill="none"/>
   <path d="M206 224 H238 M193 276 Q224 300 262 272" stroke="#525963" strokeWidth="6" fill="none" strokeLinecap="round"/>
   <path d="M369 448 Q411 379 394 325" stroke="#b9bdc3" strokeWidth="27" fill="none" strokeLinecap="round"/>
   <path d="M390 338 l-5 -53 M392 332 l20 -41" stroke="#b9bdc3" strokeWidth="12" strokeLinecap="round"/>
  </g>,
  support_c:<g>
   <path d="M65 569 L85 394 Q101 337 183 334 L278 331 Q363 359 385 435 L390 569Z" fill="#404b5b"/>
   <path d="M147 390 H320" stroke="#b8c5d1" strokeWidth="11"/>
   <ellipse cx="233" cy="222" rx="91" ry="115" fill="#c4c7c9"/>
   <path d="M130 222 Q124 103 201 103 Q258 66 308 151 L319 231 Q288 185 262 183 Q211 220 130 222Z" fill="#29333e"/>
   <path d="M131 192 C113 91 323 65 335 194" stroke="#5b6773" strokeWidth="14" fill="none"/>
   <rect x="111" y="181" width="35" height="74" rx="14" fill="#394551"/>
   <rect x="319" y="181" width="32" height="74" rx="14" fill="#394551"/>
   <path d="M338 239 Q345 299 265 307" stroke="#65727b" strokeWidth="7" fill="none"/>
   <circle cx="260" cy="306" r="10" fill="#4e5865"/>
   <path d="M171 225 q17 -9 32 2 M252 225 q17 -9 32 2 M204 279 q24 16 53 -3" stroke="#495460" strokeWidth="5" fill="none" strokeLinecap="round"/>
   <path d="M359 429 L419 382" stroke="#c5c7ca" strokeWidth="23" strokeLinecap="round"/>
  </g>,
  planner_d:<g>
   <path d="M52 568 Q69 390 150 355 L291 350 Q372 372 391 568Z" fill="#565966"/>
   <path d="M173 345 L225 414 L275 348" fill="none" stroke="#d4d2d0" strokeWidth="23"/>
   <path d="M128 199 Q117 76 211 67 Q313 64 326 195 L345 364 L295 382 L280 308 L171 307 L154 380 L107 368Z" fill="#343b47"/>
   <ellipse cx="228" cy="213" rx="91" ry="120" fill="#c7c5c4"/>
   <path d="M139 205 Q152 99 231 88 Q292 100 319 193 Q260 184 219 147 Q187 200 139 205Z" fill="#3e424b"/>
   <path d="M176 226 q15 -12 32 0 M248 226 q17 -12 33 0 M204 278 q24 10 46 -2" stroke="#535862" strokeWidth="5" strokeLinecap="round" fill="none"/>
   <rect x="299" y="414" width="136" height="115" rx="13" fill="#e6e4e1" stroke="#7d8190" strokeWidth="6" transform="rotate(-8 299 414)"/>
   <path d="M325 448 H412 M325 464 H396 M325 483 H408" stroke="#939bac" strokeWidth="6"/>
  </g>,
  docs_e:<g>
   <path d="M59 567 Q75 383 167 354 L295 347 Q374 388 384 567Z" fill="#4d5664"/>
   <path d="M166 357 L224 411 L292 354" stroke="#e2ded7" strokeWidth="19" fill="none"/>
   <ellipse cx="227" cy="215" rx="90" ry="121" fill="#c3c5c8"/>
   <path d="M131 202 Q122 105 190 87 Q276 52 320 176 Q283 139 257 153 L203 123 Q178 170 131 202Z" fill="#b9bcc3"/>
   <path d="M137 157 Q176 96 213 108 M251 113 Q291 100 313 156" stroke="#848b95" strokeWidth="23" fill="none"/>
   <rect x="145" y="210" width="77" height="42" rx="12" stroke="#3f4b5b" strokeWidth="8" fill="none"/>
   <rect x="238" y="210" width="77" height="42" rx="12" stroke="#3f4b5b" strokeWidth="8" fill="none"/>
   <path d="M222 227 H238 M202 292 Q235 308 261 288" stroke="#515964" strokeWidth="6" fill="none"/>
   <path d="M299 397 L368 436 L373 568 L288 568Z" fill="#aeb8c1" opacity=".65"/>
   <rect x="266" y="440" width="164" height="115" rx="8" fill="#f1eeeb" stroke="#8993a0" strokeWidth="6" transform="rotate(8 266 440)"/>
   <path d="M298 474 H395 M298 491 H387 M298 508 H405" stroke="#9497a2" strokeWidth="5"/>
  </g>
 };
 return <svg viewBox="0 0 460 570" style={{width:'100%',height:'100%',
   opacity:rise,transform:'translateY('+(25*(1-rise))+'px)'}} aria-label={'Ilustração original: '+id}>
   <g transform={mirror?'translate(460 0) scale(-1 1)':'translate(0 0)'}>
     {roleContours[id]||roleContours.manager_a}
   </g>
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

const SAFE_STAGE={left:160,top:435,right:1760,bottom:970};
const DramaticChaos:React.FC<{frame:number;fps:number}> = ({frame,fps})=>{
 const paths=[
 'M46 208 C85 -65 205 445 240 122 S400 386 466 72',
 'M50 398 C186 20 351 486 480 188 S620 448 720 128',
 'M160 80 C450 480 76 448 364 55 S565 450 684 65',
 'M58 115 C186 355 400 135 525 402 S640 75 746 320',
 'M164 435 C85 175 421 -15 516 298 S698 392 750 56',
 'M31 265 Q388 93 522 430 Q670 95 787 273'
 ];
 // P0: isolated editorial canvas. Scribbles NEVER cross FlowCards or headings.
 const p=natural(frame,10,fps);
 return <div style={{position:'absolute',left:790,top:490,width:905,height:395,
  overflow:'hidden',clipPath:'inset(0 round 32px)',pointerEvents:'none'}}>
  <svg viewBox="0 0 820 530" width="100%" height="100%">
   <path d="M80 75 C290 -30 582 25 728 134 Q868 298 740 427 C520 540 210 501 69 362 Q-25 217 80 75Z"
     fill="#FFF9ED" stroke="#B7A9A1" strokeWidth="4" strokeDasharray="10 12" opacity={p}/>
   {paths.map((path,i)=><path key={i} d={path} fill="none" stroke="#364052"
     strokeWidth={2.8+(i%3)} strokeLinecap="round" strokeLinejoin="round"
     strokeDasharray="1700" strokeDashoffset={1700*(1-natural(frame,24+i*18,fps))} opacity={.75}/>)}
  </svg>
 </div>;
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
const FlowCards:React.FC<{kind:string;frame:number;fps:number;durationFrames?:number}> =
({kind,frame,fps,durationFrames=360})=>{
 const labels=pickLabels(kind);
 const focusIndex=Math.min(2,Math.floor((frame/Math.max(1,durationFrames))*3));
 const beats=[.08,.37,.68].map(f=>Math.round(durationFrames*f));
 return <div style={{position:'absolute',left:SAFE_STAGE.left+70,top:SAFE_STAGE.top+100,
  width:1415,height:310,display:'flex',justifyContent:'space-between',alignItems:'center'}}>
  {labels.map((label,i)=>{
    const p=natural(frame,beats[i],fps);
    const focused=focusIndex===i;
    return <React.Fragment key={label+i}>
      <div style={{flex:1,background:'#FFFAEF',minHeight:254,
       border:focused?'3px solid #A08AC9':'2px solid #DDD4C2',
       borderRadius:25,padding:'27px 27px',
       boxShadow:focused?'0 17px 42px rgba(109,91,146,.18)':'0 12px 25px rgba(59,48,37,.08)',
       opacity:frame<beats[i]?0:p,
       transform:'translateY('+(28*(1-p))+'px) scale('+(focused?1.035:1)+')'}}>
       <div style={{display:'flex',justifyContent:'center',alignItems:'center',
        background:[violet,blue,sage][i],color:'#fff',width:60,height:60,
        borderRadius:19,fontWeight:900,fontSize:31}}>{i+1}</div>
       <div style={{marginTop:32,fontSize:31,fontWeight:900,color:ink}}>{label}</div>
       <div style={{height:6,width:90+i*40,background:[violet,blue,sage][i],
         borderRadius:8,opacity:.4,marginTop:18}}/>
      </div>
      {i<2&&<div style={{width:62,display:'flex',justifyContent:'center',
         alignItems:'center',fontSize:38,color:violet,
         opacity:natural(frame,beats[i+1]-10,fps)}}>→</div>}
    </React.Fragment>;
  })}
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
 const p=natural(frame,10,fps);
 const reveal=natural(frame,Math.round(scene.durationFrames*.30),fps);
 const useApp=Boolean(scene.appImage);
 // P2: real application image takes the majority of the stage after repository proof.
 const repoWidth=useApp? (68-36*reveal)+'%' : '100%';
 const appWidth=useApp? (28+36*reveal)+'%' : '0%';
 return <div style={{position:'absolute',left:SAFE_STAGE.left,top:420,
   right:SAFE_STAGE.left,bottom:80,display:'flex',gap:22,alignItems:'stretch'}}>
  <div style={{width:repoWidth,flexShrink:0,padding:12,
   background:'#FFF9EE',borderRadius:27,border:'2px solid #D9CEBD',
   boxShadow:'0 20px 48px rgba(56,48,44,.14)',overflow:'hidden',
   opacity:p,transform:'translateY('+(32*(1-p))+'px)'}}>
   <div style={{height:46,fontSize:20,fontWeight:900,color:'#75688b',
     padding:'8px 16px'}}>● ● ●　 REPOSITÓRIO REAL · GITHUB</div>
   {scene.image?<Img src={staticFile(scene.image)} style={{width:'100%',height:'91%',
     objectFit:'contain',objectPosition:'top',background:'#151a22',borderRadius:13}}/>:
    <div style={{fontSize:25,fontWeight:800,padding:30,color:ink}}>
      {scene.repoUrl.replace('https://github.com/','')}
      <div style={{fontSize:20,fontWeight:400,marginTop:25}}>
        Captura indisponível. Não substituir por interface inventada.
      </div>
    </div>}
  </div>
  {useApp&&<div style={{width:appWidth,flexShrink:0,padding:12,
    background:'#FFF9EE',borderRadius:27,border:'2px solid #D9CEBD',
    boxShadow:'0 24px 55px rgba(56,48,44,.15)',overflow:'hidden',
    opacity:Math.max(.08,reveal),transform:'translateY('+(38*(1-reveal))+'px)'}}>
    <div style={{height:46,fontSize:20,fontWeight:900,color:'#537969',
      padding:'8px 12px'}}>● ● ●　 INTERFACE AUTÊNTICA · README</div>
    <div style={{height:'90%',width:'100%',overflow:'hidden',borderRadius:12,
       background:'#e7e8eb'}}>
       <Img src={staticFile(scene.appImage||'')} style={{width:'100%',height:'100%',
         objectFit:'contain',objectPosition:'center',
         transform:'scale('+(1+.045*reveal)+')'}}/>
    </div>
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
 const main=scene.direction?.kind??'';
 const sceneVariant=parseInt(scene.id.split('-')[1]||'0',10)%3;
 const sideRight=sceneVariant===0 &&
   !['chaos_thought_cloud','paper_overload_collage'].includes(main);
 const portraitLeft=sideRight?1200:175;
 const bubbleLeft=sideRight?220:750;
 const bubbleLabels=main.includes('support')?['CLIENTE','MENSAGEM','RESPOSTA']:
     main.includes('task')?['TAREFAS','PRAZO','EQUIPE']:
     main.includes('lost_lead')?['CLIENTES','ORÇAMENTO','VENDAS']:
     main.includes('paper')?['CONTRATOS','NOTAS','ARQUIVOS']:
     main.includes('process')?['PESSOAS','PROCESSO','ROTINA']:
     ['SISTEMAS','CLIENTES','GESTÃO'];
 const positions=[490,640,790];
 const beats=[.10,.42,.74].map(f=>Math.round(scene.durationFrames*f));
 return <AbsoluteFill>
   {id&&<div style={{position:'absolute',width:440,height:535,
       left:portraitLeft,top:430,overflow:'hidden',
       filter:'drop-shadow(0 16px 25px rgba(43,37,34,.13))'}}>
       <Persona id={id} frame={frame} fps={fps} sceneVariant={sceneVariant}/>
    </div>}
   {bubbleLabels.map((label,i)=>
      <Bubble key={label+i} text={label} x={bubbleLeft+(i===1?230:0)}
       y={positions[i]} color={['#E8E1F5','#DCECF2','#DFEDDF'][i]}
       frame={frame} at={beats[i]} fps={fps}/>
   )}
   <svg viewBox="0 0 1920 1080" style={{position:'absolute',inset:0,
     width:'100%',height:'100%',pointerEvents:'none'}}>
    <path d={'M'+(sideRight?1190:630)+' 700 Q'+(sideRight?950:750)+' 610 '+(bubbleLeft+100)+' 570'}
      fill="none" stroke="#AFA2B6" strokeWidth="3" strokeDasharray="6 12"
      opacity={.8*natural(frame,beats[0],fps)}/>
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
 const dur=scene.durationFrames/fps;
 const camera=[{t:0,scale:1,x:0,y:0},
               {t:dur*.35,scale:1.012,x:-5,y:-2},
               {t:dur*.72,scale:1.028,x:-13,y:-5},
               {t:dur,scale:1.018,x:-7,y:-3}];
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
      <FlowCards kind={d.kind} frame={frame} fps={fps} durationFrames={scene.durationFrames}/>}
   </Plane>
   {/* Keyword effects are SMALL insets, never opaque full-screen slide changes. */}
   {cues.filter(c=> {
       // P0: native large effects are part of the scene itself.
       // Never layer them over readable labels or authentic screenshots.
       if(['scribble_chaos','paper_overload','crm_orbit'].includes(c.effect)) return false;
       return !isProof && !isOpening && !isChaos && !isPaper && !isOrbit;
     }).slice(0,1).map((cue,i)=>{
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
