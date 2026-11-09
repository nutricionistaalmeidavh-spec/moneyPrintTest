import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {dirname,resolve} from "node:path";
import {fileURLToPath} from "node:url";
import {makeTemplate,applySkill,skillCatalog,parseSkillManifest,validateFlow} from "../flow-core.mjs";
const root=resolve(dirname(fileURLToPath(import.meta.url)),"..");
const read=n=>readFileSync(resolve(root,n),"utf8");

test("mobile editor has a clearly discoverable tool and skill entry point",()=>{
  const html=read("builder.html"),ui=read("builder.js");
  assert.match(html,/id="openToolLibrary"/);
  assert.match(html,/id="toolsShowcase"/);
  assert.match(html,/id="skillsList"/);
  assert.match(html,/id="closeInspector"/);
  assert.match(html,/id="closePalette"/);
  assert.match(ui,/renderToolShowcase/);
});
test("mobile sheet is a full-height modal with its own scroll area and no overlapping bottom nav",()=>{
  const css=read("builder.css");
  assert.match(css,/\.palette\.open,\.inspector\.open\{[^}]*z-index:1\d\d/s);
  assert.match(css,/\.palette\.open,\.inspector\.open\{[^}]*height:calc\(100dvh/s);
  assert.match(css,/\.palette\.open \.contents,\.inspector\.open \.contents\{[^}]*overflow-y:auto/s);
  assert.match(css,/body\.sheet-open/);
});
test("built-in skills apply only supported, functional modules",()=>{
  const f=makeTemplate("automatic");
  const added=applySkill(f,"repo-demo");
  assert.ok(added.nodes.some(n=>n.tool==="github"));
  assert.ok(added.nodes.some(n=>n.tool==="slides"));
  assert.equal(validateFlow(added).errors.length,0);
  assert.ok(skillCatalog.some(x=>x.id==="hook-cut"));
  assert.ok(skillCatalog.every(x=>x.tools.every(y=>typeof y==="string")));
});
test("custom skill manifests compose existing adapters, never arbitrary script execution",()=>{
  const manifest=parseSkillManifest('{"name":"Meu editor","tools":["captions","news"],"description":"Montagem e notícias."}');
  assert.equal(manifest.name,"Meu editor");
  assert.deepEqual(manifest.tools,["captions","news"]);
  assert.throws(()=>parseSkillManifest('{"name":"Código","tools":["docker-exec"],"command":"rm -rf"}'),/não suportad|inválid/i);
  assert.throws(()=>parseSkillManifest('{"name":"Pago","tools":["paid_tts"]}'),/não suportad|indisponível/i);
});
