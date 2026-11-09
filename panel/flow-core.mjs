/** Pure, dependency-free MoneyPrint graph model. Shared by UI and Node.js tests. */
export const toolCatalog = Object.freeze([
  {id:"goal",label:"Objetivo do vídeo",description:"Assunto, duração e formato",group:"Planejamento",icon:"◎",available:true,required:true},
  {id:"script",label:"Roteiro",description:"Texto livre ou geração assistida",group:"Planejamento",icon:"▤",available:true,required:true},
  {id:"ollama",label:"Ollama / Qwen",description:"Roteiro e termos no modo convencional",group:"Inteligência",icon:"✧",available:true},
  {id:"github",label:"Captura GitHub",description:"Navegação ou capturas de repositórios",group:"Pesquisa e mídia",icon:"⌘",available:true},
  {id:"stock",label:"Wikimedia Commons",description:"Vídeos licenciados e fallback aberto",group:"Pesquisa e mídia",icon:"▣",available:true},
  {id:"slides",label:"Slides animados",description:"Storyboard com mockups e cenas",group:"Motion",icon:"▱",available:true},
  {id:"news",label:"Notícias verificadas",description:"Apenas manchetes reais em RSS",group:"Pesquisa e mídia",icon:"▥",available:true},
  {id:"hook",label:"Gancho de vídeo",description:"Clipe existente em assets/",group:"Motion",icon:"⚡",available:true},
  {id:"motioncanvas",label:"Motion Canvas",description:"Clipe pronto em assets/",group:"Motion",icon:"◇",available:true},
  {id:"captions",label:"Legendas",description:"Legenda gerada pelo pipeline",group:"Áudio",icon:"CC",available:true},
  {id:"piper",label:"Narração Piper",description:"Voz em português no runner",group:"Áudio",icon:"≋",available:true,required:true},
  {id:"render",label:"Render FFmpeg",description:"Montagem e codificação",group:"Saída",icon:"▶",available:true,required:true},
  {id:"final",label:"Vídeo final",description:"Arquivo MP4 para revisão",group:"Saída",icon:"▰",available:true,required:true},
  {id:"qa",label:"QA visual",description:"Workflow separado, sem encadeamento automático",group:"Validação",icon:"✓",available:false},
  {id:"autopublish",label:"Publicação automática",description:"Não integrada — revisão manual obrigatória",group:"Saída",icon:"⊘",available:false},
  {id:"paid_tts",label:"Voz comercial",description:"Provedor pago não ativado",group:"Áudio",icon:"$",available:false}
]);
const byId=Object.fromEntries(toolCatalog.map(x=>[x.id,x]));
const PATH=/^assets\/[A-Za-z0-9_.\/-]{1,160}$/;
const REPO=/^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/?$/;
const ORDER={goal:0,script:1,ollama:2,github:3,stock:3,slides:4,news:5,hook:6,motioncanvas:6,captions:7,piper:8,render:9,final:10};
const presets={
  automatic:["goal","script","ollama","stock","piper","render","final"],
  cinematic:["goal","script","github","slides","piper","render","final"],
  github:["goal","script","ollama","github","piper","render","final"],
  shorts:["goal","script","ollama","stock","captions","piper","render","final"],
  offline:["goal","script","ollama","piper","render","final"],
  stock:["goal","script","ollama","stock","piper","render","final"]
};
export const templates=Object.freeze([
  {id:"automatic",title:"Produção automática",subtitle:"Pesquisa de mídia e narração",icon:"✧"},
  {id:"cinematic",title:"Slides cinematográficos",subtitle:"Repositórios, mockups e motion",icon:"▱"},
  {id:"github",title:"Captura GitHub",subtitle:"Navegação pelos projetos",icon:"⌘"},
  {id:"shorts",title:"Short vertical",subtitle:"Vídeo curto e legendas",icon:"⚡"},
  {id:"offline",title:"Artes locais",subtitle:"Sem busca de vídeos externos",icon:"▣"},
  {id:"stock",title:"Mídia licenciada",subtitle:"Wikimedia Commons, sem API paga",icon:"▥"}
]);
export function makeTemplate(name="automatic"){
  if(!presets[name])throw Error("Template desconhecido");
  const nodes=presets[name].map((tool,i)=>({id:tool,tool,enabled:true,x:54+i*205,y:110+(i%2)*20}));
  const edges=nodes.slice(1).map((node,i)=>({from:nodes[i].id,to:node.id}));
  return {version:1,id:cryptoRandomId(),name:templates.find(x=>x.id===name)?.title||name,nodes,edges,settings:{
    topic:"",duration_seconds:name==="cinematic"?180:40,aspect:["cinematic","github"].includes(name)?"16:9":"9:16",
    script:"",terms:[],repo_urls:[],sections:[],stock_required:name==="stock",hook_asset:"",
    motion_canvas_clip:"",hook_seconds:3,universe_seconds:0,universe_title:"UNIVERSO OPEN SOURCE",transition:"cut"
  }};
}
function cryptoRandomId(){return "flow-"+Math.random().toString(36).slice(2,12)}
export function cloneFlow(flow){return JSON.parse(JSON.stringify(flow))}
export function insertTool(flow,tool){
  if(!byId[tool]?.available)throw Error("Ferramenta indisponível");
  if(flow.nodes.some(x=>x.tool===tool))throw Error("Ferramenta já está no fluxo");
  if(byId[tool].required)throw Error("Etapa obrigatória já pertence ao fluxo");
  const f=cloneFlow(flow);
  const at=f.nodes.findIndex(x=>x.tool==="render");
  if(at<1)throw Error("Render ausente");
  const node={id:tool,tool,enabled:true,x:54+at*205,y:110};
  f.nodes.splice(at,0,node);
  f.edges=f.nodes.slice(1).map((n,i)=>({from:f.nodes[i].id,to:n.id}));
  return f;
}
export function removeTool(flow,id){
  const node=flow.nodes.find(x=>x.id===id);
  if(!node)throw Error("Bloco inexistente");
  if(byId[node.tool]?.required)throw Error("Esta etapa é obrigatória");
  const f=cloneFlow(flow);
  f.nodes=f.nodes.filter(x=>x.id!==id);
  // Collapse a linear chain; explicitly remade connectors stay editable afterwards.
  f.edges=f.nodes.slice(1).map((n,i)=>({from:f.nodes[i].id,to:n.id}));
  return f;
}
export function moveTool(flow,id,delta){
  const f=cloneFlow(flow),i=f.nodes.findIndex(x=>x.id===id);
  if(i<0)throw Error("Bloco inexistente");
  if(byId[f.nodes[i].tool]?.required)throw Error("Etapa obrigatória não pode ser reordenada");
  let position=i+(delta<0?-1:1);
  if(position<=1||position>=f.nodes.findIndex(x=>x.tool==="render"))return f;
  [f.nodes[i],f.nodes[position]]=[f.nodes[position],f.nodes[i]];
  f.edges=f.nodes.slice(1).map((n,j)=>({from:f.nodes[j].id,to:n.id}));
  return f;
}
export function updateNodePosition(flow,id,x,y){
  const f=cloneFlow(flow),node=f.nodes.find(n=>n.id===id);
  if(!node)throw Error("Bloco inexistente");
  node.x=Math.max(12,Math.min(4000,Math.round(x)));
  node.y=Math.max(12,Math.min(3000,Math.round(y)));
  return f;
}
export function connectNodes(flow,from,to){
  const f=cloneFlow(flow);
  if(from===to)throw Error("Não é possível conectar o bloco a si mesmo");
  if(!f.nodes.some(x=>x.id===from)||!f.nodes.some(x=>x.id===to))throw Error("Bloco não encontrado");
  if(f.edges.some(x=>x.from===from&&x.to===to))return f;
  f.edges.push({from,to});
  const report=validateFlow(f);
  if(report.errors.some(x=>/ciclo/i.test(x)))throw Error("Conexão causaria ciclo");
  return f;
}
export function removeEdge(flow,from,to){
  const f=cloneFlow(flow);
  f.edges=f.edges.filter(e=>e.from!==from||e.to!==to);
  return f;
}
export function validateFlow(flow){
  const errors=[];
  if(!flow||typeof flow!=="object"||!Array.isArray(flow.nodes)||!Array.isArray(flow.edges))return {errors:["Fluxo inválido"],warnings:[]};
  const nodes=flow.nodes.filter(x=>x.enabled!==false),ids=new Set(nodes.map(x=>x.id));
  if(ids.size!==nodes.length)errors.push("IDs de blocos repetidos");
  for(const n of nodes)if(!byId[n.tool]?.available)errors.push("Ferramenta indisponível: "+n.tool);
  for(const t of ["goal","script","piper","render","final"])if(!nodes.some(n=>n.tool===t))errors.push("Etapa obrigatória ausente: "+(byId[t]?.label||t));
  const edges=flow.edges.filter(x=>ids.has(x.from)&&ids.has(x.to));
  const map=new Map(nodes.map(n=>[n.id,[]]));
  edges.forEach(e=>map.get(e.from).push(e.to));
  const gray=new Set(),black=new Set();
  function cycle(id){if(gray.has(id))return true;if(black.has(id))return false;gray.add(id);for(const next of map.get(id)||[])if(cycle(next))return true;gray.delete(id);black.add(id);return false}
  if(nodes.some(n=>cycle(n.id)))errors.push("O fluxo contém um ciclo");
  const start=nodes.find(n=>n.tool==="goal");
  const end=nodes.find(n=>n.tool==="final");
  if(start&&end){
    const reachable=(source,graph)=>{const visited=new Set([source]),stack=[source];while(stack.length){for(const next of graph.get(stack.pop())||[])if(!visited.has(next)){visited.add(next);stack.push(next)}}return visited};
    const visited=reachable(start.id,map);
    const reverse=new Map(nodes.map(n=>[n.id,[]]));edges.forEach(e=>reverse.get(e.to).push(e.from));
    const toEnd=reachable(end.id,reverse);
    if(!visited.has(end.id))errors.push("Saída desconectada do objetivo");
    for(const n of nodes)if(!visited.has(n.id)||!toEnd.has(n.id))errors.push("Bloco desconectado: "+(byId[n.tool]?.label||n.tool));
  }
  return {errors:[...new Set(errors)],warnings:[]};
}
function asList(input){if(Array.isArray(input))return input.map(x=>String(x).trim()).filter(Boolean);return String(input||"").split(/[,\n]/).map(x=>x.trim()).filter(Boolean)}
function fileAsset(path){return typeof path==="string"&&PATH.test(path)&&!path.split("/").includes("..")&&!path.includes("//")}
export function compileFlow(flow){
  const report=validateFlow(flow);
  if(report.errors.length)throw Error(report.errors[0]);
  const set=new Set(flow.nodes.filter(n=>n.enabled!==false).map(n=>n.tool));
  const s=flow.settings||{};
  const topic=String(s.topic||"").trim();
  if(topic.length<3||topic.length>150)throw Error("Preencha o objetivo do vídeo (3 a 150 caracteres)");
  const cinematic=set.has("slides");
  const github=set.has("github");
  if(cinematic&&!github)throw Error("Slides cinematográficos exigem Captura GitHub");
  if((set.has("hook")||set.has("motioncanvas")||set.has("news"))&&!cinematic)throw Error("Gancho, Motion Canvas e notícias exigem slides cinematográficos");
  const mode=cinematic?"github_cinematic":github?"github":set.has("stock")?"auto":"local";
  if(set.has("ollama")&&cinematic&&!(s.sections||[]).length)throw Error("O modo cinematográfico exige narração por seção");
  const maxDuration=(github||cinematic)?360:90;
  const duration=Number(s.duration_seconds??40);
  if(!Number.isInteger(duration)||duration<15||duration>maxDuration)throw Error("Duração deve estar entre 15 e "+maxDuration+" segundos");
  const aspect=s.aspect||"9:16";
  if(!["9:16","16:9","1:1"].includes(aspect))throw Error("Formato inválido");
  const request={topic,duration_seconds:duration,aspect,visual_mode:mode};
  const script=String(s.script||"").trim();
  if(script.length>(github?9000:2400))throw Error("Roteiro excede limite do motor atual");
  if(script)request.script=script;
  const terms=asList(s.terms);
  if(terms.length>12||terms.some(x=>x.length<2||x.length>70))throw Error("Palavras-chave inválidas (máximo 12)");
  if(terms.length)request.terms=terms;
  if(!cinematic&&!set.has("ollama")&&(!script||!terms.length))throw Error("Sem Ollama, informe o roteiro e as palavras-chave de mídia");
  if(github){
    const repos=asList(s.repo_urls);
    if(repos.length===0||repos.length>12||repos.some(x=>!REPO.test(x)))throw Error("Informe 1 a 12 URLs GitHub válidas");
    request.repo_urls=repos;
    if(cinematic){
      const sections=Array.isArray(s.sections)?s.sections:[];
      if(sections.length!==repos.length)throw Error("Complete as seções e narrações de todos os repositórios");
      request.sections=repos.map((repo,i)=>{
        const sec=sections[i]||{};
        if(sec.repo_url!==repo)throw Error("A ordem das seções deve corresponder às URLs");
        const title=String(sec.title||"").trim(),narration=String(sec.narration||"").trim(),query=String(sec.broll_query||"").trim();
        if(title.length<2||title.length>75||narration.length<15||narration.length>1700||query.length>70)throw Error("Revise título, narração e busca de mídia da seção "+(i+1));
        return {repo_url:repo,title,narration,broll_query:query};
      });
    }
  }
  if(set.has("news"))request.include_verified_news=true;
  if(cinematic){
    const motion={};
    if(set.has("hook")){
      if(!fileAsset(s.hook_asset)||!/\.(mp4|mov|webm)$/i.test(s.hook_asset))throw Error("Gancho precisa de um vídeo existente em assets/");
      motion.hook_asset=s.hook_asset;
      motion.hook_seconds=Number(s.hook_seconds||3);
      if(motion.hook_seconds<.5||motion.hook_seconds>10)throw Error("Gancho deve ter entre 0,5 e 10 segundos");
    }
    if(set.has("motioncanvas")){
      if(!fileAsset(s.motion_canvas_clip)||!/\.(mp4|mov|webm)$/i.test(s.motion_canvas_clip))throw Error("Motion Canvas exige vídeo existente em assets/");
      motion.motion_canvas_clip=s.motion_canvas_clip;
    }
    if(Number(s.universe_seconds||0)>0){
      motion.universe_seconds=Number(s.universe_seconds);
      motion.universe_title=String(s.universe_title||"UNIVERSO OPEN SOURCE").slice(0,100);
    }
    if(s.transition)motion.transition=s.transition;
    if(Object.keys(motion).length)request.motion=motion;
  }
  if(set.has("stock")&&!github&&s.stock_required)request.visual_mode="stock";
  return request;
}
