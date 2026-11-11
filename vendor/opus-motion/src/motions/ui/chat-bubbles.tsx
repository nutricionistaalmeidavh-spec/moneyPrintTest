import React from 'react';
import {AbsoluteFill, spring, useCurrentFrame} from 'remotion';
import {clamp, ease, lerp, prog} from '../../core/ease';
import {BoxBot} from '../../core/character-kit';
import {estWidth, tfonts} from '../../core/text-kit';
import {useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';
import {FlatIcon, blinkOn, inBack, lin, outBack, typedCount} from '../../core/ui-kit';

/**
 * video12 conversation beats around the orange box-bot in a synthwave "cyberspace":
 *  chat-bubble-pop (dark user bubble grows 0.3 -> 1 in place; the orange reply flies out of the bot, 4 f, overshoot),
 *  comment-chip-stagger (white ink-bordered comment chips and translucent orange prompt chips pop 0.9 -> 1 one by
 *  one around the subject, prompt chips drift upward), speech-balloon-pop (white oval with a 3 px ink stroke and a
 *  tapered tail snaps on in one frame), thought-bubble-sequence (three glossy lavender dots rise from the head, a
 *  pale cloud pill fades/grows 0.9 -> 1, icons pop in left to right separated by bullets, a caption types, the
 *  bubble drifts up) and finally a green verdict chip drops in from above.
 */
type Msg = {text: string; kind: 'user' | 'reply' | 'chip' | 'comment' | 'speech'; at?: number};
type Props = {
  messages: Msg[];
  stagger: number;
  thoughtIcons: string[];
  thoughtCaption: string;
  verdict: string;
  verdictColor: string;
  showBot: boolean;
  background: string;
};

const SLOTS = {
  landscape: {
    user: [[0.72, 0.18]],
    reply: [[0.3, 0.27]],
    chip: [
      [0.16, 0.5],
      [0.84, 0.46],
      [0.19, 0.7],
      [0.83, 0.68],
    ],
    comment: [
      [0.52, 0.09],
      [0.66, 0.36],
      [0.34, 0.42],
    ],
    speech: [[0.36, 0.56]],
  },
  portrait: {
    user: [[0.66, 0.13]],
    reply: [[0.38, 0.21]],
    chip: [
      [0.3, 0.42],
      [0.7, 0.48],
      [0.28, 0.54],
      [0.72, 0.36],
    ],
    comment: [
      [0.5, 0.06],
      [0.62, 0.3],
      [0.34, 0.3],
    ],
    speech: [[0.4, 0.62]],
  },
} as const;

const ChatBubbles: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const {w, h, u, cx, fps, portrait} = useStage();
  const k = portrait ? 1.25 : 1.15;
  const slots = portrait ? SLOTS.portrait : SLOTS.landscape;
  const botX = cx;
  const botY = portrait ? h * 0.86 : h * 0.9;
  const botS = (portrait ? 300 : 230) * u;
  const headY = botY - botS * 1.1;
  const horizon = portrait ? h * 0.7 : h * 0.66;

  // timeline
  const msgs = p.messages.map((m, i) => ({...m, at: m.at ?? 8 + i * p.stagger}));
  const lastAt = Math.max(...msgs.map((m) => m.at), 0);
  const clearAt = lastAt + 22;
  const T0 = clearAt + 14; // thought start
  const iconsAt = T0 + 18;
  const capAt = iconsAt + p.thoughtIcons.length * 6 + 6;
  const driftAt = capAt + 22;
  const verdictAt = driftAt + 6;
  const counters: Record<string, number> = {};
  const clearT = (i: number) => inBack(lin(frame, clearAt + i * 1.5, clearAt + i * 1.5 + 6), 1.6);

  const talking = msgs.some((m) => m.kind === 'reply' && frame >= m.at && frame < m.at + 20);
  const expr = frame >= T0 && frame < driftAt ? 'squint' : talking ? 'happy' : Math.floor(frame / 50) % 4 === 3 && frame % 50 < 4 ? 'blink' : 'dots';

  const bubble = (m: (typeof msgs)[number], i: number) => {
    const list = slots[m.kind] as readonly (readonly number[])[];
    const n = counters[m.kind] ?? 0;
    counters[m.kind] = n + 1;
    const [fx, fy] = list[n % list.length];
    let x = w * fx;
    let y = h * fy;
    const l = frame - m.at;
    if (l < 0) return null;
    const out = clearT(i);
    if (out >= 1) return null;
    let sc = 1;
    let op = 1;
    if (m.kind === 'user') sc = lerp(0.3, 1, outBack(clamp(l / 4), 2.2));
    if (m.kind === 'reply') {
      const t = outBack(clamp(l / 4), 1.6);
      x = lerp(botX - 40 * u, x, clamp(t));
      y = lerp(headY, y, clamp(t));
      sc = lerp(0.3, 1, t);
    }
    if (m.kind === 'chip' || m.kind === 'comment') {
      sc = lerp(0.9, 1, clamp(l / 2));
      op = clamp(l / 2 + 0.3);
    }
    if (m.kind === 'chip') y -= (l / 30) * 0.012 * h;
    sc *= 1 - out;
    const fs = (m.kind === 'chip' ? 26 : m.kind === 'comment' ? 29 : 34) * u * k;
    if (m.kind === 'speech') {
      const tw = estWidth(m.text, fs, 'rounded');
      const rx = tw / 2 + 46 * u;
      const ry = fs * 1.15;
      const tx = botX - botS * 0.25;
      const ty = headY + 10 * u;
      const ang = Math.atan2(ty - y, tx - x);
      const bx = x + Math.cos(ang) * rx * 0.75;
      const by = y + Math.sin(ang) * ry * 0.75;
      const nx = -Math.sin(ang) * 18 * u;
      const ny = Math.cos(ang) * 18 * u;
      return (
        <svg key={i} width={w} height={h} style={{position: 'absolute', inset: 0, overflow: 'visible', transform: `scale(${1 - out})`, transformOrigin: `${x}px ${y}px`}}>
          <path d={`M${bx + nx} ${by + ny} L${lerp(bx, tx, 0.75)} ${lerp(by, ty, 0.75)} L${bx - nx} ${by - ny} Z`} fill="#fff" stroke="#16081C" strokeWidth={3 * u} strokeLinejoin="round" />
          <ellipse cx={x} cy={y} rx={rx} ry={ry} fill="#fff" stroke="#16081C" strokeWidth={3 * u} />
          <path d={`M${bx + nx * 0.8} ${by + ny * 0.8} L${bx - nx * 0.8} ${by - ny * 0.8}`} stroke="#fff" strokeWidth={6 * u} />
          <text x={x} y={y + fs * 0.35} textAnchor="middle" fontFamily={tfonts.rounded} fontWeight={700} fontSize={fs} fill="#16081C">
            {m.text}
          </text>
        </svg>
      );
    }
    const style: React.CSSProperties =
      m.kind === 'user'
        ? {background: '#120223', color: '#fff', borderRadius: 14 * u, padding: `${14 * u}px ${24 * u}px`, boxShadow: `0 0 0 ${2 * u}px rgba(255,255,255,0.15), 0 ${8 * u}px ${24 * u}px rgba(0,0,0,0.35)`}
        : m.kind === 'reply'
          ? {background: '#DB8644', color: '#fff', borderRadius: 40 * u, padding: `${14 * u}px ${26 * u}px`, boxShadow: `0 ${8 * u}px ${24 * u}px rgba(0,0,0,0.3)`}
          : m.kind === 'chip'
            ? {background: 'rgba(242,142,104,0.78)', color: '#fff', borderRadius: 40 * u, padding: `${8 * u}px ${20 * u}px`, boxShadow: `0 0 ${18 * u}px rgba(255,140,120,0.45)`}
            : {background: '#fff', color: '#16081C', border: `${2 * u}px solid #16081C`, borderRadius: 12 * u, padding: `${8 * u}px ${18 * u}px`};
    return (
      <div
        key={i}
        style={{
          position: 'absolute',
          left: x,
          top: y,
          transform: `translate(-50%, -50%) scale(${sc})`,
          opacity: op,
          fontFamily: tfonts.rounded,
          fontWeight: 700,
          fontSize: fs,
          whiteSpace: 'nowrap',
          ...style,
        }}
      >
        {m.text}
      </div>
    );
  };

  // thought bubble
  const thought = (() => {
    if (frame < T0) return null;
    const drift = ease.in(lin(frame, driftAt, driftAt + 24));
    const dy = -drift * 0.15 * h;
    const fade = 1 - drift;
    const dots = [8, 12, 18].map((r, i) => {
      const t0 = T0 + i * 4;
      const s = outBack(lin(frame, t0, t0 + 5), 1.8);
      const x = botX - botS * (0.1 + i * 0.12);
      const y = headY - (30 + i * 45) * u * k;
      return s > 0 ? <circle key={i} cx={x} cy={y + dy} r={r * u * k * 1.3 * s} fill="url(#cb-dot)" opacity={fade} /> : null;
    });
    const cw = Math.min(w * 0.88, (p.thoughtIcons.length * 110 + 60) * u * k);
    const ch = 170 * u * k;
    const ccx = cx - (portrait ? 0 : 60 * u);
    const ccy = headY - 260 * u * k - ch / 2 + dy;
    const ca = prog(frame, T0 + 12, T0 + 20, ease.out);
    const cs = lerp(0.9, 1, ca);
    const isz = 76 * u * k;
    const n = p.thoughtIcons.length;
    const step = (cw - 60 * u * k) / n;
    const capN = typedCount(frame, capAt, 1);
    return (
      <g opacity={fade}>
        {dots}
        <g transform={`translate(${ccx} ${ccy}) scale(${cs}) translate(${-ccx} ${-ccy})`} opacity={ca}>
          <rect x={ccx - cw / 2 + 8 * u} y={ccy - ch / 2 + 14 * u} width={cw} height={ch} rx={ch / 2} fill="#1a0830" opacity={0.25} style={{filter: `blur(${10 * u}px)`}} />
          <rect x={ccx - cw / 2} y={ccy - ch / 2} width={cw} height={ch} rx={ch / 2} fill="#E9DFFB" opacity={0.82} />
          {p.thoughtIcons.map((ic, i) => {
            const t0 = iconsAt + i * 6;
            const s = frame < t0 ? 0 : lerp(0, 1, outBack(clamp((frame - t0) / 3), 2));
            const x = ccx - cw / 2 + 30 * u * k + step * (i + 0.5);
            return (
              <g key={i}>
                {s > 0 && <FlatIcon kind={ic} x={x} y={ccy} s={isz * s} ink="#2a1640" />}
                {i < n - 1 && frame >= t0 + 3 && <circle cx={x + step / 2} cy={ccy} r={4 * u * k} fill="#9C86C8" />}
              </g>
            );
          })}
        </g>
        {capN > 0 && (
          <text x={ccx} y={ccy + ch / 2 + 52 * u * k} textAnchor="middle" fontFamily={tfonts.rounded} fontWeight={700} fontSize={36 * u * k} fill="#F6EEFF" style={{filter: `drop-shadow(0 ${2 * u}px ${4 * u}px rgba(0,0,0,0.5))`}}>
            {p.thoughtCaption.slice(0, capN)}
            {capN < p.thoughtCaption.length || blinkOn(frame) ? '▊' : ''}
          </text>
        )}
      </g>
    );
  })();

  const vs = frame >= verdictAt ? spring({frame: frame - verdictAt, fps, config: {damping: 13, stiffness: 180}}) : 0;
  const scroll = (frame * 4 * u) % (80 * u);
  return (
    <AbsoluteFill style={{background: p.background}}>
      <svg width={w} height={h} style={{position: 'absolute', inset: 0}}>
        <defs>
          <linearGradient id="cb-sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#1c0738" />
            <stop offset="0.6" stopColor="#5a1474" />
            <stop offset="1" stopColor="#ff4fa0" />
          </linearGradient>
          <linearGradient id="cb-floor" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#3a0a5a" />
            <stop offset="1" stopColor="#12031f" />
          </linearGradient>
          <radialGradient id="cb-dot" cx="35%" cy="30%" r="70%">
            <stop offset="0" stopColor="#ffffff" />
            <stop offset="0.4" stopColor="#C9B5F2" />
            <stop offset="1" stopColor="#7E62C2" />
          </radialGradient>
        </defs>
        <rect width={w} height={horizon} fill="url(#cb-sky)" />
        <circle cx={cx} cy={horizon - 40 * u} r={170 * u * k} fill="#FFB36B" opacity={0.85} />
        {Array.from({length: 6}, (_, i) => (
          <rect key={i} x={cx - 180 * u * k} y={horizon - 40 * u - 10 * u + i * 26 * u} width={360 * u * k} height={(4 + i * 2.2) * u} fill="#5a1474" />
        ))}
        <rect y={horizon} width={w} height={h - horizon} fill="url(#cb-floor)" />
        <g stroke="#ff4fd8" strokeWidth={2 * u} opacity={0.75}>
          {Array.from({length: 25}, (_, i) => {
            const t = (i - 12) / 12;
            return <line key={i} x1={cx + t * w * 0.12} y1={horizon} x2={cx + t * w * 1.4} y2={h} />;
          })}
          {Array.from({length: 12}, (_, i) => {
            const z = (i * 80 * u + scroll) / (12 * 80 * u);
            const y = horizon + (h - horizon) * Math.pow(z, 2.2);
            return <line key={`h${i}`} x1={0} x2={w} y1={y} y2={y} stroke="#38e6ff" opacity={0.5 * z + 0.2} />;
          })}
        </g>
        <rect y={horizon - 2 * u} width={w} height={4 * u} fill="#ffd1f0" opacity={0.8} />
        {p.showBot && <BoxBot id="cb-bot" x={botX} y={botY + Math.sin(frame * 0.15) * 3 * u} size={botS} style="toon" pose={{yaw: -10, pitch: 18, armL: talking ? 120 : 10, armR: frame >= verdictAt ? 150 : 10}} expression={expr as 'dots'} />}
        {thought}
      </svg>
      {msgs.map(bubble)}
      {vs > 0 && p.verdict !== '' && (
        <div
          style={{
            position: 'absolute',
            left: cx,
            top: lerp(-80 * u, (portrait ? 0.07 : 0.1) * h, vs),
            transform: 'translate(-50%, -50%)',
            background: p.verdictColor,
            color: '#0d1a12',
            fontFamily: tfonts.rounded,
            fontWeight: 700,
            fontSize: 34 * u * k,
            padding: `${10 * u}px ${24 * u}px`,
            borderRadius: 10 * u,
            whiteSpace: 'nowrap',
            boxShadow: `0 0 ${24 * u}px ${p.verdictColor}88`,
          }}
        >
          {p.verdict}
        </div>
      )}
    </AbsoluteFill>
  );
};

export const chatBubbles = defineMotion<Props>({
  id: 'chat-bubbles',
  title: 'Chat bubbles, chips & thought bubble',
  category: 'ui',
  description: 'Chat bubbles and comment / prompt chips pop in one by one around a box-bot, a speech balloon snaps on, then a thought bubble rises (dots -> cloud -> icons -> caption) and a green verdict chip drops in.',
  source: ['video12 25:90-36:03 chat-bubble-pop, speech-balloon-pop', 'video12 55:03-57:60 comment-chip-stagger', 'video12 83:80-86:60 thought-bubble-sequence'],
  useFor: 'Conversations, user feedback / comments, "what people are asking", a character thinking back over its day, verdict reveals.',
  durationInFrames: 240,
  defaultProps: {
    messages: [
      {text: 'hi Claude!', kind: 'user'},
      {text: 'Hi! How can I help?', kind: 'reply'},
      {text: 'rename all the variables', kind: 'chip'},
      {text: 'did it get faster?', kind: 'comment'},
      {text: 'why is prod down??', kind: 'chip'},
      {text: 'it forgot what it just did', kind: 'comment'},
      {text: 'help me quit vim', kind: 'chip'},
      {text: 'Morning, little guy!', kind: 'speech'},
    ],
    stagger: 10,
    thoughtIcons: ['alarm', 'train', 'toast', 'flask', 'button', 'moon'],
    thoughtCaption: '…and again tomorrow',
    verdict: 'POSTMORTEM: 3 changes, all reverted',
    verdictColor: '#7DFDB0',
    showBot: true,
    background: '#12031f',
  },
  propDocs: {
    messages: "[{text, kind, at?}] kind = user (dark bubble) | reply (orange, flies from the bot) | chip (orange prompt chip) | comment (white ink chip) | speech (comic balloon); at = start frame",
    stagger: 'frames between messages when `at` is not given',
    thoughtIcons: 'icons that pop into the thought cloud (alarm|train|toast|flask|button|moon|sun|coffee|bolt|heart|star|gear|chat|leaf|check|flame|shield|sword)',
    thoughtCaption: 'caption typed under the thought cloud',
    verdict: 'text of the green chip that drops in at the end ("" = none)',
    verdictColor: 'verdict chip colour',
    showBot: 'draw the orange box-bot speaker',
  },
  component: ChatBubbles,
  tags: ['chat', 'bubbles', 'comments', 'speech', 'thought', 'ui', 'conversation'],
});
