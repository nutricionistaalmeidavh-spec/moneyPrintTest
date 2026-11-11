import React from 'react';
import {AbsoluteFill, Easing, Img, interpolate, useCurrentFrame} from 'remotion';
import {clamp, ease} from '../../core/ease';
import {n2} from '../../core/random';
import {FilmGrain, PaperTexture, Vignette, useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';
import {Plate, PlatePaletteName, RainLayer, resolveSrc} from '../../core/image-kit';
import {kickAt, punchZoom, rigAt} from '../../core/r2-e2-cam-kit';

/**
 * Ken Burns camera on a still plate.
 *  - push / pull / pan at measured rates: ambient 0.6–2 %/s, emotional 3–5 %/s (video16),
 *    woodblock 2–4 % per shot (video10), warm push ≈ 8–9 %/s (video11 ken-burns-push).
 *  - punch-in cut: hard cut to ≈1.25x re-centred on the subject (video10 3.50 s).
 *  - tall-tilt: one tall picture tilted bottom -> top with cubic-bezier(.45,0,.4,1), lateral drift
 *    ≈70 px/s, fade from black 0.2 -> 0.6 s (video21 cold open).
 *  - optional 1–2 px handheld noise, rain streaks and print grain + paper fibre (video10 recipe).
 */
type Props = {
  src: string;
  images: string[];
  seed: number;
  palette: PlatePaletteName;
  mode: 'push' | 'pull' | 'pan' | 'tall-tilt';
  rate: number;
  focus: number[];
  pan: number[];
  easing: 'linear' | 'sine' | 'inOut';
  handheld: number;
  punchAt: number;
  punchScale: number;
  punchFocus: number[];
  drift: number;
  rain: boolean;
  rainDensity: number;
  grain: number;
  paper: number;
  vignette: number;
  fadeIn: number;
  punches: {at: number; zoom: number}[];
  kick: {at: number; amp: number}[];
  rig: number;
  gait: number;
  fear: number[];
  holdBreath: number[][];
  layers: {src: string; depth: number}[];
  depthRate: number;
};

const EASE = {linear: Easing.linear, sine: ease.sine, inOut: ease.inOut};

const KenBurns: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const {w, h, u, fps, durationInFrames: D} = useStage();
  const shots = p.images.length > 0 ? p.images : [p.src];
  const n = shots.length;
  const shotLen = D / n;
  const si = Math.min(n - 1, Math.floor(frame / shotLen));
  const s0 = si * shotLen;
  const lf = frame - s0;
  const T = shotLen / fps;
  const t = clamp(lf / shotLen);
  const et = EASE[p.easing](t);
  const src = shots[si] || '';

  // handheld micro noise (1–2 px)
  const hx = n2('kbx' + p.seed, frame * 0.023, 0.3) * p.handheld * u + n2('kbx2', frame * 0.07, 1.1) * p.handheld * 0.35 * u;
  const hy = n2('kby' + p.seed, frame * 0.021, 2.7) * p.handheld * u + n2('kby2', frame * 0.065, 4.2) * p.handheld * 0.35 * u;
  const margin = 1 + (6 * p.handheld * u) / Math.min(w, h);

  // R2 extras (all off by default): handheld fear rig, beat kicks, multi-plane layers
  const rg = rigAt(frame, fps, h, u, D, {amount: p.rig, gait: p.gait, breathHz: 0.27, fear: p.fear, holdBreath: p.holdBreath}, p.seed);
  const kk = kickAt(frame, fps, p.kick, u);
  const ex = rg.x + kk.x;
  const ey = rg.y + kk.y;
  const eroll = rg.roll + kk.r;
  const extraOn = p.rig > 0 || p.kick.length > 0;

  const fade = p.fadeIn > 0 ? interpolate(frame, [p.fadeIn * 0.33, p.fadeIn], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;

  let layer: React.ReactNode;
  if (p.mode === 'tall-tilt') {
    // one tall picture, camera tilts up across it; content also drifts left (camera pans right)
    const a = Math.round(D * 0.12);
    const b = Math.round(D * 0.9);
    const k = interpolate(frame, [a, b], [0, 1], {easing: Easing.bezier(0.45, 0, 0.4, 1), extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    const driftTotal = Math.abs(p.drift) * u * ((b - a) / fps);
    const Wt = Math.round(w + driftTotal + 8 * u);
    const Ht = Math.round(h * 2.7);
    const dx = -(p.drift >= 0 ? k : 1 - k) * driftTotal;
    const ty = src ? `calc(${-(1 - k)} * max(0px, 100% - ${h}px))` : `${-(1 - k) * (Ht - h)}px`;
    layer = (
      <div style={{position: 'absolute', left: 0, top: 0, width: Wt, transform: `translate(${dx + hx}px, ${hy}px)`}}>
        <div style={{transform: `translateY(${ty})`}}>
          {src ? (
            <Img src={resolveSrc(src)} style={{display: 'block', width: Wt, height: 'auto'}} />
          ) : (
            <div style={{position: 'relative', width: Wt, height: Ht}}>
              <Plate seed={p.seed} palette={p.palette} width={Wt} height={Ht} tall />
            </div>
          )}
        </div>
      </div>
    );
  } else {
    const dir = p.mode === 'pull' ? -1 : p.mode === 'pan' ? 0 : n > 1 ? (si % 2 === 0 ? 1 : -1) : 1;
    const total = (Math.abs(p.rate) / 100) * T; // scale change over the shot
    let scale = dir >= 0 ? 1 + total * et : 1 + total * (1 - et);
    if (dir === 0) scale = 1;
    // pan in px/s (1080-units), centred so the plate stays covered
    const panX = (p.pan[0] ?? 0) * u * T;
    const panY = (p.pan[1] ?? 0) * u * T;
    const tx = panX * (et - 0.5);
    const ty = panY * (et - 0.5);
    const panCover = 1 + Math.max(Math.abs(panX) / w, Math.abs(panY) / h) + 0.004;
    // punch-in cut (hard cut, no transition frames)
    const pa = p.punchAt;
    const stepZ = punchZoom(frame, p.punches, s0, s0 + shotLen);
    const inShot = pa >= s0 && pa < s0 + shotLen;
    const punched = p.punchAt >= 0 && inShot && frame >= pa;
    const fx = (punched ? p.punchFocus[0] : p.focus[0]) ?? 0.5;
    const fy = (punched ? p.punchFocus[1] : p.focus[1]) ?? 0.5;
    const ps = punched ? p.punchScale : 1;
    const extraCover = extraOn ? 1.03 : 1;
    const S = scale * margin * panCover * ps * stepZ * extraCover * rg.scale;
    const tf = `translate(${tx + hx + ex}px, ${ty + hy + ey}px) rotate(${eroll}deg) scale(${S})`;
    if (p.layers.length > 0) {
      // multi-plane dolly: near layers grow faster than far ones about the focus point
      layer = (
        <AbsoluteFill>
          {p.layers.map((ly, i) => {
            const d = clamp(ly.depth);
            const sc = (1 + (p.depthRate / 100) * (lf / fps) * (0.4 + 0.6 * d)) * margin * panCover * stepZ * extraCover * rg.scale;
            const px = (p.pan[0] ?? 0) * u * (lf / fps) * d * 0.5;
            return (
              <AbsoluteFill key={i} style={{transform: `translate(${px + hx * (0.4 + d) + ex}px, ${hy * (0.4 + d) + ey}px) rotate(${eroll}deg) scale(${sc})`, transformOrigin: `${fx * 100}% ${fy * 100}%`}}>
                <Img src={resolveSrc(ly.src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
              </AbsoluteFill>
            );
          })}
        </AbsoluteFill>
      );
    } else {
      layer = (
        <AbsoluteFill style={{transform: tf, transformOrigin: `${fx * 100}% ${fy * 100}%`}}>
          <Plate src={src} seed={p.seed + si} palette={p.palette} />
        </AbsoluteFill>
      );
    }
  }

  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      <AbsoluteFill style={{opacity: fade}}>
        {layer}
        {p.rain && <RainLayer frame={frame} density={p.rainDensity} angle={15} speed={0.9} color="#e8ecf5" opacity={0.85} seed={p.seed} />}
        {p.paper > 0 && <PaperTexture opacity={p.paper * 4} tint="#6b5a40" />}
        {p.vignette > 0 && <Vignette strength={p.vignette} />}
        {p.grain > 0 && <FilmGrain opacity={p.grain * 2.2} />}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const kenBurns = defineMotion<Props>({
  id: 'ken-burns',
  title: 'Ken Burns push / pull / tilt',
  category: 'image',
  description: 'Slow push, pull, pan or tall tilt-up across a still plate with handheld noise, an optional punch-in cut, rain and print grain.',
  source: ['video10 0:00-0:42 woodblock-ken-burns + punch-in-cut', 'video16 slow-push-ken-burns', 'video22 shot-push-in', 'video21 0:01-0:07 tall-tilt-reveal', 'video11 ken-burns-push'],
  useFor: 'Turning any still (AI art, photo, illustration) into a living shot; emphasis punch-ins on a caption beat; cold-open tilt reveals of tall images.',
  durationInFrames: 180,
  defaultProps: {
    src: '',
    images: [],
    seed: 1,
    palette: 'dusk',
    mode: 'push',
    rate: 2.5,
    focus: [0.62, 0.55],
    pan: [-14, 0],
    easing: 'sine',
    handheld: 1.5,
    punchAt: 96,
    punchScale: 1.25,
    punchFocus: [0.63, 0.56],
    drift: 70,
    rain: false,
    rainDensity: 0.6,
    grain: 0.04,
    paper: 0.06,
    vignette: 0.3,
    fadeIn: 0,
    punches: [] as {at: number; zoom: number}[],
    kick: [] as {at: number; amp: number}[],
    rig: 0,
    gait: 1.8,
    fear: [0] as number[],
    holdBreath: [] as number[][],
    layers: [] as {src: string; depth: number}[],
    depthRate: 2,
  },
  propDocs: {
    src: 'public/ image path (e.g. "demo/owl.jpg"); empty = procedural dusk plate',
    images: 'several public/ images: the duration is split into hard-cut shots alternating push / pull',
    seed: 'procedural plate seed',
    palette: 'procedural plate palette: dusk | night | dawn',
    mode: 'push | pull | pan | tall-tilt (tilts bottom -> top over a tall image)',
    rate: 'scale change in %/s (ambient 0.6–2, emotional 3–5, warm push 8–9)',
    focus: '[x, y] 0..1 point the push moves toward (subject / eyes)',
    pan: '[dx, dy] lateral drift in px/s at 1080p',
    easing: 'linear | sine | inOut (shot-push-in uses inOut)',
    handheld: 'handheld noise amplitude in px (0 = locked off)',
    punchAt: 'frame of the punch-in hard cut (-1 = off)',
    punchScale: 'extra scale at the punch-in (≈1.25)',
    punchFocus: '[x, y] subject the punch-in re-centres on',
    drift: 'tall-tilt horizontal drift in px/s (camera pans right for positive)',
    rain: 'overlay 3-layer rain streaks',
    rainDensity: 'rain density multiplier',
    grain: 'print grain amount (0.04 ≈ source)',
    paper: 'paper fibre multiply amount (0.06 ≈ source)',
    vignette: 'corner darkening 0..1',
    fadeIn: 'fade from black over this many frames (tall-tilt source: 18)',
    punches: 'stepped beat punch-ins [{at: frame, zoom}] e.g. [{at:60,zoom:1.4},{at:75,zoom:2},{at:90,zoom:2.9}]',
    kick: 'damped kick shakes on hits [{at: frame, amp: px}]',
    rig: 'handheld camcorder rig amount (0 = off, 1 = documentary): gait bob, sway, roll, breathing, tremor',
    gait: 'rig: footsteps per second',
    fear: 'rig: fear keys 0..1 spread across the duration; tremor grows with fear',
    holdBreath: 'rig: [[fromFrame, toFrame]] ranges where bob and breathing freeze',
    layers: 'multi-plane dolly: [{src, depth 0..1}] full-frame (transparent png) layers, far to near; near layers push faster',
    depthRate: 'multi-plane: %/s zoom at depth 1 (far layers move 40 % of it)',
  },
  component: KenBurns,
  tags: ['image', 'camera', 'push-in', 'zoom', 'pan', 'tilt', 'punch-in', 'rain', 'grain', 'handheld', 'fear', 'multiplane', 'parallax', 'dolly', 'beat punch', 'camera shake'],
});
