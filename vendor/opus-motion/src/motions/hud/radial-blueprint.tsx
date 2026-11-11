import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {clamp, ease, prog} from '../../core/ease';
import {fonts} from '../../core/fonts';
import {BP, GlowDot, RadialPlan, ScanlineBg, typed} from '../../core/hud-kit';
import {Svg, Vignette, useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * video19 11.05-15.4: a glowing blue dot pings, the camera snaps back (easeOutExpo) to reveal a
 * seeded circular "library plan" (rings of hatched shelf blocks, 12 sectors, glowing blue hub,
 * thick blue paths entering from outside). Blue spokes then shoot from the hub to category labels
 * (radar-spoke-draw: 0.1 s out, 0.05 s hold, 0.1 s retract, pairs fire together) while nodes flow
 * along the network spokes and the plan turns slowly (~3 deg/s).
 */
type Props = {
  background: string;
  categories: string[];
  centerLabel: string;
  seed: number;
  rings: number;
  sectors: number;
  accentPaths: number;
  networkSpokes: number;
  pullFrom: number;
  rotateSpeed: number;
  accent: string;
  line: string;
  labelColor: string;
  scanlines: boolean;
};

const RadialBlueprint: React.FC<Props> = ({background, categories, centerLabel, seed, rings, sectors, accentPaths, networkSpokes, pullFrom, rotateSpeed, accent, line, labelColor, scanlines}) => {
  const frame = useCurrentFrame();
  const {w, h, u, cx, cy, portrait} = useStage();
  const R = Math.min(w, h) * (portrait ? 0.43 : 0.45);

  // pull-back reveal (snap-zoom-reveal / powers-of-ten feel)
  const pull = prog(frame, 6, 40, ease.expoOut);
  const zoom = Math.exp(Math.log(Math.max(1.01, pullFrom)) * (1 - pull));
  const r = R * zoom;
  const reveal = prog(frame, 6, 52, ease.out);
  const hub = prog(frame, 2, 22, ease.out);
  const paths = prog(frame, 30, 62, ease.inOut);
  const rot = (rotateSpeed * Math.max(0, frame - 20)) / 30;

  // dot ping at the start
  const ping = prog(frame, 1, 7, ease.in);
  const glow = 1 + 0.6 * Math.max(0, 1 - Math.abs(frame - 8) / 6) + 0.15 * Math.sin(frame * 0.2);

  // network spokes with flowing nodes
  const net = prog(frame, 40, 64, ease.out);

  // category spokes
  const n = categories.length;
  const baseAngles = portrait ? [-90, -52, 52, 128, -128, 90, 0, 180] : [-90, -30, 30, 150, -150, 90, 0, 180];
  const groups = categories.map((_, i) => (i === 0 ? 0 : Math.ceil(i / 2)));
  const labelSize = 22 * u;
  const margin = 48 * u;

  return (
    <AbsoluteFill style={{background}}>
      {scanlines && <ScanlineBg offsetX={-rot * 4 * u} />}
      <Svg>
        <RadialPlan id="rbp" cx={cx} cy={cy} r={r} seed={seed} rings={rings} sectors={sectors} accentPaths={accentPaths} reveal={reveal} hub={hub} paths={paths} rotate={rot} flow={frame} line={line} blue={accent} u={u} detail={clamp(1.6 - (zoom - 1) * 0.5)} />
        {/* radial network spokes with outward-flowing nodes */}
        {net > 0 &&
          Array.from({length: networkSpokes}, (_, i) => {
            const a = ((i / networkSpokes) * 360 + 360 / networkSpokes / 2 + rot) * (Math.PI / 180);
            const r0 = r * 0.3;
            const r1 = r * (0.3 + 0.88 * net);
            const L = r * 0.88;
            return (
              <g key={i}>
                <line x1={cx + Math.cos(a) * r0} y1={cy + Math.sin(a) * r0} x2={cx + Math.cos(a) * r1} y2={cy + Math.sin(a) * r1} stroke={accent} strokeWidth={1.6 * u} strokeOpacity={0.85} />
                {net >= 1 &&
                  [0, 1, 2, 3].map((k) => {
                    const rr = r0 + ((((frame * 2.2 * u) / 1 + k * L * 0.25 + i * 37 * u) % L) + L) % L;
                    const o = Math.min(1, (rr - r0) / (40 * u), (r0 + L - rr) / (60 * u));
                    return <circle key={k} cx={cx + Math.cos(a) * rr} cy={cy + Math.sin(a) * rr} r={(k % 2 ? 2.6 : 3.6) * u} fill={k % 2 ? '#9DBBF0' : accent} opacity={clamp(o)} />;
                  })}
              </g>
            );
          })}
        {/* periodic radar ping waves from the hub */}
        {Array.from({length: 8}, (_, k) => {
          const st = 104 + k * 40;
          const p = (frame - st) / 34;
          if (p < 0 || p > 1) return null;
          return <circle key={`pw${k}`} cx={cx} cy={cy} r={r * (0.3 + 0.75 * ease.out(p))} fill="none" stroke={accent} strokeWidth={(3 - 2 * p) * u} opacity={0.7 * (1 - p)} />;
        })}
        {/* hub dot + ping */}
        {frame < 8 && <circle cx={cx} cy={cy} r={(90 * (1 - ping) + 8) * u} fill="none" stroke="#7F98C9" strokeWidth={1.5 * u} opacity={0.7 * (1 - ping * 0.8)} />}
        <GlowDot id="rbp-dot" x={cx} y={cy} r={7 * u * Math.min(zoom, 1.6)} boost={glow} />
        {/* radar spokes to category labels */}
        {categories.map((label, i) => {
          const start = 66 + groups[i] * 9;
          if (frame < start) return null;
          const a = ((baseAngles[i % baseAngles.length] + (i >= baseAngles.length ? 17 : 0)) * Math.PI) / 180;
          const dx = Math.cos(a);
          const dy = Math.sin(a);
          const anchorR = R * 1.0;
          const align = Math.abs(dx) < 0.3 ? 'middle' : dx > 0 ? 'start' : 'end';
          const tw = label.length * labelSize * 0.62 * 1.3;
          let lx = cx + dx * R * 1.08;
          let ly = cy + dy * R * 1.08 + (Math.abs(dx) < 0.3 ? (dy < 0 ? -10 : 26) * u : 8 * u);
          const left = align === 'start' ? lx : align === 'end' ? lx - tw : lx - tw / 2;
          const shift = Math.min(0, w - margin - (left + tw)) + Math.max(0, margin - left);
          lx += shift;
          ly = clamp(ly, margin + labelSize, h - margin);
          const tipX = cx + dx * anchorR;
          const tipY = cy + dy * anchorR;
          const out = prog(frame, start, start + 4, ease.expoOut);
          const back = prog(frame, start + 6, start + 10, ease.in);
          const x0 = cx + (tipX - cx) * back;
          const y0 = cy + (tipY - cy) * back;
          const x1 = cx + (tipX - cx) * out;
          const y1 = cy + (tipY - cy) * out;
          const txt = typed(label, frame, start + 3, 40);
          const plateW = txt.length * labelSize * 0.62 * 1.3 + 18 * u;
          const plateX = align === 'start' ? lx - 9 * u : align === 'end' ? lx - plateW + 9 * u : lx - plateW / 2;
          return (
            <g key={i}>
              {back < 1 && <line x1={x0} y1={y0} x2={x1} y2={y1} stroke={accent} strokeWidth={3 * u} strokeLinecap="round" />}
              {back < 1 && <line x1={x0} y1={y0} x2={x1} y2={y1} stroke={accent} strokeWidth={10 * u} strokeOpacity={0.25} strokeLinecap="round" />}
              {out >= 1 && (
                <g opacity={prog(frame, start + 3, start + 6)}>
                  <circle cx={tipX} cy={tipY} r={6 * u} fill={background} stroke={labelColor} strokeWidth={1.5 * u} />
                  <circle cx={tipX} cy={tipY} r={2.2 * u} fill={labelColor} />
                  <line x1={tipX} y1={tipY} x2={align === 'middle' ? lx : align === 'start' ? lx - 9 * u : lx + 9 * u} y2={ly - labelSize * 0.35} stroke={labelColor} strokeOpacity={0.5} strokeWidth={1 * u} />
                  {txt.length > 0 && <rect x={plateX} y={ly - labelSize * 1.05} width={plateW} height={labelSize * 1.5} fill={background} fillOpacity={0.88} stroke={labelColor} strokeOpacity={0.45} strokeWidth={1 * u} />}
                  <text x={lx} y={ly} textAnchor={align} fill={labelColor} fontFamily={fonts.mono} fontWeight={700} fontSize={labelSize} letterSpacing={labelSize * 0.3}>
                    {txt}
                  </text>
                </g>
              )}
            </g>
          );
        })}
        {centerLabel && frame > 56 && (
          <g opacity={prog(frame, 56, 66)}>
            <rect x={cx - (centerLabel.length * 0.62 * 1.3 * 18 * u) / 2 - 10 * u} y={cy + R * 0.33} width={centerLabel.length * 0.62 * 1.3 * 18 * u + 20 * u} height={30 * u} fill={background} fillOpacity={0.9} stroke={line} strokeOpacity={0.3} strokeWidth={u} />
            <text x={cx + 0.15 * 18 * u} y={cy + R * 0.33 + 21 * u} textAnchor="middle" fill={line} fontFamily={fonts.mono} fontSize={18 * u} letterSpacing={18 * u * 0.3}>
              {typed(centerLabel, frame, 58, 40)}
            </text>
          </g>
        )}
      </Svg>
      <Vignette strength={0.55} />
    </AbsoluteFill>
  );
};

export const radialBlueprint = defineMotion<Props>({
  id: 'radial-blueprint',
  title: 'Radial blueprint plan',
  category: 'hud',
  description: 'Dark blueprint: a blue dot pings, the camera snaps back to a seeded circular library plan with a glowing hub, blue paths and flowing nodes, then spokes shoot out to category labels.',
  source: ['video19 11.05-15.40 (radial-plan-blueprint, radar-spoke-draw, radial-network-reveal, blue-dot-motif)'],
  useFor: 'Hero background for systems / knowledge / network stories; reveal 3-8 categories around a hub.',
  durationInFrames: 240,
  defaultProps: {
    background: BP.bg,
    categories: ['MODELS', 'AGENTS', 'CONTEXT', 'TOOLS', 'EVALS'],
    centerLabel: 'TODAY',
    seed: 7,
    rings: 4,
    sectors: 12,
    accentPaths: 3,
    networkSpokes: 8,
    pullFrom: 5,
    rotateSpeed: 3,
    accent: BP.blue,
    line: BP.line,
    labelColor: '#7FA2E6',
    scanlines: true,
  },
  propDocs: {
    categories: 'labels the blue spokes shoot out to (first fires alone, then in pairs)',
    centerLabel: 'small tracked label under the hub ("" to hide)',
    seed: 'procedural plan layout seed',
    rings: 'number of shelf rings',
    sectors: 'number of radial sectors',
    accentPaths: 'thick blue paths entering from outside',
    networkSpokes: 'thin blue spokes with flowing nodes',
    pullFrom: 'starting zoom of the pull-back reveal',
    rotateSpeed: 'plan rotation in degrees per second',
    accent: 'blue accent colour',
    line: 'line-art colour',
    labelColor: 'category label colour',
    scanlines: 'engraved scanline texture behind',
  },
  component: RadialBlueprint,
  tags: ['blueprint', 'radar', 'network', 'hub', 'categories', 'zoom-out'],
});
