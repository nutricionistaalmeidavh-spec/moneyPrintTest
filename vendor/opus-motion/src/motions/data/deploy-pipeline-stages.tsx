import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {useStage} from '../../core/stage';
import {
  CheckDot,
  CrossDot,
  Spinner,
  backOut,
  bgOf,
  isDark,
  monoFont,
  onFill,
  outCubic,
  sansFont,
  seg,
  withAlpha,
} from '../../core/dev-explainer-kit';
import {defineMotion} from '../../core/types';

/**
 * A CI/CD pipeline: stage cards (build → test → scan → deploy) run in sequence — a spinner turns into a check
 * (or a red cross), sub-steps tick off one by one, a timer counts up and the connector between stages fills.
 * A failing stage stops the line and the remaining stages show as skipped. Ends on a success / failure banner.
 */
type Stage = {name: string; steps?: string[]; seconds?: number; result?: 'pass' | 'fail'};
type Props = {
  title: string;
  subtitle: string;
  stages: Stage[];
  successText: string;
  failText: string;
  stageFrames: number;
  speed: number;
  startAt: number;
  background: string;
  panel: string;
  ink: string;
  accent: string;
  okColor: string;
  errColor: string;
  fontFamily: string;
};

const mmss = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

const DeployPipelineStages: React.FC<Props> = (p) => {
  const frame = useCurrentFrame();
  const {w, h, u, portrait} = useStage();
  const t = (frame - p.startAt) * Math.max(0.1, p.speed);
  const mono = monoFont(p.fontFamily);
  const sans = sansFont('');
  const dark = isDark(p.background === 'transparent' ? '#101010' : p.background);
  const stages = p.stages.length ? p.stages : [{name: 'Build'}, {name: 'Deploy'}];
  const N = stages.length;
  const sf = Math.max(24, p.stageFrames);
  const T0 = 26;
  const rs = (i: number) => T0 + i * sf;
  const failIdx = stages.findIndex((s) => s.result === 'fail');
  const lastRun = failIdx >= 0 ? failIdx : N - 1; // last stage that actually runs
  const endT = rs(lastRun) + sf;

  type St = 'pending' | 'running' | 'pass' | 'fail' | 'skip';
  const stateOf = (i: number): St => {
    if (failIdx >= 0 && i > failIdx) return t >= endT ? 'skip' : 'pending';
    if (t < rs(i)) return 'pending';
    if (t < rs(i) + sf) return 'running';
    return i === failIdx ? 'fail' : 'pass';
  };

  // geometry
  const headH = (portrait ? 230 : 190) * u;
  const footH = (portrait ? 190 : 170) * u;
  const gap = (portrait ? 26 : 60) * u;
  const area = {x: w * (portrait ? 0.05 : 0.05), y: headH, w: w * (portrait ? 0.9 : 0.9), h: h - headH - footH};
  const cardW = portrait ? area.w : (area.w - gap * (N - 1)) / N;
  const cardH = portrait ? (area.h - gap * (N - 1)) / N : Math.min(area.h, 500 * u);
  const cardX = (i: number) => (portrait ? area.x : area.x + i * (cardW + gap));
  const cardY = (i: number) => (portrait ? area.y + i * (cardH + gap) : area.y + (area.h - cardH) / 2);

  const stateColor = (s: St) => (s === 'pass' ? p.okColor : s === 'fail' ? p.errColor : s === 'running' ? p.accent : withAlpha(p.ink, 0.35));
  const hIn = outCubic(seg(t, 0, 14));
  const overall: St = t >= endT ? (failIdx >= 0 ? 'fail' : 'pass') : t >= rs(0) ? 'running' : 'pending';
  const iconS = (portrait ? 62 : 54) * u;
  const stepFs = (portrait ? 26 : 23) * u;
  const nameFs = (portrait ? 42 : 38) * u;

  const renderIcon = (s: St, i: number, size: number) => {
    if (s === 'running') return <Spinner size={size} color={p.accent} frame={frame} stroke={size * 0.1} speed={13} />;
    if (s === 'pass') return <CheckDot size={size} color={p.okColor} k={seg(t, rs(i) + sf, rs(i) + sf + 12)} />;
    if (s === 'fail') return <CrossDot size={size} color={p.errColor} k={seg(t, rs(i) + sf, rs(i) + sf + 12)} />;
    if (s === 'skip') return (
      <svg width={size} height={size} viewBox="0 0 24 24"><circle cx={12} cy={12} r={10} fill="none" stroke={withAlpha(p.ink, 0.35)} strokeWidth={2} strokeDasharray="3 3" /><path d="M8 12 H16" stroke={withAlpha(p.ink, 0.45)} strokeWidth={2.2} strokeLinecap="round" /></svg>
    );
    return <svg width={size} height={size} viewBox="0 0 24 24"><circle cx={12} cy={12} r={10} fill="none" stroke={withAlpha(p.ink, 0.28)} strokeWidth={2} /></svg>;
  };

  return (
    <AbsoluteFill style={{background: bgOf(p.background), overflow: 'hidden'}}>
      {/* header */}
      <div style={{position: 'absolute', left: area.x, right: area.x, top: (portrait ? 84 : 52) * u, display: 'flex', justifyContent: 'space-between', opacity: hIn, transform: `translateY(${(1 - hIn) * -14 * u}px)`, flexDirection: 'row', gap: 18 * u, alignItems: 'center'}}>
        <div>
          <div style={{fontFamily: sans, fontWeight: 800, fontSize: (portrait ? 52 : 50) * u, color: p.ink, lineHeight: 1.1}}>{p.title}</div>
          {p.subtitle ? <div style={{fontFamily: mono, fontSize: (portrait ? 26 : 24) * u, color: withAlpha(p.ink, 0.55), marginTop: 8 * u}}>{p.subtitle}</div> : null}
        </div>
        <div style={{display: 'flex', alignItems: 'center', gap: 14 * u, padding: `${10 * u}px ${22 * u}px`, borderRadius: 999, background: withAlpha(stateColor(overall), 0.16), border: `${2 * u}px solid ${withAlpha(stateColor(overall), 0.6)}`, fontFamily: sans, fontWeight: 700, fontSize: 26 * u, color: p.ink}}>
          <div style={{width: 30 * u, height: 30 * u}}>{renderIcon(overall, lastRun, 30 * u)}</div>
          {overall === 'pending' ? 'Queued' : overall === 'running' ? 'Running' : overall === 'pass' ? 'Passed' : 'Failed'}
        </div>
      </div>
      {/* connectors */}
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} style={{position: 'absolute', inset: 0}}>
        {stages.slice(0, -1).map((_, i) => {
          const a = portrait ? {x: cardX(i) + cardW / 2, y: cardY(i) + cardH} : {x: cardX(i) + cardW, y: cardY(i) + cardH / 2};
          const b = portrait ? {x: cardX(i + 1) + cardW / 2, y: cardY(i + 1)} : {x: cardX(i + 1), y: cardY(i + 1) + cardH / 2};
          const k = stateOf(i) === 'pass' ? outCubic(seg(t, rs(i) + sf, rs(i) + sf + 14)) : 0;
          const shown = hIn;
          return (
            <g key={i} opacity={shown}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={withAlpha(p.ink, 0.18)} strokeWidth={5 * u} strokeLinecap="round" />
              <line x1={a.x} y1={a.y} x2={a.x + (b.x - a.x) * k} y2={a.y + (b.y - a.y) * k} stroke={p.okColor} strokeWidth={5 * u} strokeLinecap="round" />
            </g>
          );
        })}
      </svg>
      {/* stage cards */}
      {stages.map((s, i) => {
        const st = stateOf(i);
        const inK = backOut(seg(t, 4 + i * 4, 18 + i * 4), 1.6);
        const col = stateColor(st);
        const steps = s.steps ?? [];
        const m = Math.max(1, steps.length);
        const local = t - rs(i);
        const runK = st === 'running' ? seg(local, 0, sf) : st === 'pass' || st === 'fail' ? 1 : 0;
        const secTotal = s.seconds ?? 10 + ((i * 7) % 20);
        const timer = st === 'pending' ? '--:--' : st === 'skip' ? 'skipped' : mmss(secTotal * runK);
        const stepState = (j: number): St => {
          if (st === 'pending') return 'pending';
          if (st === 'skip') return 'skip';
          const startJ = (j / m) * sf;
          const endJ = ((j + 1) / m) * sf;
          if (st === 'pass' || (st === 'fail' && j < m - 1)) return local >= endJ - 1 || st === 'pass' ? 'pass' : local >= startJ ? 'running' : 'pending';
          if (st === 'fail') return 'fail';
          return local >= endJ ? 'pass' : local >= startJ ? 'running' : 'pending';
        };
        const pulse = st === 'running' ? 0.5 + 0.5 * Math.sin(frame * 0.25) : 0;
        const shake = st === 'fail' ? Math.max(0, 1 - seg(local, sf, sf + 14)) * Math.sin((local - sf) * 2.6) * 7 * u : 0;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: cardX(i) + shake,
              top: cardY(i),
              width: cardW,
              height: cardH,
              boxSizing: 'border-box',
              opacity: Math.min(1, inK) * (st === 'skip' ? 0.55 : 1),
              transform: `scale(${0.85 + 0.15 * inK})`,
              borderRadius: 26 * u,
              background: p.panel,
              border: `${3 * u}px solid ${st === 'pending' || st === 'skip' ? withAlpha(p.ink, 0.14) : withAlpha(col, 0.75)}`,
              boxShadow: `0 ${16 * u}px ${44 * u}px ${withAlpha('#000000', dark ? 0.38 : 0.12)}${st === 'running' ? `, 0 0 ${(18 + pulse * 22) * u}px ${withAlpha(col, 0.45)}` : ''}`,
              padding: `${(portrait ? 24 : 30) * u}px ${28 * u}px`,
              display: 'flex',
              flexDirection: portrait ? 'row' : 'column',
              gap: (portrait ? 26 : 18) * u,
              overflow: 'hidden',
            }}
          >
            <div style={{display: 'flex', alignItems: 'center', gap: 18 * u, flex: portrait ? '0 0 34%' : undefined, flexDirection: portrait ? 'column' : 'row', justifyContent: portrait ? 'center' : 'flex-start'}}>
              <div style={{width: iconS, height: iconS, flex: '0 0 auto'}}>{renderIcon(st, i, iconS)}</div>
              <div style={{textAlign: portrait ? 'center' : 'left'}}>
                <div style={{fontFamily: sans, fontWeight: 800, fontSize: nameFs, color: p.ink, lineHeight: 1.1}}>{s.name}</div>
                <div style={{fontFamily: mono, fontSize: (portrait ? 26 : 22) * u, color: st === 'running' ? p.accent : withAlpha(p.ink, 0.5), marginTop: 6 * u}}>{timer}</div>
              </div>
            </div>
            <div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: portrait ? 'center' : 'flex-start', gap: (portrait ? 12 : 16) * u, minWidth: 0, marginTop: portrait ? 0 : 8 * u}}>
              {steps.slice(0, 5).map((tx, j) => {
                const ss = stepState(j);
                return (
                  <div key={j} style={{display: 'flex', alignItems: 'center', gap: 14 * u, opacity: ss === 'pending' || ss === 'skip' ? 0.45 : 1}}>
                    <div style={{width: stepFs * 1.05, height: stepFs * 1.05, flex: '0 0 auto'}}>
                      {ss === 'running' ? <Spinner size={stepFs * 1.05} color={p.accent} frame={frame} stroke={stepFs * 0.13} speed={14} /> : ss === 'pass' ? <CheckDot size={stepFs * 1.05} color={p.okColor} k={seg(local - ((j + 1) / m) * sf, 0, 8)} filled={false} /> : ss === 'fail' ? <CrossDot size={stepFs * 1.05} color={p.errColor} k={seg(local - sf, 0, 8)} /> : renderIcon(ss === 'skip' ? 'skip' : 'pending', 0, stepFs * 1.05)}
                    </div>
                    <div style={{fontFamily: mono, fontSize: stepFs, color: ss === 'fail' ? p.errColor : p.ink, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{tx}</div>
                  </div>
                );
              })}
            </div>
            {/* progress bar */}
            {!portrait ? (
              <div style={{position: 'absolute', left: 28 * u, right: 28 * u, bottom: 24 * u, height: 8 * u, borderRadius: 8 * u, background: withAlpha(p.ink, 0.1), overflow: 'hidden'}}>
                <div style={{width: `${runK * 100}%`, height: '100%', background: col, borderRadius: 8 * u}} />
              </div>
            ) : (
              <div style={{position: 'absolute', left: 28 * u, right: 28 * u, bottom: 14 * u, height: 7 * u, borderRadius: 8 * u, background: withAlpha(p.ink, 0.1), overflow: 'hidden'}}>
                <div style={{width: `${runK * 100}%`, height: '100%', background: col, borderRadius: 8 * u}} />
              </div>
            )}
          </div>
        );
      })}
      {/* result banner */}
      {(() => {
        const ok = failIdx < 0;
        const k = backOut(seg(t, endT + 6, endT + 22), 1.8);
        const c = ok ? p.okColor : p.errColor;
        return (
          <div style={{position: 'absolute', left: 0, right: 0, bottom: (portrait ? 40 : 36) * u, display: 'flex', justifyContent: 'center', opacity: Math.min(1, k), transform: `scale(${0.85 + 0.15 * k})`}}>
            <div style={{display: 'flex', alignItems: 'center', gap: 20 * u, padding: `${18 * u}px ${44 * u}px`, borderRadius: 22 * u, background: c, color: onFill(c), fontFamily: sans, fontWeight: 800, fontSize: (portrait ? 46 : 42) * u, boxShadow: `0 ${10 * u}px ${40 * u}px ${withAlpha(c, 0.5)}`}}>
              <svg width={44 * u} height={44 * u} viewBox="0 0 24 24">
                {ok ? <path d="M5 12.5 L10 17.5 L19 7" fill="none" stroke={onFill(c)} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" /> : <path d="M6 6 L18 18 M18 6 L6 18" fill="none" stroke={onFill(c)} strokeWidth={3} strokeLinecap="round" />}
              </svg>
              {ok ? p.successText : p.failText}
            </div>
          </div>
        );
      })()}
    </AbsoluteFill>
  );
};

export const deployPipelineStages = defineMotion<Props>({
  id: 'deploy-pipeline-stages',
  title: 'Deploy pipeline stages',
  category: 'data',
  description:
    'A CI/CD pipeline of stage cards (build, test, scan, deploy): each runs in turn with a spinner that becomes a check or a red cross, sub-steps tick off, a timer counts up and the connector fills; a failing stage stops the line, later stages show as skipped, and a banner ends it.',
  source: ['original (generic developer explainer)'],
  useFor: 'DevOps / CI-CD explainers, "how we ship" and release-process videos, deployment tooling promos, incident stories (set one stage to fail).',
  durationInFrames: 270,
  defaultProps: {
    title: 'Deploy to production',
    subtitle: 'main · 5de2147',
    stages: [
      {name: 'Build', steps: ['Install dependencies', 'Compile', 'Bundle assets'], seconds: 41},
      {name: 'Test', steps: ['Unit tests', 'Integration tests', 'Coverage 92%'], seconds: 78},
      {name: 'Scan', steps: ['Dependency audit', 'Secret scan'], seconds: 23},
      {name: 'Deploy', steps: ['Upload artifact', 'Switch traffic', 'Health check'], seconds: 35},
    ],
    successText: 'Deployed to production',
    failText: 'Pipeline failed',
    stageFrames: 48,
    speed: 1,
    startAt: 0,
    background: '#0C0F16',
    panel: '#151A25',
    ink: '#EAEFF8',
    accent: '#4C8DFF',
    okColor: '#2EC4A6',
    errColor: '#FF5C5C',
    fontFamily: '',
  },
  propDocs: {
    title: 'pipeline name',
    subtitle: 'branch / commit line under the title',
    stages: "stages in order [{name, steps? (up to 5 sub-steps), seconds? (timer end value), result? ('pass' default | 'fail' — stops the pipeline, later stages are skipped)}]",
    successText: 'banner text when every stage passes',
    failText: 'banner text when a stage fails',
    stageFrames: 'frames each stage runs',
    speed: 'timing multiplier',
    startAt: 'frame the pipeline starts',
    background: "page colour or 'transparent'",
    panel: 'card colour',
    ink: 'text colour',
    accent: 'running colour',
    okColor: 'pass colour',
    errColor: 'fail colour',
    fontFamily: 'monospace font override (empty = JetBrains Mono)',
  },
  component: DeployPipelineStages,
  tags: ['ci', 'cd', 'pipeline', 'deploy', 'devops', 'build', 'test', 'release', 'github actions', 'stages', 'developer', 'software', 'checks', 'spinner', 'automation'],
});
