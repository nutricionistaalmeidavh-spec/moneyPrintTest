"""Smoke/E2E for the visual MoneyPrint editor: iPhone-sized + desktop browsers."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

PANEL=Path(__file__).resolve().parents[1]
ART=Path(os.environ.get("PANEL_QA_ARTIFACTS","qa-panel"))
ART.mkdir(parents=True,exist_ok=True)
FILES={"/":"builder.html","/ui/builder.css":"builder.css","/ui/builder.js":"builder.js","/ui/flow-core.mjs":"flow-core.mjs","/ui/studio-ui.mjs":"studio-ui.mjs"}
MIME={"html":"text/html","css":"text/css","js":"text/javascript","mjs":"text/javascript"}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        if self.path in FILES:
            f=PANEL/FILES[self.path]
            self.send_response(200)
            self.send_header("Content-Type",MIME[f.suffix.lstrip(".")]+"; charset=utf-8")
            self.end_headers()
            self.wfile.write(f.read_bytes())
        elif self.path=="/api/me":
            self.json({"csrf":"qa-csrf","github_connected":False})
        elif self.path=="/api/flows":
            self.json({"flows":[]})
        else:
            self.send_error(404)
    def json(self,data):
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

def run():
    with ThreadingHTTPServer(("127.0.0.1",0),Handler) as server:
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        url="http://127.0.0.1:"+str(server.server_port)
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            iphone=browser.new_context(viewport={"width":390,"height":844},device_scale_factor=3,is_mobile=True,has_touch=True)
            page=iphone.new_page()
            failures=[]
            page.on("pageerror",lambda e:failures.append(str(e)))
            page.goto(url,wait_until="networkidle")
            page.locator("#application").wait_for(state="visible")
            assert page.locator("#mobileQuickTools").is_visible(),"No mobile quick-add!"
            assert page.locator("#toolsShowcase").count()==1
            page.screenshot(path=str(ART/"mobile-studio.png"),full_page=True)
            page.locator("#openToolLibrary").click()
            sheet=page.locator("#palette")
            assert sheet.is_visible(),"Tool library did not open"
            assert page.locator("#skillsList [data-apply-skill]").count()>=4
            r=sheet.bounding_box()
            assert r["y"]>=-1 and r["y"]+r["height"]<=844+2,r
            assert page.eval_on_selector("body","el => el.classList.contains('sheet-open')")
            page.locator("#searchTools").fill("Motion")
            assert page.locator("#toolList .tool").count()>0
            page.locator("#searchTools").fill("")
            page.screenshot(path=str(ART/"mobile-tools.png"))
            page.locator("#closePalette").click()
            assert not sheet.is_visible()
            page.locator("#quickToolButtons button[data-quick-tool='hook']").click()
            inspector=page.locator("#inspector")
            assert inspector.is_visible(),"Editor not open after adding node"
            box=inspector.bounding_box()
            assert box["y"]>=-1 and box["y"]+box["height"]<=844+2,box
            assert page.locator("#inspectorBody [data-setting='hook_asset']").count()==1
            page.screenshot(path=str(ART/"mobile-editor.png"))
            info=page.eval_on_selector("#inspector .contents","el=>({height:el.clientHeight,scroll:el.scrollHeight,max:el.scrollHeight-el.clientHeight})")
            assert info["height"]>=180,info
            page.eval_on_selector("#inspector .contents","el=>{el.scrollTop=el.scrollHeight}")
            assert page.locator("#doneInspector").is_visible()
            page.locator("#doneInspector").click()
            assert not inspector.is_visible()
            page.locator("[data-catalog-tab='skills']").click()
            assert page.locator("#showcaseCatalog [data-apply-skill]").count()>=5
            # Regression: clicking a packaged skill must attach actual nodes, not
            # mistake catalog metadata (id, icon, category) for external code.
            page.locator("#showcaseCatalog [data-apply-skill='repo-demo']").click()
            assert page.locator("#canvasNodes [data-tool='github']").count()==1
            assert page.locator("#canvasNodes [data-tool='slides']").count()==1
            assert "Formato de skill inválido" not in page.locator("#toast").inner_text()

            page.locator("#skillFileInput").set_input_files({
                "name":"sample-skill.json","mimeType":"application/json",
                "buffer":b'{"name":"Minha Skill","description":"Combina legendas e pesquisa.","tools":["captions","stock"]}'
            })
            page.locator("#showcaseCatalog").get_by_text("Minha Skill").wait_for(state="visible",timeout=4000)
            page.locator("#showcaseCatalog [data-apply-skill='custom-0']").click()
            assert page.locator("#canvasNodes [data-tool='captions']").count()==1
            assert "Formato de skill inválido" not in page.locator("#toast").inner_text()

            page.screenshot(path=str(ART/"mobile-skills.png"),full_page=True)
            assert not failures,failures
            desktop=browser.new_context(viewport={"width":1440,"height":900})
            dp=desktop.new_page()
            dp.goto(url,wait_until="networkidle")
            assert dp.locator("#toolsShowcase").is_visible(),"Desktop tool shelf not visible"
            assert dp.locator("#showcaseCatalog .showcase-card").count()>=5
            assert dp.locator("#canvasNodes .block").count()>=5
            dp.screenshot(path=str(ART/"desktop-studio.png"),full_page=True)
            browser.close()
        server.shutdown()
    print("PASS: iPhone and desktop visual editor; screenshots in",ART)

if __name__=="__main__":
    run()
