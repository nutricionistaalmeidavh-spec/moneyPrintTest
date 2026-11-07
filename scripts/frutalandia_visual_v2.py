"""Frutalândia Visual V2: deterministic reusable CG character bible + nordeste set.

True Blender 3D geometry and node materials. No image generation, paid asset,
remote dependency, or stock-photo replacement. This module is bundled with the
Kaggle runner when available.
"""
from __future__ import annotations

import math
import bpy


def _principled(material):
    if not material or not material.use_nodes:
        return None
    return material.node_tree.nodes.get("Principled BSDF")


def enhance_material(material):
    """Give fruit skin subtle physical pores; keep exact palette across scenes."""
    if material.get("frutalandia_visual_v2"):
        return
    material["frutalandia_visual_v2"] = True
    bsdf = _principled(material)
    if bsdf is None:
        return
    name = material.name.lower()
    if any(x in name for x in ("uva roxa", "morango vermelho", "pera verde",
                                "caju coral", "caju amarelo")):
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 25.0
        tex.inputs["Detail"].default_value = 3.0
        tex.inputs["Roughness"].default_value = .65
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .12
        bump.inputs["Distance"].default_value = .015
        links.new(tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        bsdf.inputs["Roughness"].default_value = .28
        # Subsurface scattering on newer versions; roughness/pores still apply
        # on Blender releases which don't expose this particular input.
        for key in ("Subsurface Weight", "Subsurface"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = .07
                break
    elif any(x in name for x in ("jeans", "polo", "vestido", "top preto", "top verde")):
        bsdf.inputs["Roughness"].default_value = .61


def _curve(name, coords, material, radius=.018, parent=None):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 16
    data.bevel_depth = radius
    data.bevel_resolution = 3
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(coords) - 1)
    for p, xyz in zip(spline.bezier_points, coords):
        p.co = xyz
        p.handle_left_type = "AUTO"
        p.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(material)
    if parent is not None:
        obj.parent = parent
    return obj


def _shader(name, rgb, gloss=.24, emit=0):
    m = bpy.data.materials.get("V2_"+name)
    if m is not None:
        return m
    m = bpy.data.materials.new("V2_"+name)
    m.diffuse_color=(*rgb,1)
    m.use_nodes=True
    bsdf=m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=(*rgb,1)
    bsdf.inputs["Roughness"].default_value=gloss
    if emit and "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value=(*rgb,1)
        bsdf.inputs["Emission Strength"].default_value=emit
    elif emit and "Emission" in bsdf.inputs:
        bsdf.inputs["Emission"].default_value=(*rgb,1)
    return m


def detail_character(char_id, root, head, stage_i, sphere, cube, torus):
    """Polish the same four canonical characters on every shot.

    Camera-facing features use the existing -Y face convention; none of the
    additions replace or reidentify a character.
    """
    cream=_shader("perola_olho",(.99,.95,.88),.11)
    iris=_shader("iris_cafe",(.17,.093,.06),.12)
    glossy=_shader("brilho_olho",(.98,.99,1),.07,1.2)
    eyelash=_shader("pestana",(.08,.045,.065),.35)
    blush=_shader("blush",(.97,.21,.19),.64)
    mouth=_shader("interior_boca",(.16,.016,.035),.38)
    teeth=_shader("dentes",(.98,.96,.87),.16)
    outfit=_shader("costura_roupa",(.88,.76,.60),.37)
    counter_box=_shader("visor_fumê",(.03,.10,.13),.16)
    counter_red=_shader("display_laranja",(.99,.33,.12),.11,1.8)

    eye_y=-.72 if char_id=="uva" else -.65
    for side in (-1,1):
        # Large three-layer eyes + 2 specular glints, readable at 360 x 640.
        sphere("v2_iris_%s_%s"%(char_id,side),
               (side*.26,eye_y-.052,.14),(.101,.058,.112),iris,head,16,12)
        sphere("v2_brilho_olho_%s_%s"%(char_id,side),
               (side*.26-.033,eye_y-.105,.196),(.042,.019,.044),glossy,head,12,8)
        sphere("v2_reflexo_%s_%s"%(char_id,side),
               (side*.26+.038,eye_y-.103,.105),(.018,.012,.021),cream,head,10,8)
        for j in range(2):
            bx=side*(.30+.12*j)
            _curve("v2_pestana_%s_%s_%s"%(char_id,side,j),
                   [(bx,eye_y-.02,.32),(bx+side*.035,eye_y-.01,.38),
                    (bx+side*.065,eye_y+.03,.41)],eyelash,.014,head)
        eyelid=sphere("v2_palpebra_%s_%s_%s"%(stage_i,char_id,side),
                      (side*.26,eye_y-.035,.34),(.18,.045,.015),
                      eyelash,head,14,8)
        root["v2_eyelid_%s"%side]=eyelid.name
    # Blush is subtle and sits on the cheek, not over the irises.
    for side in (-1,1):
        sphere("v2_bochecha_%s_%s"%(char_id,side),
               (side*.46,eye_y+.05,-.17),(.13,.026,.067),blush,head,14,8)
    sphere("v2_nariz_%s"%char_id,
           (0,eye_y-.02,-.087),(.083,.074,.072),
           _shader("nariz_luz",(.94,.44,.32),.36),head,16,8)
    # Mouth is keyed independently from the pre-existing torus lip rig.
    inside=sphere("v2_boca_interna_%s_%s"%(stage_i,char_id),
                  (0,eye_y-.08,-.34),(.25,.016,.072),
                  mouth,head,20,12)
    sphere("v2_dentes_%s"%char_id,
           (0,eye_y-.098,-.298),(.17,.011,.027),teeth,head,16,8)
    root["v2_mouth_inside"]=inside.name

    # Character-specific silhouettes remain the same in every episode.
    if char_id=="moranguete":
        _curve("v2_frente_cabelo_moranguete",
               [(-.53,-.16,.63),(-.37,-.49,.80),(.10,-.49,.78),(.33,-.20,.66)],
               _shader("castanho_moranguete",(.25,.065,.028),.27),.095,head)
        for side in (-1,1):
            _curve("v2_cachos_moranguete_%s"%side,
                   [(side*.53,.05,.69),(side*.68,-.05,.20),
                    (side*.61,-.02,-.26),(side*.72,.08,-.55)],
                   _shader("castanho_moranguete",(.25,.065,.028)),.084,head)
        cube("v2_gola_green",(0,-.29,1.93),(.36,.06,.055),outfit,root)
    elif char_id=="uva":
        for side in (-1,1):
            _curve("v2_franja_uva_%s"%side,
                   [(side*.36,-.15,.80),(side*.23,-.45,.67),
                    (side*.40,-.48,.45)],_shader("cabelo_uva",(.045,.023,.09),.23),.11,head)
        cube("v2_cinto_uva",(0,-.28,1.16),(.34,.043,.075),
             _shader("cinto_preto",(.07,.05,.08),.32),root)
    elif char_id=="mae-pera":
        sphere("v2_rabo_cabelo_pera",(0,.38,.75),(.32,.25,.26),
               _shader("coque_pera",(.24,.105,.045),.34),head,20,12)
        # Collar pearls for a more mature recognizable character.
        for k in range(7):
            angle=math.pi*(k+1)/8
            sphere("v2_colar_perola",
                   (.36*math.cos(angle),-.28,.05+1.96-.25*math.sin(angle)),
                   (.047,.047,.047),cream,root,10,8)
    elif char_id=="pai-caju":
        for side in (-1,1):
            _curve("v2_bigode_caju_%s"%side,
                   [(0,eye_y-.045,-.31),(side*.19,eye_y-.09,-.29),
                    (side*.32,eye_y-.03,-.25)],eyelash,.05,head)
        cube("v2_gola_polo",(0,-.295,1.91),(.31,.08,.068),outfit,root)

    # The counter is a true piece of visible 3D hardware over the forehead.
    if "counter_object" in root:
        face=bpy.data.objects[root["counter_object"]]
        face.location=(0,-.715,.52)
        face.data.size=.235
        if counter_red not in face.data.materials[:]:
            face.data.materials.clear()
            face.data.materials.append(counter_red)
        cube("v2_painel_contador_%s_%s"%(stage_i,char_id),
             (0,-.665,.55),(.39,.025,.155),counter_box,head)
        # This also exercises Blender's standard bevel circle operator: the
        # circular LED indicator is independent of the digital number.
        bpy.ops.curve.primitive_bezier_circle_add(radius=.036)
        led=bpy.context.object
        led.name="v2_led_contador_%s"%char_id
        led.data.dimensions="3D"
        led.data.bevel_depth=.012
        led.data.materials.append(counter_red)
        led.parent=head
        led.location=(-.32,-.708,.56)
        led.rotation_euler=(math.pi/2,0,0)


def animate_details(root, head, first, last, speaking, char_id):
    """Emphasis / blink keyed per shot; result reproducible across rerenders."""
    for side in (-1,1):
        name=root.get("v2_eyelid_%s"%side)
        if not name:
            continue
        lid=bpy.data.objects.get(name)
        if lid is None:
            continue
        for frame in sorted({first, min(last,first+9), min(last,first+11), last}):
            closed=frame in (min(last,first+9),min(last,first+11))
            lid.scale.z=.26 if closed else .08
            lid.keyframe_insert(data_path="scale",frame=frame)
    inside=bpy.data.objects.get(root.get("v2_mouth_inside",""))
    if inside:
        for frame in range(first,last+1,3):
            speaking_now=(char_id==speaking)
            inside.scale.z=1.8 if speaking_now and (frame-first)//3%2 else .52
            inside.keyframe_insert(data_path="scale",frame=frame)
    for frame in sorted({first,first+max(1,(last-first)//2),last}):
        # Layered eye / head acting, on top of the existing broad torso motion.
        head.rotation_euler.x=.045*math.sin((frame-first)*.13+len(char_id))
        head.keyframe_insert(data_path="rotation_euler",frame=frame)


def detail_market(X, scene_i, cube, sphere):
    """Northeastern Brazilian outdoor feira: shops, banners, cacti, stalls."""
    sky=_shader("ceu_azul",(.27,.61,.84),.94)
    warm=_shader("casario_terracota",(.89,.35,.19),.76)
    turquoise=_shader("casario_turquesa",(.13,.58,.57),.62)
    ochre=_shader("casario_amarelo",(.95,.69,.31),.72)
    white=_shader("parede_cal",(.95,.86,.65),.73)
    red=_shader("lona_vermelha",(.87,.12,.14),.72)
    green=_shader("mandacaru",(.11,.41,.27),.58)
    brown=_shader("madeira_banca",(.38,.19,.075),.65)
    dark=_shader("placa_feira",(.08,.15,.18),.58)

    # Hide the old living-room back wall without deleting the canonical scene.
    cube("v2_parede_ceu",(X,3.70,3.45),(7.9,.04,3.60),sky)
    for k,wall in enumerate((warm,turquoise,ochre,white)):
        px=X-5.1+k*3.0
        cube("v2_casa_fachada_%s"%k,(px,3.25,1.85),(.92,.33,1.8),wall)
        cube("v2_porta_madeira_%s"%k,(px-.17,2.88,.72),(.36,.065,.68),brown)
        cube("v2_janela_%s"%k,(px+.25,2.87,1.97),(.26,.055,.30),dark)
        cube("v2_lintel_%s"%k,(px,2.85,2.62),(.95,.07,.14),white)

    # Striped fabric roof in place of a featureless rectangle.
    for k in range(8):
        cube("v2_toldo_listrado_%s"%k,
             (X-1.85+k*.50,.72,3.52),(.26,1.28,.065),red if k%2 else white)
    for side in (-1,1):
        cube("v2_estrutura_tenda_%s"%side,
             (X+side*1.88,.71,1.80),(.055,.055,1.77),brown)
    cube("v2_balcao_feira",(X,1.60,.86),(2.00,.70,.11),brown)
    cube("v2_caixa_fruta",(X-1.18,1.23,1.13),(.53,.42,.27),brown)
    for k in range(8):
        cx=X-1.26+(k%4)*.27
        cz=1.42+(k//4)*.18
        sphere("v2_fruta_caixa",(cx,1.0,cz),(.135,.135,.155),
               red if k%3==0 else ochre,segments=12,rings=8)

    # Textile flags are grouped into two receding bunting strands.
    flags=[red,ochre,turquoise,white]
    for strand,yy in enumerate((-.65,1.85)):
        z=4.35-strand*.38
        _curve("v2_varal_bandeirinha_%s"%strand,
               [(X-5.0,yy,z),(X,yy,z-.22),(X+5.0,yy,z)],
               _shader("corda_fibra",(.43,.30,.14),.85),.012)
        for k in range(13):
            fx=X-4.7+k*.77
            cube("v2_bandeirinha_%s_%s"%(strand,k),
                 (fx,yy,z-.31),(.17,.022,.20),flags[(k+strand)%4])

    # Mandacaru is unmistakable; silhouette at the edge of the composition.
    for side in (-1,1):
        sx=X+side*5.7
        sphere("v2_mandacaru_tronco",(sx,2.10,1.55),
               (.21,.20,1.65),green,segments=12,rings=8)
        sphere("v2_mandacaru_braço",(sx+side*.39,2.10,1.8),
               (.45,.17,.19),green,segments=12,rings=8)
        sphere("v2_mandacaru_ponta",(sx+side*.77,2.10,2.18),
               (.16,.17,.55),green,segments=12,rings=8)

    # Warm cobblestone rhythm, restrained geometry (no huge scene BVH).
    for k in range(10):
        bx=X-4.5+k
        cube("v2_pedras_rusticas",(bx,-2.4,.011),
             (.40,.31,.016),white if k%2 else warm)
