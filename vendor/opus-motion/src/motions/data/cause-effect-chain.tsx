import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {fonts} from '../../core/fonts';
import {backOut, easeOut3, mixHex, sseg, withAlpha} from '../../core/r2-s1-kit';
import {fitText, inkOn} from '../../core/r3-explain';
import {Svg, useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * Cause -> effect chain: step boxes laid out along a (serpentine) path, linked by arrows. They light up one after
 * another, the colour blending from the cause colour to the effect colour, ending in a pulse on the final effect.
 */
type Props = {
  title: string;
  steps: string[];
  causeLabel: string;
  effectLabel: string;
  background: string;
  ink: string;
  accent: string;
  accent2: string;
  card: string;
  fontFamily: string;
  startAt: number;
  stagger: number;
};

const CauseEffectChain: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const {w, h, u, portrait} = useStage();
  const steps = (p.steps || []).slice(0, 7);
  const n = Math.max(1, steps.length);
  const f = Math.max(0, frame - p.startAt);
  const font = p.fontFamily || fonts.grotesk;
  const wide = w / h > 1.5;
  const cols = portrait ? 1 : wide ? (n <= 4 ? n : Math.ceil(n / 2)) : 2;
  const rowsN = Math.ceil(n / cols);
  const mx = w * 0.06;
  const top = h * (p.title ? 0.2 : 0.08);
  const bottom = h * 0.07;
  const areaW = w - mx * 2;
  const areaH = h - top - bottom;
  const gapX = (portrait ? 0 : 0.34) * areaW / cols;
  const bw = cols === 1 ? Math.min(areaW, 900 * u) : (areaW - gapX * (cols - 1)) / cols;
  const gapY = rowsN > 1 ? (portrait ? 100 : 90) * u : 0;
  const bh = Math.min((areaH - gapY * (rowsN - 1)) / rowsN, portrait ? 190 * u : 220 * u);
  const gridH = rowsN * bh + (rowsN - 1) * gapY;
  const oy = top + (areaH - gridH) / 2;
  const gx = cols === 1 ? 0 : (areaW - cols * bw) / (cols - 1);
  const ox = cols === 1 ? mx + (areaW - bw) / 2 : mx;

  const pos = steps.map((_, i) => {
    const r = Math.floor(i / cols);
    const cc = i % cols;
    const c = r % 2 === 0 ? cc : cols - 1 - cc;
    return {x: ox + c * (bw + gx), y: oy + r * (bh + gapY), r, c};
  });
  const fitAll = Math.min(...steps.map((s) => fitText(s, bw - 40 * u, bh - 60 * u, (portrait ? 44 : 38) * u, 20 * u).fs), 60 * u);
  const per = Math.max(10, p.stagger || 30);
  const t0 = 20;
  const last = n - 1;
  const titleIn = easeOut3(sseg(f, 0, 20));
  const showBg = p.background !== 'transparent';

  return (
    <AbsoluteFill style={{background: showBg ? p.background : undefined}}>
      <Svg>
        {p.title ? (
          <text x={w / 2} y={h * 0.1 + 16 * u} textAnchor="middle" fontFamily={font} fontWeight={700} fontSize={Math.min((portrait ? 64 : 58) * u, (w * 0.9) / Math.max(8, p.title.length * 0.56))} fill={p.ink} opacity={titleIn} transform={`translate(0 ${(1 - titleIn) * -20 * u})`}>
            {p.title}
          </text>
        ) : null}
        {/* arrows */}
        {steps.slice(0, -1).map((_, i) => {
          const a = pos[i];
          const b = pos[i + 1];
          const col = mixHex(p.accent, p.accent2, (i + 0.5) / Math.max(1, last));
          const start = t0 + i * per + per * 0.55;
          const k = sseg(f, start, start + per * 0.55);
          let x1: number, y1: number, x2: number, y2: number;
          if (a.r === b.r) {
            const dir = b.x > a.x ? 1 : -1;
            x1 = a.x + (dir > 0 ? bw : 0) + dir * 10 * u;
            x2 = b.x + (dir > 0 ? 0 : bw) - dir * 14 * u;
            y1 = y2 = a.y + bh / 2;
          } else {
            x1 = x2 = a.x + bw / 2;
            y1 = a.y + bh + 10 * u;
            y2 = b.y - 26 * u;
          }
          const L = Math.hypot(x2 - x1, y2 - y1) || 1;
          const head = 22 * u;
          const kl = Math.min(k, (L - head * 0.8) / L);
          const ex = x1 + (x2 - x1) * kl;
          const ey = y1 + (y2 - y1) * kl;
          const ang = (Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI;
          const travel = sseg(f, start + per * 0.3, start + per * 0.9);
          return (
            <g key={i}>
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={withAlpha(p.ink, 0.16)} strokeWidth={6 * u} strokeLinecap="round" strokeDasharray={`${12 * u} ${12 * u}`} />
              {k > 0 ? <line x1={x1} y1={y1} x2={ex} y2={ey} stroke={col} strokeWidth={7 * u} strokeLinecap="round" /> : null}
              {k >= 0.98 ? <path d={`M0 0L${-head} ${-head * 0.55}L${-head} ${head * 0.55}z`} fill={col} transform={`translate(${x2} ${y2}) rotate(${ang})`} /> : null}
              {k >= 0.98 && travel > 0 && travel < 1 ? <circle cx={x1 + (x2 - x1) * travel} cy={y1 + (y2 - y1) * travel} r={9 * u} fill={col} opacity={0.9 * (1 - travel)} /> : null}
            </g>
          );
        })}
        {/* boxes */}
        {steps.map((s, i) => {
          const a = pos[i];
          const at = t0 + i * per;
          const enter = backOut(sseg(f, at - 12, at + 4), 1.5);
          const lit = easeOut3(sseg(f, at, at + 14));
          const col = mixHex(p.accent, p.accent2, i / Math.max(1, last));
          const fill = mixHex(p.card, col, lit);
          const ink = lit > 0.55 ? inkOn(col) : p.ink;
          const fit = fitText(s, bw - 44 * u, bh - 62 * u, fitAll, 14 * u);
          const isLast = i === last && n > 1;
          const pulse = isLast ? sseg(f, at + 8, at + 40) : 0;
          const tag = i === 0 && n > 1 ? p.causeLabel : isLast ? p.effectLabel : '';
          return (
            <g key={i} transform={`translate(${a.x + bw / 2} ${a.y + bh / 2}) scale(${Math.max(0.001, enter)})`} opacity={Math.min(1, enter * 2)}>
              {pulse > 0 && pulse < 1 ? <rect x={-bw / 2 - pulse * 30 * u} y={-bh / 2 - pulse * 30 * u} width={bw + pulse * 60 * u} height={bh + pulse * 60 * u} rx={26 * u + pulse * 30 * u} fill="none" stroke={col} strokeWidth={5 * u} opacity={1 - pulse} /> : null}
              <rect x={-bw / 2} y={-bh / 2} width={bw} height={bh} rx={26 * u} fill={fill} stroke={lit > 0.1 ? col : withAlpha(p.ink, 0.2)} strokeWidth={4 * u} />
              <circle cx={-bw / 2 + 4 * u} cy={-bh / 2 + 4 * u} r={22 * u} fill={col} stroke={mixHex(p.background === 'transparent' ? '#ffffff' : p.background, '#ffffff', 0)} strokeWidth={0} />
              <text x={-bw / 2 + 4 * u} y={-bh / 2 + 4 * u + 8 * u} textAnchor="middle" fontFamily={fonts.display} fontSize={22 * u} fill={inkOn(col)}>
                {i + 1}
              </text>
              <text textAnchor="middle" fontFamily={font} fontWeight={700} fontSize={fit.fs} fill={ink}>
                {fit.lines.map((l, j) => (
                  <tspan key={j} x={0} y={(j - (fit.lines.length - 1) / 2) * fit.fs * fit.lh + fit.fs * 0.34}>
                    {l}
                  </tspan>
                ))}
              </text>
              {tag ? (
                <g transform={`translate(0 ${-bh / 2})`}>
                  <rect x={-tag.length * 8.5 * u - 14 * u} y={-17 * u} width={tag.length * 17 * u + 28 * u} height={34 * u} rx={17 * u} fill={p.ink} />
                  <text textAnchor="middle" y={8 * u} fontFamily={fonts.display} fontSize={20 * u} letterSpacing={3 * u} fill={inkOn(p.ink)}>
                    {tag}
                  </text>
                </g>
              ) : null}
            </g>
          );
        })}
      </Svg>
    </AbsoluteFill>
  );
};

export const causeEffectChain = defineMotion<Props>({
  id: 'cause-effect-chain',
  title: 'Cause and effect chain',
  category: 'data',
  description: 'Step boxes linked by dashed arrows; each arrow fills with a travelling pulse and the next box lights up, the colour sliding from the cause colour to the effect colour, ending with a pulse ring on the last box.',
  source: ['original (round 3)'],
  useFor: 'Domino-effect explainers, "how X leads to Y" chains, root-cause stories, economics / science / news cause chains — pass `steps` (2-7 short strings).',
  durationInFrames: 240,
  defaultProps: {
    title: 'How one decision ripples out',
    steps: ['Interest rates rise', 'Loans cost more', 'People spend less', 'Businesses sell less', 'Prices stop rising'],
    causeLabel: 'CAUSE',
    effectLabel: 'EFFECT',
    background: '#0F1B2D',
    ink: '#EAF0FA',
    accent: '#F4B63D',
    accent2: '#E5543F',
    card: '#1B2D48',
    fontFamily: '',
    startAt: 0,
    stagger: 30,
  },
  propDocs: {
    title: 'heading above the chain (empty = none)',
    steps: 'chain step texts, in order (up to 7)',
    causeLabel: 'tag on the first box',
    effectLabel: 'tag on the last box',
    background: "backdrop colour or 'transparent'",
    ink: 'title and idle text colour',
    accent: 'cause end colour',
    accent2: 'effect end colour',
    card: 'idle box fill',
    fontFamily: 'optional CSS font-family (empty = grotesk)',
    startAt: 'frame the chain starts',
    stagger: 'frames between steps lighting up',
  },
  component: CauseEffectChain,
  tags: ['cause', 'effect', 'chain', 'flow', 'steps', 'domino', 'sequence', 'arrows', 'process', 'because', 'consequence', 'explainer', 'education'],
});
