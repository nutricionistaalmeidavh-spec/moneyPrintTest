import test from "node:test";
import assert from "node:assert/strict";
import {chromium} from "playwright";
import panel from "./worker.js";

// Browser contract test runs without Cloudflare/GitHub tokens or paid services.
test("mobile Studio creates, edits, previews and saves scenes",async()=>{
  const browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
  try{
    const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
    const errors=[];
    page.on("pageerror",e=>errors.push(String(e)));
    const html=await (await panel.fetch(new Request("https://studio.test/"),{})).text();
    let logged=false,project=null;
    await page.route("https://studio.test/**",async route=>{
      const request=route.request(),url=new URL(request.url());
      const path=url.pathname;
      function ok(data,status=200){return route.fulfill({status,contentType:"application/json",body:JSON.stringify(data)})}
      if(path==="/"&&request.method()==="GET")return route.fulfill({status:200,contentType:"text/html",body:html});
      if(path.startsWith("/ui/")){const file=await panel.fetch(new Request("https://studio.test"+path),{});return route.fulfill({status:file.status,contentType:file.headers.get("content-type")||"text/javascript",body:await file.text()})}
      if(path==="/api/login"&&request.method()==="POST"){logged=true;return ok({ok:true})}
      if(path==="/api/me")return logged?ok({csrf:"csrf-test",github_connected:false}):ok({error:"not logged"},401);
      if(path==="/api/studio/projects"&&request.method()==="GET"){
        return ok({projects:project?[{id:project.id,topic:project.topic,revision:project.revision,updated_at:"2026-11-09"}]:[]});
      }
      if(path==="/api/studio/projects"&&request.method()==="POST"){
        const req=request.postDataJSON();
        const chunks=req.script.match(/[^.!?]+[.!?]?/g).map(x=>x.trim()).filter(Boolean);
        const frames=req.duration_seconds*30;
        const unit=Math.floor(frames/chunks.length);
        let start=0;
        project={schema_version:3,id:"22222222-2222-4222-8222-222222222222",
          revision:1,topic:req.topic,script:req.script,fps:30,aspect:req.aspect,
          total_frames:frames,assets:[],tracks:[{id:"video",kind:"video"}],
          scenes:chunks.map((chunk,i)=>{
            const duration_frames=i===chunks.length-1?frames-start:unit;
            const scene={id:"scene-"+String(i+1).padStart(3,"0"),track_id:"video",title:chunk,
              text:chunk,kind:"text",asset_id:null,start_frame:start,duration_frames,
              animation:"cut",framing:"contain"};
            start+=duration_frames;return scene;
          })};
        return ok({project},201);
      }
      if(path==="/api/studio/projects/"+project?.id&&request.method()==="GET")return ok({project});
      if(path==="/api/studio/projects/"+project?.id+"/save"&&request.method()==="POST"){
        const body=request.postDataJSON();
        if(body.revision!==project.revision)return ok({error:"revision conflict"},409);
        project={...project,revision:project.revision+1,assets:body.assets,scenes:body.scenes};
        return ok({project});
      }
      return ok({error:"not found"},404);
    });
    await page.goto("https://studio.test/");
    await page.locator("#password").fill("SomeValidLoginPassword");
    await page.locator("#loginForm button[type=submit]").click();
    await page.locator('[data-mobile="videos"]').click();
    await page.locator("#studioTopic").fill("Como criar repositórios");
    await page.locator("#studioScript").fill("Crie sua conta no GitHub. Escolha o nome do repositório. Publique os arquivos.");
    await page.locator("#studioDuration").fill("30");
    await page.locator("#studioCreateButton").click();
    await page.locator("#studioTimeline [data-studio-scene]").first().waitFor();
    assert.equal(await page.locator("#studioTimeline [data-studio-scene]").count(),3);
    await page.locator("#studioTimeline [data-studio-scene]").nth(1).click();
    await page.locator("#studioSceneTitle").fill("Cena editada");
    await page.locator("#studioSceneTitle").press("Tab");
    assert.match(await page.locator("#studioStageTitle").textContent(),/Cena editada/);
    await page.locator("#studioSave").click();
    await page.getByText("Revisão 2 salva", {exact:false}).first().waitFor();
    assert.equal(project.revision,2);
    await page.locator("#studioOpen").click();
    assert.equal(await page.locator("#studioSceneTitle").inputValue(),project.scenes[0].title);
    const dimensions=await page.evaluate(()=>({width:document.documentElement.scrollWidth,viewport:window.innerWidth}));
    assert.ok(dimensions.width<=dimensions.viewport+6,"O painel não deve gerar scroll horizontal global no celular");
    assert.deepEqual(errors,[]);
  }finally{await browser.close()}
});
