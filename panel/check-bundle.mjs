import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {dirname,join} from "node:path";
const dir=dirname(fileURLToPath(import.meta.url));
const source=file=>readFileSync(join(dir,file),"utf8");
const assets={
  "/ui/builder.css":{content:source("builder.css"),type:"text/css; charset=utf-8"},
  "/ui/builder.js":{content:source("builder.js"),type:"text/javascript; charset=utf-8"},
  "/ui/flow-core.mjs":{content:source("flow-core.mjs"),type:"text/javascript; charset=utf-8"}
};
const expected="const PAGE="+JSON.stringify(source("builder.html"))+";\nconst ASSETS="+JSON.stringify(assets)+";\n";
if(!source("worker.js").startsWith(expected)){
  console.error("ERROR: panel/worker.js bundle does not match the UI sources; update it before deploy.");
  process.exitCode=1;
}else{
  console.log("OK: Worker bundle matches HTML/CSS/JS and graph model.");
}
