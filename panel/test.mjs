import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import { createHash, randomBytes } from "node:crypto";
import panel from "./worker.js";

const db=new DatabaseSync(":memory:");
db.exec(readFileSync(new URL("./schema.sql",import.meta.url),"utf8"));
const binding={prepare(sql){let args=[];return {bind(...x){args=x;return this},async first(){return db.prepare(sql).get(...args)||null},async all(){return {results:db.prepare(sql).all(...args)}},async run(){return db.prepare(sql).run(...args)}}}};
const password="testingStrongPassword_2026";
const env={DB:binding,ADMIN_PASS_HASH:createHash("sha256").update(password).digest("hex"),SESSION_KEY:randomBytes(32).toString("base64url"),ENCRYPTION_KEY:randomBytes(32).toString("base64url")};
const origin="https://painel.example";
async function call(path,method="GET",payload,session="",csrf=""){
  const headers={};
  if(method==="POST"){headers["content-type"]="application/json";headers.origin=origin;headers["x-requested-with"]="ArtiSysPanel";headers["x-csrf-token"]=csrf}
  if(session)headers.cookie=session;
  return panel.fetch(new Request(origin+path,{method,headers,body:method==="POST"?JSON.stringify(payload||{}):undefined}),env);
}
test("health endpoint sem segredos",async()=>{const r=await call("/health");assert.equal(r.status,200);assert.deepEqual(await r.json(),{ok:true})});
test("pagina e protecao de rotas",async()=>{const a=await call("/");assert.equal(a.status,200);assert.match(await a.text(),/(Central de automações|Estúdio de automações)/);const b=await call("/api/jobs");assert.equal(b.status,401);assert.equal(b.headers.get("x-frame-options"),"DENY")});
test("login, sessão, CSRF, token não conectado e logout",async()=>{
  const invalid=await call("/api/login","POST",{password:"senha-errada"});assert.equal(invalid.status,401);
  const login=await call("/api/login","POST",{password});assert.equal(login.status,200);
  const setCookie=login.headers.get("set-cookie");assert.match(setCookie,/HttpOnly/);assert.match(setCookie,/SameSite=Strict/);assert.match(setCookie,/Secure/);
  const session=setCookie.split(";")[0];
  const me=await call("/api/me","GET",null,session);assert.equal(me.status,200);
  const identity=await me.json();assert.equal(identity.github_connected,false);assert.ok(identity.csrf.length>30);
  const jobs=await call("/api/jobs","GET",null,session);assert.equal(jobs.status,200);assert.deepEqual((await jobs.json()).jobs,[]);
  const forbidden=await call("/api/connect","POST",{token:"bad"},session,"bad");assert.equal(forbidden.status,403);
  const connect=await call("/api/connect","POST",{token:"bad"},session,identity.csrf);assert.equal(connect.status,400);
  const render=await call("/api/render","POST",{topic:"video",duration_seconds:40,aspect:"9:16",visual_mode:"auto"},session,identity.csrf);assert.equal(render.status,409);
  const dispatch=await call("/api/dispatch","POST",{workflow:"qa-browser.yml"},session,identity.csrf);assert.equal(dispatch.status,409);
  const logout=await call("/api/logout","POST",{},session,identity.csrf);assert.equal(logout.status,200);
  assert.match(logout.headers.get("set-cookie"),/Max-Age=0/);
});
