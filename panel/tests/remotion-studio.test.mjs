import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
const panel=resolve(dirname(fileURLToPath(import.meta.url)), '..');
const read=(name)=>readFileSync(resolve(panel,name),'utf8');

test('engine selector is explicit and FFmpeg is always the default',()=>{
  const page=read('builder.html');
  const ui=read('studio-ui.mjs');
  assert.match(page, /id="studioRenderEngineCreate"/);
  assert.match(page, /id="studioRenderEngine"/);
  assert.match(page, /option value="ffmpeg" selected/);
  assert.match(page, /option value="remotion"/);
  assert.match(ui, /render_engine:studio.render_engine\|\|"ffmpeg"/);
  assert.match(ui, /render_engine:by\("studioRenderEngineCreate"\).value/);
});
test('backend dispatches remotion only when explicitly selected',()=>{
  const worker=read('worker.js');
  assert.match(worker, /project.render_engine==="remotion"\?"studio-remotion.yml":"studio-render.yml"/);
  assert.match(worker, /\(project.render_engine\?\?"ffmpeg"\)\s*===\s*"remotion"/);
  assert.match(worker, /render_engine:input.render_engine\?\?current.render_engine\?\?"ffmpeg"/);
});
