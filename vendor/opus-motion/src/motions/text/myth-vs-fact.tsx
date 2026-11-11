import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {fonts} from '../../core/fonts';
import {backOut, easeIO, easeOut3, mixHex, sseg, withAlpha} from '../../core/r2-s1-kit';
import {fitText, inkOn} from '../../core/r3-explain';
import {useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * Myth card drops in, a big red FALSE stamp slams on it (card shudders), then the card flips over to reveal the
 * fact card with a TRUE tick. Any statement pair works.
 */
type Props = {
  myth: string;
  fact: string;
  mythLabel: string;
  factLabel: string;
  stampText: string;
  factStamp: string;
  background: string;
  ink: string;
  accent: string;
  accent2: string;
  card: string;
  fontFamily: string;
  startAt: number;
  hold: number;
  speed: number;
};

const MythVsFact: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const {w, h, u, portrait} = useStage();
  const f = Math.max(0, frame - p.startAt) * (p.speed || 1);
  const font = p.fontFamily || fonts.grotesk;
  const cw = portrait ? w * 0.88 : Math.min(w * 0.72, 1220 * u);
  const ch = portrait ? Math.min(h * 0.52, 1020 * u) : Math.min(h * 0.74, 700 * u);
  const pad = 54 * u;
  const labelH = 92 * u;
  const bodyW = cw - pad * 2;
  const bodyH = ch - labelH - pad * 1.5;
  const maxFs = (portrait ? 70 : 62) * u;
  const mythFit = fitText(`“${p.myth}”`, bodyW, bodyH, maxFs, 26 * u);
  const factFit = fitText(p.fact, bodyW, bodyH, maxFs, 26 * u);

  const inT = easeOut3(sseg(f, 0, 24));
  const stampAt = 24 + Math.max(0, p.hold);
  const flipAt = stampAt + 36;
  const stampK = sseg(f, stampAt, stampAt + 7);
  const stampScale = f < stampAt ? 3 : stampK < 1 ? 3 - 2 * stampK * stampK : 1 + 0.12 * Math.exp(-(f - stampAt - 7) * 0.35) * Math.cos((f - stampAt - 7) * 0.9);
  const shake = f >= stampAt + 6 && f < stampAt + 18 ? Math.sin((f - stampAt) * 3.2) * 9 * u * (1 - sseg(f, stampAt + 6, stampAt + 18)) : 0;
  const flip = easeIO(sseg(f, flipAt, flipAt + 28));
  const angle = 180 * flip;
  const lift = Math.sin(Math.PI * flip) * 0.07;
  const enterY = (1 - inT) * -h * 0.5;
  const tick = backOut(sseg(f, flipAt + 22, flipAt + 40), 2.2);
  const factIn = easeOut3(sseg(f, flipAt + 14, flipAt + 40));
  const glow = withAlpha(angle > 90 ? p.accent : p.accent2, 0.22);
  const showBg = p.background !== 'transparent';

  const face: React.CSSProperties = {
    position: 'absolute',
    inset: 0,
    borderRadius: 34 * u,
    background: p.card,
    backfaceVisibility: 'hidden',
    WebkitBackfaceVisibility: 'hidden',
    boxShadow: `0 ${24 * u}px ${70 * u}px rgba(0,0,0,0.28)`,
    overflow: 'hidden',
  };
  const pill = (c: string, t: string) => (
    <div style={{position: 'absolute', left: pad, top: pad * 0.8, height: labelH * 0.62, padding: `0 ${26 * u}px`, borderRadius: 999, background: c, color: inkOn(c), fontFamily: fonts.display, fontSize: 34 * u, letterSpacing: 5 * u, display: 'flex', alignItems: 'center'}}>
      {t}
    </div>
  );

  return (
    <AbsoluteFill style={{background: showBg ? p.background : undefined}}>
      {showBg ? <AbsoluteFill style={{background: `radial-gradient(circle at 50% 50%, ${glow} 0%, transparent ${portrait ? 70 : 52}%)`}} /> : null}
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', perspective: 2400 * u}}>
        <div style={{width: cw, height: ch, position: 'relative', transform: `translate(${shake}px, ${enterY}px) rotate(${(1 - inT) * -6}deg) scale(${1 + lift})`, transformStyle: 'preserve-3d', opacity: inT}}>
          <div style={{...face, transform: `rotateY(${angle}deg)`}}>
            {pill(p.accent2, p.mythLabel)}
            <div style={{position: 'absolute', left: pad, top: labelH + pad * 0.5, width: bodyW, height: bodyH, display: 'flex', alignItems: 'center'}}>
              <div style={{fontFamily: font, fontWeight: 700, fontSize: mythFit.fs, lineHeight: mythFit.lh, color: p.ink}}>{mythFit.lines.join(' ')}</div>
            </div>
            {f >= stampAt ? (
              <div style={{position: 'absolute', right: pad * 0.6, bottom: pad * 1.0, transform: `rotate(-11deg) scale(${stampScale})`, transformOrigin: '50% 50%'}}>
                <div style={{border: `${10 * u}px solid ${p.accent2}`, borderRadius: 18 * u, padding: `${6 * u}px ${34 * u}px`, color: p.accent2, fontFamily: fonts.display, fontSize: (portrait ? 108 : 112) * u, letterSpacing: 6 * u, lineHeight: 1.1, background: withAlpha(p.card, 0.55)}}>
                  {p.stampText}
                </div>
              </div>
            ) : null}
          </div>
          <div style={{...face, transform: `rotateY(${angle + 180}deg)`, background: mixHex(p.card, p.accent, 0.07), border: `${6 * u}px solid ${p.accent}`}}>
            {pill(p.accent, p.factLabel)}
            <div style={{position: 'absolute', right: pad * 0.8, top: pad * 0.6, width: labelH * 0.8, height: labelH * 0.8, borderRadius: '50%', background: p.accent, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${Math.max(0.001, tick)})`}}>
              <svg width={labelH * 0.5} height={labelH * 0.5} viewBox="0 0 24 24">
                <path d="M4 12.5l5 5L20 6.5" fill="none" stroke={inkOn(p.accent)} strokeWidth={3.4} strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div style={{position: 'absolute', left: pad, top: labelH + pad * 0.5, width: bodyW, height: bodyH, display: 'flex', alignItems: 'center', opacity: factIn}}>
              <div style={{fontFamily: font, fontWeight: 700, fontSize: factFit.fs, lineHeight: factFit.lh, color: p.ink}}>{factFit.lines.join(' ')}</div>
            </div>
            <div style={{position: 'absolute', right: pad, bottom: pad * 0.6, fontFamily: fonts.display, fontSize: 30 * u, letterSpacing: 6 * u, color: p.accent, opacity: factIn}}>{p.factStamp}</div>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const mythVsFact = defineMotion<Props>({
  id: 'myth-vs-fact',
  title: 'Myth vs fact',
  category: 'text',
  description: 'A MYTH card drops in, a red FALSE stamp slams across it and shakes the card, then the card flips in 3D to a FACT card with a green tick.',
  source: ['original (round 3)'],
  useFor: 'Myth-busting beats, misconception explainers, health / science / finance "common belief vs reality" shorts, quiz answers — pass your own myth and fact.',
  durationInFrames: 180,
  defaultProps: {
    myth: 'We only use 10% of our brains.',
    fact: 'Brain scans show that nearly every region is active over the course of a day.',
    mythLabel: 'MYTH',
    factLabel: 'FACT',
    stampText: 'FALSE',
    factStamp: 'VERIFIED',
    background: '#16181F',
    ink: '#1A1A22',
    accent: '#1FA971',
    accent2: '#E5412D',
    card: '#FBF7EE',
    fontFamily: '',
    startAt: 0,
    hold: 40,
    speed: 1,
  },
  propDocs: {
    myth: 'the false claim (shown in quotes on the front card)',
    fact: 'the correct statement (back of the card)',
    mythLabel: 'pill on the myth card',
    factLabel: 'pill on the fact card',
    stampText: 'word stamped across the myth (FALSE, BUSTED, WRONG...)',
    factStamp: 'small caption at the bottom of the fact card',
    background: "backdrop colour or 'transparent'",
    ink: 'statement text colour',
    accent: 'fact colour (tick, border, pill)',
    accent2: 'myth colour (stamp, pill)',
    card: 'card face colour',
    fontFamily: 'optional CSS font-family for the statements (empty = grotesk)',
    startAt: 'frame the card starts dropping in',
    hold: 'frames the myth is read before the stamp lands',
    speed: 'playback speed multiplier',
  },
  component: MythVsFact,
  tags: ['myth', 'fact', 'misconception', 'false', 'true', 'stamp', 'flip', 'card', 'debunk', 'education', 'explainer', 'vs'],
});
