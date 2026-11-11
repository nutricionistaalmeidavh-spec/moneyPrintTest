import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {fonts} from '../../core/fonts';
import {backOut, easeOut3, mixHex, sseg, withAlpha} from '../../core/r2-s1-kit';
import {inkOn} from '../../core/r3-explain';
import {Burst, list, roundStarPath} from '../../core/r3-edu-kit';
import {useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * Early-years counting: friendly shapes pop into a ten-frame-style grid one at a time while a big number (and its
 * word) counts up in step; when the last one lands the whole set does a happy wave and the total is announced.
 */
type Props = {
  count: number;
  shape: string;
  colors: string[];
  title: string;
  unitLabel: string;
  doneText: string;
  numberWords: string[];
  showWords: boolean;
  faces: boolean;
  perRow: number;
  interval: number;
  background: string;
  ink: string;
  accent: string;
  card: string;
  fontFamily: string;
  startAt: number;
  speed: number;
};

const WORDS = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty'];
const SHAPES = ['star', 'circle', 'heart', 'apple', 'balloon', 'square', 'triangle', 'flower', 'fish'];

/** one friendly object in a ±50 box, centred on (0,0) */
const Obj: React.FC<{kind: string; c: string; ink: string; faces: boolean}> = ({kind, c, ink, faces}) => {
  const edge = mixHex(c, ink, 0.4);
  const sw = {stroke: edge, strokeWidth: 4, strokeLinejoin: 'round' as const};
  let body: React.ReactNode;
  let fy = 2;
  let fx = 0;
  switch (kind) {
    case 'circle':
      body = (
        <>
          <circle r="46" fill={c} {...sw} />
          <ellipse cx="-17" cy="-24" rx="12" ry="7" fill="#fff" opacity="0.45" transform="rotate(-35 -17 -24)" />
        </>
      );
      break;
    case 'heart':
      fy = -6;
      body = <path d="M0 42 C-62 4 -54 -44 -24 -44 C-9 -44 0 -33 0 -25 C0 -33 9 -44 24 -44 C54 -44 62 4 0 42Z" fill={c} {...sw} />;
      break;
    case 'apple':
      fy = 6;
      body = (
        <>
          <path d="M0 -26 C-26 -48 -58 -28 -54 8 C-50 42 -22 56 0 46 C22 56 50 42 54 8 C58 -28 26 -48 0 -26Z" fill={c} {...sw} />
          <path d="M0 -26 C0 -38 4 -46 10 -52" fill="none" stroke="#7A4B2A" strokeWidth="6" strokeLinecap="round" />
          <path d="M6 -40 C16 -56 36 -56 42 -48 C34 -34 18 -32 6 -40Z" fill="#3FA34D" {...sw} stroke={mixHex('#3FA34D', ink, 0.4)} />
        </>
      );
      break;
    case 'balloon':
      fy = -10;
      body = (
        <>
          <path d="M0 48 C-4 62 6 70 0 80" fill="none" stroke={withAlpha(ink, 0.5)} strokeWidth="3" strokeLinecap="round" />
          <path d="M0 40 L-8 54 L8 54Z" fill={edge} />
          <ellipse cx="0" cy="-8" rx="40" ry="48" fill={c} {...sw} />
          <ellipse cx="-14" cy="-26" rx="8" ry="13" fill="#fff" opacity="0.4" transform="rotate(20 -14 -26)" />
        </>
      );
      break;
    case 'square':
      body = (
        <>
          <rect x="-44" y="-44" width="88" height="88" rx="16" fill={c} {...sw} />
          <rect x="-34" y="-36" width="30" height="9" rx="4.5" fill="#fff" opacity="0.4" />
        </>
      );
      break;
    case 'triangle':
      fy = 14;
      body = <path d="M0 -44 L50 40 L-50 40Z" fill={c} {...sw} strokeWidth={12} />;
      break;
    case 'flower':
      body = (
        <>
          {Array.from({length: 6}, (_, i) => {
            const a = (i / 6) * Math.PI * 2;
            return <circle key={i} cx={Math.cos(a) * 29} cy={Math.sin(a) * 29} r="21" fill={c} {...sw} />;
          })}
          <circle r="22" fill="#FFD23F" stroke={mixHex('#FFD23F', ink, 0.4)} strokeWidth="4" />
        </>
      );
      break;
    case 'fish':
      fx = -10;
      body = (
        <>
          <path d="M26 0 L56 -26 L56 26Z" fill={mixHex(c, '#ffffff', 0.2)} {...sw} />
          <ellipse cx="-6" cy="0" rx="40" ry="30" fill={c} {...sw} />
          <path d="M-2 -18 C6 -8 6 8 -2 18" fill="none" stroke={edge} strokeWidth="3.5" strokeLinecap="round" />
        </>
      );
      break;
    case 'star':
    default:
      fy = 4;
      body = (
        <>
          <path d={roundStarPath(0, 3, 56, 0.5, 5, 0.14)} fill={c} {...sw} />
        </>
      );
  }
  return (
    <g>
      {body}
      {faces && (
        <g transform={`translate(${fx} ${fy})`}>
          <circle cx="-12" cy="-4" r="4.5" fill={ink} />
          <circle cx="12" cy="-4" r="4.5" fill={ink} />
          <path d="M-9 7 C-4 15 4 15 9 7" fill="none" stroke={ink} strokeWidth="3.4" strokeLinecap="round" />
        </g>
      )}
    </g>
  );
};

const CountingObjects: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const {w, h, u, portrait} = useStage();
  const f = Math.max(0, frame - p.startAt) * (p.speed || 1);
  const font = p.fontFamily || fonts.display;
  const showBg = p.background !== 'transparent';
  const n = Math.max(1, Math.min(40, Math.round(p.count || 7)));
  const colors = list<string>(p.colors, ['#FF6B6B', '#FFB020', '#2EC4B6', '#4D96FF', '#9B5DE5']);
  const words = list<string>(p.numberWords, WORDS);
  const kind = SHAPES.includes(p.shape) ? p.shape : 'star';
  const perRow = Math.max(2, Math.min(10, Math.round(p.perRow || 5)));
  const rows = Math.ceil(n / perRow);
  const interval = p.interval > 0 ? p.interval : Math.max(9, Math.min(28, Math.round(265 / n)));
  const t0 = 34;
  const tEnd = t0 + (n - 1) * interval + 16;

  // layout
  const areaX = portrait ? w * 0.06 : w * 0.43;
  const areaW = portrait ? w * 0.88 : w * 0.52;
  const areaY = portrait ? h * 0.42 : h * 0.2;
  const areaH = portrait ? h * 0.46 : h * 0.68;
  const cols = Math.min(perRow, n);
  const cell = Math.min(areaW / cols, areaH / rows, 220 * u);
  const gridW = cell * cols;
  const gridH = cell * rows;
  const gx = areaX + (areaW - gridW) / 2;
  const gy = areaY + (areaH - gridH) / 2;

  const popped = Math.max(0, Math.min(n, Math.floor((f - t0) / interval) + 1));
  const lastT = t0 + (popped - 1) * interval;
  const sinceChange = popped > 0 ? f - lastT : 99;
  const bump = popped > 0 ? 1 + 0.28 * Math.max(0, 1 - sinceChange / 12) * Math.cos(sinceChange * 0.55) : 1;
  const lastColor = popped > 0 ? colors[(popped - 1) % colors.length] : mixHex(p.ink, p.card, 0.8);
  const numCol = inkOn(lastColor);
  const done = f >= tEnd;
  const doneIn = easeOut3(sseg(f, tEnd + 4, tEnd + 24));
  const titleIn = easeOut3(sseg(f, 0, 18));
  const numIn = easeOut3(sseg(f, 6, 26));
  const doneStr = String(p.doneText).replace('{n}', String(n)).replace('{unit}', p.unitLabel);

  const boxS = portrait ? Math.min(w * 0.44, h * 0.2) : Math.min(w * 0.26, h * 0.46);
  const boxCx = portrait ? w / 2 : w * 0.22;
  const boxCy = portrait ? h * 0.255 : h * 0.47;
  const word = popped > 0 ? words[(popped - 1) % words.length] : '';

  return (
    <AbsoluteFill style={{background: showBg ? p.background : undefined, overflow: 'hidden'}}>
      {/* title */}
      <div style={{position: 'absolute', left: 0, right: 0, top: (portrait ? 100 : 56) * u, textAlign: 'center', fontFamily: font, fontSize: (portrait ? 76 : 70) * u, color: p.ink, opacity: titleIn * (1 - doneIn), transform: `translateY(${(1 - titleIn) * -20 * u}px)`}}>{p.title}</div>
      <div style={{position: 'absolute', left: 0, right: 0, top: (portrait ? 100 : 56) * u, textAlign: 'center', fontFamily: font, fontSize: (portrait ? 76 : 70) * u, color: p.accent, opacity: doneIn, transform: `scale(${0.8 + 0.2 * backOut(sseg(f, tEnd + 4, tEnd + 24))})`}}>{doneStr}</div>

      {/* number box */}
      <div style={{position: 'absolute', left: boxCx - boxS / 2, top: boxCy - boxS / 2, width: boxS, height: boxS, borderRadius: boxS * 0.2, background: popped > 0 ? lastColor : p.card, boxShadow: `0 ${20 * u}px ${56 * u}px rgba(0,0,0,0.2)`, opacity: numIn, transform: `scale(${(0.88 + 0.12 * numIn) * (done ? 1 + 0.04 * Math.sin((f - tEnd) * 0.3) * doneIn : 1)})`, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden'}}>
        <div style={{fontFamily: font, fontSize: boxS * (String(popped).length > 2 ? 0.4 : String(popped).length > 1 ? 0.54 : 0.74), lineHeight: 1, color: popped > 0 ? numCol : mixHex(p.ink, p.card, 0.7), transform: `scale(${bump})`}}>{popped}</div>
      </div>
      {p.showWords && (
        <div style={{position: 'absolute', left: boxCx - boxS * 0.7, width: boxS * 1.4, top: boxCy + boxS / 2 + 22 * u, textAlign: 'center', fontFamily: fonts.sans, fontWeight: 800, fontSize: (portrait ? 56 : 54) * u, letterSpacing: 2 * u, textTransform: 'uppercase', color: p.ink, opacity: popped > 0 ? 1 : 0, transform: `scale(${1 + (bump - 1) * 0.5})`}}>{word}</div>
      )}

      {/* grid */}
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        {Array.from({length: n}, (_, i) => {
          const r = Math.floor(i / perRow);
          const c = i % perRow;
          const cx = gx + c * cell + cell / 2;
          const cy = gy + r * cell + cell / 2;
          const slotIn = easeOut3(sseg(f, 10 + i * 1.5, 30 + i * 1.5));
          const ti = t0 + i * interval;
          const q = sseg(f, ti, ti + 16);
          const sc = q > 0 ? backOut(q, 2.4) : 0;
          const ring = sseg(f, ti, ti + 20);
          const col = colors[i % colors.length];
          const jq = sseg(f, tEnd + 8 + i * 3, tEnd + 8 + i * 3 + 18);
          const jump = jq > 0 && jq < 1 ? Math.sin(jq * Math.PI) * cell * 0.22 : 0;
          const sq = jq > 0 && jq < 1 ? 1 + 0.06 * Math.sin(jq * Math.PI * 2) : 1;
          const slot = cell * 0.88;
          return (
            <g key={i}>
              <rect x={cx - slot / 2} y={cy - slot / 2} width={slot} height={slot} rx={slot * 0.16} fill={withAlpha(p.ink, 0.045)} stroke={withAlpha(p.ink, 0.2)} strokeWidth={2.5 * u} strokeDasharray={`${8 * u} ${8 * u}`} opacity={slotIn * (1 - Math.min(1, q) * 0.7)} />
              {ring > 0 && ring < 1 && <circle cx={cx} cy={cy} r={cell * (0.3 + 0.5 * ring)} fill="none" stroke={col} strokeWidth={5 * u * (1 - ring)} opacity={1 - ring} />}
              {q > 0 && (
                <>
                  <ellipse cx={cx} cy={cy + cell * 0.38} rx={cell * 0.26 * sc} ry={cell * 0.05} fill="rgba(0,0,0,0.14)" opacity={1 - jump / (cell * 0.3)} />
                  <g transform={`translate(${cx} ${cy - jump}) rotate(${(1 - Math.min(1, q)) * -24}) scale(${sc * sq * (cell * 0.86) / 110})`}>
                    <Obj kind={kind} c={col} ink={p.ink} faces={p.faces} />
                  </g>
                </>
              )}
            </g>
          );
        })}
        <Burst x={boxCx} y={boxCy} t={done ? sseg(f, tEnd + 2, tEnd + 44) : 0} colors={[...colors, '#FFD23F']} n={20} radius={boxS * 0.9} seed={3} size={14 * u} />
      </svg>
    </AbsoluteFill>
  );
};

export const countingObjects = defineMotion<Props>({
  id: 'counting-objects',
  title: 'Counting objects',
  category: 'text',
  description: 'Kid-friendly counting: cute faced shapes (stars, hearts, apples, balloons, fish ...) pop into a ten-frame grid one by one while a big number and its word count up in step, then the set waves and the total is announced with confetti.',
  source: ['original (round 3)'],
  useFor: 'Early-years maths and number-recognition videos, kids\' app promos, preschool lessons and "how many?" social posts — pass the count, the shape, the unit word and your colours.',
  durationInFrames: 360,
  defaultProps: {
    count: 7,
    shape: 'star',
    colors: ['#FF6B6B', '#FFB020', '#2EC4B6', '#4D96FF', '#9B5DE5'],
    title: "Let's count!",
    unitLabel: 'stars',
    doneText: '{n} {unit}!',
    numberWords: WORDS,
    showWords: true,
    faces: true,
    perRow: 5,
    interval: 0,
    background: '#FFF6E5',
    ink: '#2B2A4C',
    accent: '#FF6B6B',
    card: '#FFFFFF',
    fontFamily: '',
    startAt: 0,
    speed: 1,
  },
  propDocs: {
    count: 'how many objects to count (1-40)',
    shape: 'star | circle | heart | apple | balloon | square | triangle | flower | fish',
    colors: 'colours cycled across the objects (also tints the number box)',
    title: 'heading shown while counting',
    unitLabel: 'what is being counted, plural (used in doneText)',
    doneText: 'heading after the last object; {n} = the count, {unit} = unitLabel',
    numberWords: 'number words for 1, 2, 3 ... (translate for other languages)',
    showWords: 'show the number word under the number',
    faces: 'give each object a smiling face',
    perRow: 'objects per row in the grid (5 = ten-frame style)',
    interval: 'frames between pops (0 = auto-fit to the clip)',
    background: "backdrop colour or 'transparent'",
    ink: 'text, face and outline colour',
    accent: 'completion heading colour',
    card: 'number box colour before counting starts',
    fontFamily: 'optional CSS font-family for the number and headings (empty = display)',
    startAt: 'frame the lesson starts',
    speed: 'playback speed multiplier',
  },
  component: CountingObjects,
  tags: ['counting', 'numbers', 'kids', 'children', 'preschool', 'maths', 'math', 'early years', 'shapes', 'education', 'school', 'learning', 'count', 'ten frame', 'cute'],
});
