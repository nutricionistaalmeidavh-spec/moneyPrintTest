import React from 'react';
import {AbsoluteFill, Img, useCurrentFrame} from 'remotion';
import {resolveSrc} from '../../core/asset';
import {fonts} from '../../core/fonts';
import {useSafeId} from '../../core/image-kit';
import {backOut, eo3, eo5, lum, mix, seg, withAlpha} from '../../core/r3-brand-kit';
import {Svg, useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * Outro / end screen: a headline, two video-card slots and a round "subscribe" circle with a rotating ring of text and pulsing
 * halos. Cards rise in one after the other (picture via `src`, otherwise a placeholder thumbnail), each with a thin timer bar
 * that runs while the screen is up; the circle pops and the supporting line fades in. Leave the card areas free of anything
 * else — they are where you place your platform's end-screen elements.
 */
type CardProp = {label: string; src: string};
type Props = {
  title: string;
  subtitle: string;
  cards: CardProp[];
  circleLabel: string;
  circleSrc: string;
  ringText: string;
  background: string;
  ink: string;
  accent: string;
  cardColor: string;
  timerBars: boolean;
  startAt: number;
  speed: number;
  fontFamily: string;
};

const Thumb: React.FC<{src: string; accent: string; ink: string; seed: number; u: number}> = ({src, accent, ink, seed, u}) => {
  if (src) return <Img src={resolveSrc(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />;
  const hue = seed % 2 ? 0.0 : 0.25;
  return (
    <div style={{position: 'absolute', inset: 0, background: `linear-gradient(${135 + seed * 50}deg, ${withAlpha(accent, 0.95 - hue)}, ${withAlpha(ink, 0.55)})`}}>
      <svg width="100%" height="100%" viewBox="0 0 160 90" preserveAspectRatio="xMidYMid slice" style={{position: 'absolute', inset: 0}}>
        <circle cx={seed % 2 ? 120 : 40} cy={30} r={34} fill="#fff" opacity={0.13} />
        <circle cx={seed % 2 ? 30 : 130} cy={80} r={26} fill="#fff" opacity={0.1} />
        <circle cx={80} cy={45} r={15} fill="#000" opacity={0.35} />
        <path d="M75 37 L90 45 L75 53 Z" fill="#fff" />
      </svg>
      <div style={{position: 'absolute', right: 8 * u, bottom: 8 * u, background: 'rgba(0,0,0,.7)', color: '#fff', fontFamily: fonts.sans, fontWeight: 600, fontSize: 15 * u, padding: `${2 * u}px ${6 * u}px`, borderRadius: 4 * u}}>
        {seed % 2 ? '12:08' : '8:42'}
      </div>
    </div>
  );
};

const EndScreenCards: React.FC<Props> = ({title, subtitle, cards, circleLabel, circleSrc, ringText, background, ink, accent, cardColor, timerBars, startAt, speed, fontFamily}) => {
  const frame = useCurrentFrame();
  const {w, h, u, cx, portrait, durationInFrames: D} = useStage();
  const uid = useSafeId('esc');
  const f = Math.max(0, (frame - startAt) * speed);
  const wide = w / h >= 1.4;
  const fam = fontFamily || fonts.sans;
  const cs = cards.slice(0, 2);
  const cardAr = 16 / 9;

  let cw: number, circleR: number;
  let circleC: [number, number];
  let cardPos: [number, number][]; // top-left
  let titleY: number;
  if (wide) {
    cw = Math.min(w * 0.3, h * 0.5 * cardAr);
    circleR = Math.min(h * 0.17, w * 0.085);
    const row = h * 0.52;
    const gap = 34 * u + circleR * 0.2;
    const total = cw * 2 + circleR * 2 + gap * 2;
    const x0 = (w - total) / 2;
    circleC = [x0 + cw + gap + circleR, row];
    cardPos = [[x0, row - cw / cardAr / 2], [x0 + cw + gap * 2 + circleR * 2, row - cw / cardAr / 2]];
    titleY = h * 0.15;
  } else if (portrait) {
    cw = w * 0.68;
    circleR = w * 0.16;
    circleC = [cx, h * 0.245];
    const ch = cw / cardAr;
    const y0 = h * 0.385;
    cardPos = [[(w - cw) / 2, y0], [(w - cw) / 2, y0 + ch + 76 * u]];
    titleY = h * 0.075;
  } else {
    cw = w * 0.4;
    circleR = h * 0.135;
    circleC = [cx, h * 0.335];
    cardPos = [[w * 0.08, h * 0.6], [w * 0.52, h * 0.6]];
    titleY = h * 0.1;
  }
  const ch = cw / cardAr;
  const bg = background === 'transparent' ? undefined : background;
  const dark = lum(background === 'transparent' ? '#000000' : background) < 0.5;
  const sub = withAlpha(ink, 0.68);

  const titleT = eo3(seg(f, 0, 20));
  const subT = eo3(seg(f, 74, 98));
  const circleT = backOut(seg(f, 18, 38), 2.2);
  const cardT = (i: number) => eo5(seg(f, 30 + i * 12, 58 + i * 12));
  const timer = (i: number) => seg(f, 62 + i * 12, D / Math.max(0.01, speed) - 8);
  const rot = f * 0.9;
  const R = circleR;
  const ringR = R * 1.2;
  const fsTitle = (portrait ? 74 : wide ? 64 : 58) * u;
  const labFs = (portrait ? 28 : 22) * u;
  const circ = (pct: number) => <circle cx={circleC[0]} cy={circleC[1]} r={mix(R * 1.02, R * 1.75, pct)} fill="none" stroke={accent} strokeWidth={3 * u} opacity={0.5 * (1 - pct) * circleT} />;
  const ph = (k: number) => ((f - 40) / 70 + k) % 1;

  return (
    <AbsoluteFill style={{background: bg, fontFamily: fam}}>
      <div style={{position: 'absolute', left: 0, right: 0, top: titleY, textAlign: 'center', transform: `translateY(${(1 - titleT) * 26 * u - fsTitle / 2}px)`, opacity: titleT, filter: titleT < 1 ? `blur(${(1 - titleT) * 8 * u}px)` : undefined, color: ink, fontWeight: 800, fontSize: fsTitle, letterSpacing: '-0.01em', padding: `0 ${w * 0.06}px`, lineHeight: 1.1}}>
        {title}
      </div>
      <Svg>
        <defs>
          <path id={`${uid}-ring`} d={`M ${circleC[0]} ${circleC[1] - ringR} a ${ringR} ${ringR} 0 1 1 -0.01 0`} />
        </defs>
        {f > 40 && [0, 1, 2].map((k) => circ(ph(k / 3)))}
        <g transform={`rotate(${rot} ${circleC[0]} ${circleC[1]})`} opacity={circleT}>
          <text fontFamily={fam} fontWeight={800} fontSize={R * 0.17} letterSpacing={R * 0.045} fill={ink} opacity={0.85}>
            <textPath href={`#${uid}-ring`}>{ringText}</textPath>
          </text>
        </g>
      </Svg>
      {/* subscribe circle */}
      <div
        style={{
          position: 'absolute',
          left: circleC[0] - R,
          top: circleC[1] - R,
          width: R * 2,
          height: R * 2,
          borderRadius: '50%',
          overflow: 'hidden',
          background: accent,
          transform: `scale(${circleT})`,
          boxShadow: `0 ${10 * u}px ${34 * u}px ${withAlpha(accent, 0.45)}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {circleSrc ? (
          <Img src={resolveSrc(circleSrc)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        ) : (
          <div style={{color: '#fff', fontWeight: 800, fontSize: R * 0.3, textAlign: 'center', lineHeight: 1.05, letterSpacing: '0.02em', padding: R * 0.2, textTransform: 'uppercase'}}>{circleLabel}</div>
        )}
      </div>
      {/* cards */}
      {cs.map((c, i) => {
        const t = cardT(i);
        const float = Math.sin(f * 0.05 + i * 1.7) * 3 * u * t;
        const [x, y] = cardPos[i];
        return (
          <div key={i} style={{position: 'absolute', left: x, top: y, width: cw, opacity: t, transform: `translateY(${(1 - t) * 90 * u + float}px) scale(${mix(0.94, 1, t)})`}}>
            <div style={{position: 'relative', width: cw, height: ch, borderRadius: 14 * u, overflow: 'hidden', background: cardColor, boxShadow: `0 ${14 * u}px ${40 * u}px rgba(0,0,0,${dark ? 0.5 : 0.22}), 0 0 0 ${2 * u}px ${withAlpha(ink, 0.14)}`}}>
              <Thumb src={c.src} accent={accent} ink={ink} seed={i} u={u} />
              {timerBars && <div style={{position: 'absolute', left: 0, bottom: 0, height: 5 * u, width: `${timer(i) * 100}%`, background: accent}} />}
            </div>
            {c.label && <div style={{marginTop: 14 * u, color: ink, fontWeight: 600, fontSize: labFs, opacity: 0.85, textAlign: 'center', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{c.label}</div>}
          </div>
        );
      })}
      {subtitle && (
        <div style={{position: 'absolute', left: 0, right: 0, bottom: h * (wide ? 0.07 : portrait ? 0.045 : 0.035), textAlign: 'center', color: sub, fontWeight: 600, fontSize: (portrait ? 34 : 28) * u, letterSpacing: '0.04em', opacity: subT, transform: `translateY(${(1 - subT) * 14 * u}px)`, padding: `0 ${w * 0.06}px`}}>
          {subtitle}
        </div>
      )}
    </AbsoluteFill>
  );
};

export const endScreenCards = defineMotion<Props>({
  id: 'end-screen-cards',
  title: 'End screen with video cards',
  category: 'text',
  description:
    'Outro screen: headline, two video-card slots (thumbnail or placeholder, label, running timer bar) and a round subscribe circle with a rotating ring of text and pulsing halos; everything rises in staggered, then a supporting line fades in. Lays out 3-across on 16:9 and stacks on 1:1 and 9:16.',
  source: ['original (branding pass, round 3)'],
  useFor: 'YouTube / social end screens, "watch next" outros and channel sign-offs; keep the card areas for the platform end-screen elements.',
  durationInFrames: 240,
  defaultProps: {
    title: 'Thanks for watching',
    subtitle: 'New videos every week',
    cards: [
      {label: 'Watch next', src: ''},
      {label: 'Most popular', src: ''},
    ],
    circleLabel: 'Subscribe',
    circleSrc: '',
    ringText: 'SUBSCRIBE · SUBSCRIBE · SUBSCRIBE · SUBSCRIBE · ',
    background: '#10131A',
    ink: '#F3F1EC',
    accent: '#FF4D4D',
    cardColor: '#1C2130',
    timerBars: true,
    startAt: 0,
    speed: 1,
    fontFamily: '',
  },
  propDocs: {
    title: 'big headline at the top',
    subtitle: 'supporting line at the bottom ("" = none)',
    cards: '[{label, src}] up to 2 video cards; src = thumbnail image (public/ path or URL), empty = placeholder',
    circleLabel: 'text inside the circle when no circleSrc is given',
    circleSrc: 'channel avatar / logo picture for the circle',
    ringText: 'text that rotates around the circle (repeat it to fill the ring)',
    background: 'backdrop colour, or "transparent" to place over footage',
    ink: 'text colour',
    accent: 'brand colour of the circle, halos and timer bars',
    cardColor: 'card background shown behind thumbnails',
    timerBars: 'show the running timer bar along the bottom of each card',
    startAt: 'frame the screen starts building',
    speed: 'timing multiplier',
    fontFamily: 'optional CSS font-family for all text',
  },
  component: EndScreenCards,
  tags: ['end screen', 'outro', 'endscreen', 'cards', 'subscribe', 'youtube', 'watch next', 'channel', 'call to action', 'thumbnails', 'video cards', 'sign-off', 'circle'],
});
