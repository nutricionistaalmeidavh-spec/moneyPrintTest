import React from 'react';
import {AbsoluteFill, Img, useCurrentFrame} from 'remotion';
import {clamp, lerp} from '../../core/ease';
import {resolveSrc} from '../../core/asset';
import {alpha, eio3, eo3, estWidth, lf, on, seg, wrapText} from '../../core/r3-news-kit';
import {useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

/**
 * A document page (procedural, or your own page image) sits on a dark desk; the camera zooms in on one paragraph,
 * the rest of the page dims, a highlighter sweeps over the key phrase and a SOURCE label slides in lower-left.
 */
type Props = {
  pageSrc: string;
  org: string;
  title: string;
  meta: string;
  paragraphs: string[];
  focusParagraph: number;
  highlightText: string;
  region: number[];
  source: string;
  sourceTag: string;
  highlightColor: string;
  accent: string;
  ink: string;
  paper: string;
  desk: string;
  tilt: number;
  fill: number;
  zoomAt: number;
  markAt: number;
  speed: number;
};

const PW = 1000;
const MARGIN = 96;
const COL = PW - MARGIN * 2;
const SIZE = 26;
const LH = 42;

type PLine = {x: number; y: number; w: number; text: string; start: number; end: number; last: boolean};
type Para = {lines: PLine[]; y0: number; y1: number; text: string};

const layoutPage = (paragraphs: string[]) => {
  let y = 372;
  const paras: Para[] = paragraphs.map((raw) => {
    const text = (raw || '').replace(/\s+/g, ' ').trim();
    const wrapped = wrapText(text, SIZE, COL, 'serif');
    let cursor = 0;
    const lines: PLine[] = wrapped.map((l, i) => {
      const at = text.indexOf(l.replace(/…$/, ''), cursor);
      const start = at < 0 ? cursor : at;
      const end = start + l.length;
      cursor = end;
      const last = i === wrapped.length - 1;
      const est = estWidth(l, SIZE, 'serif');
      const line: PLine = {x: MARGIN, y: y + i * LH, w: last ? Math.min(COL, Math.max(est * 1.08, 120)) : COL, text: l, start, end, last};
      return line;
    });
    const y0 = y - SIZE * 0.86;
    const y1 = y + (lines.length - 1) * LH + SIZE * 0.32;
    y += lines.length * LH + 28;
    return {lines, y0, y1, text};
  });
  const H = Math.max(1294, y + 150);
  return {paras, H};
};

const DocZoom: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const {w, h, u, portrait} = useStage();
  const f = frame * (p.speed || 1);

  const {paras, H} = React.useMemo(() => layoutPage(p.paragraphs && p.paragraphs.length ? p.paragraphs : ['']), [p.paragraphs]);
  const fi = clamp(Math.round(p.focusParagraph), 0, paras.length - 1);
  const fp = paras[fi];
  const useImg = on(p.pageSrc);

  // ---- focus region in page units
  const rg = p.region && p.region.length >= 4 ? p.region : [0.1, 0.4, 0.8, 0.14];
  const reg = useImg ? {x0: rg[0] * PW, y0: rg[1] * H, x1: (rg[0] + rg[2]) * PW, y1: (rg[1] + rg[3]) * H} : {x0: MARGIN - 14, y0: fp.y0 - 8, x1: PW - MARGIN + 14, y1: fp.y1 + 8};
  const rcx = (reg.x0 + reg.x1) / 2;
  const rcy = (reg.y0 + reg.y1) / 2;

  // ---- highlight strips (page units)
  const strips: {x: number; y: number; w: number; h: number}[] = [];
  if (useImg) {
    const rows = Math.max(1, Math.round((reg.y1 - reg.y0) / 40));
    for (let i = 0; i < rows; i++) strips.push({x: reg.x0, y: reg.y0 + ((reg.y1 - reg.y0) * i) / rows, w: reg.x1 - reg.x0, h: (reg.y1 - reg.y0) / rows});
  } else {
    const phrase = on(p.highlightText) ? fp.text.indexOf(p.highlightText) : -1;
    const hs = phrase >= 0 ? phrase : 0;
    const he = phrase >= 0 ? phrase + p.highlightText.length : fp.text.length;
    for (const l of fp.lines) {
      const a = Math.max(hs, l.start);
      const b = Math.min(he, l.end);
      if (b <= a) continue;
      const n = Math.max(1, l.end - l.start);
      const x0 = l.x + (l.w * (a - l.start)) / n;
      const x1 = l.x + (l.w * (b - l.start)) / n;
      strips.push({x: x0 - 4, y: l.y - SIZE * 0.86, w: x1 - x0 + 8, h: SIZE * 1.22});
    }
  }

  // ---- camera
  const k0 = portrait ? (w * 0.72) / PW : (h * 0.88) / H;
  const regW = reg.x1 - reg.x0;
  const k1 = Math.min((w * (portrait ? Math.max(p.fill, 0.88) : p.fill)) / regW, (h * 0.8) / Math.max(1, reg.y1 - reg.y0));
  const t = eio3(seg(f, p.zoomAt, p.zoomAt + 42));
  const drift = 1 + 0.035 * seg(f, p.zoomAt + 42, p.zoomAt + 190);
  const S = lerp(k0, k1, t) * drift;
  const fx = lerp(PW / 2, rcx, t);
  const fy = lerp(H / 2, rcy, t);
  const sx = w / 2;
  const sy = lerp(h / 2, h * (portrait ? 0.43 : 0.45), t);
  const rot = p.tilt * (1 - t);
  const intro = eo3(seg(f, 0, 18));
  const dim = eo3(seg(f, p.zoomAt + 12, p.zoomAt + 44));

  const pageTransform = `translate(${sx}px, ${sy}px) rotate(${rot}deg) scale(${S}) translate(${-fx}px, ${-fy}px)`;

  // ---- label
  const labK = eo3(seg(f, p.markAt + 24, p.markAt + 42));
  const lfs = (portrait ? w : h) * (portrait ? 0.03 : 0.03);
  const vg = 0.35 + 0.35 * t;

  return (
    <AbsoluteFill style={{background: p.desk === 'transparent' ? 'transparent' : `radial-gradient(ellipse at 50% 40%, ${alpha('#FFFFFF', 0.06)} 0%, rgba(0,0,0,0) 65%), ${p.desk}`, overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: PW, height: H, transformOrigin: '0 0', transform: pageTransform, opacity: intro}}>
        <div style={{position: 'absolute', left: 14, top: 22, width: PW, height: H, background: 'rgba(0,0,0,0.45)', filter: 'blur(26px)'}} />
        <div style={{position: 'absolute', left: 0, top: 0, width: PW, height: H, background: `linear-gradient(135deg, ${p.paper} 0%, ${alpha('#E9E2D0', 1)} 100%)`}} />
        {useImg && <Img src={resolveSrc(p.pageSrc)} style={{position: 'absolute', left: 0, top: 0, width: PW, height: H, objectFit: 'cover'}} />}
        <svg width={PW} height={H} viewBox={`0 0 ${PW} ${H}`} style={{position: 'absolute', left: 0, top: 0}}>
          {!useImg && (
            <g>
              <text x={MARGIN} y={140} fontFamily={lf.plex} fontSize={19} letterSpacing={4} fill="#5d5f63" opacity={1 - 0.6 * dim}>
                {(p.org || '').toUpperCase()}
              </text>
              <rect x={MARGIN} y={158} width={COL} height={2.5} fill={p.ink} opacity={0.75 * (1 - 0.6 * dim)} />
              <text x={MARGIN} y={236} fontFamily={lf.text} fontWeight={600} fontSize={50} fill={p.ink} opacity={1 - 0.6 * dim}>
                {p.title}
              </text>
              <text x={MARGIN} y={284} fontFamily={lf.plex} fontSize={17} fill="#5d5f63" opacity={1 - 0.6 * dim}>
                {p.meta}
              </text>
              {paras.map((pa, pi) =>
                pa.lines.map((l, li) => (
                  <text key={`${pi}-${li}`} x={l.x} y={l.y} fontFamily={lf.text} fontSize={SIZE} fill={p.ink} opacity={pi === fi ? 1 : 1 - 0.68 * dim} textLength={l.w} lengthAdjust="spacing">
                    {l.text}
                  </text>
                )),
              )}
              {[0, 1, 2].map((k) => (
                <rect key={k} x={MARGIN} y={H - 250 + k * 30} width={COL * [0.92, 0.84, 0.5][k]} height={9} rx={4} fill="#5d5f63" opacity={0.16 * (1 - 0.6 * dim)} />
              ))}
            </g>
          )}
          {/* margin bar beside the focus paragraph */}
          <rect x={MARGIN - 30} y={reg.y0 + 4} width={6} height={(reg.y1 - reg.y0 - 8) * eo3(seg(f, p.zoomAt + 30, p.zoomAt + 56))} fill={p.accent} rx={3} />
          {/* highlighter */}
          {strips.map((s, i) => {
            const stag = Math.min(9, 34 / Math.max(1, strips.length));
            const k = eo3(seg(f, p.markAt + i * stag, p.markAt + i * stag + 15));
            const wob = Math.sin(i * 2.3) * 1.4;
            return <rect key={i} x={s.x} y={s.y + wob} width={s.w * k} height={s.h} rx={s.h * 0.2} fill={p.highlightColor} opacity={0.9} style={{mixBlendMode: 'multiply'}} />;
          })}
        </svg>
      </div>

      <AbsoluteFill style={{pointerEvents: 'none', background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,${vg}) 100%)`}} />

      {on(p.source) && (
        <div
          style={{
            position: 'absolute',
            left: w * (portrait ? 0.05 : 0.045),
            bottom: h * (portrait ? 0.07 : 0.07),
            maxWidth: w * 0.9,
            display: 'flex',
            alignItems: 'stretch',
            opacity: clamp(labK * 1.6),
            transform: `translateX(${(1 - labK) * -50 * u}px)`,
            boxShadow: `0 ${8 * u}px ${26 * u}px rgba(0,0,0,0.45)`,
          }}
        >
          <div style={{background: p.accent, color: '#fff', fontFamily: lf.sans, fontWeight: 800, fontSize: lfs * 0.78, letterSpacing: lfs * 0.12, display: 'flex', alignItems: 'center', padding: `0 ${lfs * 0.8}px`}}>{(p.sourceTag || 'SOURCE').toUpperCase()}</div>
          <div style={{background: 'rgba(12,14,18,0.92)', color: '#F4F2EC', fontFamily: lf.sans, fontWeight: 600, fontSize: lfs, padding: `${lfs * 0.55}px ${lfs * 0.9}px`}}>{p.source}</div>
        </div>
      )}
    </AbsoluteFill>
  );
};

export const documentZoomHighlight = defineMotion<Props>({
  id: 'document-zoom-highlight',
  title: 'Document zoom + highlight',
  category: 'document',
  description:
    'A document page sits on a dark desk (procedural page, or your own page image); the camera zooms in on one paragraph while the rest of the page dims, a highlighter sweeps over the key phrase, and a SOURCE label slides in lower-left.',
  source: ['library original (document-journalism "this is what it says" shot)'],
  useFor: 'Quoting a report, contract, court filing, policy or press release on screen - "here is the line that matters" - with the source credited.',
  durationInFrames: 210,
  defaultProps: {
    pageSrc: '',
    org: 'Northwind Harbour Authority',
    title: 'Report on the New Crossing',
    meta: 'Ref. NH-2041 · Filed 14 March · Page 3 of 12',
    paragraphs: [
      'The survey team walked the full length of the channel on four separate mornings and recorded every reading by hand before checking it against the harbour charts held in the archive.',
      'The measured clear span required for safe passage is 1,208 metres, more than twice the distance the present structure can offer. A cable-stayed design meets this figure with room to spare and can be built while the existing crossing remains in service.',
      'Costs and timings are set out in the tables that follow, with every figure traced to its original source document.',
    ],
    focusParagraph: 1,
    highlightText: '1,208 metres, more than twice the distance the present structure can offer',
    region: [0.1, 0.4, 0.8, 0.14],
    source: 'Northwind Harbour Authority · Report NH-2041, p. 3',
    sourceTag: 'SOURCE',
    highlightColor: '#FFD43B',
    accent: '#C8282F',
    ink: '#16181B',
    paper: '#F5F1E6',
    desk: '#1B1E25',
    tilt: -3,
    fill: 0.62,
    zoomAt: 24,
    markAt: 82,
    speed: 1,
  },
  propDocs: {
    pageSrc: 'optional page image (public/ path or URL, ~1:1.29 portrait page); empty = procedural page',
    org: 'procedural page: organisation line at the top',
    title: 'procedural page: document title',
    meta: 'procedural page: reference / date / page line',
    paragraphs: 'procedural page: body paragraphs (strings)',
    focusParagraph: 'index (0-based) of the paragraph the camera zooms to',
    highlightText: 'exact phrase inside the focus paragraph to mark ("" = the whole paragraph)',
    region: 'with pageSrc: [x, y, width, height] of the area to zoom to and highlight, as 0-1 fractions of the page',
    source: 'source label text (publisher · document · page; empty = none)',
    sourceTag: 'word in the accent block of the label',
    highlightColor: 'highlighter colour (multiplied over the text)',
    accent: 'margin bar + label tab colour',
    ink: 'page text colour',
    paper: 'page paper colour',
    desk: 'desk colour behind the page; "transparent" = overlay',
    tilt: 'page tilt in degrees before the zoom',
    fill: 'fraction of the frame width the focused paragraph fills when zoomed (landscape)',
    zoomAt: 'frame the camera starts to zoom',
    markAt: 'frame the highlighter starts',
    speed: 'timing multiplier',
  },
  component: DocZoom,
  tags: ['document', 'zoom', 'highlight', 'highlighter', 'paragraph', 'report', 'quote', 'source', 'evidence', 'journalism', 'documentary', 'pdf', 'contract', 'filing', 'news'],
});
