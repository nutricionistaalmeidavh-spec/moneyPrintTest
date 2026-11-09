import test from "node:test";
import assert from "node:assert/strict";
import { makeTemplate, compileFlow, insertTool, removeTool, moveTool, toolCatalog, validateFlow } from "../flow-core.mjs";

test("automatic template generates an eligible short request with no paid providers", () => {
  const flow=makeTemplate("automatic");
  flow.settings.topic="Ideias open source para empresas";
  const request=compileFlow(flow);
  assert.equal(request.visual_mode,"auto");
  assert.equal(request.duration_seconds,40);
  assert.deepEqual(Object.keys(request).sort(),["aspect","duration_seconds","topic","visual_mode"]);
});

test("cinematic template requires narrations for every repository",()=>{
  const flow=makeTemplate("cinematic");
  flow.settings.topic="3 repositórios";
  flow.settings.repo_urls=["https://github.com/appwrite/appwrite"];
  assert.throws(()=>compileFlow(flow),/narraç|seç|seção/i);
  flow.settings.sections=[{repo_url:flow.settings.repo_urls[0],title:"Appwrite",narration:"O Appwrite oferece autenticação e serviços de backend para novos aplicativos."}];
  const request=compileFlow(flow);
  assert.equal(request.visual_mode,"github_cinematic");
  assert.equal(request.sections.length,1);
  assert.equal(request.sections[0].title,"Appwrite");
});

test("github capture without slides maps to browser capture, without undefined features",()=>{
  const flow=makeTemplate("github");
  flow.settings.topic="Ferramentas open source";
  flow.settings.repo_urls=["https://github.com/payloadcms/payload"];
  const request=compileFlow(flow);
  assert.equal(request.visual_mode,"github");
  assert.deepEqual(request.repo_urls,flow.settings.repo_urls);
  assert.ok(!("sections" in request));
});

test("verified news and motion options only run in compatible cinematic pipelines",()=>{
  const flow=makeTemplate("cinematic");flow.settings.topic="Projetos";
  flow.settings.repo_urls=["https://github.com/appwrite/appwrite"];
  flow.settings.sections=[{repo_url:flow.settings.repo_urls[0],title:"Appwrite",narration:"Veja a plataforma Appwrite, uma solução aberta para construir APIs e autenticação."}];
  const edited=insertTool(flow,"news");
  const motion=insertTool(edited,"hook");
  motion.settings.hook_asset="assets/approved/hook.mp4";
  const request=compileFlow(motion);
  assert.equal(request.include_verified_news,true);
  assert.equal(request.motion.hook_asset,"assets/approved/hook.mp4");
  assert.equal(request.motion.hook_seconds,3);
});

test("no silent unsupported expensive or draft integrations",()=>{
  const names=toolCatalog.filter(x=>x.available).map(x=>x.id);
  assert.ok(names.includes("piper"));
  assert.ok(!names.includes("paid_tts"));
  assert.ok(!names.includes("autopublish"));
  const flow=makeTemplate("automatic");
  assert.throws(()=>insertTool(flow,"autopublish"),/indisponível/i);
});

test("graph nodes can be inserted, reordered and removed consistently",()=>{
  const flow=makeTemplate("automatic");
  const added=insertTool(flow,"captions");
  assert.equal(added.nodes.filter(n=>n.tool==="captions").length,1);
  const before=added.nodes.find(n=>n.tool==="captions");
  const moved=moveTool(added,before.id,-1);
  assert.notDeepEqual(moved.edges,added.edges);
  const removed=removeTool(moved,before.id);
  assert.equal(removed.nodes.filter(n=>n.tool==="captions").length,0);
  assert.equal(validateFlow(removed).errors.length,0);
});

test("cycle and disconnected nodes never dispatch",()=>{
  const flow=makeTemplate("automatic");flow.settings.topic="Teste";
  flow.edges.push({from:"final",to:"goal"});
  assert.throws(()=>compileFlow(flow),/ciclo/i);
  const other=makeTemplate("automatic");
  other.settings.topic="Teste";
  other.nodes.push({id:"orphan",tool:"captions",enabled:true,x:700,y:10});
  assert.throws(()=>compileFlow(other),/desconectad/i);
});

test("maximum duration follows the actual render engine limits",()=>{
  const flow=makeTemplate("automatic");flow.settings.topic="Teste";flow.settings.duration_seconds=300;
  assert.throws(()=>compileFlow(flow),/90/);
  const cinematic=makeTemplate("cinematic");cinematic.settings.topic="Teste";cinematic.settings.duration_seconds=400;
  cinematic.settings.repo_urls=["https://github.com/appwrite/appwrite"];
  cinematic.settings.sections=[{repo_url:cinematic.settings.repo_urls[0],title:"Appwrite",narration:"O Appwrite permite integrar serviços de backend em projetos modernos."}];
  assert.throws(()=>compileFlow(cinematic),/360/);
});
