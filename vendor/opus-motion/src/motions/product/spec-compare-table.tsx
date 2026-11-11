import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {fonts} from '../../core/fonts';
import {textW} from '../../core/product-kit';
import {backOut, easeOut3, mixHex, sseg, withAlpha} from '../../core/r2-s1-kit';
import {Svg, useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * Spec comparison table: 2-4 products across, spec rows tick in one by one, the per-row best value gets a check,
 * then the winning column is lit up with a band and a badge.
 */
type Row = {label: string; values: string[]; win?: number};
type Props = {
  title: string;
  products: string[];
  rows: Row[];
  winner: number;
  winnerLabel: string;
  background: string;
  ink: string;
  accent: string;
  card: string;
  fontFamily: string;
  startAt: number;
  stagger: number;
};

const SpecCompareTable: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const {w, h, u, portrait} = useStage();
  const prods = (p.products || []).slice(0, 4);
  const nc = Math.max(1, prods.length);
  const rows = (p.rows || []).slice(0, 9);
  const tw = portrait ? w * 0.92 : Math.min(w * 0.8, 1500 * u);
  const labelW = tw * (portrait ? 0.27 : 0.25);
  const colW = (tw - labelW) / nc;
  const rh = Math.min(h * 0.095, (portrait ? 118 : 104) * u);
  const headH = rh * 1.35;
  const titleH = (portrait ? 150 : 110) * u;
  const total = titleH + headH + rows.length * rh;
  const x0 = (w - tw) / 2;
  const y0 = Math.max(h * 0.04, (h - total) / 2);
  const font = p.fontFamily || fonts.grotesk;
  const fsL = Math.min(rh * 0.34, 30 * u * (portrait ? 1.05 : 1));
  const rowsDone = p.startAt + 24 + rows.length * p.stagger;
  const bandIn = easeOut3(sseg(frame, rowsDone, rowsDone + 22));
  const enter = easeOut3(sseg(frame, 0, 22));
  const hasWin = p.winner >= 0 && p.winner < nc;
  const wx = x0 + labelW + p.winner * colW;
  const bg = p.background === 'transparent' ? '#ffffff' : p.background;

  return (
    <AbsoluteFill style={{background: p.background === 'transparent' ? undefined : p.background}}>
      <Svg>
        <text x={x0} y={y0 + titleH * 0.5} fontFamily={font} fontWeight={700} fontSize={(portrait ? 62 : 56) * u} fill={p.ink} opacity={enter}>
          {p.title}
        </text>
        <g transform={`translate(0 ${y0 + titleH})`}>
          {/* card */}
          <rect x={x0} y={0} width={tw} height={headH + rows.length * rh} rx={20 * u} fill={p.card} opacity={enter} stroke={withAlpha(p.ink, 0.12)} strokeWidth={2 * u} />
          {/* winner band */}
          {hasWin ? (
            <g opacity={bandIn}>
              <rect x={wx + 6 * u} y={-14 * u * bandIn} width={colW - 12 * u} height={headH + rows.length * rh + 28 * u * bandIn} rx={18 * u} fill={withAlpha(p.accent, 0.12)} stroke={p.accent} strokeWidth={3.5 * u} />
              <g transform={`translate(${wx + colW / 2} ${-14 * u - 4 * u})`}>
                <rect x={-textW(p.winnerLabel, 20 * u, 0.62) / 2 - 18 * u} y={-34 * u} width={textW(p.winnerLabel, 20 * u, 0.62) + 36 * u} height={34 * u} rx={17 * u} fill={p.accent} />
                <text y={-10 * u} textAnchor="middle" fontFamily={fonts.sans} fontWeight={800} fontSize={20 * u} letterSpacing={2 * u} fill={mixHex(p.accent, '#ffffff', 0.92)}>
                  {p.winnerLabel}
                </text>
              </g>
            </g>
          ) : null}
          {/* header */}
          {prods.map((name, c) => {
            const k = easeOut3(sseg(frame, 8 + c * 5, 24 + c * 5));
            const fs = Math.min(headH * 0.3, (colW * 0.88) / Math.max(1, textW(name, 1, 0.6)), 38 * u);
            return (
              <text key={c} x={x0 + labelW + c * colW + colW / 2} y={headH * 0.6} textAnchor="middle" fontFamily={font} fontWeight={700} fontSize={fs} fill={p.ink} opacity={k}>
                {name}
              </text>
            );
          })}
          {/* rows */}
          {rows.map((r, i) => {
            const t0 = p.startAt + 24 + i * p.stagger;
            const k = easeOut3(sseg(frame, t0, t0 + 14));
            const y = headH + i * rh;
            const vals = r.values || [];
            return (
              <g key={i} opacity={k} transform={`translate(${(1 - k) * -26 * u} 0)`}>
                <line x1={x0 + 22 * u} y1={y} x2={x0 + tw - 22 * u} y2={y} stroke={withAlpha(p.ink, 0.12)} strokeWidth={2 * u} />
                <text x={x0 + 26 * u} y={y + rh * 0.62} fontFamily={fonts.sans} fontWeight={600} fontSize={fsL * 0.92} fill={withAlpha(p.ink, 0.62)}>
                  {r.label}
                </text>
                {prods.map((_, c) => {
                  const v = vals[c] ?? '';
                  const fs = Math.min(fsL, (colW * 0.8) / Math.max(1, textW(v, 1, 0.58)));
                  const cxc = x0 + labelW + c * colW + colW / 2;
                  const isWin = r.win === c;
                  const tk = backOut(sseg(frame, t0 + 8, t0 + 20), 2.4);
                  return (
                    <g key={c}>
                      <text x={cxc} y={y + rh * 0.62} textAnchor="middle" fontFamily={font} fontWeight={isWin ? 800 : 600} fontSize={fs} fill={isWin ? p.accent : p.ink}>
                        {v}
                      </text>
                      {isWin ? (
                        <g transform={`translate(${cxc + Math.min(colW * 0.42, textW(v, fs, 0.58) / 2 + 26 * u)} ${y + rh * 0.5}) scale(${Math.max(0.001, tk)})`}>
                          <circle r={13 * u} fill={p.accent} />
                          <path d={`M${-6 * u} ${0}L${-1.5 * u} ${5 * u}L${7 * u} ${-5 * u}`} fill="none" stroke={bg} strokeWidth={3 * u} strokeLinecap="round" strokeLinejoin="round" />
                        </g>
                      ) : null}
                    </g>
                  );
                })}
              </g>
            );
          })}
        </g>
      </Svg>
    </AbsoluteFill>
  );
};

export const specCompareTable = defineMotion<Props>({
  id: 'spec-compare-table',
  title: 'Spec comparison table',
  category: 'product',
  description:
    'A comparison card: product names across the top, spec rows ticking in one after another with a check on each row winner, then the winning column is lit with an accent band and a badge.',
  source: ['original (round 3)'],
  useFor: 'Versus / comparison videos, plan and pricing tiers, "why ours" slides, product roundups — pass your products and rows.',
  durationInFrames: 210,
  defaultProps: {
    title: 'Which one is for you?',
    products: ['Lite', 'Pro', 'Max'],
    rows: [
      {label: 'Battery', values: ['20 h', '36 h', '48 h'], win: 2},
      {label: 'Weight', values: ['240 g', '255 g', '310 g'], win: 0},
      {label: 'Noise cancelling', values: ['Basic', 'Adaptive', 'Adaptive'], win: 1},
      {label: 'Water rating', values: ['None', 'IPX4', 'IPX5'], win: 2},
      {label: 'Price', values: ['$129', '$199', '$299'], win: 0},
    ],
    winner: 1,
    winnerLabel: 'BEST VALUE',
    background: '#EFEBE3',
    ink: '#1A1A22',
    accent: '#F0502C',
    card: '#FFFFFF',
    fontFamily: '',
    startAt: 10,
    stagger: 18,
  },
  propDocs: {
    title: 'heading above the table',
    products: 'column headings (2-4)',
    rows: 'array of {label, values[] (one per product), win? (column index that gets the check)}',
    winner: 'index of the highlighted column (-1 for none)',
    winnerLabel: 'badge text above the winning column',
    background: "backdrop colour or 'transparent'",
    ink: 'text colour',
    accent: 'check, winner band and badge colour',
    card: 'table card colour',
    fontFamily: 'optional CSS font-family for names and values (empty = grotesk)',
    startAt: 'frame the first row starts',
    stagger: 'frames between rows',
  },
  component: SpecCompareTable,
  tags: ['compare', 'comparison', 'table', 'specs', 'versus', 'pricing', 'plans', 'product', 'features', 'winner', 'checklist'],
});
