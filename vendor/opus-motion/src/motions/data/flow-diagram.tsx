import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {clamp, ease, lerp, prog, springAt} from '../../core/ease';
import {fonts} from '../../core/fonts';
import {IconBox, clamp01, measureText} from '../../core/r2-pr1-kit';
import {Svg, useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * How-it-works diagram: boxes (with icons) joined by arrows that draw on in sequence; packets (glowing dots, or chips
 * carrying the edge label) travel along the edges, the receiving node pulses 1 -> 1.08 -> 1 and a highlight ring follows
 * the active step. Auto-lays out left -> right (top -> bottom on portrait) from the edge graph when nodes have no x/y.
 */

type N = {id: string; label: string; icon?: string; x?: number; y?: number};
type E = {from: string; to: string; label?: string};
type Step = {at: number; edge?: string | number; node?: string};
type Props = {
  nodes: N[];
  edges: E[];
  steps: Step[];
  direction: 'auto' | 'horizontal' | 'vertical';
  theme: 'blueprint' | 'paper' | 'dark';
  accent: string;
  packetColor: string;
  drawFrames: number;
  stagger: number;
  stepFrames: number;
  loop: boolean;
  title: string;
};

const THEMES = {
  blueprint: {bg: '#1E4F8E', line: '#EAF2FF', fill: 'rgba(255,255,255,0.09)', ink: '#F5F9FF', muted: 'rgba(234,242,255,0.55)', accent: '#FFC857', grid: 'rgba(255,255,255,0.08)', glow: 0.9},
  paper: {bg: '#F2ECE0', line: '#2A2A2E', fill: '#FFFFFF', ink: '#1F1F23', muted: 'rgba(31,31,35,0.5)', accent: '#E4572E', grid: 'rgba(60,50,30,0.1)', glow: 0.5},
  dark: {bg: '#0D1016', line: '#8892A8', fill: '#161A23', ink: '#EDF0F7', muted: 'rgba(237,240,247,0.5)', accent: '#4DE1C1', grid: 'rgba(255,255,255,0.05)', glow: 1},
};

type Pt = [number, number];
const bez = (p: Pt[], t: number): Pt => {
  const q = 1 - t;
  return [q * q * q * p[0][0] + 3 * q * q * t * p[1][0] + 3 * q * t * t * p[2][0] + t * t * t * p[3][0], q * q * q * p[0][1] + 3 * q * q * t * p[1][1] + 3 * q * t * t * p[2][1] + t * t * t * p[3][1]];
};

const FlowDiagram: React.FC<Props> = ({nodes, edges, steps, direction, theme, accent, packetColor, drawFrames, stagger, stepFrames, loop, title}) => {
  const frame = useCurrentFrame();
  const {w, h, u, fps, portrait} = useStage();
  const T = THEMES[theme] ?? THEMES.blueprint;
  const acc = accent || T.accent;
  const pk = packetColor || acc;
  const vertical = direction === 'vertical' || (direction === 'auto' && portrait);

  // ---- layers (longest path)
  const idx = new Map(nodes.map((n, i) => [n.id, i]));
  const validEdges = edges.filter((e) => idx.has(e.from) && idx.has(e.to));
  const layer = nodes.map(() => 0);
  for (let pass = 0; pass < nodes.length; pass++) for (const e of validEdges) layer[idx.get(e.to)!] = Math.max(layer[idx.get(e.to)!], Math.min(nodes.length - 1, layer[idx.get(e.from)!] + 1));
  const L = Math.max(...layer) + 1;
  const inLayer: number[][] = Array.from({length: L}, () => []);
  nodes.forEach((_, i) => inLayer[layer[i]].push(i));

  // ---- geometry
  const nh = 112 * u;
  const fs = 32 * u;
  const nodeW = nodes.map((n) => Math.min(w * 0.42, 104 * u + measureText(n.label, fonts.sans, fs, 600)));
  const mx = (vertical ? 0.14 : 0.045) * w;
  const topM = h * (title ? 0.2 : 0.14);
  const botM = h * 0.12;
  const cxy: Pt[] = nodes.map((n, i) => {
    if (n.x !== undefined && n.y !== undefined) return [(n.x / 100) * w, (n.y / 100) * h];
    const li = layer[i];
    const k = inLayer[li].indexOf(i);
    const cnt = inLayer[li].length;
    if (vertical) {
      const y = L === 1 ? h / 2 : lerp(topM + nh / 2, h - botM - nh / 2, li / (L - 1));
      const x = cnt === 1 ? w / 2 : lerp(w * 0.28, w * 0.72, k / (cnt - 1));
      return [x, y];
    }
    const x = L === 1 ? w / 2 : lerp(mx + 135 * u, w - mx - 135 * u, li / (L - 1));
    const y = cnt === 1 ? h * 0.52 : lerp(h * 0.3, h * 0.76, k / (cnt - 1));
    return [x, y];
  });

  type Geo = {pts: Pt[]; len: number; table: number[]};
  const geo: Geo[] = validEdges.map((e) => {
    const a = idx.get(e.from)!;
    const b = idx.get(e.to)!;
    const [ax, ay] = cxy[a];
    const [bx, by] = cxy[b];
    const dx = bx - ax;
    const dy = by - ay;
    const horiz = vertical ? Math.abs(dx) > Math.abs(dy) * 2.2 : Math.abs(dx) >= Math.abs(dy) * 0.5;
    let p0: Pt;
    let p3: Pt;
    let p1: Pt;
    let p2: Pt;
    if (horiz) {
      const s = dx >= 0 ? 1 : -1;
      p0 = [ax + (s * nodeW[a]) / 2, ay];
      p3 = [bx - (s * nodeW[b]) / 2, by];
      const d = Math.max(50 * u, Math.abs(p3[0] - p0[0]) * 0.5);
      p1 = [p0[0] + s * d, p0[1]];
      p2 = [p3[0] - s * d, p3[1]];
    } else {
      const s = dy >= 0 ? 1 : -1;
      p0 = [ax, ay + (s * nh) / 2];
      p3 = [bx, by - (s * nh) / 2];
      const d = Math.max(50 * u, Math.abs(p3[1] - p0[1]) * 0.5);
      p1 = [p0[0], p0[1] + s * d];
      p2 = [p3[0], p3[1] - s * d];
    }
    const pts = [p0, p1, p2, p3];
    const table = [0];
    let len = 0;
    let prev = pts[0];
    for (let i = 1; i <= 40; i++) {
      const q = bez(pts, i / 40);
      len += Math.hypot(q[0] - prev[0], q[1] - prev[1]);
      table.push(len);
      prev = q;
    }
    return {pts, len, table};
  });
  const atLen = (g: Geo, f: number): Pt => {
    const target = clamp01(f) * g.len;
    let i = 1;
    while (i < g.table.length - 1 && g.table[i] < target) i++;
    const seg = g.table[i] - g.table[i - 1] || 1;
    return bez(g.pts, (i - 1 + (target - g.table[i - 1]) / seg) / 40);
  };

  // ---- draw-on schedule: edges ordered by the layer of their source
  const order = validEdges.map((e, i) => i).sort((a, b) => layer[idx.get(validEdges[a].from)!] - layer[idx.get(validEdges[b].from)!] || a - b);
  const rank: number[] = [];
  order.forEach((ei, r) => (rank[ei] = r));
  const drawAt = (ei: number) => 12 + rank[ei] * stagger;
  const nodeAt = nodes.map(() => Infinity);
  validEdges.forEach((e, ei) => {
    const a = idx.get(e.from)!;
    const b = idx.get(e.to)!;
    nodeAt[a] = Math.min(nodeAt[a], drawAt(ei) - 8);
    nodeAt[b] = Math.min(nodeAt[b], drawAt(ei) + drawFrames * 0.7);
  });
  nodes.forEach((_, i) => {
    if (!isFinite(nodeAt[i])) nodeAt[i] = 4 + i * stagger;
  });
  const sources = nodes.map((_, i) => i).filter((i) => !validEdges.some((e) => idx.get(e.to) === i));
  sources.forEach((i) => (nodeAt[i] = Math.min(nodeAt[i], 2 + i * 2)));

  // ---- steps (packets)
  const startAll = 12 + Math.max(0, validEdges.length - 1) * stagger + drawFrames + 8;
  let evList: Step[] = steps;
  let period = 0;
  if (!evList.length) {
    // one group per source layer
    const layers = [...new Set(order.map((ei) => layer[idx.get(validEdges[ei].from)!]))].sort((a, b) => a - b);
    evList = [];
    layers.forEach((ly, g) => order.forEach((ei) => layer[idx.get(validEdges[ei].from)!] === ly && evList.push({at: startAll + g * stepFrames, edge: ei})));
    period = layers.length * stepFrames + 26;
  } else if (loop) {
    period = Math.max(...evList.map((s) => s.at)) - Math.min(...evList.map((s) => s.at)) + stepFrames + 26;
  }
  const edgeIndex = (s: Step) => (typeof s.edge === 'number' ? s.edge : s.edge ? validEdges.findIndex((e) => `${e.from}>${e.to}` === s.edge) : -1);
  const travel = Math.max(8, Math.round(stepFrames * 0.85));

  const firstAt = Math.min(...evList.map((s) => s.at), 1e9);
  const cyc = period > 0 && frame > firstAt ? Math.floor((frame - firstAt) / period) : 0;
  const packets: {ei: number; p: number; label?: string}[] = [];
  const arrivals: {node: number; t: number}[] = [];
  for (let k = Math.max(0, cyc - 1); k <= cyc; k++) {
    for (const s of evList) {
      const t0 = s.at + k * period;
      if (k > 0 && period === 0) continue;
      const ei = edgeIndex(s);
      if (ei >= 0 && geo[ei]) {
        if (frame >= t0 && frame <= t0 + travel) packets.push({ei, p: ease.inOut((frame - t0) / travel), label: validEdges[ei].label});
        if (frame >= t0 + travel) arrivals.push({node: idx.get(validEdges[ei].to)!, t: t0 + travel});
      } else if (s.node && idx.has(s.node) && frame >= t0) arrivals.push({node: idx.get(s.node)!, t: t0});
    }
  }
  const lastArrival = (ni: number) => arrivals.filter((a) => a.node === ni).reduce((m, a) => Math.max(m, a.t), -1);
  const newest = arrivals.reduce((m, a) => Math.max(m, a.t), -1);

  const gridStep = 54 * u;
  return (
    <AbsoluteFill style={{background: T.bg, overflow: 'hidden'}}>
      <Svg>
        <defs>
          <filter id="fd-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation={6 * u} />
          </filter>
        </defs>
        {theme === 'paper'
          ? Array.from({length: Math.ceil(w / gridStep)}).flatMap((_, i) => Array.from({length: Math.ceil(h / gridStep)}).map((__, j) => <circle key={`${i}-${j}`} cx={i * gridStep + gridStep / 2} cy={j * gridStep + gridStep / 2} r={1.6 * u} fill={T.grid} />))
          : [
              ...Array.from({length: Math.ceil(w / gridStep)}, (_, i) => <line key={`v${i}`} x1={i * gridStep} y1={0} x2={i * gridStep} y2={h} stroke={T.grid} strokeWidth={1.2 * u} />),
              ...Array.from({length: Math.ceil(h / gridStep)}, (_, j) => <line key={`h${j}`} x1={0} y1={j * gridStep} x2={w} y2={j * gridStep} stroke={T.grid} strokeWidth={1.2 * u} />),
            ]}
        {/* edges */}
        {geo.map((g, ei) => {
          const p = prog(frame, drawAt(ei), drawAt(ei) + drawFrames, ease.inOut);
          if (p <= 0) return null;
          const [p0, p1, p2, p3] = g.pts;
          const d = `M ${p0[0]} ${p0[1]} C ${p1[0]} ${p1[1]} ${p2[0]} ${p2[1]} ${p3[0]} ${p3[1]}`;
          const tip = bez(g.pts, 0.985);
          const ang = Math.atan2(p3[1] - tip[1], p3[0] - tip[0]);
          const ah = 15 * u;
          const lbl = bez(g.pts, 0.5);
          const hot = packets.some((pk2) => pk2.ei === ei);
          return (
            <g key={ei}>
              <path d={d} fill="none" stroke={hot ? acc : T.line} strokeOpacity={hot ? 1 : 0.85} strokeWidth={(hot ? 3.4 : 2.6) * u} strokeLinecap="round" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - p} />
              {p > 0.96 ? (
                <path d={`M ${p3[0]} ${p3[1]} L ${p3[0] - Math.cos(ang - 0.45) * ah} ${p3[1] - Math.sin(ang - 0.45) * ah} M ${p3[0]} ${p3[1]} L ${p3[0] - Math.cos(ang + 0.45) * ah} ${p3[1] - Math.sin(ang + 0.45) * ah}`} stroke={hot ? acc : T.line} strokeWidth={2.6 * u} strokeLinecap="round" fill="none" />
              ) : null}
              {validEdges[ei].label && p > 0.9 && !hot ? (
                <text x={lbl[0] + (Math.abs(p3[0] - p0[0]) < Math.abs(p3[1] - p0[1]) * 0.15 ? 18 * u : 0)} y={lbl[1] - (Math.abs(p3[0] - p0[0]) < Math.abs(p3[1] - p0[1]) * 0.15 ? -8 * u : 14 * u)} fill={T.muted} fontFamily={fonts.mono} fontSize={24 * u} textAnchor={Math.abs(p3[0] - p0[0]) < Math.abs(p3[1] - p0[1]) * 0.15 ? 'start' : 'middle'}>
                  {validEdges[ei].label}
                </text>
              ) : null}
            </g>
          );
        })}
        {/* packets */}
        {packets.map((pkt, i) => {
          const [x, y] = atLen(geo[pkt.ei], pkt.p);
          if (pkt.label) {
            const tw = measureText(pkt.label, fonts.mono, 23 * u, 700) + 32 * u;
            return (
              <g key={i} transform={`translate(${x} ${y})`}>
                <rect x={-tw / 2} y={-21 * u} width={tw} height={42 * u} rx={21 * u} fill={pk} />
                <text y={8 * u} textAnchor="middle" fontFamily={fonts.mono} fontWeight={700} fontSize={23 * u} fill={theme === 'paper' ? '#fff' : '#101218'}>
                  {pkt.label}
                </text>
              </g>
            );
          }
          return (
            <g key={i} transform={`translate(${x} ${y})`}>
              <circle r={17 * u} fill={pk} opacity={0.55 * T.glow} filter="url(#fd-glow)" />
              <circle r={9 * u} fill={pk} />
              <circle r={3.6 * u} fill="#fff" />
            </g>
          );
        })}
        {/* nodes */}
        {nodes.map((n, i) => {
          const s = springAt(frame, fps, nodeAt[i], 'pop');
          if (s <= 0.001) return null;
          const [x, y] = cxy[i];
          const la = lastArrival(i);
          const age = la >= 0 ? frame - la : 99;
          const pulse = age >= 0 && age < 12 ? 1 + 0.08 * Math.sin((age / 12) * Math.PI) : 1;
          const active = la >= 0 && la === newest && age < Math.max(stepFrames, 24);
          const sc = clamp(s, 0, 1.15) * pulse;
          const nw = nodeW[i];
          return (
            <g key={n.id} transform={`translate(${x} ${y}) scale(${sc})`} opacity={clamp01(s * 1.5)}>
              {active ? <rect x={-nw / 2 - 8 * u} y={-nh / 2 - 8 * u} width={nw + 16 * u} height={nh + 16 * u} rx={26 * u} fill="none" stroke={acc} strokeWidth={3 * u} opacity={0.85} /> : null}
              <rect x={-nw / 2} y={-nh / 2} width={nw} height={nh} rx={20 * u} fill={T.fill} stroke={active ? acc : T.line} strokeWidth={2.4 * u} />
              <g transform={`translate(${-nw / 2 + 24 * u} ${-23 * u})`}>
                <IconBox name={n.icon ?? 'spark'} size={46 * u} color={active ? acc : T.ink} sw={1.9} />
              </g>
              <text x={-nw / 2 + 88 * u} y={fs * 0.35} fill={T.ink} fontFamily={fonts.sans} fontWeight={600} fontSize={fs}>
                {n.label}
              </text>
            </g>
          );
        })}
      </Svg>
      {title ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: h * 0.07, textAlign: 'center', fontFamily: fonts.sans, fontWeight: 800, fontSize: 44 * u, letterSpacing: '-0.02em', color: T.ink, opacity: prog(frame, 0, 14)}}>{title}</div>
      ) : null}
    </AbsoluteFill>
  );
};

export const flowDiagram = defineMotion<Props>({
  id: 'flow-diagram',
  title: 'Flow diagram (packets on edges)',
  category: 'data',
  description:
    'Rounded boxes with icons joined by arrows that draw on in sequence (14 f each, 5 f stagger); glowing packets or labelled chips travel the edges, each receiving node pulses 1 -> 1.08 -> 1 and a highlight ring follows the active step. Auto-lays out left-to-right (top-to-bottom on portrait) from the edge graph; blueprint / paper / dark themes.',
  source: ['prompt-corpus: flow-diagram (31 cases)', 'awesome-opus5-5-videos prompts (MIT) — technique only'],
  useFor: 'How-it-works explainers (APIs, AI agents, networks, payments), onboarding and architecture videos: pass `nodes` + `edges`; optionally `steps` to script which edge fires when.',
  durationInFrames: 270,
  defaultProps: {
    nodes: [
      {id: 'app', label: 'Your app', icon: 'user'},
      {id: 'gw', label: 'Gateway', icon: 'shield'},
      {id: 'auth', label: 'Auth', icon: 'lock'},
      {id: 'queue', label: 'Queue', icon: 'queue'},
      {id: 'worker', label: 'Worker', icon: 'cog'},
      {id: 'store', label: 'Storage', icon: 'db'},
    ],
    edges: [
      {from: 'app', to: 'gw', label: 'request'},
      {from: 'gw', to: 'auth', label: 'token'},
      {from: 'gw', to: 'queue', label: 'job'},
      {from: 'queue', to: 'worker'},
      {from: 'worker', to: 'store', label: 'result'},
    ],
    steps: [],
    direction: 'auto',
    theme: 'blueprint',
    accent: '',
    packetColor: '',
    drawFrames: 14,
    stagger: 5,
    stepFrames: 28,
    loop: true,
    title: '',
  },
  propDocs: {
    nodes: '[{id, label, icon?: bolt|shield|chart|chat|globe|spark|lock|cog|user|db|cloud|star|queue|server|mail, x?, y? in % of frame}] (3-7 nodes)',
    edges: '[{from, to, label?}] — a label turns the packet into a chip',
    steps: "[{at: frame, edge?: 'a>b' | index, node?: id}] — empty = auto: packets fire layer by layer and loop",
    direction: "'auto' (vertical on portrait) | 'horizontal' | 'vertical'",
    theme: "'blueprint' | 'paper' | 'dark'",
    accent: 'highlight colour (empty = theme default)',
    packetColor: 'packet colour (empty = accent)',
    drawFrames: 'frames to draw one edge',
    stagger: 'frames between edge starts',
    stepFrames: 'frames per step / packet travel',
    loop: 'repeat the steps',
    title: 'optional heading',
  },
  component: FlowDiagram,
  tags: ['diagram', 'flow', 'flowchart', 'architecture', 'pipeline', 'api', 'workflow', 'nodes', 'edges', 'arrows', 'packets', 'how it works', 'explainer', 'agents', 'network', 'payments', 'blueprint'],
});
