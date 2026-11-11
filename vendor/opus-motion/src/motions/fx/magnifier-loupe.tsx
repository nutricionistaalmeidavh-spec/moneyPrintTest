import React, {useMemo} from 'react';
import {AbsoluteFill, Img, useCurrentFrame} from 'remotion';
import {clamp, ease, prog} from '../../core/ease';
import {resolveSrc} from '../../core/asset';
import {bookLayout, DeskBook, INK3} from '../../core/r2-x14-kit';
import {useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * x3 reading loupe: a thin round glass lens wanders across the page text like a reader's cursor, magnifying
 * it ≈ 1.6× with a slight barrel bulge (the centre is magnified a little more than the edge). Its rim has a
 * thin prismatic fringe — orange outside, magenta inside, with tinted ghost copies of the text — a soft white
 * edge highlight and a small magnifier icon at its centre. It follows its path with a critically damped
 * lag (≈ 0.1 s). Unlike `loupe-magnify` (black-rimmed shader magnifier that lands on an image), this is a
 * light glass reading lens on a path, over the procedural textbook page or any `src` image; with backdrop
 * "none" it draws only the glass over host content.
 */

type Props = {
  src: string;
  backdrop: string;
  path: number[][];
  zoom: number;
  bulge: number;
  size: number;
  lag: number;
  fringe: number;
  fringeOuter: string;
  fringeInner: string;
  icon: boolean;
  drift: number;
  background: string;
};

/** eased target along [x, y, travelFrames] keys */
const targetAt = (path: number[][], f: number) => {
  if (!path.length) return {x: 0.5, y: 0.5};
  let t = 0;
  for (let i = 1; i < path.length; i++) {
    const d = Math.max(1, path[i][2] ?? 20);
    if (f <= t + d) {
      const k = ease.sine(clamp((f - t) / d));
      return {x: path[i - 1][0] + (path[i][0] - path[i - 1][0]) * k, y: path[i - 1][1] + (path[i][1] - path[i - 1][1]) * k};
    }
    t += d;
  }
  const l = path[path.length - 1];
  return {x: l[0], y: l[1]};
};

/** critically damped follow, simulated from frame 0 (deterministic) */
const followTrack = (path: number[][], frames: number, fps: number, lag: number) => {
  const out: {x: number; y: number}[] = [];
  const w0 = 1 / Math.max(0.02, lag);
  const sub = 6;
  const dt = 1 / fps / sub;
  let p = targetAt(path, 0);
  let v = {x: 0, y: 0};
  for (let f = 0; f < frames; f++) {
    for (let s = 0; s < sub; s++) {
      const tg = targetAt(path, f + s / sub);
      const ax = w0 * w0 * (tg.x - p.x) - 2 * w0 * v.x;
      const ay = w0 * w0 * (tg.y - p.y) - 2 * w0 * v.y;
      v = {x: v.x + ax * dt, y: v.y + ay * dt};
      p = {x: p.x + v.x * dt, y: p.y + v.y * dt};
    }
    out.push(p);
  }
  return out;
};

const MagnifierLoupe: React.FC<Props> = ({src, backdrop, path, zoom, bulge, size, lag, fringe, fringeOuter, fringeInner, icon, drift, background}) => {
  const frame = useCurrentFrame();
  const {w, h, u, fps, durationInFrames, portrait} = useStage();
  const glassOnly = !src && backdrop === 'none';
  const camZoom = (1 + drift * clamp(frame / Math.max(1, durationInFrames))) * (portrait && !src && !glassOnly ? 1.1 : 1);
  const track = useMemo(() => followTrack(path, durationInFrames + 1, fps, lag), [JSON.stringify(path), durationInFrames, fps, lag]);
  const p = track[Math.min(track.length - 1, Math.max(0, frame))];

  // reading area -> screen
  let area = {x: 0, y: 0, w, h};
  if (!src && !glassOnly) {
    const L = bookLayout(w, h, 'auto', portrait ? 0 : 0);
    area = L.page;
  }
  // the camera push scales the backdrop about the frame centre: map the area through it
  const sx = (v: number) => w / 2 + (v - w / 2) * camZoom;
  const sy = (v: number) => h / 2 + (v - h / 2) * camZoom;
  const X = sx(area.x + p.x * area.w);
  const Y = sy(area.y + p.y * area.h);
  const enter = prog(frame, 0, 14, ease.back);
  const R = (size * u * (0.65 + 0.35 * enter)) / 2;
  const op = prog(frame, 0, 8, ease.out);

  const content = src ? (
    <div style={{position: 'absolute', inset: 0, transform: `scale(${camZoom})`}}>
      <Img src={resolveSrc(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    </div>
  ) : glassOnly ? null : (
    <DeskBook uid="mlp" zoom={camZoom} />
  );
  const clip = `circle(${R}px at ${X}px ${Y}px)`;
  const copy = (scale: number, extra: React.CSSProperties = {}, key?: string) => (
    <div key={key} style={{position: 'absolute', inset: 0, clipPath: clip, ...extra}}>
      <div style={{position: 'absolute', inset: 0, transform: `scale(${scale})`, transformOrigin: `${X}px ${Y}px`}}>{content}</div>
    </div>
  );
  const ring = (a: number, b: number, c: number, d: number) =>
    `radial-gradient(circle at ${X}px ${Y}px, transparent ${a * R}px, #000 ${b * R}px, #000 ${c * R}px, transparent ${d * R}px)`;
  const tint = (hex: string) => {
    const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
    return c.map((ci) => `${((1 - ci) * 0.3).toFixed(3)} ${((1 - ci) * 0.59).toFixed(3)} ${((1 - ci) * 0.11).toFixed(3)} 0 ${ci.toFixed(3)}`).join(' ') + ' 0 0 0 1 0';
  };
  return (
    <AbsoluteFill style={{background: glassOnly ? background : INK3.mat, overflow: 'hidden'}}>
      {content}
      <svg width={0} height={0} style={{position: 'absolute'}}>
        <filter id="mlp-tintA" colorInterpolationFilters="sRGB">
          <feColorMatrix type="matrix" values={tint(fringeOuter)} />
        </filter>
        <filter id="mlp-tintB" colorInterpolationFilters="sRGB">
          <feColorMatrix type="matrix" values={tint(fringeInner)} />
        </filter>
      </svg>
      <div style={{opacity: op}}>
        {/* drop shadow of the lens on the page */}
        <div
          style={{
            position: 'absolute',
            left: X - R,
            top: Y - R,
            width: 2 * R,
            height: 2 * R,
            borderRadius: '50%',
            boxShadow: `0 ${4 * u}px ${12 * u}px rgba(0,0,0,0.18), 0 ${14 * u}px ${30 * u}px rgba(0,0,0,0.08)`,
          }}
        />
        {content ? (
          <>
            {copy(zoom)}
            {[1, 2, 3].map((k) => {
              const m = `radial-gradient(circle at ${X}px ${Y}px, #000 0px, #000 ${(0.78 - k * 0.2) * R}px, transparent ${(0.9 - k * 0.2) * R}px)`;
              return copy(zoom * (1 + (bulge * k) / 3), {WebkitMaskImage: m, maskImage: m}, 'b' + k);
            })}
            {copy(zoom * (1 - bulge * 0.3), {WebkitMaskImage: ring(0.84, 0.92, 1, 1.01), maskImage: ring(0.84, 0.92, 1, 1.01)})}
            {fringe > 0
              ? [
                  copy(zoom * (1 + 0.05 * fringe), {WebkitMaskImage: ring(0.66, 0.86, 1, 1.01), maskImage: ring(0.66, 0.86, 1, 1.01), mixBlendMode: 'multiply', filter: 'url(#mlp-tintA)', opacity: 0.85}, 'a'),
                  copy(zoom * (1 - 0.06 * fringe), {WebkitMaskImage: ring(0.66, 0.86, 1, 1.01), maskImage: ring(0.66, 0.86, 1, 1.01), mixBlendMode: 'multiply', filter: 'url(#mlp-tintB)', opacity: 0.75}, 'b'),
                ]
              : null}
          </>
        ) : (
          <div style={{position: 'absolute', left: X - R, top: Y - R, width: 2 * R, height: 2 * R, borderRadius: '50%', backdropFilter: `blur(${0.6 * u}px) saturate(1.15)`}} />
        )}
        <svg width={w} height={h} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
          <defs>
            <radialGradient id="mlp-glass" cx="0.38" cy="0.32" r="0.8">
              <stop offset="0" stopColor="#fff" stopOpacity={0.14} />
              <stop offset="0.6" stopColor="#fff" stopOpacity={0.02} />
              <stop offset="0.92" stopColor="#fff" stopOpacity={0.1} />
              <stop offset="1" stopColor="#fff" stopOpacity={0.35} />
            </radialGradient>
            <filter id="mlp-soft" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation={1.4 * u} />
            </filter>
            <filter id="mlp-softer" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation={3 * u} />
            </filter>
          </defs>
          <circle cx={X} cy={Y} r={R} fill="url(#mlp-glass)" />
          {fringe > 0 ? (
            <g filter="url(#mlp-soft)" opacity={Math.min(1, fringe)}>
              <circle cx={X} cy={Y} r={R + 1.6 * u} fill="none" stroke={fringeOuter} strokeWidth={3 * u} opacity={0.8} />
              <circle cx={X} cy={Y} r={R - 2.6 * u} fill="none" stroke={fringeInner} strokeWidth={2.6 * u} opacity={0.55} />
            </g>
          ) : null}
          <circle cx={X} cy={Y} r={R} fill="none" stroke="#fff" strokeWidth={1.3 * u} opacity={0.75} />
          <path
            d={`M ${X - R * 0.86} ${Y - R * 0.18} A ${R * 0.88} ${R * 0.88} 0 0 1 ${X - R * 0.2} ${Y - R * 0.86}`}
            stroke="#fff"
            strokeWidth={5 * u}
            strokeLinecap="round"
            fill="none"
            opacity={0.55}
            filter="url(#mlp-softer)"
          />
          <path d={`M ${X + R * 0.5} ${Y + R * 0.78} A ${R * 0.93} ${R * 0.93} 0 0 0 ${X + R * 0.86} ${Y + R * 0.3}`} stroke="#000" strokeWidth={4 * u} strokeLinecap="round" fill="none" opacity={0.08} filter="url(#mlp-softer)" />
          {icon ? (
            <g transform={`translate(${X} ${Y})`} stroke={INK3.ink} strokeWidth={2.4 * u} fill="none" strokeLinecap="round" opacity={0.85}>
              <circle cx={-2 * u} cy={-2 * u} r={8.5 * u} fill="rgba(255,255,255,0.65)" />
              <path d={`M ${4 * u} ${4 * u} L ${10 * u} ${10 * u} M ${-6.5 * u} ${-2 * u} H ${2.5 * u} M ${-2 * u} ${-6.5 * u} V ${2.5 * u}`} />
            </g>
          ) : null}
        </svg>
      </div>
    </AbsoluteFill>
  );
};

export const magnifierLoupe = defineMotion<Props>({
  id: 'magnifier-loupe',
  title: 'Magnifier reading loupe',
  category: 'fx',
  description:
    'A thin round glass lens wanders across textbook text like a reading cursor, magnifying it 1.6× with a slight barrel bulge, a prismatic orange/magenta rim fringe with tinted ghost text, a white edge highlight and a small magnifier icon; it follows its path with a soft critically damped lag. Works over any `src` image, or as glass only over host content (backdrop "none").',
  source: ['video x3 13.9-20.0 (magnifier-loupe)'],
  useFor: 'Drawing attention to fine print, a definition, a UI detail or a chart value; "look closer" and "read along" beats in explainers and product tours.',
  durationInFrames: 240,
  defaultProps: {
    src: '',
    backdrop: 'book',
    path: [
      [1.05, 0.95, 0],
      [0.3, 0.14, 26],
      [0.16, 0.19, 12],
      [0.74, 0.19, 40],
      [0.16, 0.23, 12],
      [0.74, 0.23, 38],
      [0.3, 0.355, 16],
      [0.4, 0.355, 22],
      [0.22, 0.5, 16],
      [0.6, 0.52, 30],
      [0.4, 0.665, 22],
    ],
    zoom: 1.6,
    bulge: 0.12,
    size: 250,
    lag: 0.1,
    fringe: 1,
    fringeOuter: '#F6BC7C',
    fringeInner: '#E38AE8',
    icon: true,
    drift: 0.02,
    background: 'transparent',
  },
  propDocs: {
    src: 'image to read over (public/ path or URL); empty = procedural textbook page',
    backdrop: '"book" procedural textbook | "none" = transparent overlay: only the glass is drawn (no magnified copy)',
    path: 'lens path as [x, y, travelFrames] in 0..1 of the reading area (left page, or the whole frame with src)',
    zoom: 'magnification (1.6 = source)',
    bulge: 'barrel bulge: extra magnification at the centre (0 = flat)',
    size: 'lens diameter in u',
    lag: 'follow lag in seconds (critically damped)',
    fringe: 'prismatic rim strength (0 = none)',
    fringeOuter: 'outer fringe colour (orange)',
    fringeInner: 'inner fringe colour (magenta)',
    icon: 'show the small magnifier icon at the centre',
    drift: 'slow camera push on the backdrop over the clip',
    background: 'colour behind the glass in overlay mode ("transparent")',
  },
  component: MagnifierLoupe,
  tags: ['magnifier', 'loupe', 'lens', 'zoom', 'magnify', 'reading', 'text', 'fine print', 'detail', 'glass', 'chromatic', 'prismatic', 'cursor', 'textbook', 'education', 'overlay', 'look closer'],
});
