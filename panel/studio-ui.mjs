// Additive Studio timeline mounted through current visual workflow panel.
export function mountStudio({api,toast}){
const by=id=>document.getElementById(id);
const request=api,notice=toast;
const esc=s=>String(s??"").replace(/[&<>"\x27]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","\x27":"&#39;"}[c]));
/* Studio V3 editor: explicit save, no background mutation or paid dependencies. */
var studio=null,studioIndex=0,studioUndo=[],studioRedo=[],studioTimer=null;
function studioClone(v){return JSON.parse(JSON.stringify(v))}
function studioStop(){if(studioTimer!==null){clearTimeout(studioTimer);studioTimer=null}by("studioPlay").textContent="Reproduzir prévia";by("studioStage").classList.remove("playing")}
function studioRecalc(){var total=0;studio.scenes.forEach(function(s){s.start_frame=total;total+=s.duration_frames});studio.total_frames=total}
function studioSnapshot(){studioUndo.push(studioClone(studio));if(studioUndo.length>30)studioUndo.shift();studioRedo=[]}
function studioInfo(msg){by("studioState").textContent=msg}
async function studioList(){
  try{var list=(await request("/api/studio/projects")).projects||[];
    var sel=by("studioProjectSelect"),old=sel.value;
    sel.innerHTML='<option value="">Selecione um projeto</option>'+list.map(function(x){return '<option value="'+esc(x.id)+'">'+esc(x.topic)+" · r"+x.revision+'</option>'}).join("");
    if(list.some(function(x){return x.id===old}))sel.value=old;
  }catch(err){studioInfo(err.message)}
}
function studioLoad(p){
  studioStop();studio=studioClone(p);studioIndex=0;studioUndo=[];studioRedo=[];
  by("studioEditor").classList.remove("hidden");by("studioProjectSelect").value=studio.id;
  studioInfo("Revisão "+studio.revision+" salva. Alterações são locais até clicar em Salvar.");
  studioDraw();
}
function studioDraw(){
  if(!studio)return;
  var scenes=studio.scenes,scene=scenes[studioIndex]||scenes[0];if(!scene)return;
  by("studioName").textContent=studio.topic;
  by("studioProjectTheme").value=studio.visual_style||"classic";
  by("studioSummary").textContent="Revisão "+studio.revision+" · "+studio.aspect+" · "+(studio.total_frames/30).toFixed(1)+"s · "+scenes.length+" cenas";
  var stage=by("studioStage");stage.style.aspectRatio=studio.aspect.replace(":"," / ");
  by("studioStageTitle").textContent=scene.title;
  by("studioStageBody").textContent=scene.text;
  by("studioStageLabel").textContent="CENA "+(studioIndex+1)+" / "+scenes.length+" · PRÉVIA DO STORYBOARD";
  by("studioSceneTitle").value=scene.title;
  by("studioSceneText").value=scene.text;
  by("studioSceneSeconds").value=Number((scene.duration_frames/30).toFixed(2));
  by("studioSceneAnimation").value=scene.animation||"cut";
  by("studioSceneLayout").value=scene.layout||"hero";
  by("studioSceneRepoUrl").value=scene.repo_url||"";
  by("studioSceneAsset").innerHTML='<option value="">Sem mídia</option>'+studio.assets.filter(function(a){return a.verified}).map(function(a){return '<option value="'+esc(a.id)+'">'+esc(a.title)+'</option>'}).join("");
  by("studioSceneAsset").value=scene.asset_id||"";
  by("studioTime").textContent=(scene.start_frame/30).toFixed(1)+"s – "+((scene.start_frame+scene.duration_frames)/30).toFixed(1)+"s · "+(studio.total_frames/30).toFixed(1)+"s total";
  by("studioAssetCount").textContent=studio.assets.length+" mídias no projeto";
  by("studioTimeline").innerHTML=scenes.map(function(s,i){
    var active=i===studioIndex?' selected':'';
    return '<button class="studio-shot'+active+'" role="listitem" data-studio-scene="'+i+'" type="button" aria-label="Cena '+(i+1)+' '+esc(s.title)+'"><b>'+esc(s.title)+'</b><small>'+((s.start_frame/30).toFixed(1))+'s · '+((s.duration_frames/30).toFixed(1))+'s</small><small>'+esc(s.asset_id?"Vídeo / imagem":"Tipografia")+'</small></button>';
  }).join("");
}
function studioSelect(i){if(!studio||i<0||i>=studio.scenes.length)return;studioStop();studioIndex=i;studioDraw()}
function studioChange(key,value){
  if(!studio)return;var s=studio.scenes[studioIndex];if(s[key]===value)return;
  studioSnapshot();s[key]=value;if(key==="asset_id")s.kind=value?"media":"text";
  studioRecalc();studioInfo("Alterações pendentes. Salve para persistir no painel.");studioDraw();
}
by("studioTimeline").addEventListener("click",function(e){var button=e.target.closest("[data-studio-scene]");if(button)studioSelect(Number(button.dataset.studioScene))});
by("studioPrevious").addEventListener("click",function(){studioSelect(studioIndex-1)});
by("studioNext").addEventListener("click",function(){studioSelect(studioIndex+1)});
by("studioProjectTheme").addEventListener("change",function(){if(!studio)return;studioStop();studioSnapshot();studio.visual_style=this.value;studioInfo("Estilo alterado localmente. Salve antes de renderizar.");studioDraw()});
by("studioSceneTitle").addEventListener("change",function(){studioChange("title",this.value.trim())});
by("studioSceneText").addEventListener("change",function(){studioChange("text",this.value.trim())});
by("studioSceneSeconds").addEventListener("change",function(){var n=Math.round(Number(this.value)*30);if(!Number.isInteger(n)||n<1){notice("Informe duração maior que zero");return}studioChange("duration_frames",n)});
by("studioSceneAnimation").addEventListener("change",function(){studioChange("animation",this.value)});
by("studioSceneAsset").addEventListener("change",function(){studioChange("asset_id",this.value||null)});
by("studioSceneLayout").addEventListener("change",function(){studioChange("layout",this.value)});
by("studioSceneRepoUrl").addEventListener("change",function(){var url=this.value.trim();if(url&&!/^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/?$/.test(url)){notice("URL deve apontar para repositório público no GitHub");this.value=studio.scenes[studioIndex].repo_url||"";return}studioChange("repo_url",url)});
function studioMove(dir){
 if(!studio)return;var next=studioIndex+dir;if(next<0||next>=studio.scenes.length)return;
 studioStop();studioSnapshot();var temp=studio.scenes[next];studio.scenes[next]=studio.scenes[studioIndex];studio.scenes[studioIndex]=temp;studioIndex=next;studioRecalc();studioInfo("Ordem alterada; salve a revisão.");studioDraw();
}
by("studioMoveLeft").addEventListener("click",function(){studioMove(-1)});
by("studioMoveRight").addEventListener("click",function(){studioMove(1)});
by("studioUndo").addEventListener("click",function(){if(!studioUndo.length)return;studioStop();studioRedo.push(studioClone(studio));studio=studioUndo.pop();studioIndex=Math.min(studioIndex,studio.scenes.length-1);studioInfo("Desfeito localmente");studioDraw()});
by("studioRedo").addEventListener("click",function(){if(!studioRedo.length)return;studioStop();studioUndo.push(studioClone(studio));studio=studioRedo.pop();studioIndex=Math.min(studioIndex,studio.scenes.length-1);studioInfo("Refeito localmente");studioDraw()});
by("studioPlay").addEventListener("click",function(){
 if(!studio)return;if(studioTimer!==null){studioStop();return}
 var start=studioIndex;by("studioPlay").textContent="Pausar prévia";
 function next(i){if(i>=studio.scenes.length){studioStop();return}studioIndex=i;studioDraw();by("studioStage").classList.remove("playing");void by("studioStage").offsetWidth;by("studioStage").classList.add("playing");studioTimer=setTimeout(function(){next(i+1)},Math.min(20000,studio.scenes[i].duration_frames/30*1000))}
 next(start);
});
by("studioCreateForm").addEventListener("submit",async function(e){
 e.preventDefault();var btn=by("studioCreateButton");btn.disabled=true;
 try{var body={topic:by("studioTopic").value.trim(),script:by("studioScript").value.trim(),duration_seconds:Number(by("studioDuration").value),aspect:by("studioAspect").value,visual_style:by("studioVisualStyle").value};
 var created=await request("/api/studio/projects","POST",body);
 studioLoad(created.project);await studioList();by("studioProjectSelect").value=created.project.id;
 notice("Storyboard criado. Edite as cenas na timeline.");
 }catch(err){notice(err.message)}finally{btn.disabled=false}
});
by("studioOpen").addEventListener("click",async function(){
 var id=by("studioProjectSelect").value;if(!id){notice("Selecione um projeto");return}
 try{studioLoad((await request("/api/studio/projects/"+encodeURIComponent(id))).project)}catch(err){notice(err.message)}
});
by("studioReload").addEventListener("click",studioList);
by("studioAddAsset").addEventListener("click",function(){
 if(!studio){notice("Abra um projeto");return}
 var a={id:"asset-"+crypto.randomUUID().slice(0,12),
   title:by("studioAssetTitle").value.trim(),path:by("studioAssetPath").value.trim(),
   license:by("studioAssetLicense").value.trim(),attribution:by("studioAssetAuthor").value.trim(),
   tags:by("studioAssetTitle").value.trim().split(" "),verified:true};
 if(!a.title||!a.license||!a.attribution||!/^assets\/[A-Za-z0-9_.\/-]{1,200}$/.test(a.path)||a.path.split("/").includes("..")){
   notice("Informe arquivo assets/ seguro, licença e origem");return
 }
 studioSnapshot();studio.assets.push(a);studioInfo("Mídia incluída no rascunho. Ela deve existir em assets/ no executor.");
 ["studioAssetTitle","studioAssetPath","studioAssetLicense","studioAssetAuthor"].forEach(function(k){by(k).value=""});studioDraw();
});
by("studioSave").addEventListener("click",async function(){
 if(!studio)return;var btn=this;btn.disabled=true;
 try{var result=await request("/api/studio/projects/"+encodeURIComponent(studio.id)+"/save","POST",
   {revision:studio.revision,scenes:studio.scenes,assets:studio.assets,visual_style:studio.visual_style||"classic"});
 studioLoad(result.project);await studioList();by("studioProjectSelect").value=result.project.id;
 notice("Revisão "+result.project.revision+" salva no banco.");
 }catch(err){studioInfo("Não salvo: "+err.message);notice(err.message)}finally{btn.disabled=false}
});
by("studioExport").addEventListener("click",function(){
 if(!studio)return;var blob=new Blob([JSON.stringify(studio,null,2)],{type:"application/json"});
 var url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="moneyprint-studio-"+studio.id+".json";a.click();setTimeout(function(){URL.revokeObjectURL(url)},5000)
});


by("studioImportButton").addEventListener("click",function(){by("studioImportFile").click()});
by("studioImportFile").addEventListener("change",async function(){
 const file=this.files?.[0];if(!file)return;
 try{
   if(file.size>64000)throw Error("Storyboard ultrapassa 64 KB");
   const parsed=JSON.parse(await file.text());
   const result=await request("/api/studio/projects/import","POST",{project:parsed});
   studioLoad(result.project);await studioList();by("studioProjectSelect").value=result.project.id;
   notice("Storyboard importado e salvo como novo projeto.");
 }catch(e){notice("Importação não realizada: "+e.message)}
 finally{this.value=""}
});
by("studioRender").addEventListener("click",async function(){
 if(!studio)return;
 if(studioUndo.length){notice("Salve a revisão antes de renderizar o MP4.");return}
 const btn=this;btn.disabled=true;
 try{
   const result=await request("/api/studio/projects/"+encodeURIComponent(studio.id)+"/render","POST",{revision:studio.revision});
   studioInfo("Render solicitado: "+result.project_path+". Veja o resultado em Execuções.");
   notice("Render solicitado ao GitHub Actions. Sem publicação automática.");
 }catch(e){notice("Render não solicitado: "+e.message)}finally{btn.disabled=false}
});
return {refresh:studioList,stop:studioStop};
}
