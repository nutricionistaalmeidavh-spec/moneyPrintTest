import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {fonts} from '../../core/fonts';
import {easeIO, easeOut3, mixHex, sseg, withAlpha} from '../../core/r2-s1-kit';
import {fitText, inkOn} from '../../core/r3-explain';
import {list} from '../../core/r3-edu-kit';
import {useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * A study deck: cards slide in term-side up, flip over to reveal the definition, then fly off while the next one
 * arrives. A deck stack, progress dots and a counter keep the learner oriented; a "deck complete" end state closes it.
 */
type Card = {term: string; definition: string};
type Props = {
  cards: Card[];
  title: string;
  termLabel: string;
  definitionLabel: string;
  flipHint: string;
  doneText: string;
  doneSubtitle: string;
  background: string;
  ink: string;
  accent: string;
  accent2: string;
  card: string;
  fontFamily: string;
  hold: number;
  startAt: number;
  speed: number;
};

const DEFAULT_CARDS: Card[] = [
  {term: 'Photosynthesis', definition: 'How plants turn sunlight, water and air into food.'},
  {term: 'Habitat', definition: 'The natural home where an animal or plant lives.'},
  {term: 'Evaporation', definition: 'When liquid water warms up and rises as vapour.'},
  {term: 'Gravity', definition: 'The force that pulls objects toward each other.'},
];

const ENTER = 14;
const FLIP = 16;
const EXIT = 12;

const FlashcardFlipDeck: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const {w, h, u, portrait} = useStage();
  const cards = list<Card>(p.cards, DEFAULT_CARDS).map((c) => ({term: String(c?.term ?? ''), definition: String(c?.definition ?? '')}));
  const n = cards.length;
  const f = Math.max(0, frame - p.startAt) * (p.speed || 1);
  const font = p.fontFamily || fonts.grotesk;
  const hold = Math.max(8, p.hold || 24);
  const holdDef = Math.round(hold * 1.3);
  const cycle = ENTER + hold + FLIP + holdDef + EXIT;
  const lead = 10;
  const showBg = p.background !== 'transparent';

  const cw = portrait ? w * 0.84 : Math.min(w * 0.52, 940 * u);
  const ch = Math.min(portrait ? cw * 0.82 : cw * 0.62, h * (portrait ? 0.46 : 0.6));
  const pad = 46 * u;
  const cy = h * (portrait ? 0.5 : 0.53);
  const cx = w / 2;

  const idx = Math.min(n - 1, Math.max(0, Math.floor((f - lead) / cycle)));
  const t = f - lead - idx * cycle;
  const finished = f - lead >= n * cycle;
  const doneIn = easeOut3(sseg(f, lead + n * cycle + 2, lead + n * cycle + 26));
  const cardsDone = Math.min(n, Math.max(0, Math.floor((f - lead - ENTER - hold - FLIP) / cycle) + 1));

  const frontBg = p.accent;
  const frontInk = inkOn(frontBg);
  const backInk = inkOn(p.card, '#FFFFFF', p.ink);

  const renderCard = (c: Card, k: number) => {
    const enter = easeOut3(sseg(t, 0, ENTER));
    const flipT = easeIO(sseg(t, ENTER + hold, ENTER + hold + FLIP));
    const exitT = easeIO(sseg(t, cycle - EXIT, cycle));
    const angle = flipT * 180;
    const lift = 1 + 0.08 * Math.sin(flipT * Math.PI);
    const tx = (1 - enter) * cw * 0.9 - exitT * w * 0.7;
    const rz = (1 - enter) * 7 - exitT * 9;
    const op = Math.min(enter * 1.4, 1) * (1 - exitT * 0.6);
    const termFit = fitText(c.term, cw - pad * 2, ch * 0.5, (portrait ? 96 : 104) * u, 34 * u, 0.58, 1.08);
    const defFit = fitText(c.definition, cw - pad * 2, ch * 0.5, (portrait ? 54 : 52) * u, 24 * u, 0.52, 1.28);
    const face: React.CSSProperties = {position: 'absolute', inset: 0, borderRadius: 34 * u, backfaceVisibility: 'hidden', WebkitBackfaceVisibility: 'hidden', overflow: 'hidden', boxSizing: 'border-box', padding: pad, display: 'flex', flexDirection: 'column'};
    const pill = (bg: string, fg: string, txt: string): React.ReactNode => (
      <div style={{alignSelf: 'flex-start', padding: `${6 * u}px ${20 * u}px`, borderRadius: 999, background: bg, color: fg, fontFamily: fonts.sans, fontWeight: 800, fontSize: 22 * u, letterSpacing: 3 * u, textTransform: 'uppercase'}}>{txt}</div>
    );
    return (
      <div key={k} style={{position: 'absolute', left: cx - cw / 2, top: cy - ch / 2, width: cw, height: ch, perspective: 2400 * u, opacity: op, transform: `translateX(${tx}px) rotate(${rz}deg) scale(${lift})`}}>
        <div style={{position: 'relative', width: '100%', height: '100%', transformStyle: 'preserve-3d', transform: `rotateY(${angle}deg)`}}>
          {/* front: the term */}
          <div style={{...face, background: frontBg, color: frontInk, boxShadow: `0 ${26 * u}px ${70 * u}px rgba(0,0,0,0.32)`}}>
            <div style={{position: 'absolute', right: -ch * 0.18, top: -ch * 0.18, width: ch * 0.6, height: ch * 0.6, borderRadius: '50%', background: withAlpha(frontInk, 0.1)}} />
            <div style={{position: 'absolute', left: -ch * 0.1, bottom: -ch * 0.22, width: ch * 0.5, height: ch * 0.5, borderRadius: '50%', background: withAlpha(frontInk, 0.07)}} />
            {pill(withAlpha(frontInk, 0.18), frontInk, p.termLabel)}
            <div style={{flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center'}}>
              <div style={{fontFamily: font, fontWeight: 700, fontSize: termFit.fs, lineHeight: termFit.lh, letterSpacing: -1.5 * u}}>{termFit.lines.join(' ')}</div>
            </div>
            {p.flipHint ? (
              <div style={{display: 'flex', alignItems: 'center', gap: 12 * u, alignSelf: 'center', opacity: 0.8, fontFamily: fonts.sans, fontWeight: 600, fontSize: 24 * u}}>
                <svg width={30 * u} height={30 * u} viewBox="0 0 24 24">
                  <path d="M20 12a8 8 0 1 1-2.6-5.9M20 4v4.5h-4.5" fill="none" stroke={frontInk} strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {p.flipHint}
              </div>
            ) : null}
          </div>
          {/* back: the definition */}
          <div style={{...face, transform: 'rotateY(180deg)', background: p.card, color: backInk, boxShadow: `0 ${26 * u}px ${70 * u}px rgba(0,0,0,0.32)`}}>
            <div style={{position: 'absolute', left: 0, top: 0, right: 0, height: 16 * u, background: p.accent2}} />
            <div style={{marginTop: 10 * u, display: 'flex'}}>{pill(withAlpha(p.accent2, 0.2), mixHex(p.accent2, backInk, 0.45), p.definitionLabel)}</div>
            <div style={{flex: 1, display: 'flex', alignItems: 'center'}}>
              <div style={{fontFamily: fonts.sans, fontWeight: 600, fontSize: defFit.fs, lineHeight: defFit.lh}}>{defFit.lines.join(' ')}</div>
            </div>
            <div style={{fontFamily: font, fontWeight: 700, fontSize: 28 * u, color: p.accent, letterSpacing: -0.5 * u}}>{c.term}</div>
          </div>
        </div>
      </div>
    );
  };

  const remaining = n - idx - 1;
  const stack = [2, 1].map((d) => {
    if (finished || d > remaining) return null;
    const e = easeOut3(sseg(f, 0, 20));
    return (
      <div key={d} style={{position: 'absolute', left: cx - cw / 2, top: cy - ch / 2 + d * 28 * u * e, width: cw, height: ch, borderRadius: 34 * u, background: mixHex(p.accent, p.background === 'transparent' ? '#000000' : p.background, 0.18 + d * 0.22), transform: `scale(${1 - d * 0.045})`, opacity: e, boxShadow: `0 ${14 * u}px ${40 * u}px rgba(0,0,0,0.22)`}} />
    );
  });

  const headIn = easeOut3(sseg(f, 0, 18));
  const dotY = cy + ch / 2 + 62 * u;
  const dotR = 11 * u;

  return (
    <AbsoluteFill style={{background: showBg ? p.background : undefined, overflow: 'hidden'}}>
      {/* header */}
      <div style={{position: 'absolute', left: portrait ? 56 * u : 90 * u, right: portrait ? 56 * u : 90 * u, top: (portrait ? 110 : 70) * u, display: 'flex', alignItems: 'center', justifyContent: 'space-between', opacity: headIn, transform: `translateY(${(1 - headIn) * -20 * u}px)`}}>
        <div style={{fontFamily: font, fontWeight: 700, fontSize: (portrait ? 56 : 50) * u, color: p.ink, letterSpacing: -1 * u}}>{p.title}</div>
        <div style={{fontFamily: fonts.mono, fontWeight: 700, fontSize: 34 * u, color: p.ink, padding: `${6 * u}px ${22 * u}px`, borderRadius: 999, background: withAlpha(p.ink, 0.1)}}>
          {Math.min(n, finished ? n : idx + 1)} / {n}
        </div>
      </div>
      {stack}
      {!finished && renderCard(cards[idx], idx)}
      {/* progress dots */}
      <svg width={w} height={h} style={{position: 'absolute', inset: 0, opacity: headIn}}>
        {cards.map((_, i) => {
          const x = cx + (i - (n - 1) / 2) * dotR * 3.2;
          const done = i < cardsDone;
          const cur = i === idx && !finished;
          return <circle key={i} cx={x} cy={dotY} r={dotR * (cur ? 1.25 : 1)} fill={done ? p.accent : 'none'} stroke={done || cur ? p.accent : withAlpha(p.ink, 0.35)} strokeWidth={2.5 * u} />;
        })}
      </svg>
      {/* done */}
      {doneIn > 0 && (
        <div style={{position: 'absolute', left: 0, right: 0, top: cy - ch * 0.5, textAlign: 'center', opacity: doneIn, transform: `scale(${0.85 + 0.15 * doneIn})`}}>
          <svg width={150 * u} height={150 * u} viewBox="0 0 150 150" style={{display: 'block', margin: '0 auto'}}>
            <circle cx="75" cy="75" r="62" fill={p.accent} />
            <path d="M46 78 L67 98 L106 54" fill="none" stroke={inkOn(p.accent)} strokeWidth="13" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="1 1" pathLength={1} strokeDashoffset={1 - easeOut3(sseg(f, lead + n * cycle + 10, lead + n * cycle + 30))} />
          </svg>
          <div style={{marginTop: 26 * u, fontFamily: font, fontWeight: 700, fontSize: (portrait ? 84 : 92) * u, color: p.ink, letterSpacing: -2 * u}}>{p.doneText}</div>
          <div style={{marginTop: 8 * u, fontFamily: fonts.sans, fontWeight: 600, fontSize: 36 * u, color: withAlpha(p.ink, 0.65)}}>{String(p.doneSubtitle).replace('{n}', String(n))}</div>
        </div>
      )}
    </AbsoluteFill>
  );
};

export const flashcardFlipDeck = defineMotion<Props>({
  id: 'flashcard-flip-deck',
  title: 'Flashcard flip deck',
  category: 'text',
  description: 'A study deck of flashcards: each card slides in showing the term, flips over in 3D to reveal its definition, then flies off as the next arrives, with a deck stack, progress dots, a counter and a deck-complete finish.',
  source: ['original (round 3)'],
  useFor: 'Vocabulary, revision and quiz-prep videos, language-learning reels, course trailers and "test yourself" social posts — pass your own cards (term + definition), labels and brand colours.',
  durationInFrames: 430,
  defaultProps: {
    cards: DEFAULT_CARDS,
    title: 'Science words',
    termLabel: 'Term',
    definitionLabel: 'Meaning',
    flipHint: 'Think, then flip',
    doneText: 'Deck complete!',
    doneSubtitle: '{n} cards reviewed',
    background: '#F4EFE6',
    ink: '#1F2430',
    accent: '#3D5AFE',
    accent2: '#FF9F1C',
    card: '#FFFFFF',
    fontFamily: '',
    hold: 24,
    startAt: 0,
    speed: 1,
  },
  propDocs: {
    cards: 'array of {term, definition} cards, shown in order',
    title: 'deck title shown top-left',
    termLabel: 'small label on the term side',
    definitionLabel: 'small label on the definition side',
    flipHint: 'hint line at the bottom of the term side (empty hides it)',
    doneText: 'headline of the end state',
    doneSubtitle: 'end-state subtitle; {n} is replaced by the card count',
    background: "backdrop colour or 'transparent'",
    ink: 'title / counter / end-state text colour',
    accent: 'term-side card colour, progress dots, check mark',
    accent2: 'definition-side top stripe and label colour',
    card: 'definition-side card colour',
    fontFamily: 'optional CSS font-family for terms and the title (empty = grotesk)',
    hold: 'frames each side is held before flipping / moving on (definition is held 30% longer)',
    startAt: 'frame the deck starts',
    speed: 'playback speed multiplier',
  },
  component: FlashcardFlipDeck,
  tags: ['flashcard', 'flip', 'deck', 'study', 'revision', 'vocabulary', 'term', 'definition', 'cards', 'education', 'language', 'learning', 'quiz', 'school'],
});
