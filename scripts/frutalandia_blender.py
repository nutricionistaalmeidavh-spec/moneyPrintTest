"""3D CGI episode rendered with Blender Cycles. No paid cloud models.

Run: blender -b --python scripts/frutalandia_blender.py -- story.json output_dir
Renders real animated 3D meshes (actors, expressions, body motion and camera).
"""
import bpy
import json
import math
import os
import sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(args) != 2:
    raise SystemExit("Usage: blender -b --python frutalandia_blender.py -- story.json outdir")
story = json.loads(Path(args[0]).read_text(encoding="utf-8"))
outdir = Path(args[1])
outdir.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for data in bpy.data.materials:
    bpy.data.materials.remove(data)

FPS = 12
RES_X, RES_Y = 360, 640
CHAR_IDS = [x["id"] for x in story["characters"]]
MATS = {}


def mat(name, rgb, metallic=0.0, rough=0.35, emit=0.0):
    key = (name, tuple(rgb))
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    if emit:
        try:
            bsdf.inputs["Emission Color"].default_value = (*rgb, 1)
            bsdf.inputs["Emission Strength"].default_value = emit
        except KeyError:
            bsdf.inputs["Emission"].default_value = (*rgb, 1)
    MATS[key] = m
    return m


RED = mat("Morango vermelho acetinado", (.69,.025,.055), rough=.26)
GREEN = mat("folhas verdes", (.10,.48,.15))
PURPLE = mat("uva roxa perolada", (.25,.055,.48), rough=.24)
PEAR = mat("pera verde dourada", (.62,.74,.20))
ORANGE = mat("caju coral", (.96,.29,.075))
YELLOW = mat("caju amarelo", (.98,.59,.10))
DARK = mat("cabelo preto", (.045,.03,.075))
BROWN = mat("cabelo castanho", (.20,.075,.038))
PINK = mat("rosa bolsa", (.92,.18,.44))
WHITE = mat("olhos marfim", (.97,.94,.87))
BLACK = mat("pupila preta", (.012,.010,.018))
LIPS = mat("labios", (.30,.020,.040))
GOLD = mat("brincos dourados", (.93,.64,.20), metallic=.85, rough=.16)
SILVER = mat("prata", (.68,.79,.90), metallic=.8, rough=.15)
TOP_GREEN = mat("top verde de Moranguete", (.07,.38,.29))
TOP_BLACK = mat("top preto de Uva", (.045,.04,.085))
TOP_PEAR = mat("vestido floral Pera", (.18,.30,.45))
TOP_BLUE = mat("polo azul marinho Caju", (.06,.10,.28))
JEANS = mat("jeans", (.09,.14,.36))
SHOE = mat("tenis", (.89,.84,.80))
WALL = mat("parede creme escura", (.30,.22,.26), rough=.9)
FLOOR = mat("piso madeira", (.24,.12,.075), rough=.65)
SOFA = mat("sofa veludo", (.25,.19,.41))
PHONE = mat("brilho azul celular", (.07,.58,1.0), emit=6)
SHADOW = mat("tapete", (.14,.12,.23))
WOOD = mat("mesa", (.35,.18,.09))


def sphere(name, loc, scale, material, parent=None, segments=20, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=(0,0,0))
    o = bpy.context.object
    o.name = name
    o.location = loc
    o.scale = scale
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def cube(name, loc, scale, material, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
    o = bpy.context.object
    o.name = name
    o.location = loc
    o.scale = scale
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    bevel = o.modifiers.new("borda macia", "BEVEL")
    bevel.width = .09
    bevel.segments = 2
    o.modifiers.new("normais suaves", "WEIGHTED_NORMAL")
    return o


def empty(name, loc=(0,0,0), parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.location = loc
    if parent:
        o.parent = parent
    return o


def torus(name, loc, scale, material, parent=None):
    bpy.ops.mesh.primitive_torus_add(major_segments=24, minor_segments=8,
                                    location=(0,0,0), major_radius=.20, minor_radius=.035)
    o = bpy.context.object
    o.name = name
    o.location = loc
    o.scale = scale
    o.rotation_euler = (math.pi/2, 0, 0)
    o.data.materials.append(material)
    if parent:
        o.parent = parent
    return o


def build_character(char_id, x, stage_i):
    root = empty("%02d_%s_CORPO" % (stage_i,char_id), (x,0,0))
    clothes = {"moranguete": TOP_GREEN, "uva": TOP_BLACK,
               "mae-pera": TOP_PEAR, "pai-caju": TOP_BLUE}[char_id]
    headmat = {"moranguete": RED, "uva": PURPLE,
               "mae-pera": PEAR, "pai-caju": ORANGE}[char_id]
    body = sphere(char_id+"_torso", (0,0,1.58), (.43,.29,.63), clothes, root)
    if char_id == "mae-pera":
        sphere("vestido_sainha", (0,0,1.13), (.55,.39,.32), clothes, root)
    for side in (-1, 1):
        sphere("perna", (side*.23,0,.61), (.15,.17,.52), JEANS, root)
        sphere("sapato", (side*.23,-.12,.13), (.22,.33,.12), SHOE, root)
        pivot=empty("ombro_animado", (side*.43,0,1.93), root)
        sphere("braço", (side*.17,0,-.36), (.19,.21,.44), clothes, pivot)
        sphere("mao", (side*.18,-.05,-.72), (.16,.17,.19), headmat, pivot)
        pivot["arm_side"]=side
        root["arm_%s"%side]=pivot.name
    neck=sphere("pescoço", (0,0,2.17), (.20,.18,.22), headmat, root)
    h=empty(char_id+"_cabeca", (0,0,2.91), root)
    fruit=sphere(char_id+"_fruta_3d", (0,0,0), (.68,.59,.77), headmat, h, 32,20)
    if char_id == "moranguete":
        for vert in fruit.data.vertices:
            factor=.82+.19*vert.co.z
            vert.co.x*=factor
            vert.co.y*=factor
        for i in range(4):
            angle=i*math.pi/2
            leaf=sphere("folha_verde", (.30*math.cos(angle),.30*math.sin(angle),.74),
                        (.38,.17,.09), GREEN, h)
            leaf.rotation_euler[1]=-.35
        for row in range(3):
            for col in range(5):
                px=(col-2)*.19+(row%2)*.05
                pz=.46-row*.29
                if abs(px)> .48:
                    continue
                sphere("sementes_douradas", (px,-.60,pz), (.025,.016,.055),
                       GOLD,h,8,6)
        for k in range(5):
            sphere("cabelo_ondulado", ((k-2)*.22,.10,.75),
                   (.21,.25,.22), BROWN, h)
    elif char_id=="uva":
        for z, count in ((.53,3),(.20,4),(-.11,3),(-.36,2)):
            for k in range(count):
                xg=(k-(count-1)/2)*.37
                sphere("gomo_uva", (xg,.03,z), (.28,.28,.30),PURPLE,h)
        for k in range(4):
            sphere("cabelo_escuro", ((k-1.5)*.26,.17,.73),(.22,.20,.17),DARK,h)
    elif char_id=="mae-pera":
        for v in fruit.data.vertices:
            # pera larga embaixo, afunila até o topo
            factor=.98-.26*v.co.z
            v.co.x*=factor
            v.co.y*=factor
        sphere("coque", (0,.26,.83), (.28,.29,.27),BROWN,h)
        sphere("talo", (0,.08,.88),(.08,.09,.22),WOOD,h)
    else:
        fruit.scale=(.65,.57,.82)
        sphere("blush_caju", (0,-.17,-.35),(.55,.52,.31),YELLOW,h)
        sphere("tampa_azul", (0,.03,.80),(.66,.63,.10),TOP_BLUE,h)
        cube("aba_do_bone", (0,-.40,.77),(.43,.28,.045),TOP_BLUE,h)
        for k in range(3):
            sphere("barba", ((k-1)*.22,-.52,-.57),(.17,.08,.11),DARK,h)
    eye_y=-.57 if char_id!="uva" else -.66
    for side in (-1,1):
        sphere("olho_branco", (side*.26,eye_y,.17),(.15,.10,.19), WHITE,h)
        sphere("pupila", (side*.26,-.66 if char_id!="uva" else -.76,.15),
               (.073,.048,.09),BLACK,h)
        brow=sphere("sobrancelha", (side*.27,eye_y-.05,.42),
                    (.17,.05,.035),DARK,h)
        brow.rotation_euler[1]=side*.13
        if char_id in ("moranguete","mae-pera","uva"):
            torus("brinco", (side*.64,-.07,-.21),(.36,.58,.36),
                  GOLD if char_id!="uva" else SILVER,h)
    mouth=torus("boca_falante", (0,eye_y-.05,-.28),(.57,.60,.46),LIPS,h)
    if char_id=="moranguete":
        cube("bolsa_rosa", (.56,.15,1.40),(.23,.16,.32),PINK,root)
        cube("celular_luminoso", (.83,-.45,1.59),(.13,.045,.22),PHONE,root)
    return root,h,mouth


def room(stage, i):
    X=i*21.0
    cube("piso_cenario", (X,0,-.25), (8,8,.23), FLOOR)
    cube("parede_atras", (X,4,3.65), (8,.25,3.7), WALL)
    cube("rodape", (X,3.65,.24), (7,.12,.14), WOOD)
    cube("tapete_sala", (X,-.2,.017),(2.7,2,.018),SHADOW)
    if i in (0,1,3):
        cube("sofa", (X+2,1,1.02), (1.7,.65,.55), SOFA)
        cube("costas_sofa", (X+2,1.62,1.36),(1.85,.22,.72), SOFA)
        cube("mesa_centro", (X,-2,.6), (1.2,.66,.12),WOOD)
        for k in (-1,1):
            cube("pe_mesa",(X+k*.93,-2,.32),(.10,.10,.31), WOOD)
    elif i in (4,5):
        for k in range(5):
            cube("escadaria", (X+2.8+k*.55, 1.65+k*.43, .28+k*.32),
                 (1.75,.53,.25+k*.32), WOOD)
    else:
        cube("balcao_cozinha",(X+2.4,1.75,.77),(1.7,.65,.77),WOOD)
    # brilho do teto e contraluz azul misteriosa
    def light(name, loc, power, color, size):
        bpy.ops.object.light_add(type="AREA", location=loc)
        o=bpy.context.object
        o.name=name
        o.data.energy=power
        o.data.color=color
        o.data.shape="DISK"
        o.data.size=size
        direction=Vector((X,0,2.1))-o.location
        o.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()
    light("luz_quente_cinematografica",(X-3.5,-3,7),1000,(1,.67,.42),6)
    light("rim_lighting_azul",(X+3,2,5.5),520,(.24,.55,1),4)
    return X


bpy.ops.object.camera_add()
camera=bpy.context.object
camera.name="Camera_3D_frutas"
bpy.context.scene.camera=camera
camera.data.lens=42
camera.data.dof.use_dof=False

frame_cursor=1
for idx, scene_spec in enumerate(story["scenes"]):
    X=room(scene_spec,idx)
    identities = (
        ["moranguete","uva"] if idx in (0,1) else
        ["pai-caju","mae-pera"] if idx==2 else
        ["mae-pera","moranguete"] if idx==3 else
        ["moranguete","uva"] if idx==4 else
        ["moranguete","uva","mae-pera","pai-caju"]
    )
    positions = [X+((j-(len(identities)-1)/2)*1.55) for j in range(len(identities))]
    cast = [build_character(cid,x,idx) for cid,x in zip(identities,positions)]
    first=frame_cursor
    last=first+scene_spec["seconds"]*FPS-1
    speaker=scene_spec["dialogue"][0]["speaker"]
    for cidx,(root,head,mouth) in enumerate(cast):
        actor = identities[cidx]
        for t in range(first,last+1,6):
            phase=(t-first)*.15+cidx*1.8
            root.rotation_euler.z=.045*math.sin(phase)
            root.keyframe_insert(data_path="rotation_euler",frame=t)
            root.location.z=.055*math.sin(phase)
            root.keyframe_insert(data_path="location",frame=t)
            head.rotation_euler.y=.09*math.sin(phase*.82)
            head.rotation_euler.z=.07*math.sin(phase*.70)
            head.keyframe_insert(data_path="rotation_euler",frame=t)
            # Boca se move enquanto o personagem fala
            mouth.scale.y=.50 if actor==speaker and int((t-first)/6)%2 else .15
            mouth.keyframe_insert(data_path="scale",frame=t)
            for side in (-1,1):
                arm=bpy.data.objects[root["arm_%s"%side]]
                arm.rotation_euler.y=(.25 if actor==speaker else .08)*math.sin(phase)
                arm.keyframe_insert(data_path="rotation_euler",frame=t)
    # corte entre cenas; movimento cinematográfico dentro de cada tomada
    lead_index=identities.index(speaker)
    focus=positions[lead_index]
    if idx==5:
        focus=X
    if first>1:
        camera.location=(previous_focus, -9.1, 3.6)
        look=Vector((previous_focus,0,2.15))
        camera.rotation_euler=(look-camera.location).to_track_quat("-Z","Y").to_euler()
        camera.keyframe_insert(data_path="location",frame=first-1)
        camera.keyframe_insert(data_path="rotation_euler",frame=first-1)
    camera.location=(focus-0.23,-9.15,3.5)
    look=Vector((focus,0,2.15))
    camera.rotation_euler=(look-camera.location).to_track_quat("-Z","Y").to_euler()
    camera.keyframe_insert(data_path="location",frame=first)
    camera.keyframe_insert(data_path="rotation_euler",frame=first)
    camera.location=(focus+.20,-8.40,3.52)
    camera.rotation_euler=(look-camera.location).to_track_quat("-Z","Y").to_euler()
    camera.keyframe_insert(data_path="location",frame=last)
    camera.keyframe_insert(data_path="rotation_euler",frame=last)
    previous_focus=focus
    frame_cursor=last+1

sc=bpy.context.scene
sc.frame_start=1
sc.frame_end=1 if os.environ.get("FRUTALANDIA_SMOKE")=="1" else frame_cursor-1
sc.render.resolution_x=RES_X
sc.render.resolution_y=RES_Y
sc.render.resolution_percentage=50 if os.environ.get("FRUTALANDIA_SMOKE")=="1" else 100
sc.render.fps=FPS
sc.world.color=(.15,.11,.16)
sc.render.engine="CYCLES"
sc.cycles.samples=1 if os.environ.get("FRUTALANDIA_SMOKE")=="1" else 4
sc.cycles.use_denoising=False
try:
    bpy.context.view_layer.cycles.use_denoising=False
except AttributeError:
    pass
chosen="CPU"
try:
    pref=bpy.context.preferences.addons["cycles"].preferences
    pref.compute_device_type="CUDA"
    pref.get_devices()
    cuda=[dev for dev in pref.devices if dev.type=="CUDA"]
    if cuda:
        for d in pref.devices:
            d.use=(d.type=="CUDA")
        sc.cycles.device="GPU"
        chosen="CUDA "+", ".join(d.name for d in cuda)
except Exception as exc:
    print("GPU Cycles indisponível, fallback CPU:",exc)
if chosen=="CPU":
    sc.cycles.samples=2
sc.render.image_settings.file_format="FFMPEG"
sc.render.ffmpeg.format="MPEG4"
sc.render.ffmpeg.codec="H264"
sc.render.ffmpeg.constant_rate_factor="MEDIUM"
sc.render.ffmpeg.ffmpeg_preset="GOOD"
sc.render.filepath=str(outdir/"silent.mp4")
print("FRUTALANDIA RENDER",sc.frame_end,"frames",chosen,flush=True)
(outdir/"blender-render-config.json").write_text(json.dumps({
    "engine":"Blender Cycles","device":chosen,"frames":sc.frame_end,"fps":FPS,
    "resolution":[RES_X,RES_Y], "scene_count":len(story["scenes"])
},indent=2))
bpy.ops.render.render(animation=True)
files=list(outdir.glob("silent*.mp4"))
if not files or max(p.stat().st_size for p in files)<100000:
    raise RuntimeError("Blender não criou vídeo silencioso válido")
print("FRUTALANDIA_RENDER_OK",max(files,key=lambda p:p.stat().st_size),flush=True)
