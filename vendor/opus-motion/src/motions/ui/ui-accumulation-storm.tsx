// Adapted from lemo-opuscar/styles/dark-keynote/demo/{engine.js,world.js} (UI kit, generator) (MIT, © LemoLab) — see THIRD_PARTY_NOTICES.md
import React, {useMemo} from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Svg, useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';
import {KAppIcon, KBadge, KEY, KFile, KItem, KNotif, KPhoto, KeynoteStage, backOut, eo, ei, keynoteWorld, la2Fonts, rgba, seg} from '../../core/r2-la2-kit';

/**
 * ui-accumulation-storm — the "problem" act of a SaaS film: notification cards, file icons, photo tiles, app icons
 * and red badges spawn faster and faster (drop+bounce, fling, slide-in, pop), piling up with depth and parallax
 * over a quiet note until the screen is overwhelmed; a red unread counter races; everything trembles; optional freeze.
 */
type Props = {
  count: number;
  seed: number;
  accel: number;
  spawnEnd: number;
  freezeAt: number;
  note: string;
  accent: string;
  counterLabel: string;
  tremble: number;
  pullBack: number;
  noteTitle: string;
};

const UiAccumulationStorm: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const {w, h, u, fps, portrait} = useStage();
  const tRaw = frame / fps;
  const frozen = p.freezeAt > 0 && tRaw >= p.freezeAt;
  const t = frozen ? p.freezeAt : tRaw;
  const items = useMemo(() => {
    const it = keynoteWorld(p.seed, p.count, w, h, p.spawnEnd, p.accel);
    return it.map((x) => ({...x, t: x.t + 0.35})).sort((a, b) => a.z - b.z);
  }, [p.seed, p.count, w, h, p.spawnEnd, p.accel]);
  // camera: slow log pull-back + drift; nearer layers move more (2.5D parallax)
  const zoom = Math.exp(Math.log(1 + p.pullBack) * (1 - eo(seg(t, 0, p.spawnEnd + 1))));
  const driftX = Math.sin(t * 0.35) * 22 * u;
  const driftY = Math.cos(t * 0.27) * 14 * u;
  const stress = seg(t, p.spawnEnd * 0.45, p.spawnEnd);
  const spawned = items.filter((x) => x.t <= t).length;
  const noteW = Math.min(620 * u, w * 0.8);
  const noteH = 230 * u;
  const caretOn = Math.floor(tRaw * 2) % 2 === 0;
  const pose = (x: KItem) => {
    const d = (t - x.t) / 0.26;
    const k = Math.max(0, Math.min(1, d));
    const zs = x.z;
    let px = x.x;
    let py = x.y;
    let sc = 1;
    let rot = x.rot;
    let op = 1;
    if (x.spawn === 'drop') {
      py = x.y - (1 - backOut(k, 1.6)) * 260 * u;
      op = Math.min(1, k * 3);
    } else if (x.spawn === 'fling') {
      px = x.x + x.from * (1 - eo(k)) * w * 0.6;
      py = x.y - Math.sin(Math.PI * k) * 60 * u;
      rot = x.rot + x.from * (1 - eo(k)) * 160;
    } else if (x.spawn === 'slide') {
      px = x.x + (1 - backOut(k, 1.3)) * w * 0.35;
      op = Math.min(1, k * 2);
    } else {
      sc = backOut(k, 2.2);
    }
    // tremble grows with the pile
    const tr = p.tremble * stress * u * (0.5 + x.z * 0.5);
    px += Math.sin(frame * 1.9 + x.i * 2.1) * tr * (frozen ? 0 : 1);
    py += Math.cos(frame * 2.3 + x.i * 1.3) * tr * (frozen ? 0 : 1);
    // parallax about centre
    const cx = w / 2 + (px - w / 2) * zoom * (0.7 + 0.3 * zs) + driftX * zs;
    const cy = h / 2 + (py - h / 2) * zoom * (0.7 + 0.3 * zs) + driftY * zs;
    return {cx, cy, sc: sc * zs * zoom * (portrait ? 1.15 : 1), rot, op: op * (0.55 + 0.45 * Math.min(1, zs))};
  };
  return (
    <AbsoluteFill style={{background: KEY.bg0}}>
      <Svg>
        <KeynoteStage id="uas-st" w={w} h={h} u={u} scale={zoom} />
        {/* the quiet note being buried */}
        <g transform={`translate(${w / 2 + driftX * 0.8} ${h / 2 + driftY * 0.8}) scale(${zoom})`} opacity={1 - stress * 0.4}>
          <rect x={-noteW / 2} y={-noteH / 2 + 10 * u} width={noteW} height={noteH} rx={18 * u} fill="rgba(0,0,0,.45)" />
          <rect x={-noteW / 2} y={-noteH / 2} width={noteW} height={noteH} rx={18 * u} fill={KEY.surf} stroke="rgba(255,255,255,.08)" />
          <rect x={-noteW / 2} y={-noteH / 2} width={noteW} height={40 * u} rx={18 * u} fill={KEY.surf2} />
          <text x={-noteW / 2 + 22 * u} y={-noteH / 2 + 26 * u} fontFamily={la2Fonts.monoHeavy} fontSize={13 * u} fill={KEY.mute} letterSpacing={2 * u}>
            {p.noteTitle}
          </text>
          <text x={-noteW / 2 + 36 * u} y={16 * u} fontFamily={la2Fonts.inter} fontWeight={500} fontSize={34 * u} fill={KEY.text}>
            {p.note}
          </text>
          {caretOn && <rect x={-noteW / 2 + 36 * u + p.note.length * 34 * u * 0.53 + 6 * u} y={-16 * u} width={4 * u} height={42 * u} rx={2 * u} fill={p.accent} />}
        </g>
        {items.map((x) => {
          if (x.t > t) return null;
          const q = pose(x);
          const tf = `translate(${q.cx} ${q.cy}) rotate(${q.rot}) scale(${q.sc})`;
          let el: React.ReactNode = null;
          if (x.kind === 'file') el = <KFile x={0} y={0} s={1.25 * u} ext={x.ext} tint={x.tint} name={x.name} font={la2Fonts.inter} mono={la2Fonts.monoHeavy} id={`uas-f${x.i}`} />;
          else if (x.kind === 'photo') el = <KPhoto x={-70 * u} y={-50 * u} w={140 * u} h={100 * u} seed={x.seed} id={`uas-p${x.i}`} />;
          else if (x.kind === 'notif') el = <KNotif x={-170 * u} y={-38 * u} w={340 * u} h={76 * u} app={x.app} title={x.title} body={x.body} badge={x.i % 3 === 0 ? String(2 + (x.i % 9)) : undefined} font={la2Fonts.inter} />;
          else if (x.kind === 'app') el = <KAppIcon x={0} y={0} s={58 * u} k={x.app} />;
          else el = <KBadge x={0} y={0} text={String(1 + (x.seed % 24))} s={1.4 * u} font={la2Fonts.inter} />;
          return (
            <g key={x.i} transform={tf} opacity={q.op}>
              {el}
            </g>
          );
        })}
        {/* unread counter, problem red */}
        <g transform={`translate(${w - (portrait ? 150 : 190) * u} ${70 * u})`} opacity={seg(tRaw, 0.6, 1.2)}>
          <rect x={-120 * u} y={-34 * u} width={240 * u} height={68 * u} rx={34 * u} fill="rgba(12,14,19,.82)" stroke="rgba(255,255,255,.1)" />
          <circle cx={-88 * u} cy={0} r={9 * u} fill={KEY.red} opacity={0.6 + 0.4 * Math.abs(Math.sin(tRaw * 6))} />
          <text x={-68 * u} y={10 * u} fontFamily={la2Fonts.tight} fontWeight={600} fontSize={30 * u} fill={KEY.text}>
            {spawned * 3 > 999 ? '999+' : String(spawned * 3)}
          </text>
          <text x={100 * u} y={7 * u} textAnchor="end" fontFamily={la2Fonts.monoHeavy} fontSize={12 * u} letterSpacing={2 * u} fill={KEY.dim}>
            {p.counterLabel}
          </text>
        </g>
        {/* overwhelm: the light dims at the very end */}
        <rect width={w} height={h} fill="#000" opacity={0.25 * ei(seg(tRaw, p.spawnEnd + 0.4, p.spawnEnd + 1.4))} />
        <rect width={w} height={h} fill={rgba(KEY.red, 0.05 * stress)} style={{mixBlendMode: 'screen'}} />
      </Svg>
    </AbsoluteFill>
  );
};

export const uiAccumulationStorm = defineMotion<Props>({
  id: 'ui-accumulation-storm',
  title: 'UI accumulation storm',
  category: 'ui',
  description:
    'Dark keynote stage: notification cards, file icons, landscape photo tiles, app icons and red badges spawn faster and faster (drop+bounce, fling, slide-in, pop) with 2.5D depth and parallax, burying a quiet note with a lime caret; a red unread counter races, the pile trembles, light dims — the "too much" problem act.',
  source: ['lemo-opuscar styles/dark-keynote (MIT, LemoLab) — demo/world.js generator, demo/engine.js UI kit (notif, fileIcon, photo, appIcon, badge)'],
  useFor: 'The problem act of SaaS ads and explainers (inbox overload, file chaos, notification fatigue); pair with snap-grid-collapse as cause → effect.',
  durationInFrames: 210,
  defaultProps: {
    count: 200,
    seed: 4,
    accel: 0.5,
    spawnEnd: 5.6,
    freezeAt: 0,
    note: 'One thing at a time',
    accent: KEY.accent,
    counterLabel: 'UNREAD',
    tremble: 3,
    pullBack: 0.35,
    noteTitle: 'NOTE.TXT',
  },
  propDocs: {
    count: 'number of UI elements spawned',
    seed: 'layout seed',
    accel: 'spawn acceleration exponent (<1 = faster and faster)',
    spawnEnd: 'second the last element lands',
    freezeAt: 'second to freeze everything mid-air (0 = never)',
    note: 'text in the quiet note that gets buried',
    accent: 'brand accent (caret)',
    counterLabel: 'label of the red counter pill',
    tremble: 'tension tremble in px@1080 at full pile',
    pullBack: 'extra zoom at the start, pulled back over the act',
    noteTitle: 'title of the note card',
  },
  component: UiAccumulationStorm,
  tags: ['ui', 'notifications', 'chaos', 'overload', 'files', 'photos', 'badges', 'saas', 'keynote', 'dark', 'problem', 'storm', 'clutter', 'inbox', 'productivity', 'parallax'],
});
