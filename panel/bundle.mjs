// Rebuilds the single-file Cloudflare Worker from source UI assets without npm dependencies.
import {readFileSync,writeFileSync} from "node:fs";
import {dirname,resolve} from "node:path";
import {fileURLToPath} from "node:url";
const folder=dirname(fileURLToPath(import.meta.url));
const get=n=>readFileSync(resolve(folder,n),"utf8");
const existing=get("worker.js");
const marker='\nconst REPO="nutricionistaalmeidavh-spec/moneyPrintTest";';
const markerIndex=existing.lastIndexOf(marker);
if(markerIndex<0)throw Error("Worker backend marker not found; refusing to overwrite");
const prefix="const PAGE="+JSON.stringify(get("builder.html"))+";\n"+
"const ASSETS="+JSON.stringify({
 "/ui/builder.css":{content:get("builder.css"),type:"text/css; charset=utf-8"},
 "/ui/builder.js":{content:get("builder.js"),type:"text/javascript; charset=utf-8"},
 "/ui/flow-core.mjs":{content:get("flow-core.mjs"),type:"text/javascript; charset=utf-8"}
})+";";
const generated=prefix+existing.slice(markerIndex);
if(process.argv.includes("--check")){
 if(existing!==generated){console.error("worker.js is stale; run node panel/bundle.mjs");process.exitCode=1}
 else console.log("Worker sources match bundled assets");
}else{
 writeFileSync(resolve(folder,"worker.js"),generated);
 console.log("Updated panel/worker.js from source assets");
}
