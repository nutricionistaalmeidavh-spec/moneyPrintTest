import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {clamp, lerp} from '../../core/ease';
import {backOut, eio3, eo3, estWidth, fitSize, lf, seg, wrapText} from '../../core/r3-news-kit';
import {useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * Full-screen "BREAKING NEWS" takeover: white flash, accent panel wipes across and the label slams in with a shake,
 * then the panel contracts to a top band while the headline wipes in line by line, the sub-line fades up and a
 * ticker slides in along the bottom. Channel name is a prop (no real outlets).
 */
type Props = {
  label: string;
  channel: string;
  headline: string;
  subhead: string;
  ticker: string[];
  tickerTag: string;
  accent: string;
  ink: string;
  background: string;
  slamHold: number;
  startAt: number;
  speed: number;
  live: boolean;
};

const BreakingNews: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const {w, h, u, portrait} = useStage();
  const f = frame - p.startAt;
  const transparentBg = p.background === 'transparent';

  const pad = w * (portrait ? 0.06 : 0.05);
  const bH = h * (portrait ? 0.085 : 0.135);
  const tH = h * (portrait ? 0.05 : 0.085);

  // ---- slam timeline
  const flash = 1 - seg(f, 0, 7);
  const wipe = eo3(seg(f, 1, 10));
  const slamT = seg(f, 6, 18);
  const hold0 = 18 + Math.max(0, p.slamHold);
  const e = eio3(seg(f, hold0, hold0 + 22));
  const panelH = lerp(h, bH, e);
  const shakeK = f > 8 && f < 22 ? 1 - seg(f, 8, 22) : 0;
  const shx = Math.sin(f * 2.9) * 16 * u * shakeK;
  const shy = Math.cos(f * 3.7) * 10 * u * shakeK;

  // ---- label sizes
  const label = (p.label || 'BREAKING NEWS').toUpperCase();
  const words = label.split(/\s+/);
  const bigLines = portrait && words.length > 1 ? words : [label];
  const WK = 1.14; // Archivo Black runs wider than the generic display estimate
  const fsBig = Math.min(...bigLines.map((l) => fitSize(l, h * (portrait ? 0.14 : 0.2), (w * 0.86) / WK, 'display', 0.02)));
  const fsBand = fitSize(label, bH * 0.5, (w * (portrait ? 0.62 : 0.5)) / WK, 'display', 0.02);
  const slamScale = lerp(2.2, 1, backOut(slamT, 1.1));

  const bigBlockH = bigLines.length * fsBig * 1.02;
  const landscapeFs = lerp(fsBig, fsBand, e);
  const landscapeW = estWidth(label, landscapeFs, 'display', 0.02) * WK;
  const lx = lerp((w - landscapeW) / 2, pad, e);
  const lcy = lerp(h / 2, bH / 2, e);

  // ---- body timeline
  const bodyAt = hold0 + 10;
  const headSize0 = portrait ? w * 0.098 : h * 0.098;
  const maxW = w - pad * 2 - 26 * u;
  let headSize = headSize0;
  let lines = wrapText(p.headline, headSize, maxW, 'sans', 5);
  while (lines.length > (portrait ? 5 : 3) && headSize > 28 * u) {
    headSize *= 0.92;
    lines = wrapText(p.headline, headSize, maxW, 'sans', 5);
  }
  const lineH = headSize * 1.12;
  const headH = lines.length * lineH;
  const barK = eo3(seg(f, bodyAt - 2, bodyAt + 16));
  const subSize = portrait ? w * 0.04 : h * 0.036;
  const subK = eo3(seg(f, bodyAt + 12 + lines.length * 6, bodyAt + 28 + lines.length * 6));
  const subLines = wrapText(p.subhead, subSize, maxW, 'sans', 3);
  const blockH = headH + (subLines.length ? subSize * 1.4 * subLines.length + 18 * u : 0);
  const headTop = bH + Math.max(h * 0.03, (h - bH - tH - blockH) * 0.45);

  // ---- ticker
  const tIn = eo3(seg(f, bodyAt + 4, bodyAt + 22));
  const ts = tH * 0.42;
  const items = (p.ticker && p.ticker.length ? p.ticker : ['']).filter((t) => t !== undefined);
  const gap = ts * 2.2;
  const widths = items.map((t) => estWidth(t, ts, 'sans', 0.01) * 1.07 + gap);
  const loopW = Math.max(1, widths.reduce((a, b) => a + b, 0));
  const tagW = estWidth((p.tickerTag || '').toUpperCase(), ts * 0.9, 'sans', 0.08) + ts * 1.8;
  const scroll = (Math.max(0, f - bodyAt) * 3.2 * p.speed * u) % loopW;
  const reps = Math.ceil((w - tagW) / loopW) + 2;

  const bgGlowX = 50 + Math.sin(f * 0.018) * 18;

  return (
    <AbsoluteFill style={{background: transparentBg ? 'transparent' : p.background, overflow: 'hidden'}}>
      {!transparentBg && (
        <AbsoluteFill
          style={{
            background: `radial-gradient(ellipse at ${bgGlowX}% 30%, rgba(255,255,255,0.09) 0%, rgba(255,255,255,0) 60%)`,
            opacity: 0.9,
          }}
        />
      )}
      {!transparentBg && (
        <AbsoluteFill style={{backgroundImage: `repeating-linear-gradient(115deg, rgba(255,255,255,0.025) 0 ${22 * u}px, rgba(255,255,255,0) ${22 * u}px ${44 * u}px)`}} />
      )}

      {f >= 0 && (
        <>
          {/* headline block */}
          <div style={{position: 'absolute', left: pad, top: headTop, width: maxW + 26 * u}}>
            <div style={{position: 'absolute', left: 0, top: 0, width: 10 * u, height: (headH + (subLines.length ? subSize * 1.5 * subLines.length + 18 * u : 0)) * barK, background: p.accent}} />
            <div style={{paddingLeft: 26 * u}}>
              {lines.map((l, i) => {
                const k = eo3(seg(f, bodyAt + i * 6, bodyAt + 16 + i * 6));
                return (
                  <div key={i} style={{height: lineH, overflow: 'hidden'}}>
                    <div
                      style={{
                        fontFamily: lf.sans,
                        fontWeight: 800,
                        fontSize: headSize,
                        lineHeight: `${lineH}px`,
                        color: p.ink,
                        whiteSpace: 'nowrap',
                        transform: `translateY(${(1 - k) * 100}%)`,
                        opacity: clamp(k * 3),
                        letterSpacing: -headSize * 0.012,
                      }}
                    >
                      {l}
                    </div>
                  </div>
                );
              })}
              <div style={{marginTop: 18 * u, opacity: subK, transform: `translateY(${(1 - subK) * 14 * u}px)`}}>
                {subLines.map((l, i) => (
                  <div key={i} style={{fontFamily: lf.sans, fontWeight: 400, fontSize: subSize, lineHeight: 1.4, color: p.ink, opacity: 0.78}}>
                    {l}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* ticker */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              bottom: 0,
              width: w,
              height: tH,
              transform: `translateY(${(1 - tIn) * 110}%)`,
              background: '#F6F5F1',
              overflow: 'hidden',
              boxShadow: `0 -${6 * u}px ${24 * u}px rgba(0,0,0,0.35)`,
            }}
          >
            <div style={{position: 'absolute', left: tagW, top: 0, width: w - tagW, height: '100%', overflow: 'hidden'}}>
              <div style={{position: 'absolute', left: -scroll, top: 0, height: '100%', display: 'flex', alignItems: 'center'}}>
                {Array.from({length: reps}).flatMap((_, r) =>
                  items.map((t, i) => (
                    <div key={`${r}-${i}`} style={{width: widths[i], display: 'flex', alignItems: 'center', flex: '0 0 auto'}}>
                      <span style={{fontFamily: lf.sans, fontWeight: 600, fontSize: ts, color: '#14171C', whiteSpace: 'nowrap'}}>{t}</span>
                      <span style={{marginLeft: 'auto', marginRight: gap * 0.38, width: ts * 0.38, height: ts * 0.38, background: p.accent, transform: 'rotate(45deg)'}} />
                    </div>
                  )),
                )}
              </div>
            </div>
            <div style={{position: 'absolute', left: 0, top: 0, width: tagW, height: '100%', background: p.accent, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
              <span style={{fontFamily: lf.sans, fontWeight: 800, fontSize: ts * 0.9, letterSpacing: ts * 0.08, color: '#FFFFFF'}}>{(p.tickerTag || '').toUpperCase()}</span>
            </div>
          </div>

          {/* accent panel (full-screen slam -> top band) */}
          <div style={{position: 'absolute', left: 0, top: 0, width: w * wipe, height: panelH, background: p.accent, overflow: 'hidden', boxShadow: e > 0.9 ? `0 ${6 * u}px ${24 * u}px rgba(0,0,0,0.35)` : 'none'}}>
            <AbsoluteFill style={{backgroundImage: `repeating-linear-gradient(115deg, rgba(0,0,0,0.12) 0 ${30 * u}px, rgba(0,0,0,0) ${30 * u}px ${60 * u}px)`, opacity: 1 - e}} />
            {!portrait && (
              <div
                style={{
                  position: 'absolute',
                  left: lx + shx,
                  top: lcy + shy,
                  transform: `translateY(-50%) scale(${lerp(slamScale, 1, e)})`,
                  transformOrigin: `${landscapeW / 2}px 50%`,
                  opacity: clamp(slamT * 4),
                  fontFamily: lf.display,
                  fontSize: landscapeFs,
                  letterSpacing: landscapeFs * 0.02,
                  lineHeight: 1,
                  color: '#FFFFFF',
                  whiteSpace: 'nowrap',
                  textShadow: e < 0.5 ? `0 ${8 * u}px 0 rgba(0,0,0,0.22)` : 'none',
                }}
              >
                {label}
              </div>
            )}
            {portrait && (
              <>
                <div
                  style={{
                    position: 'absolute',
                    left: 0,
                    width: w,
                    top: h / 2 + shy,
                    transform: `translate(${shx}px, -50%) scale(${slamScale})`,
                    textAlign: 'center',
                    opacity: clamp(slamT * 4) * (1 - seg(e, 0, 0.45)),
                    fontFamily: lf.display,
                    fontSize: fsBig,
                    lineHeight: 1.02,
                    height: bigBlockH,
                    color: '#FFFFFF',
                    textShadow: `0 ${8 * u}px 0 rgba(0,0,0,0.22)`,
                  }}
                >
                  {bigLines.map((l, i) => (
                    <div key={i}>{l}</div>
                  ))}
                </div>
                <div
                  style={{
                    position: 'absolute',
                    left: pad,
                    top: bH / 2,
                    transform: 'translateY(-50%)',
                    opacity: seg(e, 0.55, 1),
                    fontFamily: lf.display,
                    fontSize: fsBand,
                    letterSpacing: fsBand * 0.02,
                    lineHeight: 1,
                    color: '#FFFFFF',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {label}
                </div>
              </>
            )}
            {/* channel + live pill (band) */}
            <div style={{position: 'absolute', right: pad, top: bH / 2, transform: 'translateY(-50%)', display: 'flex', alignItems: 'center', gap: bH * 0.14, opacity: seg(e, 0.7, 1)}}>
              {p.live && (
                <div style={{display: 'flex', alignItems: 'center', gap: bH * 0.07, background: 'rgba(0,0,0,0.28)', padding: `${bH * 0.07}px ${bH * 0.16}px`, borderRadius: bH * 0.08}}>
                  <div style={{width: bH * 0.1, height: bH * 0.1, borderRadius: '50%', background: '#fff', opacity: 0.55 + 0.45 * Math.abs(Math.sin(f * 0.11))}} />
                  <span style={{fontFamily: lf.sans, fontWeight: 800, fontSize: bH * 0.2, letterSpacing: bH * 0.02, color: '#fff'}}>LIVE</span>
                </div>
              )}
              {!portrait && <span style={{fontFamily: lf.sans, fontWeight: 800, fontSize: bH * 0.27, letterSpacing: bH * 0.025, color: '#fff'}}>{(p.channel || '').toUpperCase()}</span>}
            </div>
          </div>

          {/* channel line under the band in portrait */}
          {portrait && (
            <div style={{position: 'absolute', left: pad, top: bH + 14 * u, opacity: seg(e, 0.8, 1), fontFamily: lf.sans, fontWeight: 800, fontSize: w * 0.032, letterSpacing: w * 0.004, color: p.ink}}>
              {(p.channel || '').toUpperCase()}
            </div>
          )}

          {/* white flash */}
          <AbsoluteFill style={{background: '#fff', opacity: flash * flash, pointerEvents: 'none'}} />
        </>
      )}
    </AbsoluteFill>
  );
};

export const breakingNewsTakeover = defineMotion<Props>({
  id: 'breaking-news-takeover',
  title: 'Breaking news takeover',
  category: 'hud',
  description:
    'A full-screen "BREAKING NEWS" slam: white flash, an accent panel wipes across and the label crashes in with a shake, then contracts to a top band while the headline wipes in line by line, a sub-line fades up and a ticker scrolls along the bottom. Generic channel name; set background to "transparent" to lay it over footage.',
  source: ['library original (broadcast news takeover pattern)'],
  useFor: 'Urgent news beats, alert announcements, "just in" updates, product-incident or outage notices, news-style explainers and parody bulletins.',
  durationInFrames: 210,
  defaultProps: {
    label: 'BREAKING NEWS',
    channel: 'Northwind News',
    headline: 'City council approves new harbour crossing after overnight vote',
    subhead: 'Construction is expected to begin next spring, officials said.',
    ticker: ['Markets open higher after a quiet start', 'Heavy rain expected across the coast tonight', 'Regional rail service resumes after maintenance', 'Library extends opening hours for exam season'],
    tickerTag: 'LATEST',
    accent: '#D81E27',
    ink: '#FFFFFF',
    background: '#0B1220',
    slamHold: 22,
    startAt: 0,
    speed: 1,
    live: true,
  },
  propDocs: {
    label: 'the slam word(s), e.g. "BREAKING NEWS", "JUST IN", "ALERT"',
    channel: 'channel / programme name shown in the band (generic sample, replace)',
    headline: 'main headline (wraps to 3 lines in 16:9, 5 in portrait)',
    subhead: 'one or two supporting sentences under the headline (empty = none)',
    ticker: 'ticker items scrolling along the bottom',
    tickerTag: 'text of the accent tab at the left of the ticker',
    accent: 'slam panel / band / ticker tab colour',
    ink: 'headline colour',
    background: 'backdrop colour behind the headline; "transparent" = overlay on other footage',
    slamHold: 'extra frames the full-screen label holds before it contracts to the band',
    startAt: 'frame the flash fires (shift the whole beat)',
    speed: 'ticker scroll speed multiplier',
    live: 'show the pulsing LIVE pill in the band',
  },
  component: BreakingNews,
  tags: ['news', 'breaking', 'takeover', 'headline', 'ticker', 'alert', 'bulletin', 'broadcast', 'slam', 'urgent', 'just in', 'overlay', 'journalism', 'live'],
});

