import {mountStudio} from "./studio-ui.mjs";
import {
  toolCatalog, templates, makeTemplate, compileFlow, validateFlow, insertTool,
  removeTool, moveTool, updateNodePosition, connectNodes, removeEdge, cloneFlow,
  skillCatalog, applySkill, parseSkillManifest
} from "./flow-core.mjs";

const $=id=>document.getElementById(id);
const escapeHtml=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const selectLabel=tool=>toolCatalog.find(x=>x.id===tool)?.label||tool;
let csrf="",authenticated=false,githubConnected=false,flow=makeTemplate("automatic"),selected="goal",zoom=.7,connecting=null,activeTemplate="automatic",savedFlows=[],catalogTab="tools",customSkills=[];
const repo="https://github.com/nutricionistaalmeidavh-spec/moneyPrintTest";
const events={};
let studioModule=null;
function toast(message){$("toast").textContent=message;$("toast").classList.remove("hidden");clearTimeout(events.toast);events.toast=setTimeout(()=>$("toast").classList.add("hidden"),5200)}
async function api(url,method="GET",data){
  const headers={"X-Requested-With":"ArtiSysPanel"};
  if(method!=="GET"){headers["content-type"]="application/json";headers["x-csrf-token"]=csrf}
  const response=await fetch(url,{method,headers,credentials:"same-origin",body:method==="GET"?undefined:JSON.stringify(data||{})});
  const result=await response.json().catch(()=>({}));
  if(!response.ok)throw Error(result.error||"Falha HTTP "+response.status);
  return result;
}
function showAuthenticated(ok){authenticated=ok;$("auth").classList.toggle("hidden",ok);$("application").classList.toggle("hidden",!ok);$("logout").classList.toggle("hidden",!ok);$("mobileBar").classList.toggle("hidden",!ok);$("statusDot").classList.toggle("ok",ok);$("sessionStatus").textContent=ok?"Painel seguro":"Acesso protegido"}
function persist(){try{localStorage.setItem("artisys-flow-draft-v2",JSON.stringify(flow))}catch{}}
function loadDraft(){try{const v=JSON.parse(localStorage.getItem("artisys-flow-draft-v2")||"null");if(v&&v.version===1&&Array.isArray(v.nodes)&&Array.isArray(v.edges)&&v.nodes.length<30){flow=v;activeTemplate=""}}catch{}}
function mobile(){return matchMedia("(max-width:720px)").matches}
function openPanel(panel){
  const visible=panel==="inspector"||(mobile()&&panel==="palette");
  $("palette").classList.toggle("open",visible&&panel==="palette");
  $("inspector").classList.toggle("open",visible&&panel==="inspector");
  $("scrim").classList.toggle("open",visible&&mobile());
  document.body.classList.toggle("sheet-open",visible&&mobile());
  if(visible){
    const inner=$(panel==="palette"?"palette":"inspector").querySelector(".contents");
    if(inner)inner.scrollTop=0;
    requestAnimationFrame(()=>$(panel==="palette"?"searchTools":"closeInspector").focus({preventScroll:true}));
  }
}
function showView(view){
  document.querySelectorAll(".view").forEach(x=>x.classList.toggle("hidden",x.id!=="view-"+view));
  document.querySelectorAll(".topnav [data-view]").forEach(x=>{if(x.dataset.view===view)x.setAttribute("aria-current","page");else x.removeAttribute("aria-current")});
  closePanels();
  if(view==="history")refreshHistory();
  if(view==="connections")updateConnectionStatus();
  if(view==="videos"){if(!studioModule)studioModule=mountStudio({api,toast});studioModule.refresh()}
  else if(studioModule)studioModule.stop();
}
function closePanels(){openPanel(null)}
function syncDom(){
  renderTemplates();renderToolPalette();renderToolShowcase();renderMobileQuick();renderCanvas();renderInspector();renderSummary();persist();
}
function renderTemplates(){
  $("templates").innerHTML=templates.map(t=>'<button class="template '+(t.id===activeTemplate?"selected":"")+'" data-template="'+escapeHtml(t.id)+'" title="'+escapeHtml(t.subtitle)+'"><em>'+escapeHtml(t.icon)+'</em>'+escapeHtml(t.title)+'</button>').join("");
}

function allSkills(){return [...skillCatalog,...customSkills]}
function loadCustomSkills(){
 try{
  const stored=JSON.parse(localStorage.getItem("artisys-custom-skills-v1")||"[]");
  customSkills=Array.isArray(stored)?stored.slice(0,20).map((v,i)=>({...parseSkillManifest(v),id:"custom-"+i,icon:"✳",category:"Personalizadas"})):[];
 }catch{customSkills=[]}
}
function saveCustomSkills(){
 try{localStorage.setItem("artisys-custom-skills-v1",JSON.stringify(customSkills.map(({name,description,tools})=>({name,description,tools}))))}catch{}
}
function addSkillFromCatalog(id){
 const skill=allSkills().find(x=>x.id===id);if(!skill){toast("Skill não encontrada");return}
 try{
  const updated=applySkill(flow,skill);flow=updated;selected=updated.nodes.some(n=>n.tool==="slides")?"slides":updated.nodes.find(n=>n.tool==="hook")?"hook":"goal";
  activeTemplate="";layoutNodes();syncDom();
  toast("Skill aplicada: "+skill.name+". Configure os blocos adicionados antes de executar.");
  if(mobile())openPanel("inspector");
 }catch(e){toast(e.message)}
}
function resourceCard(x,isSkill){
 const used=isSkill?x.tools.every(id=>flow.nodes.some(n=>n.tool===id)):flow.nodes.some(n=>n.tool===x.id);
 const disabled=isSkill?false:!x.available||used||x.required;
 const action=isSkill?'data-apply-skill="'+escapeHtml(x.id)+'"':'data-add="'+escapeHtml(x.id)+'"';
 return '<article class="showcase-card '+(!isSkill&&!x.available?"unavailable":"")+'">'+
   '<span class="showcase-ico">'+escapeHtml(x.icon||"✳")+'</span><div class="showcase-copy"><strong>'+escapeHtml(isSkill?x.name:x.label)+'</strong>'+
   '<p>'+escapeHtml(x.description||"")+'</p></div><button type="button" '+action+' '+(disabled?"disabled":"")+' aria-label="'+escapeHtml((isSkill?"Aplicar Skill ":"Adicionar ferramenta ")+(isSkill?x.name:x.label))+'" title="'+(used?"Já adicionado":"Adicionar ao fluxo")+'">'+(used?"✓":"+")+'</button></article>'
}
function renderToolShowcase(){
 const q=String($("showcaseSearch").value||"").trim().toLowerCase();
 const items=(catalogTab==="skills"?allSkills():toolCatalog).filter(x=>([x.name,x.label,x.description,x.group,x.category]||[]).join(" ").toLowerCase().includes(q));
 $("showcaseCatalog").innerHTML=items.length?items.map(x=>resourceCard(x,catalogTab==="skills")).join(""):'<p class="empty">Nenhuma ferramenta ou Skill com esse nome</p>';
 $("skillImportBox").classList.toggle("hidden",catalogTab!=="skills");
 document.querySelectorAll("[data-catalog-tab]").forEach(btn=>{
   const active=btn.dataset.catalogTab===catalogTab;
   btn.classList.toggle("active",active);btn.setAttribute("aria-selected",active?"true":"false");
 });
}
function renderMobileQuick(){
 const priority=["github","slides","hook","news"];
 $("quickToolButtons").innerHTML=priority.map(id=>{
  const x=toolCatalog.find(t=>t.id===id);if(!x)return "";
  const used=flow.nodes.some(n=>n.tool===id);
  return '<button type="button" data-quick-tool="'+id+'" '+(used?"disabled":"")+'><b>'+escapeHtml(x.icon)+'</b><span>'+(used?"✓ ":"+ ")+escapeHtml(x.label)+'</span></button>';
 }).join("");
}

function renderToolPalette(){
  const q=$("searchTools").value.toLocaleLowerCase("pt-BR").trim();
  const filtered=toolCatalog.filter(t=>(t.label+" "+t.description+" "+t.group).toLocaleLowerCase("pt-BR").includes(q));
  const groups=[...new Set(filtered.map(t=>t.group))];
  $("toolList").innerHTML=groups.map(group=>'<div class="category">'+escapeHtml(group)+'</div>'+filtered.filter(t=>t.group===group).map(t=>{
    const used=flow.nodes.some(n=>n.tool===t.id);
    const disabled=!t.available||used||t.required;
    return '<div class="tool '+(!t.available?"unavailable":"")+'" '+(!disabled?'draggable="true" data-dragtool="'+escapeHtml(t.id)+'"':"")+'><span class="toolicon">'+escapeHtml(t.icon)+'</span><div style="min-width:0;flex:1"><strong>'+escapeHtml(t.label)+'</strong><p>'+escapeHtml(t.description)+'</p></div><button class="plus" data-add="'+escapeHtml(t.id)+'" aria-label="Adicionar '+escapeHtml(t.label)+'" title="'+(disabled?(used||t.required?"Já está no fluxo":"Integração não disponível"):"Adicionar ao fluxo")+'" '+(disabled?"disabled":"")+'>+</button></div>'
  }).join("")).join("")||'<p class="empty">Nenhuma ferramenta encontrada</p>';
  const skills=allSkills().filter(x=>(x.name+" "+x.description+" "+x.category).toLowerCase().includes(q));
  $("skillsList").innerHTML=skills.map(x=>'<div class="tool"><span class="toolicon">'+escapeHtml(x.icon||"✳")+'</span><div style="min-width:0;flex:1"><strong>'+escapeHtml(x.name)+'</strong><p>'+escapeHtml(x.description)+'</p></div><button class="plus" type="button" data-apply-skill="'+escapeHtml(x.id)+'" aria-label="Adicionar skill '+escapeHtml(x.name)+'">+</button></div>').join("")||'<p class="empty">Nenhuma Skill encontrada</p>';
}
function layoutNodes(){
  const positions={goal:[32,260],script:[242,260],ollama:[452,260],github:[452,60],stock:[452,485],slides:[665,80],news:[890,50],hook:[895,180],motioncanvas:[895,260],captions:[1080,500],piper:[890,475],render:[1190,270],final:[1450,270]};
  const taken={};
  flow.nodes.forEach((node,i)=>{
    const base=positions[node.tool]||[200+i*200,250];
    const key=base.join(",");const count=taken[key]||0;taken[key]=count+1;
    node.x=base[0]+count*160;node.y=base[1]+count*120;
  });
}
function renderCanvas(){
  const box=$("canvasNodes");
  box.innerHTML=flow.nodes.map(n=>{
    const entry=toolCatalog.find(t=>t.id===n.tool)||{icon:"?",label:n.tool,description:""};
    return '<article class="block '+(selected===n.id?"selected ":"")+(connecting===n.id?"focus-source":"")+'" data-node="'+escapeHtml(n.id)+'" data-tool="'+escapeHtml(n.tool)+'" style="left:'+Number(n.x||0)+'px;top:'+Number(n.y||0)+'px" role="group" aria-label="'+escapeHtml(entry.label)+'">'+
      '<div class="head"><span class="node-ico">'+escapeHtml(entry.icon)+'</span><strong>'+escapeHtml(entry.label)+'</strong><button class="drag" type="button" aria-label="Arrastar bloco" title="Arrastar bloco">⠿</button></div>'+
      '<p>'+escapeHtml(entry.description)+'</p><div class="tools"><button data-edit="'+escapeHtml(n.id)+'">Editar</button><button data-remove="'+escapeHtml(n.id)+'" '+(entry.required?"disabled":"")+' aria-label="Remover bloco">×</button></div>'+
      '<div class="ports"><button class="port in" data-portin="'+escapeHtml(n.id)+'" aria-label="Conectar entrada de '+escapeHtml(entry.label)+'"></button><button class="port out" data-portout="'+escapeHtml(n.id)+'" aria-label="Conectar saída de '+escapeHtml(entry.label)+'"></button></div>'+
      '</article>';
  }).join("");
  const mx=Math.max(1200,...flow.nodes.map(n=>n.x+240));
  const my=Math.max(560,...flow.nodes.map(n=>n.y+180));
  $("scene").style.width=mx+"px";$("scene").style.height=my+"px";
  $("wires").setAttribute("width",mx);$("wires").setAttribute("height",my);
  $("scene").style.transform="scale("+zoom+")";
  $("zoomLabel").textContent=Math.round(zoom*100)+"%";
  drawEdges();
  const ms=$("mobileFlow");
  ms.innerHTML=flow.nodes.map((n,i)=>{
    const entry=toolCatalog.find(t=>t.id===n.tool)||{label:n.tool,icon:"?"};
    return (i?'<div class="vertical-wire" aria-hidden="true"></div>':"")+'<div class="mobile-node '+(selected===n.id?"selected":"")+'" data-mobile-node="'+escapeHtml(n.id)+'"><span class="mi">'+escapeHtml(entry.icon)+'</span><div style="min-width:0;flex:1"><strong>'+escapeHtml(entry.label)+'</strong><p>Etapa '+(i+1)+' de '+flow.nodes.length+'</p></div><div class="move"><button data-up="'+escapeHtml(n.id)+'" '+(i<=2||entry.required?"disabled":"")+' aria-label="Subir etapa">↑</button><button data-down="'+escapeHtml(n.id)+'" '+(i>=flow.nodes.length-3||entry.required?"disabled":"")+' aria-label="Descer etapa">↓</button><button data-mobile-edit="'+escapeHtml(n.id)+'" aria-label="Editar etapa">⚙</button></div></div>';
  }).join("");
  $("nodeCount").textContent=flow.nodes.length+" blocos";
}
function drawEdges(){
  const point=id=>{const n=flow.nodes.find(x=>x.id===id);return n?{x:n.x||0,y:n.y||0}:null};
  $("paths").replaceChildren(...flow.edges.flatMap(e=>{
    const from=point(e.from),to=point(e.to);if(!from||!to)return [];
    const a=from.x+176,b=from.y+49,c=to.x,d=to.y+49;
    const mid=Math.max(48,Math.abs(c-a)*.42);
    const dpath='M '+a+' '+b+' C '+(a+mid)+' '+b+', '+(c-mid)+' '+d+', '+c+' '+d;
    const group=document.createElementNS("http://www.w3.org/2000/svg","g");
    const hit=document.createElementNS("http://www.w3.org/2000/svg","path");hit.setAttribute("d",dpath);hit.setAttribute("class","hit");hit.dataset.from=e.from;hit.dataset.to=e.to;
    const wire=document.createElementNS("http://www.w3.org/2000/svg","path");wire.setAttribute("d",dpath);wire.setAttribute("class","wire");
    group.append(hit,wire);return [group];
  }));
}
function descriptor(id){return flow.nodes.find(n=>n.id===id)}
function inputField(id,label,value,help="",type="text",attrs=""){
  return '<div class="field"><label for="'+id+'">'+escapeHtml(label)+'</label><input id="'+id+'" data-setting="'+id.replace("field-","")+'" type="'+type+'" value="'+escapeHtml(value??"")+'" '+attrs+'>'+(help?'<p class="help">'+escapeHtml(help)+'</p>':"")+'</div>';
}
function area(id,label,value,help="",rows=4){
  return '<div class="field"><label for="field-'+id+'">'+escapeHtml(label)+'</label><textarea id="field-'+id+'" data-setting="'+id+'" rows="'+rows+'">'+escapeHtml(value??"")+'</textarea>'+(help?'<p class="help">'+escapeHtml(help)+'</p>':"")+'</div>';
}
function sectionControls(){
  const urls=Array.isArray(flow.settings.repo_urls)?flow.settings.repo_urls:String(flow.settings.repo_urls||"").split("\n").map(x=>x.trim()).filter(Boolean);
  const sections=Array.isArray(flow.settings.sections)?flow.settings.sections:[];
  if(!urls.length)return '<p class="notes">Informe as URLs no bloco Captura GitHub antes de editar as cenas.</p>';
  return urls.map((url,i)=>{
    const sec=sections.find(x=>x.repo_url===url)||{};
    return '<div class="section-editor"><strong>Cena '+(i+1)+' — '+escapeHtml(url.split("/").pop())+'</strong>'+
    '<div class="field"><label>Título da cena</label><input data-section="'+i+'" data-key="title" value="'+escapeHtml(sec.title||"")+'" placeholder="Nome da ferramenta"></div>'+
    '<div class="field"><label>Narração desta cena</label><textarea data-section="'+i+'" data-key="narration" placeholder="Escreva o texto que o Piper irá narrar...">'+escapeHtml(sec.narration||"")+'</textarea></div>'+
    '<div class="field"><label>Busca de vídeo de apoio (opcional)</label><input data-section="'+i+'" data-key="broll_query" value="'+escapeHtml(sec.broll_query||"")+'" placeholder="software developer working"></div></div>';
  }).join("");
}
function renderInspector(){
  const n=descriptor(selected);
  const t=toolCatalog.find(x=>x.id===n?.tool);
  $("inspectorTitle").textContent=t?t.label:"Configurações do fluxo";
  $("inspectorSub").textContent=t?t.description:"Edite os parâmetros da produção";
  const s=flow.settings||{};
  let html="";
  if(!t||t.id==="goal"){
    html='<h3>Objetivo do vídeo</h3>'+
      inputField("field-topic","Assunto / título",s.topic,"Descreva o vídeo; o roteiro pode ser gerado automaticamente")+
      inputField("field-duration_seconds","Duração solicitada (segundos)",s.duration_seconds,"Entre 15 e 90 segundos para vídeos convencionais; até 360 para GitHub","number",'min="15" max="360"')+
      '<div class="field"><label for="field-aspect">Proporção</label><select id="field-aspect" data-setting="aspect">'+["9:16","16:9","1:1"].map(a=>'<option value="'+a+'" '+(s.aspect===a?"selected":"")+'>'+a+'</option>').join("")+'</select></div>'+
      '<p class="notes">Tempo de vídeo é aproximado: a duração final acompanha a narração real.</p>';
  }else if(t.id==="script"){
    html=area("script","Roteiro opcional",s.script,"Em branco: Ollama pode escrever a fala nos modos convencionais",7);
  }else if(t.id==="github"){
    html=area("repo_urls","Repositórios públicos (um por linha)",(s.repo_urls||[]).join("\n"),"Formato: https://github.com/owner/repo. Até 12 URLs.",6)+
       '<p class="notes">O motor captura apenas URLs GitHub públicas. Outras páginas não são executadas.</p>';
  }else if(t.id==="slides"){
    html='<p class="notes">Cada repositório necessita de uma narração própria. As cenas são montadas como slides animados, com screenshots, GIFs e vídeos quando disponíveis.</p>'+sectionControls()+
       '<h3>Motion e transições</h3>'+
       inputField("field-universe_seconds","Abertura universo (segundos)",s.universe_seconds,"0 desativa a abertura","number",'min="0" max="8" step="0.5"')+
       inputField("field-universe_title","Texto da abertura",s.universe_title)+
       '<div class="field"><label for="field-transition">Transição</label><select data-setting="transition" id="field-transition">'+["cut","fade","wipeleft","slideleft","smoothleft","circleopen"].map(x=>'<option value="'+x+'" '+(s.transition===x?"selected":"")+'>'+escapeHtml(x)+"</option>").join("")+'</select></div>';
  }else if(t.id==="stock"){
    html=area("terms","Palavras-chave de mídia (uma por linha)",(s.terms||[]).join("\n"),"Sem lista: Qwen sugere buscas automaticamente nos modos convencionais",5)+
      '<p class="notes">Wikimedia Commons com licença aprovada; indisponibilidade pode resultar em artes locais no modo automático.</p>';
  }else if(t.id==="hook"){
    html=inputField("field-hook_asset","Vídeo existente em assets/",s.hook_asset,"Ex.: assets/approved/hook.mp4. Não faz upload de arquivos.")+
      inputField("field-hook_seconds","Duração do corte (segundos)",s.hook_seconds,"Corte seco por padrão.","number",'min=".5" max="8" step=".5"');
  }else if(t.id==="motioncanvas"){
    html=inputField("field-motion_canvas_clip","Clipe Motion Canvas pronto",s.motion_canvas_clip,"Ex.: assets/animations/intro.mp4. Precisa estar no repositório.");
  }else if(t.id==="news"){
    html='<p class="notes">Notícias só entram quando uma manchete real com fonte e data é encontrada no RSS. Sem resultados válidos, a cena é omitida.</p>';
  }else if(t.id==="ollama"){
    html='<p class="notes">Ollama/Qwen local pode criar o roteiro e as buscas nos modos convencionais. No cinematográfico, a narração de cada cena deve ser preenchida. Sem dependência de API paga.</p>';
  }else if(t.id==="captions"){
    html='<p class="notes">Modo convencional: o MoneyPrinterTurbo usa Whisper local. Modo cinematográfico: o pipeline entrega um SRT com tempos estimados para revisão.</p>';
  }else if(t.id==="piper"){
    html='<p class="notes">Piper pt_BR-faber-medium. O motor baixa o modelo verificado e gera o áudio no runner. A seleção de outra voz ainda não é suportada por este workflow.</p>';
  }else if(t.id==="render"){
    html='<p class="notes">Renderização com FFmpeg/MoneyPrinterTurbo. A montagem ocorre no GitHub Actions ou runner self-hosted. Não publica vídeos automaticamente.</p>';
  }else if(t.id==="final"){
    html='<p class="notes">O MP4 fica disponível como artifact do GitHub Actions para revisão. O painel não faz upload nem publica nas redes sociais.</p>';
  }
  if(t&&t.id!=="goal")html+='<div style="margin-top:16px"><button class="btn subtle" id="editGeneral">Editar configurações gerais</button></div>';
  $("inspectorBody").innerHTML=html;
}
function renderSummary(){
  const validity=validateFlow(flow);
  const status=validity.errors.length?validity.errors[0]:!String(flow.settings.topic||"").trim()?"Defina o objetivo":"Estrutura válida";
  $("flowValidity").className="pill"+(validity.errors.length?" fail":"");
  $("flowValidity").textContent=validity.errors.length?"⚠ Conexões inválidas":"✓ Estrutura válida";
  $("summaryNodes").textContent=flow.nodes.length+" blocos";
  $("summaryVideo").textContent=(flow.settings.duration_seconds||40)+"s • "+(flow.settings.aspect||"9:16");
  $("summaryMode").textContent=flow.nodes.some(n=>n.tool==="slides")?"Slides animados":flow.nodes.some(n=>n.tool==="github")?"Captura GitHub":flow.nodes.some(n=>n.tool==="stock")?"Wikimedia / vídeo":"Artes locais";
  $("summaryValidation").textContent=status;
  $("summaryValidation").className=validity.errors.length?"bad":!String(flow.settings.topic||"").trim()?"warning":"good";
}
function modify(fn,selectedNext){
  try{flow=fn(flow);if(selectedNext!==undefined)selected=selectedNext;activeTemplate="";syncDom()}catch(e){toast(e.message)}
}
function addTool(id){
  try{
    flow=insertTool(flow,id);selected=id;activeTemplate="";layoutNodes();syncDom();
    toast(selectLabel(id)+" adicionado ao fluxo");
    if(mobile())openPanel("inspector");
  }catch(e){toast(e.message)}
}
function updateSettings(id,value){
  if(id==="duration_seconds"||id==="hook_seconds"||id==="universe_seconds")value=Number(value);
  if(id==="repo_urls"){const old=Array.isArray(flow.settings.sections)?flow.settings.sections:[];const urls=value.split("\n").map(x=>x.trim()).filter(Boolean);
    flow.settings.repo_urls=urls;flow.settings.sections=urls.map(url=>old.find(x=>x.repo_url===url)||{repo_url:url,title:url.split("/").pop()||"",narration:"",broll_query:""});
  }else if(id==="terms"){flow.settings.terms=value.split(/[,\n]/).map(x=>x.trim()).filter(Boolean)}
  else{flow.settings[id]=value}
  activeTemplate="";renderSummary();persist();
}
function buildWorkflows(){
  const workflows=[
    {file:"render.yml",label:"Gerar vídeo MoneyPrinterTurbo",note:"Renderizar um pedido requests/ existente"},
    {file:"tutorial-vertical.yml",label:"Tutorial vertical",note:"Exige vídeo e gancho já aprovados em assets/approved"},
    {file:"qa-browser.yml",label:"QA da captura GitHub",note:"Playwright + FFmpeg"},
    {file:"qa-cinematic.yml",label:"QA cinematográfico",note:"B-roll, screenshots e motion"},
    {file:"qa-ai-director.yml",label:"QA de montagem 1080p",note:"Testes e amostra renderizada"}
  ];
  $("workflowList").innerHTML=workflows.map(w=>'<div class="listrow"><div><strong>'+escapeHtml(w.label)+'</strong><p>'+escapeHtml(w.note)+'</p></div><button class="btn" data-dispatch="'+escapeHtml(w.file)+'">Disparar</button></div>').join("");
  const names=["Carrossel diário — criação e fila","Captação leads — diagnóstico e TikTok","Google Sheets → fila WhatsApp","Painel diário de leads","Lembretes de follow-up","Histórico CRM","Validação apps — QA CI","TikTok Analytics — teste","Twilio — aprovação e envio"];
  $("activepiecesList").innerHTML=names.map((name,i)=>'<div class="listrow"><strong>'+escapeHtml(name)+'</strong><span class="pill '+(i>=6?"fail":"")+'">'+(i<6?"Agendado":"Rascunho")+'</span></div>').join("");
}
async function refreshHistory(){
  try{const jobs=await api("/api/jobs");$("jobsList").innerHTML=jobs.jobs.length?jobs.jobs.map(x=>'<div class="listrow"><div><strong>'+escapeHtml(x.title)+'</strong><p>'+escapeHtml(x.created_at)+" • "+escapeHtml(x.kind)+' • '+escapeHtml(x.request_path||x.workflow||"")+'</p></div><span class="pill">'+escapeHtml(x.status)+'</span></div>').join(""):'<p>Nenhuma solicitação registrada.</p>'}catch(e){$("jobsList").textContent=e.message}
  if(!githubConnected){$("runsList").textContent="Conecte o GitHub em Conexões para consultar execuções.";return}
  try{const data=await api("/api/runs");$("runsList").innerHTML=data.runs.length?data.runs.map(x=>'<div class="listrow"><div><strong>'+escapeHtml(x.name)+'</strong><p>'+escapeHtml(x.created_at)+" • "+escapeHtml(x.status)+(x.conclusion?" / "+escapeHtml(x.conclusion):"")+'</p></div><a rel="noopener noreferrer" target="_blank" href="'+escapeHtml(x.html_url)+'">Ver execução</a></div>').join(""):'<p>Nenhuma execução recente.</p>'}catch(e){$("runsList").textContent=e.message}
}
function updateConnectionStatus(){$("connectionStatus").textContent=githubConnected?"GitHub conectado ao MoneyPrint. Token criptografado no D1/SQLite.":"GitHub não conectado. Configure um token exclusivo deste repositório."}
async function fetchSavedFlows(){
  try{const data=await api("/api/flows");savedFlows=data.flows||[];renderSavedMenu()}catch(e){toast("Fluxos salvos indisponíveis: "+e.message)}
}
function renderSavedMenu(){
  let box=$("savedFlowMenu");
  if(!box){box=document.createElement("div");box.id="savedFlowMenu";box.className="actions";box.style.marginBottom="13px";const toolbar=document.querySelector(".toolbar");toolbar.parentNode.insertBefore(box,toolbar.nextSibling)}
  box.innerHTML='<select id="remoteFlowSelect" class="search" style="width:260px" aria-label="Fluxos salvos"><option value="">Abrir fluxo salvo...</option>'+savedFlows.map(x=>'<option value="'+escapeHtml(x.id)+'">'+escapeHtml(x.name)+" • "+escapeHtml(x.updated_at.slice(0,10))+'</option>').join("")+'</select><button class="btn" id="openSavedFlow">Abrir</button>';
}
async function initialize(){
  try{
    const me=await api("/api/me");csrf=me.csrf;githubConnected=!!me.github_connected;
    showAuthenticated(true);loadCustomSkills();loadDraft();syncDom();buildWorkflows();updateConnectionStatus();await fetchSavedFlows();
  }catch(e){showAuthenticated(false)}
}
function parseImported(content){
  const data=JSON.parse(content);if(!data||data.version!==1||!Array.isArray(data.nodes)||!Array.isArray(data.edges)||data.nodes.length>24||data.edges.length>65||typeof data.settings!=="object")throw Error("Arquivo de fluxo inválido");
  const v=validateFlow(data);if(v.errors.length)throw Error(v.errors[0]);return data;
}
// Event wiring: all events delegated to dynamically rendered controls.
$("loginForm").addEventListener("submit",async e=>{e.preventDefault();const btn=e.target.querySelector("button");btn.disabled=true;try{await api("/api/login","POST",{password:$("password").value});$("password").value="";await initialize();toast("Acesso autorizado")}catch(err){toast(err.message)}finally{btn.disabled=false}});
$("logout").addEventListener("click",async()=>{try{await api("/api/logout","POST")}catch{}csrf="";showAuthenticated(false)});
document.querySelectorAll(".topnav [data-view]").forEach(x=>x.addEventListener("click",()=>showView(x.dataset.view)));
$("templates").addEventListener("click",e=>{const btn=e.target.closest("[data-template]");if(!btn)return;if(flow.settings.topic&&!confirm("Substituir o fluxo atual pelo template selecionado?"))return;flow=makeTemplate(btn.dataset.template);activeTemplate=btn.dataset.template;selected="goal";layoutNodes();syncDom()});
$("searchTools").addEventListener("input",renderToolPalette);
$("toolList").addEventListener("click",e=>{
 const skill=e.target.closest("[data-apply-skill]");
 if(skill){addSkillFromCatalog(skill.dataset.applySkill);return}
 const btn=e.target.closest("[data-add]");
 if(btn&&!btn.disabled)addTool(btn.dataset.add);
});
$("showcaseSearch").addEventListener("input",renderToolShowcase);
$("showcaseCatalog").addEventListener("click",e=>{
 const skill=e.target.closest("[data-apply-skill]");
 if(skill){addSkillFromCatalog(skill.dataset.applySkill);return}
 const btn=e.target.closest("[data-add]");
 if(btn&&!btn.disabled)addTool(btn.dataset.add);
});
document.querySelectorAll("[data-catalog-tab]").forEach(btn=>btn.addEventListener("click",()=>{catalogTab=btn.dataset.catalogTab;renderToolShowcase()}));
$("quickToolButtons").addEventListener("click",e=>{const btn=e.target.closest("[data-quick-tool]");if(btn&&!btn.disabled)addTool(btn.dataset.quickTool)});
function showLibrary(){
 showView("studio");
 if(mobile()){openPanel("palette");return}
 $("toolsShowcase").scrollIntoView({behavior:"smooth",block:"center"});
 $("showcaseSearch").focus({preventScroll:true});
}
$("openToolLibrary").addEventListener("click",showLibrary);
$("mobileAllTools").addEventListener("click",showLibrary);
$("closePalette").addEventListener("click",closePanels);
$("closeInspector").addEventListener("click",closePanels);
$("doneInspector").addEventListener("click",closePanels);
function importSkill(){const inp=$("skillFileInput");inp.value="";inp.click()}
$("importSkill").addEventListener("click",importSkill);
$("importSkillPalette").addEventListener("click",importSkill);
$("skillFileInput").addEventListener("change",async e=>{
 const file=e.target.files?.[0];if(!file)return;
 try{
   if(file.size>4096)throw Error("Skill JSON muito grande (máximo 4 KB)");
   const manifest=parseSkillManifest(await file.text());
   if(customSkills.length>=20)throw Error("Limite de 20 Skills personalizadas");
   if(customSkills.some(x=>x.name.toLowerCase()===manifest.name.toLowerCase()))throw Error("Já existe Skill com esse nome");
   customSkills.push({...manifest,id:"custom-"+customSkills.length,icon:"✳",category:"Personalizadas"});
   saveCustomSkills();catalogTab="skills";renderToolPalette();renderToolShowcase();
   toast("Skill importada. Selecione + para adicioná-la ao fluxo.");
 }catch(err){toast(err.message)}finally{e.target.value=""}
});
$("toolList").addEventListener("dragstart",e=>{const el=e.target.closest("[data-dragtool]");if(el&&e.dataTransfer){e.dataTransfer.setData("text/plain",el.dataset.dragtool);e.dataTransfer.effectAllowed="copy"}});
$("canvasbody").addEventListener("dragover",e=>{if(e.dataTransfer?.types?.includes("text/plain"))e.preventDefault()});
$("canvasbody").addEventListener("drop",e=>{e.preventDefault();const id=e.dataTransfer?.getData("text/plain");if(id)addTool(id)});
$("canvasNodes").addEventListener("click",e=>{
  const from=e.target.closest("[data-portout]");const to=e.target.closest("[data-portin]");
  if(from){connecting=from.dataset.portout;toast("Selecione a entrada de outro bloco para conectar.");renderCanvas();return}
  if(to){if(!connecting){toast("Clique primeiro na saída de um bloco.");return}const s=connecting;connecting=null;modify(f=>connectNodes(f,s,to.dataset.portin));return}
  const remove=e.target.closest("[data-remove]");if(remove){modify(f=>removeTool(f,remove.dataset.remove),"goal");layoutNodes();syncDom();return}
  const edit=e.target.closest("[data-edit]");const block=e.target.closest("[data-node]");
  if(edit||block){selected=edit?.dataset.edit||block.dataset.node;renderCanvas();renderInspector();if(!mobile())openPanel("inspector")}
});
$("paths").addEventListener("click",e=>{const hit=e.target.closest("[data-from][data-to]");if(hit&&confirm("Remover esta conexão?"))modify(f=>removeEdge(f,hit.dataset.from,hit.dataset.to))});
let dragging=null;
$("canvasNodes").addEventListener("pointerdown",e=>{if(!e.target.closest(".drag"))return;const el=e.target.closest("[data-node]");if(!el)return;const id=el.dataset.node,n=descriptor(id);if(!n)return;dragging={id,startX:e.clientX,startY:e.clientY,x:n.x,y:n.y,element:el};e.target.setPointerCapture?.(e.pointerId);e.preventDefault()});
window.addEventListener("pointermove",e=>{if(!dragging)return;const node=descriptor(dragging.id);if(!node)return;node.x=Math.max(10,Math.round(dragging.x+(e.clientX-dragging.startX)/zoom));node.y=Math.max(10,Math.round(dragging.y+(e.clientY-dragging.startY)/zoom));dragging.element.style.left=node.x+"px";dragging.element.style.top=node.y+"px";drawEdges()});
window.addEventListener("pointerup",()=>{if(!dragging)return;dragging=null;persist()});
$("mobileFlow").addEventListener("click",e=>{
  const up=e.target.closest("[data-up]");if(up){modify(f=>moveTool(f,up.dataset.up,-1));layoutNodes();syncDom();return}
  const down=e.target.closest("[data-down]");if(down){modify(f=>moveTool(f,down.dataset.down,1));layoutNodes();syncDom();return}
  const edit=e.target.closest("[data-mobile-edit]"),n=e.target.closest("[data-mobile-node]");
  if(edit||n){selected=edit?.dataset.mobileEdit||n.dataset.mobileNode;renderCanvas();renderInspector();openPanel("inspector")}
});
$("inspectorBody").addEventListener("input",e=>{
  const setting=e.target.closest("[data-setting]");if(setting){updateSettings(setting.dataset.setting,setting.value);return}
  const sec=e.target.closest("[data-section][data-key]");if(sec){
    const i=Number(sec.dataset.section),url=flow.settings.repo_urls[i];if(!url)return;
    if(!Array.isArray(flow.settings.sections))flow.settings.sections=[];
    if(!flow.settings.sections[i])flow.settings.sections[i]={repo_url:url,title:"",narration:"",broll_query:""};
    flow.settings.sections[i][sec.dataset.key]=sec.value;persist();renderSummary();
  }
});
$("inspectorBody").addEventListener("change",e=>{if(e.target.dataset.setting==="repo_urls"){renderInspector();renderSummary()}});
$("inspectorBody").addEventListener("click",e=>{if(e.target.id==="editGeneral"){selected="goal";renderInspector();renderCanvas()}});
$("zoomIn").addEventListener("click",()=>{zoom=Math.min(1.6,Math.round((zoom+.1)*10)/10);renderCanvas()});
$("zoomOut").addEventListener("click",()=>{zoom=Math.max(.5,Math.round((zoom-.1)*10)/10);renderCanvas()});
$("resetZoom").addEventListener("click",()=>{zoom=.7;renderCanvas();$("canvasbody").scrollTo({left:0,top:0})});
$("autoLayout").addEventListener("click",()=>{layoutNodes();renderCanvas();persist();toast("Blocos organizados no canvas")});
$("previewRequest").addEventListener("click",()=>{try{const compiled=compileFlow(flow);$("requestJson").textContent=JSON.stringify(compiled,null,2);$("requestDialog").showModal()}catch(err){toast(err.message);selected="goal";renderInspector()}});
$("closeRequest").addEventListener("click",()=>$("requestDialog").close());
$("copyRequest").addEventListener("click",()=>{navigator.clipboard?.writeText($("requestJson").textContent).then(()=>toast("JSON copiado")).catch(()=>toast("Não foi possível copiar"))});
$("executeFlow").addEventListener("click",async e=>{
  let data;try{data=compileFlow(flow)}catch(err){toast(err.message);return}
  if(!githubConnected){toast("Conecte o GitHub em Conexões antes de executar.");showView("connections");return}
  if(!confirm("Criar este pedido no GitHub e iniciar a renderização? Não haverá publicação automática."))return;
  e.target.disabled=true;
  try{const result=await api("/api/render","POST",data);toast("Solicitação criada: "+result.request_path+" — acompanhe em Execuções.");showView("history")}catch(err){toast(err.message)}finally{e.target.disabled=false}
});
$("saveFlow").addEventListener("click",async e=>{const btn=e.target;btn.disabled=true;try{if(flow.nodes.length>24||flow.edges.length>65)throw Error("Fluxo muito grande");const result=await api("/api/flows","POST",{flow});toast("Fluxo salvo na central");flow.id=result.id;persist();await fetchSavedFlows()}catch(err){toast(err.message)}finally{btn.disabled=false}});
$("exportFlow").addEventListener("click",()=>{const data=JSON.stringify(flow,null,2),blob=new Blob([data],{type:"application/json"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="moneyprint-fluxo.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
$("importFlow").addEventListener("click",()=>$("importInput").click());
$("importInput").addEventListener("change",async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>20000)throw Error("Arquivo muito grande");flow=parseImported(await file.text());selected="goal";activeTemplate="";syncDom();toast("Fluxo importado")}catch(err){toast(err.message)}finally{e.target.value=""}});
document.addEventListener("click",e=>{if(e.target.id!=="openSavedFlow")return;const id=$("remoteFlowSelect").value,entry=savedFlows.find(x=>x.id===id);if(!entry)return;try{flow=parseImported(JSON.stringify(JSON.parse(entry.graph)));selected="goal";activeTemplate="";syncDom();toast("Fluxo carregado")}catch(err){toast(err.message)}});
$("refreshRuns").addEventListener("click",refreshHistory);
$("connectForm").addEventListener("submit",async e=>{e.preventDefault();const btn=$("connectSubmit");btn.disabled=true;try{await api("/api/connect","POST",{token:$("githubToken").value});$("githubToken").value="";githubConnected=true;updateConnectionStatus();toast("Token validado e armazenado com criptografia")}catch(err){toast(err.message)}finally{btn.disabled=false}});
$("workflowList").addEventListener("click",async e=>{
  const btn=e.target.closest("[data-dispatch]");if(!btn)return;const workflow=btn.dataset.dispatch;let inputs={};
  if(workflow==="render.yml"){const path=prompt("Pedido existente em requests/:","requests/demo.json");if(path===null)return;inputs={request_path:path}}
  if(workflow==="tutorial-vertical.yml"){const source=prompt("Vídeo aprovado (.mp4 em assets/approved/):");if(source===null)return;const hook=prompt("Gancho aprovado (.mp4 em assets/approved/):");if(hook===null)return;const recipe=prompt("Receita existente em tutorials/:","github_primeiro_repositorio.json");if(recipe===null)return;inputs={source_file:source,hook_file:hook,recipe}}
  if(!confirm("Disparar "+workflow+" no GitHub?"))return;btn.disabled=true;
  try{await api("/api/dispatch","POST",{workflow,inputs});toast("Disparo aceito pelo GitHub: "+workflow)}catch(err){toast(err.message)}finally{btn.disabled=false}
});
document.querySelectorAll("[data-mobile]").forEach(x=>x.addEventListener("click",()=>{
  const v=x.dataset.mobile;if(v==="tools"){showView("studio");openPanel("palette")}
  else if(v==="settings"){showView("studio");openPanel("inspector")}
  else if(v==="videos"){showView("videos");closePanels()}
  else if(v==="runs"){showView("history")}else{showView("studio");closePanels()}
}));
$("scrim").addEventListener("click",closePanels);
document.addEventListener("keydown",e=>{if(e.key==="Escape")closePanels()});
initialize();
