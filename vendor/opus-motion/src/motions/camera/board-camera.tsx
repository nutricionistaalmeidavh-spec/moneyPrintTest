// Idea after lemo-opuscar styles/whiteboard demo/engine/wb.js (Camera, applyCam, Board.render, frame) (MIT, LemoLab) — see THIRD_PARTY_NOTICES.md.
// Own implementation: one transformed board div, log-zoom dolly weighting, speed-triggered directional blur, wall + frame on pull-back.
import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Layers, LayerSpec} from '../../Layers';
import {ease as easeLib, prog} from '../../core/ease';
import {fonts} from '../../core/fonts';
import {useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

type Region = {id: string; x: number; y: number; w: number; h: number; title: string; doodle?: string; at?: number; layers?: LayerSpec[]};
type CamKey = [number, number, number, number, number, string];
type Props = {
  regions: Region[];
  camera: (number | string)[][];
  boardW: number;
  boardH: number;
  boardColor: string;
  wallColor: string;
  ink: string;
  accents: string[];
  frame: boolean;
  motionBlur: number;
};

const EASES: Record<string, (t: number) => number> = {
  quintic: (t) => t * t * t * (t * (t * 6 - 15) + 10),
  cubic: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  inOut: (t) => t * t * (3 - 2 * t),
  linear: (t) => t,
  hold: () => 0,
};

const camAt = (frame: number, keys: CamKey[]) => {
  if (frame <= keys[0][0]) return {x: keys[0][1], y: keys[0][2], z: keys[0][3], roll: keys[0][4]};
  for (let i = 1; i < keys.length; i++) {
    if (frame <= keys[i][0]) {
      const a = keys[i - 1];
      const b = keys[i];
      const raw = (frame - a[0]) / Math.max(1e-6, b[0] - a[0]);
      const t = (EASES[b[5]] || EASES.inOut)(raw);
      const z = Math.exp(Math.log(a[3]) + (Math.log(b[3]) - Math.log(a[3])) * t);
      // dolly weighting: keep the screen mid-point stable while zooming
      const den = 1 / a[3] - 1 / b[3];
      const wgt = Math.abs(den) < 1e-9 ? t : (1 / a[3] - 1 / z) / den;
      return {x: a[1] + (b[1] - a[1]) * wgt, y: a[2] + (b[2] - a[2]) * wgt, z, roll: a[4] + (b[4] - a[4]) * t};
    }
  }
  const l = keys[keys.length - 1];
  return {x: l[1], y: l[2], z: l[3], roll: l[4]};
};

const Doodle: React.FC<{kind: string; p: number; ink: string; accent: string; w: number; h: number}> = ({kind, p, ink, accent, w, h}) => {
  const dash = {pathLength: 1000, strokeDasharray: `${1000 * p} 1100`, fill: 'none', strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const};
  const a = {stroke: accent, strokeWidth: 9, ...dash};
  const b = {stroke: ink, strokeWidth: 7, ...dash};
  return (
    <svg width={w} height={h} viewBox="0 0 400 260">
      {kind === 'bars' ? (
        <>
          <path d="M40 20V230H370" {...b} />
          <path d="M80 230V150H130V230M160 230V100H210V230M240 230V60H290V230" {...a} />
        </>
      ) : kind === 'cycle' ? (
        <>
          <path d="M200 40A90 90 0 1 1 112 180" {...a} />
          <path d="M112 180L96 150M112 180L142 168" {...b} />
          <circle cx={200} cy={130} r={22} stroke={ink} strokeWidth={7} fill="none" strokeDasharray={`${140 * p} 200`} />
        </>
      ) : kind === 'tree' ? (
        <>
          <path d="M200 230V120M200 160L140 110M200 140L262 90" {...b} />
          <path d="M140 110m-40 0a40 34 0 1 0 80 0a40 34 0 1 0 -80 0M262 90m-42 0a42 36 0 1 0 84 0a42 36 0 1 0 -84 0M200 120m-34 -4a34 30 0 1 0 68 0a34 30 0 1 0 -68 0" {...a} />
        </>
      ) : kind === 'bulb' ? (
        <>
          <path d="M200 40C140 40 120 110 160 150V180H240V150C280 110 260 40 200 40Z" {...a} />
          <path d="M170 205H230M180 230H220" {...b} />
          <path d="M200 8V-6M70 70L50 56M330 70L350 56" {...b} />
        </>
      ) : kind === 'gear' ? (
        <>
          <circle cx={200} cy={130} r={44} stroke={ink} strokeWidth={7} fill="none" strokeDasharray={`${280 * p} 400`} />
          <path d="M200 40L214 62L238 52L246 78L272 80L264 106L288 120L268 140L282 164L256 170L252 196L226 190L214 214L196 196L172 208L168 182L142 178L152 154L128 140L148 122L138 98L164 94L170 68L194 76Z" {...a} />
        </>
      ) : (
        <>
          <path d="M20 140C70 40 120 40 170 140S270 240 320 140S380 60 390 100" {...a} />
          <path d="M20 230H390" {...b} />
        </>
      )}
    </svg>
  );
};

const BoardCamera: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const {w, h, u, durationInFrames, portrait} = useStage();
  const keys = p.camera.map((k) => [Number(k[0]), Number(k[1]), Number(k[2]), Number(k[3]), Number(k[4]), String(k[5] || 'inOut')] as CamKey);
  const cam = camAt(frame, keys);
  const prev = camAt(frame - 1, keys);
  const dx = (cam.x - prev.x) * cam.z * u;
  const dy = (cam.y - prev.y) * cam.z * u;
  const speed = Math.hypot(dx, dy);
  const blur = p.motionBlur > 0 && speed > 14 ? Math.min(p.motionBlur, (speed - 14) * 0.3) : 0;
  const bx = Math.abs(dx) / Math.max(1, speed);
  const by = Math.abs(dy) / Math.max(1, speed);
  const showFrame = p.frame ? 1 - prog(cam.z, 0.5, 0.3, easeLib.sine) : 0;
  const zoomOut = cam.z < 0.5;

  return (
    <AbsoluteFill style={{background: p.wallColor, overflow: 'hidden'}}>
      <svg width={0} height={0} style={{position: 'absolute'}}>
        <defs>
          <filter id="bc-blur" x="-10%" y="-10%" width="120%" height="120%">
            <feGaussianBlur stdDeviation={`${blur * bx} ${blur * by}`} />
          </filter>
        </defs>
      </svg>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: p.boardW,
          height: p.boardH,
          transformOrigin: '0 0',
          transform: `translate(${w / 2}px, ${h / 2}px) rotate(${cam.roll}deg) scale(${cam.z * u * (portrait ? 0.7 : 1)}) translate(${-cam.x}px, ${-cam.y}px)`,
          filter: blur > 0.3 ? 'url(#bc-blur)' : undefined,
        }}
      >
        <div style={{position: 'absolute', inset: -40, background: 'transparent', boxShadow: `0 30px 90px rgba(40,34,24,${0.35 * showFrame})`, borderRadius: 24}} />
        <div style={{position: 'absolute', inset: 0, background: p.boardColor, borderRadius: 8, boxShadow: `0 0 0 ${48 * showFrame}px #A9ADB3, 0 0 0 ${58 * showFrame}px #7d8188`}} />
        {/* sheen */}
        <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(115deg, rgba(255,255,255,0) 30%, rgba(255,255,255,0.35) 45%, rgba(255,255,255,0) 60%)', transform: `translateX(${(cam.x - p.boardW / 2) * 0.35}px)`, pointerEvents: 'none'}} />
        {/* pen tray */}
        <div style={{position: 'absolute', left: p.boardW / 2 - 700, top: p.boardH + 60, width: 1400, height: 70, background: '#A9ADB3', borderRadius: 14, opacity: showFrame, boxShadow: '0 14px 30px rgba(0,0,0,0.25)'}}>
          {['#26282C', '#E5462F', '#2F6FD0', '#2E9A5B'].map((c, i) => (
            <div key={c} style={{position: 'absolute', left: 150 + i * 260, top: -18, width: 220, height: 28, borderRadius: 14, background: c}} />
          ))}
        </div>
        {p.regions.map((r, i) => {
          const at = r.at ?? 4 + i * 20;
          const dp = prog(frame, at, at + 36, easeLib.inOut);
          const cardIn = prog(frame, at - 6, at + 10, easeLib.out);
          const accent = p.accents[i % Math.max(1, p.accents.length)] || '#E5462F';
          return (
            <div key={r.id} style={{position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, opacity: cardIn}}>
              {r.layers && r.layers.length ? (
                <div style={{position: 'absolute', inset: 0, overflow: 'hidden', borderRadius: 20}}>
                  <div style={{width: w, height: h, transformOrigin: '0 0', transform: `scale(${Math.min(r.w / w, r.h / h)})`}}>
                    <Layers layers={r.layers} length={durationInFrames} />
                  </div>
                </div>
              ) : (
                <>
                  <div style={{position: 'absolute', inset: 0, border: `7px solid ${p.ink}`, borderRadius: 26, opacity: 0.1}} />
                  <div style={{position: 'absolute', left: 90, top: 70, fontFamily: fonts.hand, fontWeight: 700, fontSize: 210, lineHeight: 1, color: p.ink}}>{r.title}</div>
                  <div style={{position: 'absolute', left: 90, top: 300, width: r.w - 180, height: r.h - 380, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                    <Doodle kind={r.doodle || 'bars'} p={dp} ink={p.ink} accent={accent} w={r.w - 220} h={r.h - 400} />
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
      {zoomOut ? null : null}
    </AbsoluteFill>
  );
};

const CX = [1550, 4000, 6450];
const CY = [1350, 3150];

export const boardCamera = defineMotion<Props>({
  id: 'board-camera',
  title: 'Board camera (one huge board, one long dolly)',
  category: 'camera',
  description:
    'A very large board holds every idea in its own region; the camera dollies between regions with log-zoom weighting and small rolls, pushes into one symbol, then pulls back past the board edge to show the whole lesson hanging on a wall in an aluminium frame with a pen tray. Directional motion blur appears when the camera moves fast.',
  source: ['lemo-opuscar styles/whiteboard demo/engine/wb.js Camera / applyCam / Board.render (MIT, LemoLab) — own implementation'],
  useFor: 'Turns hand-drawn motions into one continuous explainer: course intros, "how it works" product videos, onboarding; the full-board pull-back is a natural recap / end card. Regions can host any library motion via `layers`.',
  durationInFrames: 400,
  defaultProps: {
    regions: [
      {id: 'r1', x: CX[0] - 1150, y: CY[0] - 850, w: 2300, h: 1700, title: 'Gather', doodle: 'bulb', at: 4},
      {id: 'r2', x: CX[1] - 1150, y: CY[0] - 850, w: 2300, h: 1700, title: 'Sort', doodle: 'bars', at: 78},
      {id: 'r3', x: CX[2] - 1150, y: CY[0] - 850, w: 2300, h: 1700, title: 'Test', doodle: 'cycle', at: 172},
      {id: 'r4', x: CX[0] - 1150, y: CY[1] - 850, w: 2300, h: 1700, title: 'Ship', doodle: 'gear', at: 322},
      {id: 'r5', x: CX[1] - 1150, y: CY[1] - 850, w: 2300, h: 1700, title: 'Measure', doodle: 'wave', at: 262},
      {id: 'r6', x: CX[2] - 1150, y: CY[1] - 850, w: 2300, h: 1700, title: 'Repeat', doodle: 'tree', at: 334},
    ],
    camera: [
      [0, CX[0], CY[0], 0.62, 0, 'hold'],
      [52, CX[0], CY[0], 0.62, 0, 'hold'],
      [92, CX[1], CY[0], 0.62, 0.6, 'quintic'],
      [150, CX[1], CY[0], 0.62, 0, 'inOut'],
      [186, CX[2], CY[0], 0.62, -0.6, 'cubic'],
      [244, CX[2], CY[0], 0.62, 0, 'inOut'],
      [284, CX[1], CY[1], 1.1, 0, 'quintic'],
      [316, CX[1], CY[1], 1.1, 0, 'hold'],
      [372, 4000, 2250, 0.2, 0, 'quintic'],
      [400, 4000, 2250, 0.2, 0, 'hold'],
    ],
    boardW: 8000,
    boardH: 4500,
    boardColor: '#F7F5EF',
    wallColor: '#D8D3CA',
    ink: '#26282C',
    accents: ['#E5462F', '#2F6FD0', '#2E9A5B', '#E39A1B', '#7A4FC4', '#E5462F'],
    frame: true,
    motionBlur: 9,
  },
  propDocs: {
    regions: '[{id, x, y, w, h (board px), title, doodle:bars|cycle|tree|bulb|gear|wave, at (draw-in frame), layers? (LayerSpec[] to host library motions)}]',
    camera: "[[frame, x, y, zoom, rollDeg, ease]] ease arrives at the key: 'quintic'|'cubic'|'inOut'|'linear'|'hold'",
    boardW: 'board width in world px',
    boardH: 'board height in world px',
    boardColor: 'board surface colour',
    wallColor: 'wall colour seen on pull-back',
    ink: 'ink colour',
    accents: 'accent colours cycled over regions',
    frame: 'aluminium frame + pen tray when zoomed out',
    motionBlur: 'max blur px when the camera is fast (0 = off)',
  },
  component: BoardCamera,
  tags: ['whiteboard', 'camera', 'dolly', 'pan', 'zoom', 'board', 'explainer', 'infinite canvas', 'pull-back', 'regions', 'container'],
});
