import test from "node:test";
import assert from "node:assert/strict";
import {DatabaseSync} from "node:sqlite";
import {readFileSync} from "node:fs";
import {createHash,randomBytes} from "node:crypto";
import panel from "./worker.js";

const db = new DatabaseSync(":memory:");
db.exec(readFileSync(new URL("./schema.sql",import.meta.url),"utf8"));
const DB={prepare(sql){let args=[];return {bind(...a){args=a;return this},async first(){return db.prepare(sql).get(...args)||null},async all(){return {results:db.prepare(sql).all(...args)}},async run(){return db.prepare(sql).run(...args)}}}};
const password="StrongPasswordForStudioTests-2026";
const env={DB,ADMIN_PASS_HASH:createHash("sha256").update(password).digest("hex"),SESSION_KEY:randomBytes(32).toString("base64url"),ENCRYPTION_KEY:randomBytes(32).toString("base64url")};
const origin="https://painel.test";
async function call(path,method="GET",payload,session="",csrf=""){
  const headers={};
  if(method==="POST")Object.assign(headers,{"content-type":"application/json",origin,"x-requested-with":"ArtiSysPanel","x-csrf-token":csrf});
  if(session)headers.cookie=session;
  return panel.fetch(new Request(origin+path,{method,headers,body:method==="POST"?JSON.stringify(payload||{}):undefined}),env);
}
async function auth(){
  const response=await call("/api/login","POST",{password});
  assert.equal(response.status,200);
  const session=response.headers.get("set-cookie").split(";")[0];
  const csrf=(await(await call("/api/me","GET",null,session)).json()).csrf;
  return {session,csrf};
}
test("studio is visible in original protected panel",async()=>{
  const home=await call("/");
  assert.equal(home.status,200);
  assert.match(await home.text(),/Studio/);
  assert.equal((await call("/api/studio/projects")).status,401);
});
test("studio creates, lists, edits and reopens a canonical project",async()=>{
  const {session,csrf}=await auth();
  const input={topic:"Caixa de restaurante",script:"O cliente chega ao caixa. Registre os pedidos. Confira o relatório.",duration_seconds:30,aspect:"9:16"};
  const created=await call("/api/studio/projects","POST",input,session,csrf);
  assert.equal(created.status,201);
  const project=(await created.json()).project;
  assert.equal(project.schema_version,3);
  assert.equal(project.total_frames,900);
  assert.ok(project.scenes.length>=3);
  assert.equal(project.scenes.reduce((n,x)=>n+x.duration_frames,0),900);
  const listed=await call("/api/studio/projects","GET",null,session);
  assert.ok((await listed.json()).projects.some(x=>x.id===project.id));
  const scene=project.scenes[0];
  const update=await call("/api/studio/projects/"+project.id+"/save","POST",{revision:1,scenes:[{...scene,duration_frames:scene.duration_frames+15},...project.scenes.slice(1)]},session,csrf);
  assert.equal(update.status,200);
  const current=(await update.json()).project;
  assert.equal(current.revision,2);
  assert.equal(current.total_frames,915);
  const loaded=await call("/api/studio/projects/"+project.id,"GET",null,session);
  assert.equal((await loaded.json()).project.revision,2);
  const stale=await call("/api/studio/projects/"+project.id+"/save","POST",{revision:1,scenes:project.scenes},session,csrf);
  assert.equal(stale.status,409);
});
test("studio rejects unsafe references and invalid scene edits",async()=>{
  const {session,csrf}=await auth();
  const invalid=await call("/api/studio/projects","POST",{topic:"x",script:"test",duration_seconds:30,aspect:"9:16",assets:[{id:"bad",path:"../../secret"}]},session,csrf);
  assert.equal(invalid.status,400);
  const created=await call("/api/studio/projects","POST",{topic:"Tutorial",script:"Primeiro passo. Segundo passo.",duration_seconds:20,aspect:"16:9"},session,csrf);
  const project=(await created.json()).project;
  const edited=await call("/api/studio/projects/"+project.id+"/save","POST",{revision:1,scenes:project.scenes.map((s,i)=>i===0?{...s,duration_frames:0}:s)},session,csrf);
  assert.equal(edited.status,400);
  const noCsrf=await call("/api/studio/projects","POST",{topic:"Sem CSRF"},session,"invalid");
  assert.equal(noCsrf.status,403);
});

test("Studio V3 imports 300-second projects with layouts and keeps render protected",async()=>{
  const {session,csrf}=await auth();
  const old={schema_version:3,id:"old",revision:1,topic:"5 sistemas open source",script:"Teste de importação.",fps:30,aspect:"16:9",total_frames:9000,
    tracks:[{id:"video",kind:"video"}],assets:[],scenes:[{id:"scene-001",track_id:"video",title:"ERPNext",text:"ERPNext organiza operações.",
      kind:"text",asset_id:null,start_frame:0,duration_frames:9000,animation:"cut",framing:"contain",
      layout:"browser",repo_url:"https://github.com/frappe/erpnext"}]};
  const res=await call("/api/studio/projects/import","POST",{project:old},session,csrf);
  assert.equal(res.status,201);
  const p=(await res.json()).project;
  assert.notEqual(p.id,old.id);
  assert.equal(p.scenes[0].repo_url,"https://github.com/frappe/erpnext");
  const requestRender=await call("/api/studio/projects/"+p.id+"/render","POST",{revision:p.revision},session,csrf);
  assert.equal(requestRender.status,409); // No connected GitHub token.
  const insecure={...old,scenes:old.scenes.map(x=>({...x,repo_url:"https://evil.example/other"}))};
  const denied=await call("/api/studio/projects/import","POST",{project:insecure},session,csrf);
  assert.equal(denied.status,400);
  assert.equal((await call("/api/studio/projects/import","POST",{project:old})).status,401);
});

test("studio render endpoint requires an explicit saved revision and GitHub connection",async()=>{
  const {session,csrf}=await auth();
  const created=await call("/api/studio/projects","POST",{
    topic:"Cinco sistemas empresariais",script:"Cena inicial. Cena final.",
    duration_seconds:20,aspect:"16:9"},session,csrf);
  assert.equal(created.status,201);
  const project=(await created.json()).project;
  const path="/api/studio/projects/"+project.id+"/render";
  assert.equal((await call(path,"POST",{revision:1},session,"invalid")).status,403);
  const noToken=await call(path,"POST",{revision:1},session,csrf);
  assert.equal(noToken.status,409);
  assert.match((await noToken.json()).error,/Conecte o GitHub/);
});


test("Studio saves and reopens light animated style without affecting legacy projects",async()=>{
  const {session,csrf}=await auth();
  const input={topic:"Cinco sistemas com motion",script:"Entrada. Demonstração de software.",
    duration_seconds:30,aspect:"16:9",visual_style:"light_motion"};
  const created=await call("/api/studio/projects","POST",input,session,csrf);
  assert.equal(created.status,201);
  const p=(await created.json()).project;
  assert.equal(p.visual_style,"light_motion");
  const res=await call("/api/studio/projects/"+p.id+"/save","POST",
    {revision:1,scenes:p.scenes,visual_style:"classic"},session,csrf);
  assert.equal(res.status,200);
  assert.equal((await res.json()).project.visual_style,"classic");
  const reopened=await call("/api/studio/projects/"+p.id,"GET",null,session);
  assert.equal((await reopened.json()).project.visual_style,"classic");
  const invalid=await call("/api/studio/projects","POST",
    {...input,visual_style:"commercial_api"},session,csrf);
  assert.equal(invalid.status,400);
});


test("Talkcraft educational mode is explicit, validated, and saved in Studio V3",async()=>{
 const {session,csrf}=await auth();
 const body={topic:"Tutorial gratuito de sistemas",
   script:"O caos das planilhas. Um CRM ajuda a organizar.",
   duration_seconds:30,aspect:"16:9",visual_style:"talkcraft_edu"};
 const created=await call("/api/studio/projects","POST",body,session,csrf);
 assert.equal(created.status,201);
 const p=(await created.json()).project;
 assert.equal(p.visual_style,"talkcraft_edu");
 const saved=await call("/api/studio/projects/"+p.id+"/save","POST",
   {revision:1,scenes:p.scenes,visual_style:"talkcraft_edu"},session,csrf);
 assert.equal(saved.status,200);
 assert.equal((await saved.json()).project.visual_style,"talkcraft_edu");
 const bad=await call("/api/studio/projects","POST",
   {...body,visual_style:"paid_service"},session,csrf);
 assert.equal(bad.status,400);
});
