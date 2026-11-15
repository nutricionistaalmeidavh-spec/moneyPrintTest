import * as THREE from './node_modules/three/build/three.module.js';
const params=new URLSearchParams(location.search);
const offline=params.get('render')==='1';
document.body.classList.toggle('render',offline);
const by=id=>document.getElementById(id), viewport=by('viewport'), video=by('screenVideo');
const device=by('device'), motion=by('motion'), aspect=by('aspect');
const renderer=new THREE.WebGLRenderer({canvas:by('view'),antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(1);renderer.shadowMap.enabled=true;renderer.outputColorSpace=THREE.SRGBColorSpace;
const scene=new THREE.Scene();scene.background=new THREE.Color(0xe9e5db);
const camera=new THREE.PerspectiveCamera(36,16/9,.1,100);
scene.add(new THREE.HemisphereLight(0xffffff,0x7b8394,2.3));
const key=new THREE.DirectionalLight(0xffffff,3.1);key.position.set(-4,8,10);key.castShadow=true;scene.add(key);
const edge=new THREE.DirectionalLight(0xb4b7ff,1.4);edge.position.set(4,3,-5);scene.add(edge);
const ground=new THREE.Mesh(new THREE.PlaneGeometry(80,80),new THREE.ShadowMaterial({color:0x323445,opacity:.18}));
ground.rotation.x=-Math.PI/2;ground.position.y=-1.55;ground.receiveShadow=true;scene.add(ground);
const rig=new THREE.Group();scene.add(rig);
const mat=(color,metalness,roughness)=>new THREE.MeshStandardMaterial({color,metalness,roughness});
const metal=mat(0x9298a6,.78,.26),dark=mat(0x252934,.55,.39),black=mat(0x11151e,.25,.5),keys=mat(0x3c4451,.15,.65);
const blank=new THREE.MeshBasicMaterial({color:0x273957});
let screen=null,texture=null,fileUrl=null,start=performance.now();
function box(w,h,d,x,y,z,material){
  const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),material);
  mesh.position.set(x,y,z);mesh.castShadow=true;mesh.receiveShadow=true;rig.add(mesh);return mesh;
}
function applyTexture(){
  if(!screen)return;
  if(screen.material!==blank&&screen.material!==texture)screen.material.dispose();
  screen.material=texture?new THREE.MeshBasicMaterial({map:texture,side:THREE.FrontSide,toneMapped:false}):blank;
}
function buildDevice(kind){
  for(const item of [...rig.children]){rig.remove(item);item.geometry?.dispose();if(item.material!==metal&&item.material!==dark&&item.material!==black&&item.material!==keys&&item.material!==blank)item.material?.dispose();}
  if(kind==='monitor'){
    box(4.14,2.53,.16,0,.32,0,dark);box(3.95,2.29,.012,0,.34,.094,black);
    box(.21,1.10,.24,0,-1.03,-.12,metal);box(1.5,.09,.92,0,-1.48,.04,metal);
    screen=new THREE.Mesh(new THREE.PlaneGeometry(3.87,2.18),blank);
    screen.position.set(0,.34,.109);
  }else{
    box(4.12,2.49,.12,0,.18,-.18,dark);box(3.91,2.29,.015,0,.18,-.105,black);
    screen=new THREE.Mesh(new THREE.PlaneGeometry(3.82,2.17),blank);
    screen.position.set(0,.18,-.094);
    box(4.15,.095,2.42,0,-1.14,1.06,metal);
    box(3.72,.008,1.30,0,-1.087,.81,dark);
    for(let row=0;row<5;row++)for(let col=0;col<15;col++)box(.19,.014,.16,-1.56+col*.223,-1.072,.37+row*.22,keys);
    box(.94,.008,.51,0,-1.086,1.83,metal);
  }
  rig.add(screen);applyTexture();
}
function resize(){
  const w=Math.max(2,viewport.clientWidth),h=Math.max(2,viewport.clientHeight);
  renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();
}
function draw(t){
  const u=Math.max(0,Math.min(1,t/6)),e=u*u*(3-2*u);
  rig.rotation.set(0,0,0);rig.position.set(0,0,0);
  let z=camera.aspect<.75?14.2:camera.aspect<1.25?10.7:8.3;
  switch(motion.value){
    case 'orbit':rig.rotation.y=-.34+.68*Math.sin(t*.8);rig.rotation.x=.05*Math.sin(t*.5);break;
    case 'enter':rig.rotation.y=-.47*(1-e);rig.position.y=-1.1*(1-e);z+=3.4*(1-e);break;
    case 'zoom':z-=1.1*e;rig.rotation.y=.12*(1-e);break;
    case 'float':rig.rotation.z=.03*Math.sin(t*1.4);rig.position.y=.12*Math.sin(t*1.6);break;
  }
  camera.position.set(.12,1.05,z);camera.lookAt(0,-.14,.2);
  if(texture)texture.needsUpdate=true;
  renderer.render(scene,camera);
}
async function seek(t){
  if(!video.src||video.readyState<2)return;
  const d=Number.isFinite(video.duration)&&video.duration>0?video.duration:1;
  const target=Math.min(Math.max(0,t%d),Math.max(0,d-.025));
  if(Math.abs(video.currentTime-target)<.014)return;
  await new Promise((resolve,reject)=>{
    const timeout=setTimeout(()=>{cleanup();reject(new Error('Tempo limite ao buscar quadro de vídeo'))},5000);
    function cleanup(){clearTimeout(timeout);video.removeEventListener('seeked',done);video.removeEventListener('error',failed)}
    function done(){cleanup();resolve()}function failed(){cleanup();reject(new Error('Vídeo ilegível'))}
    video.addEventListener('seeked',done,{once:true});video.addEventListener('error',failed,{once:true});
    video.currentTime=target;
  });
}
window.renderAt=async t=>{if(offline)await seek(t);draw(t);return true};
window.mockupReady=false;
async function loadFile(file){
  if(!file)return;
  const ext=file.name.toLowerCase().split('.').pop();
  if(!['mp4','webm'].includes(ext))throw Error('Formato não suportado (MP4/WebM)');
  if(fileUrl)URL.revokeObjectURL(fileUrl);
  fileUrl=URL.createObjectURL(file);
  video.src=fileUrl;video.load();
  await new Promise((resolve,reject)=>{video.addEventListener('loadeddata',resolve,{once:true});video.addEventListener('error',()=>reject(new Error('Falha de vídeo')), {once:true})});
  if(texture)texture.dispose();
  texture=new THREE.VideoTexture(video);texture.colorSpace=THREE.SRGBColorSpace;
  texture.minFilter=THREE.LinearFilter;texture.magFilter=THREE.LinearFilter;
  applyTexture();if(!offline)video.play().catch(()=>{});draw(0);
}
by('videoFile').addEventListener('change',async e=>{try{await loadFile(e.target.files?.[0]);by('message').textContent='Vídeo carregado, sem upload.'}catch(err){by('message').textContent=err.message}});
by('replay').addEventListener('click',()=>{start=performance.now();draw(0)});
device.addEventListener('change',()=>{buildDevice(device.value);draw(0)});
motion.addEventListener('change',()=>{start=performance.now();draw(0)});
aspect.addEventListener('change',()=>{const [a,b]=aspect.value.split(':').map(Number);viewport.style.aspectRatio=a+'/'+b;viewport.style.height='auto';resize();draw(0)});
window.addEventListener('resize',()=>{resize();draw(0)});
window.addEventListener('pagehide',()=>{if(fileUrl)URL.revokeObjectURL(fileUrl)});
if(offline){
  if(['laptop','monitor'].includes(params.get('device')))device.value=params.get('device');
  if(['enter','orbit','zoom','float'].includes(params.get('motion')))motion.value=params.get('motion');
}
buildDevice(device.value);resize();draw(0);
window.mockupReady=true;
function animate(){if(offline)return;draw((performance.now()-start)/1000);requestAnimationFrame(animate)}
if(!offline)requestAnimationFrame(animate);
