import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {clamp, ease, prog} from '../../core/ease';
import {n2, rng} from '../../core/random';
import {Header, Legend, clip, itemColor, resolveFont, useChartBox} from '../../core/r3-chart-kit';
import {Svg, useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

type GNode = {id: string; label?: string; size?: number; group?: string; color?: string};
type GEdge = {from: string; to: string; weight?: number};
type Props = {
  nodes: GNode[];
  edges: GEdge[];
  seed: number;
  title: string;
  subtitle: string;
  showLabels: boolean;
  hub: string;
  hubPulse: boolean;
  minRadius: number;
  maxRadius: number;
  edgeOpacity: number;
  drift: number;
  colors: string[];
  background: string;
  ink: string;
  accent: string;
  fontFamily: string;
  startAt: number;
  speed: number;
};

const DEFAULT_NODES: GNode[] = [
  {id: 'Core', group: 'Platform'},
  {id: 'API', group: 'Platform'},
  {id: 'Auth', group: 'Platform'},
  {id: 'Queue', group: 'Platform'},
  {id: 'Web', group: 'Clients'},
  {id: 'iOS', group: 'Clients'},
  {id: 'Android', group: 'Clients'},
  {id: 'CLI', group: 'Clients'},
  {id: 'Billing', group: 'Services'},
  {id: 'Search', group: 'Services'},
  {id: 'Email', group: 'Services'},
  {id: 'Reports', group: 'Services'},
  {id: 'Cache', group: 'Data'},
  {id: 'Store', group: 'Data'},
  {id: 'Lake', group: 'Data'},
];
const DEFAULT_EDGES: GEdge[] = [
  {from: 'Core', to: 'API'},
  {from: 'Core', to: 'Auth'},
  {from: 'Core', to: 'Queue'},
  {from: 'Core', to: 'Cache'},
  {from: 'Core', to: 'Store'},
  {from: 'API', to: 'Web'},
  {from: 'API', to: 'iOS'},
  {from: 'API', to: 'Android'},
  {from: 'API', to: 'CLI'},
  {from: 'Auth', to: 'Web'},
  {from: 'Queue', to: 'Billing'},
  {from: 'Queue', to: 'Email'},
  {from: 'Queue', to: 'Reports'},
  {from: 'API', to: 'Search'},
  {from: 'Store', to: 'Lake'},
  {from: 'Reports', to: 'Lake'},
  {from: 'Search', to: 'Store'},
  {from: 'Billing', to: 'Email'},
];

type Pos = {x: number; y: number};

/** deterministic Fruchterman-Reingold relaxation in a [0,aspect] x [0,1] box, seeded start */
const relax = (n: number, edges: [number, number, number][], seed: number, aspect: number): Pos[] => {
  const r = rng(seed * 7919 + 13);
  const pos: Pos[] = Array.from({length: n}, () => ({x: r() * aspect, y: r()}));
  if (n <= 1) return pos.map(() => ({x: aspect / 2, y: 0.5}));
  const k = Math.sqrt((aspect * 1) / n) * 0.85;
  const iters = 320;
  for (let it = 0; it < iters; it++) {
    const temp = 0.12 * (1 - it / iters) + 0.002;
    const dx = new Array(n).fill(0);
    const dy = new Array(n).fill(0);
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        let ex = pos[i].x - pos[j].x;
        let ey = pos[i].y - pos[j].y;
        let d = Math.hypot(ex, ey);
        if (d < 1e-4) {
          ex = (r() - 0.5) * 1e-3;
          ey = (r() - 0.5) * 1e-3;
          d = Math.hypot(ex, ey);
        }
        const f = (k * k) / d;
        dx[i] += (ex / d) * f;
        dy[i] += (ey / d) * f;
        dx[j] -= (ex / d) * f;
        dy[j] -= (ey / d) * f;
      }
    }
    edges.forEach(([a, b, w]) => {
      const ex = pos[a].x - pos[b].x;
      const ey = pos[a].y - pos[b].y;
      const d = Math.max(1e-4, Math.hypot(ex, ey));
      const f = ((d * d) / k) * (0.6 + 0.4 * w);
      dx[a] -= (ex / d) * f;
      dy[a] -= (ey / d) * f;
      dx[b] += (ex / d) * f;
      dy[b] += (ey / d) * f;
    });
    for (let i = 0; i < n; i++) {
      // weak pull to the centre keeps disconnected parts together
      dx[i] += (aspect / 2 - pos[i].x) * 0.35;
      dy[i] += (0.5 - pos[i].y) * 0.35;
      const d = Math.max(1e-6, Math.hypot(dx[i], dy[i]));
      const m = Math.min(d, temp);
      pos[i].x += (dx[i] / d) * m;
      pos[i].y += (dy[i] / d) * m;
    }
  }
  return pos;
};

const NetworkGraph: React.FC<Props> = ({nodes, edges, seed, title, subtitle, showLabels, hub, hubPulse, minRadius, maxRadius, edgeOpacity, drift, colors, background, ink, accent, fontFamily, startAt, speed}) => {
  const frame = useCurrentFrame();
  const {u, portrait} = useStage();
  const box = useChartBox(title, subtitle);
  const font = resolveFont(fontFamily);

  const graph = React.useMemo(() => {
    const ids: string[] = [];
    const meta = new Map<string, GNode>();
    (nodes || []).forEach((nd) => {
      if (nd && nd.id !== undefined && !meta.has(String(nd.id))) {
        meta.set(String(nd.id), {...nd, id: String(nd.id)});
        ids.push(String(nd.id));
      }
    });
    const es: [number, number, number][] = [];
    (edges || []).forEach((e) => {
      if (!e) return;
      const a = String(e.from);
      const b = String(e.to);
      if (a === b) return;
      [a, b].forEach((id) => {
        if (!meta.has(id)) {
          meta.set(id, {id});
          ids.push(id);
        }
      });
      es.push([ids.indexOf(a), ids.indexOf(b), clamp(e.weight === undefined ? 1 : e.weight / 1, 0.1, 10)]);
    });
    const deg = new Array(ids.length).fill(0);
    es.forEach(([a, b]) => {
      deg[a]++;
      deg[b]++;
    });
    return {ids, meta, es, deg};
  }, [JSON.stringify(nodes), JSON.stringify(edges)]);

  const {ids, meta, es, deg} = graph;
  const n = ids.length;
  const groups: string[] = [];
  ids.forEach((id) => {
    const g = meta.get(id)!.group;
    if (g && !groups.includes(g)) groups.push(g);
  });
  const showLegend = groups.length > 1;
  const legSize = (portrait ? 28 : 24) * u;
  const legH = showLegend ? legSize * 2.1 * (portrait ? 2 : 1) : 0;

  // layout area
  const labSize = (portrait ? 26 : 22) * u;
  const padX = 70 * u;
  const padTop = 34 * u;
  const padBot = (showLabels ? 48 : 30) * u;
  const ax0 = box.x + padX;
  const ax1 = box.x + box.w - padX;
  const ay0 = box.y + padTop;
  const ay1 = box.y + box.h - legH - padBot - (showLegend ? 20 * u : 0);
  const aspect = Math.max(0.3, Math.min(4, (ax1 - ax0) / Math.max(1, ay1 - ay0)));

  const pts = React.useMemo(() => {
    const p = relax(n, es, seed, aspect);
    let x0 = Infinity,
      x1 = -Infinity,
      y0 = Infinity,
      y1 = -Infinity;
    p.forEach((q) => {
      x0 = Math.min(x0, q.x);
      x1 = Math.max(x1, q.x);
      y0 = Math.min(y0, q.y);
      y1 = Math.max(y1, q.y);
    });
    // few nodes: keep the layout compact instead of stretching it over the whole frame
    const f = clamp(Math.sqrt(Math.max(1, p.length)) / 4, 0.5, 1);
    return p.map((q) => ({x: 0.5 + ((q.x - x0) / Math.max(1e-6, x1 - x0) - 0.5) * f, y: 0.5 + ((q.y - y0) / Math.max(1e-6, y1 - y0) - 0.5) * f}));
  }, [n, JSON.stringify(es), seed, Math.round(aspect * 20)]);

  const hubIdx = hub && ids.includes(hub) ? ids.indexOf(hub) : deg.length ? deg.indexOf(Math.max(...deg)) : -1;

  // reveal order: breadth-first from the hub
  const rank = React.useMemo(() => {
    const out = new Array(n).fill(-1);
    if (hubIdx < 0) return out;
    const adj: number[][] = Array.from({length: n}, () => []);
    es.forEach(([a, b]) => {
      adj[a].push(b);
      adj[b].push(a);
    });
    const q = [hubIdx];
    out[hubIdx] = 0;
    let c = 1;
    for (let h = 0; h < q.length; h++) {
      adj[q[h]].forEach((m) => {
        if (out[m] < 0) {
          out[m] = c++;
          q.push(m);
        }
      });
    }
    for (let i = 0; i < n; i++) if (out[i] < 0) out[i] = c++;
    return out;
  }, [n, JSON.stringify(es), hubIdx]);

  const stagger = clamp(80 / Math.max(1, n), 2.5, 8) / speed;
  const nodeAt = (i: number) => startAt + rank[i] * stagger;
  const edgeAt = (a: number, b: number) => Math.max(nodeAt(a), nodeAt(b)) + 5 / speed;
  const allIn = startAt + n * stagger + 30 / speed;

  const sizes = ids.map((id, i) => {
    const s = meta.get(id)!.size;
    return s !== undefined && s > 0 ? s : Math.max(1, deg[i]);
  });
  const maxS = Math.max(...sizes, 1);
  const rOf = (i: number) => (minRadius + (maxRadius - minRadius) * Math.sqrt(sizes[i] / maxS)) * u;

  const posAt = (i: number) => {
    const bx = ax0 + pts[i].x * (ax1 - ax0);
    const by = ay0 + pts[i].y * (ay1 - ay0);
    const dr = drift * u;
    const ph = frame * 0.01;
    return {x: bx + n2('ngx' + seed, i * 1.7, ph) * dr, y: by + n2('ngy' + seed, i * 1.7, ph) * dr};
  };
  const colorOf = (id: string, i: number) => {
    const m = meta.get(id)!;
    return m.color || (m.group ? itemColor(undefined, colors, groups.indexOf(m.group)) : itemColor(undefined, colors, i));
  };
  const bgSolid = background && background !== 'transparent' ? background : 'none';

  const P = ids.map((_, i) => posAt(i));
  const pulseOn = hubPulse && hubIdx >= 0;
  const cyc = 54;

  return (
    <AbsoluteFill style={{background}}>
      <Svg>
        <Header box={box} ink={ink} fontFamily={font} frame={frame} />

        {/* edges */}
        {es.map(([a, b, w], k) => {
          const t = prog(frame, edgeAt(a, b), edgeAt(a, b) + 20 / speed, ease.inOut);
          if (t <= 0) return null;
          const isHub = a === hubIdx || b === hubIdx;
          const pa = P[a];
          const pb = P[b];
          // draw from the earlier node outwards
          const [s, e] = nodeAt(a) <= nodeAt(b) ? [pa, pb] : [pb, pa];
          return (
            <line
              key={k}
              x1={s.x}
              y1={s.y}
              x2={s.x + (e.x - s.x) * t}
              y2={s.y + (e.y - s.y) * t}
              stroke={isHub ? accent : ink}
              strokeOpacity={isHub ? Math.min(1, edgeOpacity + 0.25) : edgeOpacity}
              strokeWidth={(1.6 + 1.6 * clamp(w / 3)) * u * (isHub ? 1.25 : 1)}
              strokeLinecap="round"
            />
          );
        })}

        {/* hub pulse rings */}
        {pulseOn &&
          [0, 1, 2].map((k) => {
            const local = (frame - nodeAt(hubIdx) - 18 - k * (cyc / 3) * 1) / cyc;
            if (local < 0) return null;
            const ph = local - Math.floor(local);
            const rr = rOf(hubIdx) * (1 + ph * 3.4);
            return <circle key={'p' + k} cx={P[hubIdx].x} cy={P[hubIdx].y} r={rr} fill="none" stroke={accent} strokeWidth={3 * u} strokeOpacity={(1 - ph) * 0.65 * prog(frame, nodeAt(hubIdx) + 10, nodeAt(hubIdx) + 30)} />;
          })}

        {/* nodes */}
        {ids.map((id, i) => {
          const t = prog(frame, nodeAt(i), nodeAt(i) + 18 / speed, ease.back);
          if (t <= 0) return null;
          const col = colorOf(id, i);
          const isHub = i === hubIdx;
          const beat = isHub && pulseOn && frame > allIn - 20 ? 1 + 0.06 * Math.sin((frame / cyc) * Math.PI * 2) : 1;
          const r = rOf(i) * t * beat;
          const m = meta.get(id)!;
          const lbl = clip(m.label || m.id, 190 * u, labSize);
          return (
            <g key={id}>
              {isHub && <circle cx={P[i].x} cy={P[i].y} r={r + 7 * u} fill={col} fillOpacity={0.2} />}
              <circle cx={P[i].x} cy={P[i].y} r={r} fill={col} stroke={bgSolid === 'none' ? ink : bgSolid} strokeOpacity={bgSolid === 'none' ? 0.2 : 1} strokeWidth={3 * u} />
              {showLabels && (
                <text
                  x={P[i].x}
                  y={P[i].y + r + labSize * 1.05}
                  textAnchor="middle"
                  fontFamily={font}
                  fontWeight={isHub ? 800 : 600}
                  fontSize={labSize * (isHub ? 1.12 : 1)}
                  fill={ink}
                  stroke={bgSolid}
                  strokeWidth={5 * u}
                  strokeLinejoin="round"
                  paintOrder="stroke"
                  opacity={clamp(t * 1.3 - 0.3)}
                >
                  {lbl}
                </text>
              )}
            </g>
          );
        })}

        {showLegend && (
          <Legend
            items={groups.map((g, i) => ({label: g, color: itemColor(undefined, colors, i)}))}
            x={box.x}
            y={box.y + box.h - legH}
            w={box.w}
            cols={portrait ? 2 : Math.min(groups.length, 6)}
            rowH={legSize * 2}
            size={legSize}
            ink={ink}
            fontFamily={font}
            frame={frame}
            start={allIn - 20}
            stagger={4}
            shape="dot"
            align="center"
          />
        )}
      </Svg>
    </AbsoluteFill>
  );
};

export const networkGraph = defineMotion<Props>({
  id: 'network-graph',
  title: 'Network graph (your nodes and edges)',
  category: 'data',
  description:
    'A labelled node-link diagram built from your own nodes and edges: a seeded force layout (computed once, fully deterministic) is revealed outward from the hub, nodes pop in coloured by group and sized by importance, edges draw between them, and the hub pulses with expanding rings; nodes drift slightly after.',
  source: ['original round-3 chart motion'],
  useFor:
    'Explicit relationship maps: system architecture, supply chains, org or contact networks, dependency graphs, knowledge graphs, social graphs with named members. Pass nodes [{id, label?, group?, size?}] and edges [{from, to, weight?}]; for a random generated growth effect use node-network instead.',
  durationInFrames: 210,
  defaultProps: {
    nodes: DEFAULT_NODES,
    edges: DEFAULT_EDGES,
    seed: 3,
    title: 'How the pieces connect',
    subtitle: 'Services, clients and data stores around one core',
    showLabels: true,
    hub: 'Core',
    hubPulse: true,
    minRadius: 14,
    maxRadius: 40,
    edgeOpacity: 0.32,
    drift: 5,
    colors: ['#2F6FED', '#FF7A45', '#16B39A', '#F2B134', '#8E5CF0', '#E5487F', '#5BC0EB', '#7A8794'],
    background: '#F5F3EE',
    ink: '#18212B',
    accent: '#FF7A45',
    fontFamily: '',
    startAt: 10,
    speed: 1,
  },
  propDocs: {
    nodes: 'nodes [{id, label?, group?, size?, color?}]; group sets the colour and legend; size (default = number of links) sets the radius; nodes missing here are created from the edges',
    edges: 'links [{from, to, weight?}] using node ids; weight 0.1-10 thickens and shortens the link',
    seed: 'layout seed: change it to get a different arrangement of the same graph',
    title: 'headline (empty = none)',
    subtitle: 'small line under the headline (empty = none)',
    showLabels: 'print node names under the nodes',
    hub: 'id of the node that reveals first and pulses (empty = the most connected node)',
    hubPulse: 'expanding rings around the hub',
    minRadius: 'smallest node radius in u',
    maxRadius: 'largest node radius in u',
    edgeOpacity: 'link opacity 0-1',
    drift: 'gentle post-layout drift in u (0 = still)',
    colors: 'palette for groups / nodes without their own colour',
    background: 'page colour, or "transparent" to sit over other content',
    ink: 'text and link colour',
    accent: 'colour of the hub links and pulse',
    fontFamily: 'CSS font family (empty = Space Grotesk)',
    startAt: 'frame the hub appears',
    speed: 'animation speed multiplier',
  },
  component: NetworkGraph,
  tags: ['network', 'graph', 'nodes', 'edges', 'links', 'diagram', 'relationships', 'architecture', 'dependency', 'knowledge graph', 'force layout', 'hub', 'infographic', 'data', 'overlay'],
});
