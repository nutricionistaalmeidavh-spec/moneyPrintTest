import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {resolveSrc} from '../../core/asset';
import {clamp, ease, prog} from '../../core/ease';
import {fonts} from '../../core/fonts';
import {rgba, shade} from '../../core/r2-pr2-kit';
import {useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * A phone / android / tablet / laptop / watch frame (pure CSS, no bitmap) showing your screen (an image, or a tall
 * screenshot that scrolls) or a built-in app UI. It enters with a 3D tilt and settles on a soft floor shadow, idles
 * with a slow sway and can flip over to a second panel.
 */
type Props = {
  device: string;
  src: string;
  src2: string;
  fit: string;
  scroll: number[];
  scrollFrames: number[];
  tilt: number;
  flipAt: number;
  headline: string;
  subline: string;
  bodyColor: string;
  accent: string;
  background: string;
  background2: string;
  textColor: string;
  size: number;
  brand: string;
  statusTime: string;
  greeting: string;
  appSuffix: string;
  goal: number;
  goalLabel: string;
  goalTitle: string;
  goalNote: string;
  stats: string[][];
  activityTitle: string;
  activityRows: string[][];
  rowDays: string[];
  weekLabel: string;
  weekValue: string;
  weekDelta: string;
  weekBars: number[];
  weekDays: string[];
  highlightsTitle: string;
  highlights: string[];
  dashMenu: string[];
  dashTitles: string[];
  dashStats: string[][];
  dashChartTitle: string;
  dashBars: number[];
  watchLabel: string;
  watchValue: string;
  watchUnit: string;
};

type Spec = {bw: number; bh: number; r: number; bez: number; sr: number; refW: number; total: number};
const SPEC: Record<string, Spec> = {
  iphone: {bw: 300, bh: 620, r: 44, bez: 11, sr: 34, refW: 390, total: 620},
  android: {bw: 296, bh: 640, r: 34, bez: 9, sr: 26, refW: 390, total: 640},
  tablet: {bw: 540, bh: 720, r: 34, bez: 22, sr: 16, refW: 560, total: 720},
  laptop: {bw: 900, bh: 580, r: 24, bez: 18, sr: 6, refW: 1000, total: 604},
  watch: {bw: 250, bh: 300, r: 66, bez: 14, sr: 52, refW: 200, total: 560},
};

const Ring: React.FC<{p: number; size: number; color: string; track: string; sw: number}> = ({p, size, color, track, sw}) => {
  const r = size / 2 - sw;
  const c = 2 * Math.PI * r;
  return (
    <svg width={size} height={size}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={sw} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" strokeDasharray={`${c * p} ${c}`} transform={`rotate(-90 ${size / 2} ${size / 2})`} />
    </svg>
  );
};

const AppUI: React.FC<{P: Props; variant: number; w: number; h: number; accent: string; frame: number; scrollPct: number; brand: string}> = ({P, variant, w, h, accent, frame, scrollPct, brand}) => {
  const ink = '#14182a';
  const content = variant === 0 ? (
    <div style={{padding: '0 22px 90px'}}>
      <div style={{fontSize: 14, color: '#8a90a6', marginTop: 6}}>{P.greeting}</div>
      <div style={{fontSize: 30, fontWeight: 800, color: ink, letterSpacing: -0.5}}>{brand} {P.appSuffix}</div>
      <div style={{marginTop: 18, borderRadius: 26, padding: 22, color: '#fff', background: `linear-gradient(135deg, ${accent}, ${shade(accent, -0.35)})`, display: 'flex', alignItems: 'center', gap: 18}}>
        <div style={{position: 'relative', width: 104, height: 104}}>
          <Ring p={(P.goal / 100) * ease.out(clamp(frame / 40))} size={104} color="#fff" track="rgba(255,255,255,0.25)" sw={9} />
          <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26, fontWeight: 800}}>{P.goal}%</div>
        </div>
        <div>
          <div style={{fontSize: 13, opacity: 0.8}}>{P.goalLabel}</div>
          <div style={{fontSize: 24, fontWeight: 800, lineHeight: 1.15}}>{P.goalTitle}</div>
          <div style={{fontSize: 13, opacity: 0.8, marginTop: 4}}>{P.goalNote}</div>
        </div>
      </div>
      <div style={{display: 'flex', gap: 10, marginTop: 14}}>
        {P.stats.map(([a, b], i) => (
          <div key={`${a}${i}`} style={{flex: 1, background: '#f1f3fa', borderRadius: 16, padding: '12px 12px'}}>
            <div style={{fontSize: 11, color: '#8a90a6'}}>{a}</div>
            <div style={{fontSize: 20, fontWeight: 800, color: ink}}>{b}</div>
          </div>
        ))}
      </div>
      <div style={{fontSize: 17, fontWeight: 800, color: ink, margin: '20px 0 8px'}}>{P.activityTitle}</div>
      {P.activityRows.map(([a, b, c = '#6c8cff'], i) => (
        <div key={`${a}${i}`} style={{display: 'flex', alignItems: 'center', gap: 14, padding: '11px 0', borderBottom: '1px solid #eceef6'}}>
          <div style={{width: 40, height: 40, borderRadius: 14, background: c, opacity: 0.9}} />
          <div style={{flex: 1}}>
            <div style={{fontSize: 15, fontWeight: 700, color: ink}}>{a}</div>
            <div style={{fontSize: 12, color: '#8a90a6'}}>{P.rowDays[i % 2]}</div>
          </div>
          <div style={{fontSize: 14, fontWeight: 700, color: ink}}>{b}</div>
        </div>
      ))}
    </div>
  ) : (
    <div style={{padding: '0 22px 90px'}}>
      <div style={{fontSize: 14, color: '#8a90a6', marginTop: 6}}>{P.weekLabel}</div>
      <div style={{fontSize: 46, fontWeight: 800, color: ink, letterSpacing: -1}}>{P.weekValue}</div>
      <div style={{fontSize: 13, color: '#2faa6a', fontWeight: 700}}>{P.weekDelta}</div>
      <div style={{display: 'flex', alignItems: 'flex-end', gap: 9, height: 170, marginTop: 20}}>
        {P.weekBars.map((v, i) => (
          <div key={i} style={{flex: 1, height: `${v * 100 * ease.out(clamp((frame - 4 - i * 3) / 22))}%`, borderRadius: 10, background: i === 3 ? accent : '#dfe3f3'}} />
        ))}
      </div>
      <div style={{display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#8a90a6', marginTop: 6}}>
        {P.weekDays.map((d, i) => (
          <span key={i} style={{flex: 1, textAlign: 'center'}}>{d}</span>
        ))}
      </div>
      <div style={{fontSize: 17, fontWeight: 800, color: ink, margin: '22px 0 8px'}}>{P.highlightsTitle}</div>
      {P.highlights.map((t, i) => (
        <div key={`${t}${i}`} style={{padding: '14px 16px', marginBottom: 10, borderRadius: 16, background: '#f1f3fa', fontSize: 14, fontWeight: 600, color: ink}}>{t}</div>
      ))}
      {P.activityRows.slice(0, 4).map(([a, b], i) => (
        <div key={`${a}${i}`} style={{display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid #eceef6', fontSize: 14, color: ink}}>
          <span style={{fontWeight: 700}}>{a}</span>
          <span>{b}</span>
        </div>
      ))}
    </div>
  );
  const overflow = 1000 - (h - 150);
  return (
    <div style={{width: w, height: h, background: '#fff', position: 'relative', overflow: 'hidden', fontFamily: fonts.sans}}>
      <div style={{display: 'flex', justifyContent: 'space-between', padding: '30px 30px 12px', fontSize: 14, fontWeight: 700, color: ink, background: '#fff', position: 'relative', zIndex: 2}}>
        <span>{P.statusTime}</span>
        <span>●●● ▮</span>
      </div>
      <div style={{transform: `translateY(${-scrollPct * Math.max(0, overflow)}px)`}}>{content}</div>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: 76, background: 'rgba(255,255,255,0.94)', borderTop: '1px solid #eceef6', display: 'flex', justifyContent: 'space-around', alignItems: 'center'}}>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} style={{width: 26, height: 26, borderRadius: 9, background: i === variant ? accent : '#d5d9ea'}} />
        ))}
      </div>
    </div>
  );
};

const DashUI: React.FC<{P: Props; variant: number; w: number; h: number; accent: string; frame: number; scrollPct: number; brand: string}> = ({P, variant, w, h, accent, frame, scrollPct, brand}) => {
  const ink = '#161a2c';
  const bars = P.dashBars;
  return (
    <div style={{width: w, height: h, background: '#f4f6fb', display: 'flex', overflow: 'hidden', fontFamily: fonts.sans}}>
      <div style={{width: 190, background: '#fff', padding: 22, borderRight: '1px solid #e7eaf4'}}>
        <div style={{fontSize: 22, fontWeight: 800, color: ink, marginBottom: 26}}>
          <span style={{color: accent}}>●</span> {brand}
        </div>
        {P.dashMenu.map((t, i) => (
          <div key={`${t}${i}`} style={{padding: '11px 12px', borderRadius: 10, marginBottom: 4, fontSize: 15, fontWeight: 600, color: i === variant ? accent : '#6c7390', background: i === variant ? rgba(accent, 0.1) : 'transparent'}}>{t}</div>
        ))}
      </div>
      <div style={{flex: 1, padding: '24px 28px', overflow: 'hidden'}}>
        <div style={{transform: `translateY(${-scrollPct * 120}px)`}}>
          <div style={{fontSize: 26, fontWeight: 800, color: ink}}>{variant === 0 ? P.dashTitles[0] : P.dashTitles[1]}</div>
          <div style={{display: 'flex', gap: 14, margin: '16px 0'}}>
            {P.dashStats.map(([a, b], i) => (
              <div key={`${a}${i}`} style={{flex: 1, background: '#fff', borderRadius: 16, padding: 16, boxShadow: '0 2px 8px rgba(20,30,70,0.06)'}}>
                <div style={{fontSize: 12, color: '#7b829c'}}>{a}</div>
                <div style={{fontSize: 26, fontWeight: 800, color: i === 2 ? '#2faa6a' : ink}}>{b}</div>
              </div>
            ))}
          </div>
          <div style={{background: '#fff', borderRadius: 18, padding: 20, boxShadow: '0 2px 8px rgba(20,30,70,0.06)'}}>
            <div style={{fontSize: 14, fontWeight: 700, color: ink, marginBottom: 14}}>{P.dashChartTitle}</div>
            <div style={{display: 'flex', alignItems: 'flex-end', gap: 10, height: 190}}>
              {bars.map((v, i) => (
                <div key={i} style={{flex: 1, height: `${(variant ? 1 - v * 0.4 : v) * 100 * ease.out(clamp((frame - 3 - i * 2) / 22))}%`, borderRadius: 8, background: i === 7 ? accent : '#dde2f2'}} />
              ))}
            </div>
          </div>
          <div style={{display: 'flex', gap: 14, marginTop: 14}}>
            {[0, 1].map((i) => (
              <div key={i} style={{flex: 1, height: 110, background: '#fff', borderRadius: 18, boxShadow: '0 2px 8px rgba(20,30,70,0.06)'}} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

const WatchUI: React.FC<{P: Props; variant: number; w: number; h: number; accent: string; frame: number}> = ({P, variant, w, h, accent, frame}) => (
  <div style={{width: w, height: h, background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', fontFamily: fonts.sans, color: '#fff'}}>
    {variant === 0 ? (
      <>
        <div style={{position: 'absolute'}}>
          <Ring p={0.82 * ease.out(clamp(frame / 40))} size={176} color={accent} track="#222" sw={14} />
        </div>
        <div style={{position: 'absolute'}}>
          <Ring p={0.55 * ease.out(clamp(frame / 40))} size={136} color="#35c4c0" track="#1c1c1c" sw={14} />
        </div>
        <div style={{fontSize: 34, fontWeight: 800}}>{P.statusTime}</div>
      </>
    ) : (
      <div style={{textAlign: 'center'}}>
        <div style={{fontSize: 14, color: '#8a90a6'}}>{P.watchLabel}</div>
        <div style={{fontSize: 56, fontWeight: 800, color: accent}}>{P.watchValue}</div>
        <div style={{fontSize: 14, color: '#8a90a6'}}>{P.watchUnit}</div>
      </div>
    )}
  </div>
);

const Screen: React.FC<{P: Props; spec: Spec; k: number; variant: number; frame: number; src: string}> = ({P, spec, k, variant, frame, src}) => {
  const sw = (spec.bw - spec.bez * 2) * k;
  const sh = (spec.bh - spec.bez * 2) * k;
  const s = sw / spec.refW;
  const [f0, f1] = P.scrollFrames;
  const sp = ease.inOut(prog(frame, f0, f1, (t) => t));
  const scrollPct = variant === 1 ? 0 : clamp(P.scroll[0] + (P.scroll[1] - P.scroll[0]) * sp);
  const inner = src ? (
    P.fit === 'scroll' ? (
      <div style={{width: sw, height: sh, backgroundImage: `url(${resolveSrc(src)})`, backgroundSize: '100% auto', backgroundPosition: `50% ${scrollPct * 100}%`, backgroundRepeat: 'no-repeat', backgroundColor: '#fff'}} />
    ) : (
      <div style={{width: sw, height: sh, backgroundImage: `url(${resolveSrc(src)})`, backgroundSize: 'cover', backgroundPosition: 'center'}} />
    )
  ) : (
    <div style={{width: spec.refW, height: sh / s, transform: `scale(${s})`, transformOrigin: '0 0'}}>
      {P.device === 'watch' ? (
        <WatchUI P={P} variant={variant} w={spec.refW} h={sh / s} accent={P.accent} frame={frame} />
      ) : P.device === 'laptop' ? (
        <DashUI P={P} variant={variant} w={spec.refW} h={sh / s} accent={P.accent} frame={frame} scrollPct={scrollPct} brand={P.brand} />
      ) : (
        <AppUI P={P} variant={variant} w={spec.refW} h={sh / s} accent={P.accent} frame={frame} scrollPct={scrollPct} brand={P.brand} />
      )}
    </div>
  );
  return (
    <div style={{position: 'absolute', left: spec.bez * k, top: spec.bez * k, width: sw, height: sh, borderRadius: spec.sr * k, overflow: 'hidden', background: '#000'}}>
      {inner}
      <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(125deg, rgba(255,255,255,0.16) 0%, rgba(255,255,255,0) 34%)', pointerEvents: 'none'}} />
    </div>
  );
};

const Face: React.FC<{P: Props; spec: Spec; k: number; variant: number; frame: number; src: string; z: number; back?: boolean}> = ({P, spec, k, variant, frame, src, z, back}) => {
  const body = P.bodyColor;
  return (
    <div style={{position: 'absolute', left: 0, top: 0, width: spec.bw * k, height: spec.bh * k, transform: `translateZ(${z}px) ${back ? 'rotateY(180deg)' : ''}`, backfaceVisibility: 'hidden', borderRadius: spec.r * k, background: `linear-gradient(145deg, ${shade(body, 0.22)}, ${body} 40%, ${shade(body, -0.2)})`, boxShadow: `inset 0 0 0 ${1.6 * k}px rgba(255,255,255,0.22), inset 0 0 0 ${4 * k}px ${shade(body, -0.35)}`}}>
      <Screen P={P} spec={spec} k={k} variant={variant} frame={frame} src={src} />
      {(P.device === 'iphone' || P.device === 'android') && (
        <div style={P.device === 'iphone' ? {position: 'absolute', left: '50%', top: 22 * k, width: 92 * k, height: 26 * k, marginLeft: -46 * k, borderRadius: 14 * k, background: '#000'} : {position: 'absolute', left: '50%', top: 20 * k, width: 14 * k, height: 14 * k, marginLeft: -7 * k, borderRadius: 7 * k, background: '#000'}} />
      )}
      {P.device === 'tablet' && <div style={{position: 'absolute', left: '50%', top: 9 * k, width: 8 * k, height: 8 * k, marginLeft: -4 * k, borderRadius: 4 * k, background: '#0a0a0a'}} />}
    </div>
  );
};

const DeviceMockup: React.FC<Props> = (P) => {
  const frame = useCurrentFrame();
  const {w, h, u, portrait} = useStage();
  const device = SPEC[P.device] ? P.device : 'iphone';
  const spec = SPEC[device];
  const hasText = !!(P.headline || P.subline);
  const sideText = hasText && !portrait;
  // fit: height fraction and width limit
  const frac = (device === 'laptop' ? (portrait ? 0.34 : 0.62) : device === 'watch' ? (portrait ? 0.5 : 0.7) : device === 'tablet' ? (portrait ? 0.5 : 0.78) : portrait ? 0.62 : 0.78) * P.size;
  const availW = sideText ? w * 0.5 : w;
  const k = Math.min((h * frac) / spec.total, (availW * 0.86) / (device === 'watch' ? 250 : device === 'laptop' ? 1040 : spec.bw));
  const devW = (device === 'laptop' ? 1040 : spec.bw) * k;
  const devH = spec.total * k;
  const cx = sideText ? w * 0.72 : w / 2;
  const cy = (hasText && portrait ? h * 0.6 : h * 0.5) + (device === 'laptop' ? 0 : 0);
  // timeline
  const inP = ease.out(prog(frame, 0, 24, (t) => t));
  const flipP = P.flipAt > 0 ? ease.inOut(prog(frame, P.flipAt, P.flipAt + 32, (t) => t)) : 0;
  const idle = Math.sin(frame / 38) * 3.2;
  const floatY = Math.sin(frame / 30) * 5 * u;
  const rotY = (1 - inP) * P.tilt + idle * (1 - flipP * 0.0) + flipP * 180;
  const rotX = (1 - inP) * -6 + 5;
  const lift = Math.sin(Math.PI * flipP);
  const y = (1 - inP) * h * 0.08 + floatY;
  const thick = 14 * k;
  const slices = 9;
  const textA = ease.out(prog(frame, 14, 40, (t) => t));
  const shW = devW * (0.95 - 0.2 * lift - (1 - inP) * 0.3);
  const floorY = cy + devH / 2 + h * 0.03;
  const ink = P.textColor;
  return (
    <AbsoluteFill style={{background: `radial-gradient(90% 90% at 50% 30%, ${shade(P.background, 0.12)} 0%, ${P.background} 45%, ${P.background2} 100%)`}}>
      <div style={{position: 'absolute', left: cx - shW / 2, top: floorY - 18 * u, width: shW, height: 36 * u, borderRadius: '50%', background: 'radial-gradient(closest-side, rgba(0,0,0,0.42), rgba(0,0,0,0))', opacity: inP * (0.9 - 0.25 * lift - (floatY / u) * 0.015), filter: `blur(${5 * u}px)`}} />
      {hasText && (
        <div style={{position: 'absolute', left: sideText ? w * 0.07 : 0, right: sideText ? w * 0.55 : 0, top: sideText ? h * 0.5 : h * 0.075, transform: sideText ? `translateY(-50%) translateY(${(1 - textA) * 24 * u}px)` : `translateY(${(1 - textA) * 24 * u}px)`, opacity: textA, textAlign: sideText ? 'left' : 'center', fontFamily: fonts.sans, color: ink, padding: sideText ? 0 : `0 ${w * 0.08}px`}}>
          <div style={{fontSize: (portrait ? 78 : 76) * u, fontWeight: 800, lineHeight: 1.03, letterSpacing: -2 * u}}>{P.headline}</div>
          {P.subline && <div style={{fontSize: (portrait ? 34 : 30) * u, marginTop: 20 * u, opacity: 0.72, lineHeight: 1.3}}>{P.subline}</div>}
        </div>
      )}
      <div style={{position: 'absolute', left: cx - devW / 2, top: cy - devH / 2, width: devW, height: devH, perspective: 1900 * u, opacity: clamp(frame / 8)}}>
        <div style={{position: 'absolute', left: 0, top: 0, width: devW, height: devH, transformStyle: 'preserve-3d', transform: `translateY(${y}px) translateZ(${lift * 90 * u}px) rotateX(${rotX}deg) rotateY(${rotY}deg)`}}>
          {device === 'laptop' ? (
            <div style={{position: 'absolute', left: 0, top: 0, width: devW, height: devH, transformStyle: 'preserve-3d'}}>
              <div style={{position: 'absolute', left: (1040 - 900) * 0.5 * k, top: 0, width: spec.bw * k, height: spec.bh * k, transformStyle: 'preserve-3d'}}>
                <Face P={P} spec={spec} k={k} variant={0} frame={frame} src={P.src} z={thick / 2} />
                <Face P={P} spec={spec} k={k} variant={1} frame={frame} src={P.src2 || P.src} z={-thick / 2} back />
              </div>
              <div style={{position: 'absolute', left: 0, top: spec.bh * k, width: devW, height: 24 * k, borderRadius: `0 0 ${18 * k}px ${18 * k}px`, background: `linear-gradient(180deg, ${shade(P.bodyColor, 0.3)}, ${shade(P.bodyColor, -0.1)})`, transform: `translateZ(${thick / 2}px)`, backfaceVisibility: 'hidden'}} />
            </div>
          ) : (
            <>
              {device === 'watch' && [0, 1].map((d) => (
                <div key={d} style={{position: 'absolute', left: 50 * k, width: 150 * k, top: d === 0 ? 0 : 410 * k, height: 150 * k, borderRadius: d === 0 ? `${44 * k}px ${44 * k}px ${6 * k}px ${6 * k}px` : `${6 * k}px ${6 * k}px ${44 * k}px ${44 * k}px`, background: `linear-gradient(90deg, ${shade(P.accent, -0.45)}, ${shade(P.accent, -0.1)}, ${shade(P.accent, -0.45)})`, transform: 'translateZ(-3px)'}} />
              ))}
              <div style={{position: 'absolute', left: 0, top: device === 'watch' ? 130 * k : 0, width: spec.bw * k, height: spec.bh * k, transformStyle: 'preserve-3d'}}>
              {Array.from({length: slices}).map((_, i) => (
                <div key={i} style={{position: 'absolute', left: 0, top: 0, width: spec.bw * k, height: spec.bh * k, borderRadius: spec.r * k, background: shade(P.bodyColor, -0.12 - (i % 2) * 0.05), transform: `translateZ(${(-0.5 + i / (slices - 1)) * thick}px)`}} />
              ))}
              <Face P={P} spec={spec} k={k} variant={0} frame={frame} src={P.src} z={thick / 2} />
              <Face P={P} spec={spec} k={k} variant={1} frame={frame} src={P.src2 || P.src} z={-thick / 2} back />
              </div>
            </>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const deviceMockup = defineMotion<Props>({
  id: 'device-mockup',
  title: 'Device mockup (phone, tablet, laptop, watch)',
  category: 'ui',
  description:
    'A CSS-built phone, android, tablet, laptop or watch with your screen content (a picture, a tall screenshot that scrolls, or a built-in app UI): it tilts in from 25 degrees and settles on a soft floor shadow, sways gently, then flips over to show a second panel while an optional headline fades in beside it.',
  source: ['prompt corpus x18 (device frame with real screen content, 3D tilt entry, flip to second panel)'],
  useFor: 'App launches, feature tours, testimonials, store previews: makes a host screenshot look shipped. Pass `src` (and `src2` for the flip side) and `device`.',
  durationInFrames: 180,
  defaultProps: {
    device: 'iphone',
    src: '',
    src2: '',
    fit: 'cover',
    scroll: [0, 1],
    scrollFrames: [26, 96],
    tilt: 25,
    flipAt: 112,
    headline: '',
    subline: '',
    bodyColor: '#1c1e26',
    accent: '#4f6bff',
    background: '#dfe5f5',
    background2: '#b9c4e6',
    textColor: '#16203f',
    size: 1,
    brand: 'Lumen',
    statusTime: '9:41',
    greeting: 'Good morning',
    appSuffix: 'Today',
    goal: 78,
    goalLabel: 'Daily goal',
    goalTitle: 'On track',
    goalNote: '3 of 4 habits done',
    stats: [['Streak', '12 d'], ['Score', '864'], ['Rank', '#3']],
    activityTitle: 'Activity',
    activityRows: [
      ['Morning run', '5.2 km', '#ff8a5b'],
      ['Focus block', '2 h 10 m', '#6c8cff'],
      ['Water', '1.8 l', '#35c4c0'],
      ['Reading', '24 pages', '#b07cff'],
      ['Sleep', '7 h 40 m', '#ffb84d'],
      ['Stretching', '12 min', '#ff6b8b'],
      ['Walk', '8 400 steps', '#5bd68a'],
      ['Journal', '1 entry', '#6c8cff'],
    ],
    rowDays: ['Today', 'Yesterday'],
    weekLabel: 'This week',
    weekValue: '41.2 h',
    weekDelta: '+12% vs last week',
    weekBars: [0.45, 0.7, 0.55, 0.9, 0.62, 0.38, 0.8],
    weekDays: ['M', 'T', 'W', 'T', 'F', 'S', 'S'],
    highlightsTitle: 'Highlights',
    highlights: ['Best focus day: Thursday', 'Longest streak: 12 days', 'New personal record'],
    dashMenu: ['Overview', 'Reports', 'Customers', 'Billing', 'Settings'],
    dashTitles: ['Overview', 'Reports'],
    dashStats: [['Revenue', '$84.2k'], ['Users', '12,480'], ['Growth', '+18%']],
    dashChartTitle: 'Monthly activity',
    dashBars: [0.4, 0.62, 0.5, 0.8, 0.66, 0.9, 0.74, 0.95, 0.7, 0.55, 0.78, 0.86],
    watchLabel: 'Heart rate',
    watchValue: '72',
    watchUnit: 'bpm',
  },
  propDocs: {
    device: "'iphone' | 'android' | 'tablet' | 'laptop' | 'watch'",
    src: 'screen image (public/ path or URL); empty = built-in app UI',
    src2: 'image on the flip side (default: reuse src, or the second built-in panel)',
    fit: "'cover' (fill the screen) | 'scroll' (fit width and scroll a tall screenshot)",
    scroll: '[from, to] scroll position 0..1 of the overflow (tall screenshot or built-in list)',
    scrollFrames: '[start, end] frames of the scroll',
    tilt: 'entry rotateY in degrees (25 -> 0)',
    flipAt: 'frame the device flips to its second panel (0 = never)',
    headline: 'optional headline beside / above the device',
    subline: 'optional sub line under the headline',
    bodyColor: 'device body colour',
    accent: 'accent colour of the built-in UI (and watch strap)',
    background: 'backdrop colour',
    background2: 'backdrop edge colour',
    textColor: 'headline colour',
    size: 'device size multiplier',
    brand: 'name shown in the built-in UI',
    statusTime: 'clock text in the phone status bar and on the watch face',
    greeting: 'small greeting above the app title (phone / tablet / android UI)',
    appSuffix: 'word after the brand in the app title ("<brand> <appSuffix>")',
    goal: 'goal ring percentage 0-100 (ring fill and the number inside)',
    goalLabel: 'small label in the goal card',
    goalTitle: 'big word in the goal card',
    goalNote: 'note under the goal title',
    stats: 'three small stat tiles [label, value]',
    activityTitle: 'heading of the activity list',
    activityRows: 'activity list rows [name, value, icon colour (optional)]',
    rowDays: '[even-row tag, odd-row tag] shown under each activity name',
    weekLabel: 'small label above the big number on the second phone panel',
    weekValue: 'big number on the second phone panel',
    weekDelta: 'green delta line on the second phone panel',
    weekBars: 'bar heights 0..1 on the second phone panel',
    weekDays: 'one label under each bar',
    highlightsTitle: 'heading above the highlight chips',
    highlights: 'highlight chip texts on the second phone panel',
    dashMenu: 'laptop dashboard sidebar items',
    dashTitles: '[front, back] page heading of the laptop dashboard',
    dashStats: 'laptop dashboard stat cards [label, value]',
    dashChartTitle: 'title of the laptop dashboard bar chart',
    dashBars: 'laptop dashboard bar heights 0..1',
    watchLabel: 'label on the second watch panel',
    watchValue: 'big number on the second watch panel',
    watchUnit: 'unit under the watch number',
  },
  component: DeviceMockup,
  tags: ['device', 'mockup', 'phone', 'iphone', 'android', 'tablet', 'laptop', 'watch', 'app', 'screenshot', 'scroll', 'flip', 'product', 'launch', 'app store', 'css 3d', 'tilt', 'ui', 'testimonial'],
});
