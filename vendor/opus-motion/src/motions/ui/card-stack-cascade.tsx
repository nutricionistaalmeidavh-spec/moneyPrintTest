import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {resolveSrc} from '../../core/asset';
import {ease, lerp, prog} from '../../core/ease';
import {fonts} from '../../core/fonts';
import {IconBox, clamp01} from '../../core/r2-pr1-kit';
import {useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * Feature cards scale in from 30 % with a fade, staggered 4 f apart, into a bento grid (or a row / a fanned deck);
 * everything breathes a little, then one card is focused: it flies to the centre and grows to ~60 % of the frame while
 * the others dim to 40 % and defocus, and finally everything settles back. Layout is computed per format.
 */

type Card = {title: string; body?: string; icon?: string; image?: string; span?: string | number};
type Props = {
  cards: Card[];
  layout: 'bento' | 'row' | 'stack';
  focusAt: number;
  focusIndex: number;
  unfocusAt: number;
  stagger: number;
  dimTo: number;
  dark: boolean;
  accent: string;
  background: string;
};

const parseSpan = (s: string | number | undefined, cols: number): [number, number] => {
  if (typeof s === 'number') return [Math.min(cols, Math.max(1, s)), 1];
  const m = /^(\d+)\s*[x×]\s*(\d+)$/.exec(s ?? '');
  return m ? [Math.min(cols, Math.max(1, +m[1])), Math.max(1, +m[2])] : [1, 1];
};

type Rect = {x: number; y: number; w: number; h: number; rot: number};

const CardStackCascade: React.FC<Props> = ({cards, layout, focusAt, focusIndex, unfocusAt, stagger, dimTo, dark, accent, background}) => {
  const frame = useCurrentFrame();
  const {w, h, u, portrait, square} = useStage();
  const n = cards.length;
  const gap = Math.min(w, h) * 0.022;
  const ax = w * (portrait ? 0.06 : 0.06);
  const ay = h * (portrait ? 0.07 : 0.1);
  const aw = w - ax * 2;
  const ah = h - ay * 2;

  // ---- layout rects
  const rects: Rect[] = [];
  if (layout === 'bento') {
    const cols = portrait ? 2 : square ? 3 : 4;
    const spans = cards.map((c) => parseSpan(c.span, cols));
    const occ: boolean[][] = [];
    const place: {r: number; c: number}[] = [];
    const free = (r: number, c: number, sc: number, sr: number) => {
      if (c + sc > cols) return false;
      for (let i = 0; i < sr; i++) for (let j = 0; j < sc; j++) if (occ[r + i]?.[c + j]) return false;
      return true;
    };
    spans.forEach(([sc, sr]) => {
      let r = 0;
      let done = false;
      while (!done) {
        for (let c = 0; c < cols && !done; c++) {
          if (free(r, c, sc, sr)) {
            for (let i = 0; i < sr; i++) for (let j = 0; j < sc; j++) (occ[r + i] ??= [])[c + j] = true;
            place.push({r, c});
            done = true;
          }
        }
        r++;
      }
    });
    const rows = Math.max(...place.map((p, i) => p.r + spans[i][1]));
    const cw = (aw - gap * (cols - 1)) / cols;
    const rh = (ah - gap * (rows - 1)) / rows;
    place.forEach((p, i) => rects.push({x: ax + p.c * (cw + gap), y: ay + p.r * (rh + gap), w: spans[i][0] * cw + (spans[i][0] - 1) * gap, h: spans[i][1] * rh + (spans[i][1] - 1) * gap, rot: 0}));
  } else if (layout === 'row') {
    const horizontal = !portrait;
    for (let i = 0; i < n; i++) {
      if (horizontal) {
        const cw = (aw - gap * (n - 1)) / n;
        rects.push({x: ax + i * (cw + gap), y: h * 0.2, w: cw, h: h * 0.6, rot: 0});
      } else {
        const rh = (ah - gap * (n - 1)) / n;
        rects.push({x: ax, y: ay + i * (rh + gap), w: aw, h: rh, rot: 0});
      }
    }
  } else {
    const cw = portrait ? w * 0.74 : Math.min(w * 0.3, 560 * u);
    const ch = portrait ? h * 0.34 : h * 0.5;
    for (let i = 0; i < n; i++) {
      const k = i - (n - 1) / 2;
      rects.push({x: w / 2 - cw / 2 + k * 34 * u, y: h / 2 - ch / 2 + k * 26 * u, w: cw, h: ch, rot: k * 3.2});
    }
  }

  // ---- focus
  const fIdx = Math.min(n - 1, Math.max(0, focusIndex));
  const fo = prog(frame, focusAt, focusAt + 20, ease.inOut) * (unfocusAt > 0 ? 1 - prog(frame, unfocusAt, unfocusAt + 20, ease.inOut) : 1);

  const card = dark ? '#1C1D23' : '#FFFFFF';
  const ink = dark ? '#F2F0EA' : '#17171B';
  const muted = dark ? 'rgba(242,240,234,0.6)' : 'rgba(23,23,27,0.58)';
  const bg = background || (dark ? '#0E0F13' : '#ECE8E1');

  return (
    <AbsoluteFill style={{background: bg, overflow: 'hidden'}}>
      <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 35%, ${dark ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.55)'} 0%, rgba(0,0,0,0) 70%)`}} />
      {cards.map((c, i) => {
        const r = rects[i];
        if (!r) return null;
        const t0 = 8 + i * stagger;
        const pin = prog(frame, t0, t0 + 16, ease.back);
        if (pin <= 0) return null;
        const alpha = prog(frame, t0, t0 + 10, ease.out);
        const isF = i === fIdx;
        // focus transform
        const tw = portrait ? w * 0.86 : w * 0.5;
        const th = portrait ? h * 0.4 : h * 0.62;
        const fs = Math.min(tw / r.w, th / r.h);
        const fx = w / 2 - (r.x + r.w / 2);
        const fy = h / 2 - (r.y + r.h / 2);
        const tx = isF ? fx * fo : 0;
        const ty = isF ? fy * fo : 0;
        const sc = lerp(0.3, 1, pin) * (isF ? lerp(1, fs, fo) : lerp(1, 0.94, fo));
        const idleY = Math.sin(frame / 38 + i * 1.7) * 3.2 * u * (1 - fo);
        const op = alpha * (isF ? 1 : lerp(1, dimTo, fo));
        const base = Math.min(r.w, r.h);
        const tSize = Math.max(18 * u, Math.min(base * 0.135, 46 * u * (r.w > r.h * 1.5 ? 1.15 : 1)));
        const hue = (i * 53 + 215) % 360;
        const big = r.w * r.h > (aw * ah) / 7;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: r.x,
              top: r.y,
              width: r.w,
              height: r.h,
              borderRadius: Math.min(base * 0.12, 34 * u),
              background: card,
              boxShadow: isF && fo > 0.05 ? `0 ${40 * u * fo}px ${90 * u * fo}px rgba(0,0,0,${0.3 * fo}), 0 4px 14px rgba(0,0,0,0.08)` : dark ? '0 12px 30px rgba(0,0,0,0.4)' : '0 14px 34px rgba(60,50,30,0.12), 0 2px 6px rgba(60,50,30,0.07)',
              opacity: op,
              transform: `translate(${tx}px, ${ty + idleY}px) rotate(${r.rot * pin}deg) scale(${sc})`,
              transformOrigin: '50% 50%',
              filter: !isF && fo > 0.02 ? `blur(${2.5 * u * fo}px)` : undefined,
              zIndex: isF ? 10 : 1 + (layout === 'stack' ? i : 0),
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              padding: base * 0.1,
              boxSizing: 'border-box',
              fontFamily: fonts.sans,
              color: ink,
            }}
          >
            {c.image ? (
              <img src={resolveSrc(c.image)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', opacity: 0.95}} />
            ) : big ? (
              <svg style={{position: 'absolute', right: 0, bottom: 0, width: '50%', height: '46%', opacity: 0.9}} viewBox="0 0 100 60" preserveAspectRatio="none">
                <path d={`M0 52 C 18 ${34 - (i % 3) * 6}, 30 ${46 - (i % 2) * 8}, 46 30 S 74 ${12 + (i % 3) * 4}, 100 8 V60 H0Z`} fill={`hsl(${hue} 70% ${dark ? 40 : 90}%)`} />
                <path d={`M0 52 C 18 ${34 - (i % 3) * 6}, 30 ${46 - (i % 2) * 8}, 46 30 S 74 ${12 + (i % 3) * 4}, 100 8`} fill="none" stroke={`hsl(${hue} 70% 52%)`} strokeWidth={2.4} vectorEffect="non-scaling-stroke" />
              </svg>
            ) : null}
            <div style={{position: 'relative', width: tSize * 1.9, height: tSize * 1.9, borderRadius: tSize * 0.6, background: i === fIdx ? accent : `hsl(${hue} 80% ${dark ? 30 : 92}%)`, display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 'none'}}>
              <IconBox name={c.icon ?? ['bolt', 'shield', 'chart', 'chat', 'globe', 'spark'][i % 6]} size={tSize * 1.05} color={i === fIdx ? '#fff' : `hsl(${hue} 70% ${dark ? 70 : 42}%)`} sw={1.9} />
            </div>
            <div style={{position: 'relative', marginTop: 'auto'}}>
              <div style={{fontWeight: 800, fontSize: tSize, letterSpacing: '-0.02em', lineHeight: 1.08}}>{c.title}</div>
              {c.body ? <div style={{marginTop: tSize * 0.3, fontSize: tSize * 0.6, lineHeight: 1.3, color: muted, maxWidth: big && !c.image ? '54%' : '90%'}}>{c.body}</div> : null}
            </div>
          </div>
        );
      })}
      <AbsoluteFill style={{background: `rgba(0,0,0,${0.05 * fo})`, pointerEvents: 'none', zIndex: 5}} />
    </AbsoluteFill>
  );
};

void clamp01;

export const cardStackCascade = defineMotion<Props>({
  id: 'card-stack-cascade',
  title: 'Card stack cascade (bento + focus)',
  category: 'ui',
  description:
    'Feature cards scale in from 30 % with a fade, staggered 4 f apart, into a bento grid (or a row, or a fanned deck) with a gentle idle float; then one card flies to the centre and grows to ~60 % of the frame while the rest dim to 40 % and defocus, and everything settles back.',
  source: ['prompt-corpus: card-stack-cascade (35 cases)', 'awesome-opus5-5-videos prompts (MIT) — technique only'],
  useFor: 'Feature overviews in launch videos, website sections, pricing / plan reveals: pass `cards` (title, body, icon, span "2x1"), choose `layout`, set `focusIndex`.',
  durationInFrames: 210,
  defaultProps: {
    cards: [
      {title: 'Realtime sync', body: 'Every change lands on every device in under a second.', icon: 'bolt', span: '2x2'},
      {title: 'Private by default', body: 'End-to-end encrypted.', icon: 'shield'},
      {title: 'Insights', body: 'Dashboards that explain themselves.', icon: 'chart'},
      {title: 'Team chat', body: 'Talk where the work is.', icon: 'chat'},
      {title: 'Global scale', body: 'Edge regions worldwide.', icon: 'globe'},
      {title: 'Automations', body: 'Hand the boring parts to a workflow that never sleeps.', icon: 'spark', span: '2x1'},
    ],
    layout: 'bento',
    focusAt: 104,
    focusIndex: 1,
    unfocusAt: 176,
    stagger: 4,
    dimTo: 0.4,
    dark: false,
    accent: '#5B5FEF',
    background: '',
  },
  propDocs: {
    cards: '[{title, body?, icon?: bolt|shield|chart|chat|globe|spark|lock|cog|user|db|cloud|star, image?: public path, span?: "2x1" | number of columns}]',
    layout: "'bento' grid | 'row' | 'stack' (fanned deck)",
    focusAt: 'frame when the focused card flies to the centre',
    focusIndex: 'which card is focused (0-based)',
    unfocusAt: 'frame when everything settles back (0 = never)',
    stagger: 'frames between card entrances (3-5)',
    dimTo: 'opacity of the other cards during focus',
    dark: 'dark theme',
    accent: 'focused card accent',
    background: 'background colour (empty = theme default)',
  },
  component: CardStackCascade,
  tags: ['cards', 'bento', 'grid', 'features', 'feature overview', 'cascade', 'stack', 'deck', 'focus', 'pricing', 'plans', 'website section', 'launch', 'ui', 'saas', 'product'],
});
