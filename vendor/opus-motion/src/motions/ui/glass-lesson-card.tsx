import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {clamp, ease, prog} from '../../core/ease';
import {DeskBook, GlassPanel, INK3, x14Fonts} from '../../core/r2-x14-kit';
import {useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * x3 "pop-up textbook" lesson cards: a frosted-glass card floats top-left over the scene with a small
 * letter-spaced red-brown eyebrow (LESSON 1, THE EQUATION, KEY WORDS, PREDICT, WHY?), a serif heading and
 * 1–4 lines of body, a definition list or a checklist. Cards replace each other with a short crossfade
 * and an 8 px upward drift (old out 0.15 s, new in 0.25 s, easeOutCubic). The frost is a blurred copy of
 * the backdrop clipped to the card (reliable in headless renders); with backdrop "none" it uses CSS
 * backdrop-filter so it works as an overlay on host content.
 */

type Card = {
  eyebrow: string;
  heading: string;
  body?: string[];
  items?: {term: string; def: string}[];
  checklist?: string[];
  tick?: number;
};

type Props = {
  cards: Card[];
  startAt: number;
  holdFrames: number;
  position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
  width: number;
  backdrop: string;
  drift: number;
  eyebrowColor: string;
  headingColor: string;
  bodyColor: string;
  tickColor: string;
  background: string;
};

/** "E_p = m g h" -> E<sub>p</sub> = m g h */
const withSubs = (s: string) => {
  const parts = s.split(/_(\w)/);
  return parts.map((p, i) => (i % 2 === 1 ? <sub key={i} style={{fontSize: '0.6em', verticalAlign: '-0.25em'}}>{p}</sub> : <React.Fragment key={i}>{p}</React.Fragment>));
};

const CardBody: React.FC<{card: Card; local: number; hold: number; colors: {eyebrow: string; heading: string; body: string; tick: string}}> = ({card, local, hold, colors}) => {
  const st = useStage();
  const u = st.u * (st.portrait ? 1.3 : 1);
  const serif = x14Fonts.bookSerif;
  const isEq = /_\w|=/.test(card.heading) && card.heading.length < 24;
  const item = (i: number) => prog(local, 4 + i * 4, 14 + i * 4, ease.out);
  const tickAt = Math.round(hold * 0.5);
  const tickP = prog(local, tickAt, tickAt + 8, ease.inOut);
  return (
    <div style={{padding: `${24 * u}px ${30 * u}px ${26 * u}px`, fontFamily: serif, color: colors.body}}>
      <div style={{fontSize: 15 * u, letterSpacing: '0.16em', fontWeight: 600, color: colors.eyebrow, textTransform: 'uppercase', marginBottom: 10 * u}}>{card.eyebrow}</div>
      <div
        style={{
          fontSize: (isEq ? 40 : 34) * u,
          fontWeight: isEq ? 400 : 600,
          fontFamily: isEq ? x14Fonts.bookSerifItalic : serif,
          fontStyle: isEq ? 'italic' : 'normal',
          color: colors.heading,
          lineHeight: 1.2,
          marginBottom: 12 * u,
        }}
      >
        {withSubs(card.heading)}
      </div>
      {card.body?.map((p, i) => (
        <div key={i} style={{fontSize: 26 * u, lineHeight: 1.45, marginTop: i ? 10 * u : 0, opacity: 0.35 + 0.65 * item(i), transform: `translateY(${(1 - item(i)) * 6 * u}px)`}}>
          {p}
        </div>
      ))}
      {card.items?.map((it, i) => (
        <div key={i} style={{fontSize: 24 * u, lineHeight: 1.45, opacity: item(i), transform: `translateY(${(1 - item(i)) * 6 * u}px)`}}>
          <span style={{fontWeight: 600, color: colors.heading}}>{it.term}</span>
          <span style={{color: colors.body}}> {it.def}</span>
        </div>
      ))}
      {card.checklist?.map((c, i) => {
        const ticked = card.tick === i;
        return (
          <div key={i} style={{display: 'flex', alignItems: 'center', gap: 14 * u, fontSize: 24 * u, lineHeight: 1.5, opacity: item(i), fontFamily: x14Fonts.bookSerifItalic, fontStyle: 'italic'}}>
            <svg width={22 * u} height={22 * u} viewBox="0 0 22 22" style={{flex: 'none', overflow: 'visible'}}>
              <rect x={1} y={1} width={20} height={20} rx={3} fill={ticked && tickP > 0 ? 'rgba(255,255,255,0.5)' : 'none'} stroke={colors.body} strokeWidth={1.6} />
              {ticked ? <path d="M4 11 L9 17 L24 -2" fill="none" stroke={colors.tick} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - tickP} /> : null}
            </svg>
            <span style={{color: ticked && tickP > 0.5 ? colors.heading : colors.body}}>{c}</span>
          </div>
        );
      })}
    </div>
  );
};

const GlassLessonCard: React.FC<Props> = ({cards, startAt, holdFrames, position, width, backdrop, drift, eyebrowColor, headingColor, bodyColor, tickColor, background}) => {
  const frame = useCurrentFrame();
  const {w, h, u, portrait, durationInFrames} = useStage();
  const showBook = backdrop !== 'none';
  const zoom = 1 + drift * clamp(frame / Math.max(1, durationInFrames));
  const back = showBook ? <DeskBook uid="glc" zoom={zoom} offsetY={portrait ? 0.07 : 0} /> : null;
  const cw = portrait ? w - 96 * u : Math.min(width * u, w - 120 * u);
  const right = position.endsWith('right');
  const bottom = position.startsWith('bottom');
  const x = portrait ? (w - cw) / 2 : right ? w - cw - 0.092 * w : 0.092 * w;
  const y0 = bottom ? h * 0.56 : portrait ? h * 0.05 : h * 0.05;
  const n = Math.max(1, cards.length);
  const colors = {eyebrow: eyebrowColor, heading: headingColor, body: bodyColor, tick: tickColor};
  const fadeOut = 5;
  const fadeIn = 8;
  return (
    <AbsoluteFill style={{background: showBook ? INK3.mat : background}}>
      {back}
      {cards.map((card, i) => {
        const t0 = startAt + i * holdFrames;
        const t1 = i === n - 1 ? 1e9 : startAt + (i + 1) * holdFrames;
        if (frame < t0 - 1 || frame > t1 + fadeOut + 1) return null;
        const inP = prog(frame, t0, t0 + fadeIn, ease.out);
        const outP = prog(frame, t1, t1 + fadeOut, ease.in);
        const op = inP * (1 - outP);
        if (op <= 0.001) return null;
        const dy = (1 - inP) * 12 * u - outP * 6 * u;
        const y = y0 + dy;
        return (
          <GlassPanel key={i} x={x} y={y} width={cw} radius={20 * u} frost={back ?? undefined} opacity={op}>
            <CardBody card={card} local={frame - t0} hold={holdFrames} colors={colors} />
          </GlassPanel>
        );
      })}
    </AbsoluteFill>
  );
};

export const glassLessonCard = defineMotion<Props>({
  id: 'glass-lesson-card',
  title: 'Glass lesson cards',
  category: 'ui',
  description:
    'Frosted-glass lesson cards float top-left over an open textbook on a felt desk — red-brown letter-spaced eyebrow, serif heading, body / key-word list / ticked checklist — and swap LESSON → EQUATION → KEY WORDS → PREDICT → WHY? with a crossfade and an 8 px upward drift. Backdrop "none" turns it into a transparent overlay.',
  source: ['video x3 13.9-22.0 (glass-lesson-card)'],
  useFor: 'Lesson, step and definition overlays for educational explainers, product tours and course trailers; the card system of an "interactive lesson" video.',
  durationInFrames: 240,
  defaultProps: {
    cards: [
      {eyebrow: 'Lesson 1', heading: 'Energy stores', body: ['When something changes, energy moves from one store to another.', 'Energy is not a substance: the stores are a model that helps us keep count.']},
      {eyebrow: 'The equation', heading: 'E_p = m g h', body: ['Gravitational store = mass × field strength × height.', 'Lift it twice as high and it stores twice as much.']},
      {
        eyebrow: 'Key words',
        heading: 'Words to know',
        items: [
          {term: 'system', def: 'An object or group of objects.'},
          {term: 'energy store', def: 'A way a system holds energy.'},
          {term: 'pathway', def: 'How energy moves between stores.'},
          {term: 'joule (J)', def: 'The unit of energy.'},
        ],
      },
      {eyebrow: 'Predict', heading: 'The book falls and lands. Where is its energy now?', checklist: ['It has been used up', 'In the thermal stores around it', 'Still in its gravitational store'], tick: 1},
      {eyebrow: 'Why?', heading: 'Nothing is used up', body: ['As it falls, the gravitational store empties into the kinetic store; on landing the energy spreads out as warmth and sound.']},
    ],
    startAt: 6,
    holdFrames: 45,
    position: 'top-left',
    width: 660,
    backdrop: 'book',
    drift: 0.03,
    eyebrowColor: INK3.eyebrow,
    headingColor: INK3.heading,
    bodyColor: INK3.body,
    tickColor: '#2E7D3A',
    background: 'transparent',
  },
  propDocs: {
    cards: 'list of {eyebrow, heading, body?: string[], items?: [{term, def}], checklist?: string[], tick?: index}; "E_p" in a heading renders a subscript',
    startAt: 'frame the first card fades in',
    holdFrames: 'frames each card stays before the next replaces it (the last one holds to the end)',
    position: 'top-left | top-right | bottom-left | bottom-right (portrait always centres the card at the top)',
    width: 'card width in u (clamped to the frame)',
    backdrop: '"book" procedural textbook spread on a felt desk | "none" = transparent overlay (CSS backdrop blur over host content)',
    drift: 'slow camera push on the backdrop over the whole clip (0.03 = 3 %)',
    eyebrowColor: 'eyebrow (small caps) colour',
    headingColor: 'heading colour',
    bodyColor: 'body text colour',
    tickColor: 'checklist tick colour',
    background: 'colour behind the cards when backdrop is "none" ("transparent" to overlay)',
  },
  component: GlassLessonCard,
  tags: ['glass', 'frosted', 'card', 'lesson', 'education', 'textbook', 'explainer', 'definition', 'quiz', 'checklist', 'equation', 'serif', 'overlay', 'ui', 'backdrop-blur', 'course'],
});
