import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {fonts} from '../../core/fonts';
import {backOut, easeOut3, mixHex, sseg, withAlpha} from '../../core/r2-s1-kit';
import {Icon, fitText, inkOn} from '../../core/r3-explain';
import {Svg, useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * A winding path draws segment by segment through 3-6 numbered nodes. When the path reaches a node its circle
 * pops with the step icon, a number badge and the step title + description beside it.
 */
type Step = {title: string; text: string; icon: string};
type Props = {
  title: string;
  steps: Step[];
  background: string;
  ink: string;
  accent: string;
  accent2: string;
  card: string;
  fontFamily: string;
  startAt: number;
  stagger: number;
};

const StepProcessNumbered: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const {w, h, u, portrait} = useStage();
  const f = Math.max(0, frame - p.startAt);
  const font = p.fontFamily || fonts.grotesk;
  const steps = (p.steps || []).slice(0, 6);
  const n = Math.max(1, steps.length);
  const titleH = p.title ? (portrait ? 130 : 140) * u : 0;
  const per = Math.max(14, p.stagger || 36);
  const t0 = 22;
  const titleIn = easeOut3(sseg(f, 0, 20));
  const showBg = p.background !== 'transparent';
  const nodeR = (portrait ? 58 : 62) * u;

  // node positions
  const pts: {x: number; y: number; above: boolean; right: boolean}[] = [];
  if (portrait) {
    const top = h * 0.05 + titleH + nodeR + 20 * u;
    const bot = h - h * 0.06 - nodeR;
    for (let i = 0; i < n; i++) {
      const y = n === 1 ? (top + bot) / 2 : top + ((bot - top) * i) / (n - 1);
      const left = i % 2 === 0;
      pts.push({x: left ? w * 0.2 : w * 0.8, y, above: false, right: left});
    }
  } else {
    const mx = Math.max(w * 0.06, Math.min(((w * 0.82) / n), 440 * u) / 2 + 36 * u);
    const mid = h * 0.5 + titleH * 0.35;
    const amp = h * 0.14;
    for (let i = 0; i < n; i++) {
      const x = n === 1 ? w / 2 : mx + ((w - mx * 2) * i) / (n - 1);
      const up = i % 2 === 0;
      pts.push({x, y: mid + (up ? amp : -amp), above: !up, right: false});
    }
  }

  const seg = (i: number) => {
    const a = pts[i];
    const b = pts[i + 1];
    if (portrait) {
      const dy = b.y - a.y;
      return `M${a.x} ${a.y} C${a.x} ${a.y + dy * 0.6} ${b.x} ${b.y - dy * 0.6} ${b.x} ${b.y}`;
    }
    const dx = b.x - a.x;
    return `M${a.x} ${a.y} C${a.x + dx * 0.6} ${a.y} ${b.x - dx * 0.6} ${b.y} ${b.x} ${b.y}`;
  };

  const textW = portrait ? w * 0.5 : Math.min((w * 0.82) / n, 440 * u);

  return (
    <AbsoluteFill style={{background: showBg ? p.background : undefined}}>
      <Svg>
        {p.title ? (
          <text x={w / 2} y={h * 0.05 + titleH * 0.62} textAnchor="middle" fontFamily={font} fontWeight={700} fontSize={Math.min((portrait ? 66 : 60) * u, (w * 0.9) / Math.max(8, p.title.length * 0.56))} fill={p.ink} opacity={titleIn} transform={`translate(0 ${(1 - titleIn) * -20 * u})`}>
            {p.title}
          </text>
        ) : null}
        {/* path segments */}
        {pts.slice(0, -1).map((_, i) => {
          const k = easeOut3(sseg(f, t0 + i * per + 10, t0 + (i + 1) * per + 6));
          const col = mixHex(p.accent, p.accent2, (i + 0.5) / Math.max(1, n - 1));
          return (
            <g key={i}>
              <path d={seg(i)} fill="none" stroke={withAlpha(p.ink, 0.14)} strokeWidth={8 * u} strokeDasharray={`${14 * u} ${14 * u}`} strokeLinecap="round" />
              <path d={seg(i)} pathLength={1} fill="none" stroke={col} strokeWidth={9 * u} strokeLinecap="round" strokeDasharray="1 1" strokeDashoffset={1 - k} opacity={k > 0 ? 1 : 0} />
            </g>
          );
        })}
        {/* nodes */}
        {steps.map((s, i) => {
          const a = pts[i];
          const at = t0 + i * per;
          const k = backOut(sseg(f, at, at + 16), 2);
          const col = mixHex(p.accent, p.accent2, i / Math.max(1, n - 1));
          const tk = easeOut3(sseg(f, at + 8, at + 26));
          const fitT = fitText(s.title, textW, 90 * u, (portrait ? 44 : 38) * u, 18 * u, 0.6, 1.15);
          const fitD = fitText(s.text || '', textW, (portrait ? 140 : 170) * u, (portrait ? 30 : 28) * u, 16 * u, 0.52, 1.25);
          const tx = portrait ? (a.right ? a.x + nodeR + 36 * u : a.x - nodeR - 36 * u) : a.x;
          const anchor = portrait ? (a.right ? 'start' : 'end') : 'middle';
          const ty = portrait ? a.y - ((fitT.lines.length * fitT.fs * fitT.lh + fitD.lines.length * fitD.fs * fitD.lh) / 2) : a.above ? a.y - nodeR - 34 * u - (fitT.lines.length * fitT.fs * fitT.lh + fitD.lines.length * fitD.fs * fitD.lh) : a.y + nodeR + 36 * u;
          return (
            <g key={i}>
              <g transform={`translate(${a.x} ${a.y}) scale(${Math.max(0.001, k)})`}>
                <circle r={nodeR + 10 * u} fill={withAlpha(col, 0.2)} />
                <circle r={nodeR} fill={col} />
                <Icon name={s.icon || 'star'} x={0} y={0} size={nodeR * 0.95} color={inkOn(col)} sw={2.2} progress={sseg(f, at + 4, at + 22)} />
                <g transform={`translate(${-nodeR * 0.78} ${-nodeR * 0.78})`}>
                  <circle r={22 * u} fill={p.card} stroke={col} strokeWidth={4 * u} />
                  <text textAnchor="middle" y={8 * u} fontFamily={fonts.display} fontSize={22 * u} fill={mixHex(col, '#000000', 0.35)}>
                    {i + 1}
                  </text>
                </g>
              </g>
              <g opacity={tk} transform={`translate(0 ${(1 - tk) * 16 * u})`}>
                <text textAnchor={anchor as 'start' | 'end' | 'middle'} fontFamily={font} fontWeight={800} fontSize={fitT.fs} fill={p.ink}>
                  {fitT.lines.map((l, j) => (
                    <tspan key={j} x={tx} y={ty + fitT.fs * (j + 0.85) * fitT.lh}>
                      {l}
                    </tspan>
                  ))}
                </text>
                <text textAnchor={anchor as 'start' | 'end' | 'middle'} fontFamily={fonts.sans} fontWeight={500} fontSize={fitD.fs} fill={withAlpha(p.ink, 0.7)}>
                  {fitD.lines.map((l, j) => (
                    <tspan key={j} x={tx} y={ty + fitT.lines.length * fitT.fs * fitT.lh + 8 * u + fitD.fs * (j + 0.85) * fitD.lh}>
                      {l}
                    </tspan>
                  ))}
                </text>
              </g>
            </g>
          );
        })}
      </Svg>
    </AbsoluteFill>
  );
};

export const stepProcessNumbered = defineMotion<Props>({
  id: 'step-process-numbered',
  title: 'Numbered step process',
  category: 'data',
  description: 'A winding path draws through numbered icon nodes; each node pops as the path reaches it, with a number badge and a title + description that fade in beside it.',
  source: ['original (round 3)'],
  useFor: 'How-it-works, onboarding, recipes, tutorials and "3 steps to…" explainers — pass `steps` as {title, text, icon} (icons: check, bulb, gear, target, chart, user, doc, bolt, star, flag, search, clock, heart, globe, lock, book, rocket).',
  durationInFrames: 270,
  defaultProps: {
    title: 'How it works',
    steps: [
      {title: 'Sign up', text: 'Create a free account in under a minute.', icon: 'user'},
      {title: 'Set your goal', text: 'Pick what you want to achieve.', icon: 'target'},
      {title: 'Build the plan', text: 'We turn it into small daily steps.', icon: 'gear'},
      {title: 'See results', text: 'Track progress and celebrate wins.', icon: 'chart'},
    ],
    background: '#111A2B',
    ink: '#F1F4FB',
    accent: '#4DD0B1',
    accent2: '#FFB347',
    card: '#FFFFFF',
    fontFamily: '',
    startAt: 0,
    stagger: 36,
  },
  propDocs: {
    title: 'heading (empty = none)',
    steps: 'array of {title, text, icon} (3-6). icon is a name from the built-in set',
    background: "backdrop colour or 'transparent'",
    ink: 'text colour',
    accent: 'first-step colour',
    accent2: 'last-step colour (colours blend along the path)',
    card: 'number badge fill',
    fontFamily: 'optional CSS font-family for step titles (empty = grotesk)',
    startAt: 'frame the title starts',
    stagger: 'frames between steps',
  },
  component: StepProcessNumbered,
  tags: ['steps', 'process', 'how-it-works', 'numbered', 'workflow', 'roadmap', 'tutorial', 'onboarding', 'path', 'icons', 'timeline', 'explainer', 'education'],
});
