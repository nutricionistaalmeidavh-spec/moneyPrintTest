import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {clamp, ease, prog} from '../../core/ease';
import {Header, Legend, clip, fmt, itemColor, niceScale, ramp, resolveFont, textOn, tw, useChartBox} from '../../core/r3-chart-kit';
import {Svg, useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';

type Task = {label: string; start: number; end: number; group?: string; color?: string; progress?: number};
type Milestone = {label: string; at: number};
type Props = {
  tasks: Task[];
  milestones: Milestone[];
  today: number;
  todayLabel: string;
  title: string;
  subtitle: string;
  axisMin: number;
  axisMax: number;
  tickStep: number;
  tickPrefix: string;
  tickSuffix: string;
  tickLabels: string[];
  showDurations: boolean;
  durationSuffix: string;
  showProgress: boolean;
  colors: string[];
  background: string;
  ink: string;
  accent: string;
  fontFamily: string;
  startAt: number;
  speed: number;
};

const DEFAULT_TASKS: Task[] = [
  {label: 'Research', start: 0, end: 3, group: 'Plan', progress: 1},
  {label: 'Concept & scope', start: 2, end: 5, group: 'Plan', progress: 1},
  {label: 'Design', start: 4, end: 8, group: 'Build', progress: 0.85},
  {label: 'Development', start: 6, end: 12, group: 'Build', progress: 0.45},
  {label: 'Testing', start: 10, end: 13, group: 'Launch', progress: 0.1},
  {label: 'Launch', start: 12.5, end: 14, group: 'Launch', progress: 0},
];
const DEFAULT_MS: Milestone[] = [
  {label: 'Kick-off', at: 0},
  {label: 'Beta', at: 10},
  {label: 'Go live', at: 14},
];

const GanttTimeline: React.FC<Props> = ({
  tasks,
  milestones,
  today,
  todayLabel,
  title,
  subtitle,
  axisMin,
  axisMax,
  tickStep,
  tickPrefix,
  tickSuffix,
  tickLabels,
  showDurations,
  durationSuffix,
  showProgress,
  colors,
  background,
  ink,
  accent,
  fontFamily,
  startAt,
  speed,
}) => {
  const frame = useCurrentFrame();
  const {u, portrait, square} = useStage();
  const box = useChartBox(title, subtitle);
  const font = resolveFont(fontFamily);

  const ts = (tasks || []).filter((t) => t && isFinite(t.start) && isFinite(t.end) && t.end >= t.start);
  const ms = (milestones || []).filter((m) => m && isFinite(m.at));
  const groups: string[] = [];
  ts.forEach((t) => {
    if (t.group && !groups.includes(t.group)) groups.push(t.group);
  });
  const colorOf = (t: Task, i: number) => t.color || (t.group ? itemColor(undefined, colors, groups.indexOf(t.group)) : accent || itemColor(undefined, colors, 0));

  // axis range
  const lo = isFinite(axisMin) && axisMin !== axisMax ? axisMin : Math.min(0, ...ts.map((t) => t.start), ...ms.map((m) => m.at));
  const hiRaw = Math.max(...ts.map((t) => t.end), ...ms.map((m) => m.at), today > 0 ? today : -Infinity, lo + 1);
  const ns = niceScale(lo, isFinite(axisMax) && axisMax > lo ? axisMax : hiRaw, 7);
  const step = tickStep > 0 ? tickStep : Math.max(1, ns.step);
  const a0 = isFinite(axisMin) && axisMin !== axisMax ? axisMin : ns.min;
  const a1 = isFinite(axisMax) && axisMax > a0 ? axisMax : ns.max;

  // geometry
  const labSize = (portrait ? 28 : square ? 25 : 25) * u;
  const tickSize = (portrait ? 24 : 21) * u;
  const labW = Math.min(box.w * (portrait ? 0.32 : 0.24), Math.max(...ts.map((t) => tw(t.label, labSize, 0.6)), 80 * u) + 22 * u);
  const showLegend = groups.length > 1;
  const legSize = (portrait ? 26 : 22) * u;
  const legH = showLegend ? legSize * 2.1 : 0;
  const axisH = tickSize * 1.9;
  const msLab = tickSize * 1.05;
  const msH = ms.length ? msLab + 14 * u + 32 * u + 14 * u : 0;
  const gx0 = box.x + labW;
  const gx1 = box.x + box.w - 24 * u;
  const gy0 = box.y + msH + axisH;
  const gy1 = box.y + box.h - legH - (showLegend ? 16 * u : 0);
  const rowH = Math.min((portrait ? 150 : 78) * u, (gy1 - gy0) / Math.max(1, ts.length));
  const barH = rowH * 0.56;
  const gh = rowH * ts.length;
  const top = gy0 + 10 * u;
  const sx = (v: number) => gx0 + ((v - a0) / (a1 - a0 || 1)) * (gx1 - gx0);

  const ticks: number[] = [];
  for (let v = Math.ceil(a0 / step) * step; v <= a1 + step * 0.001; v += step) ticks.push(v);
  const tickText = (v: number) => {
    const idx = Math.round(v);
    if (tickLabels && tickLabels.length && Math.abs(v - idx) < 1e-6 && idx >= 0 && idx < tickLabels.length) return tickLabels[idx];
    if (tickLabels && tickLabels.length) return '';
    return fmt(v, step < 1 ? 1 : 0, tickPrefix, tickSuffix);
  };
  const maxTickLabels = Math.floor((gx1 - gx0) / (tw('Wk 00', tickSize, 0.58) + 6 * u));
  const thin = Math.max(1, Math.ceil(ticks.length / Math.max(2, maxTickLabels)));

  const axisT = prog(frame, startAt - 4, startAt + 14, ease.out);
  const barStart = (i: number) => startAt + 10 + i * 9;
  const lastBar = barStart(ts.length) + 36;
  const msT = (k: number) => ramp(frame, lastBar - 22 + k * 8, 18, speed, ease.back);
  const todayT = ramp(frame, lastBar + 8, 26, speed, ease.out);
  const hasToday = isFinite(today) && today >= a0 && today <= a1;
  const bobY = Math.sin((frame / 30) * Math.PI * 1.2) * 2 * u;

  return (
    <AbsoluteFill style={{background}}>
      <Svg>
        <Header box={box} ink={ink} fontFamily={font} frame={frame} />

        {/* time axis + grid */}
        <g opacity={axisT}>
          {ticks.map((v, i) => {
            const x = sx(v);
            const show = i % thin === 0 && tickText(v) !== '';
            return (
              <g key={i}>
                <line x1={x} x2={x} y1={gy0 - 6 * u} y2={top + gh + 6 * u} stroke={ink} strokeOpacity={0.09} strokeWidth={1.5 * u} />
                {show && (
                  <text x={x} y={gy0 - 16 * u} textAnchor="middle" fontFamily={font} fontWeight={500} fontSize={tickSize} fill={ink} fillOpacity={0.6} style={{fontVariantNumeric: 'tabular-nums'}}>
                    {tickText(v)}
                  </text>
                )}
              </g>
            );
          })}
          <line x1={gx0} x2={gx1} y1={gy0 - 6 * u} y2={gy0 - 6 * u} stroke={ink} strokeOpacity={0.3} strokeWidth={2 * u} />
        </g>

        {/* alternating row bands */}
        {ts.map((_, i) =>
          i % 2 === 0 ? <rect key={'band' + i} x={box.x} y={top + i * rowH} width={box.w} height={rowH} rx={8 * u} fill={ink} fillOpacity={0.035 * axisT} /> : null,
        )}

        {hasToday && (
          <line x1={sx(today)} x2={sx(today)} y1={gy0 - 2 * u} y2={gy0 - 2 * u + (top + gh + 8 * u - (gy0 - 2 * u)) * todayT} stroke="#E5484D" strokeWidth={3 * u} opacity={clamp(todayT * 1.5)} />
        )}

        {/* bars */}
        {ts.map((t, i) => {
          const col = colorOf(t, i);
          const g = ramp(frame, barStart(i), 30, speed, ease.out);
          const lt = prog(frame, barStart(i) - 2, barStart(i) + 14, ease.out);
          const x0 = sx(t.start);
          const x1 = sx(t.end);
          const full = Math.max(barH, x1 - x0);
          const w = full * g;
          const y = top + i * rowH + (rowH - barH) / 2;
          const p = clamp(t.progress ?? 0);
          const pg = ramp(frame, barStart(i) + 16, 30, speed, ease.out);
          const dur = t.end - t.start;
          const durTxt = fmt(dur, dur % 1 ? 1 : 0, '', durationSuffix);
          const durW = tw(durTxt, barH * 0.5, 0.58);
          const inside = w > durW + 28 * u;
          const overflowRight = !inside && x0 + w + 12 * u + durW > gx1 + 40 * u;
          const filledW = showProgress ? full * p * pg : full;
          const onSolid = inside && filledW > durW + 28 * u;
          return (
            <g key={i}>
              <text x={box.x + 12 * u} y={y + barH / 2 + labSize * 0.35} fontFamily={font} fontWeight={600} fontSize={labSize} fill={ink} opacity={lt}>
                {clip(t.label, labW - 26 * u, labSize)}
              </text>
              <rect x={x0} y={y} width={w} height={barH} rx={barH * 0.3} fill={col} fillOpacity={showProgress ? 0.32 : 1} />
              {showProgress && p > 0 && <rect x={x0} y={y} width={Math.max(barH * 0.6, full * p * pg) * Math.min(1, g * 1.2)} height={barH} rx={barH * 0.3} fill={col} />}
              {showDurations && g > 0.95 && (
                <text
                  x={inside ? x0 + 14 * u : overflowRight ? x0 - 12 * u - durW : x0 + w + 12 * u}
                  y={y + barH / 2 + barH * 0.2}
                  fontFamily={font}
                  fontWeight={700}
                  fontSize={barH * 0.5}
                  fill={onSolid ? textOn(col) : ink}
                  fillOpacity={onSolid ? 0.95 : 0.65}
                  opacity={prog(frame, barStart(i) + 28, barStart(i) + 42)}
                >
                  {durTxt}
                </text>
              )}
            </g>
          );
        })}

        {/* milestones */}
        {ms.map((m, k) => {
          const t = msT(k);
          const x = sx(m.at);
          const d = (portrait ? 17 : 15) * u * t;
          const cy = box.y + msLab + 14 * u + 15 * u;
          const half = tw(m.label, tickSize, 0.6) / 2;
          return (
            <g key={'m' + k} opacity={clamp(t)}>
              <line x1={x} x2={x} y1={gy0 - 6 * u} y2={top + gh + 6 * u} stroke={ink} strokeOpacity={0.35} strokeWidth={2 * u} strokeDasharray={`${6 * u} ${6 * u}`} />
              <path d={`M${x} ${cy - d} L${x + d} ${cy} L${x} ${cy + d} L${x - d} ${cy} Z`} fill={ink} />
              <text x={Math.min(Math.max(x, gx0 - 20 * u + half), gx1 + 16 * u - half)} y={box.y + msLab} textAnchor="middle" fontFamily={font} fontWeight={700} fontSize={tickSize} fill={ink}>
                {m.label}
              </text>
            </g>
          );
        })}

        {hasToday && (
          <g opacity={clamp(todayT * 1.5)}>
            <g transform={`translate(0 ${bobY})`}>
              <rect x={sx(today) - (tw(todayLabel, tickSize, 0.62) + 24 * u) / 2} y={top + gh + 12 * u} width={tw(todayLabel, tickSize, 0.62) + 24 * u} height={tickSize * 1.75} rx={tickSize * 0.875} fill="#E5484D" />
              <text x={sx(today)} y={top + gh + 12 * u + tickSize * 1.22} textAnchor="middle" fontFamily={font} fontWeight={700} fontSize={tickSize} fill="#FFFFFF" letterSpacing={tickSize * 0.06}>
                {todayLabel}
              </text>
            </g>
          </g>
        )}

        {showLegend && (
          <Legend
            items={groups.map((g, i) => ({label: g, color: itemColor(undefined, colors, i)}))}
            x={gx0}
            y={Math.min(box.y + box.h - legH, top + gh + (hasToday ? tickSize * 1.75 + 28 * u : 12 * u) + 28 * u)}
            w={gx1 - gx0}
            cols={Math.min(groups.length, portrait ? 3 : 6)}
            rowH={legSize * 2}
            size={legSize}
            ink={ink}
            fontFamily={font}
            frame={frame}
            start={startAt + 24}
            stagger={4}
          />
        )}
      </Svg>
    </AbsoluteFill>
  );
};

export const ganttTimeline = defineMotion<Props>({
  id: 'gantt-timeline',
  title: 'Gantt timeline',
  category: 'data',
  description:
    'A project Gantt chart: a time axis with grid, task rows whose bars grow from their start to their end with a progress fill and duration, diamond milestones dropping in on a lane above, and a red "today" marker sweeping down and bobbing on the timeline; bars coloured by group with a legend.',
  source: ['original round-3 chart motion'],
  useFor:
    'Schedules and roadmaps: project plans, launch timelines, sprint plans, production calendars, course or treatment plans. Pass tasks as [{label, start, end, group?, progress?}] and milestones as [{label, at}] in any unit (days, weeks, months); use tickLabels for named periods.',
  durationInFrames: 210,
  defaultProps: {
    tasks: DEFAULT_TASKS,
    milestones: DEFAULT_MS,
    today: 7,
    todayLabel: 'TODAY',
    title: 'Project timeline',
    subtitle: 'Fourteen weeks from kick-off to launch',
    axisMin: 0,
    axisMax: 0,
    tickStep: 0,
    tickPrefix: 'W',
    tickSuffix: '',
    tickLabels: [],
    showDurations: true,
    durationSuffix: ' wk',
    showProgress: true,
    colors: ['#2F6FED', '#FF7A45', '#16B39A', '#F2B134', '#8E5CF0', '#E5487F', '#5BC0EB', '#7A8794'],
    background: '#F5F3EE',
    ink: '#18212B',
    accent: '#2F6FED',
    fontFamily: '',
    startAt: 8,
    speed: 1,
  },
  propDocs: {
    tasks: 'rows [{label, start, end, group?, color?, progress? 0-1}] in axis units',
    milestones: 'diamond markers [{label, at}] in axis units (empty array = none)',
    today: 'axis position of the "today" marker (outside the axis range or negative = hidden)',
    todayLabel: 'text in the today pill',
    title: 'headline (empty = none)',
    subtitle: 'small line under the headline (empty = none)',
    axisMin: 'left end of the axis (with axisMax = 0 both are automatic)',
    axisMax: 'right end of the axis (0 = automatic)',
    tickStep: 'distance between axis ticks (0 = automatic)',
    tickPrefix: 'text before axis numbers, e.g. "W" or "Day "',
    tickSuffix: 'text after axis numbers',
    tickLabels: 'optional names for whole-number ticks, e.g. ["Jan","Feb","Mar"] (index = value)',
    showDurations: 'print each task length on or after its bar',
    durationSuffix: 'text after the length, e.g. " wk", "d"',
    showProgress: 'fill the completed part of each bar from its progress value',
    colors: 'palette for groups',
    background: 'page colour, or "transparent" to sit over other content',
    ink: 'text, grid and milestone colour',
    accent: 'bar colour for tasks without a group or colour',
    fontFamily: 'CSS font family (empty = Space Grotesk)',
    startAt: 'frame the axis starts to appear',
    speed: 'animation speed multiplier',
  },
  component: GanttTimeline,
  tags: ['gantt', 'timeline', 'schedule', 'roadmap', 'project', 'milestone', 'chart', 'plan', 'infographic', 'data', 'overlay', 'tasks', 'planning'],
});
