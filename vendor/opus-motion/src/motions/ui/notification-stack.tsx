import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {clamp, ease, prog, springAt} from '../../core/ease';
import {fonts} from '../../core/fonts';
import {useStage} from '../../core/stage';
import {defineMotion} from '../../core/types';
import {mix, NotifIcon, rgbaStr} from '../../core/r2-pr3-kit';

/**
 * Notification stack. System notifications / toasts slide in on a 10-frame spring and stack: the newest on top,
 * older ones compress behind it (6-8 px offset, 0.96 scale per level, max 4 visible) or list out in full; a
 * red counter badge pops with each arrival. Platforms: ios lock-screen banners, macos corner cards, android
 * heads-up cards and a plain toast pill. Set background="transparent" to use it as an overlay.
 */
type Item = {app: string; icon: string; color: string; title: string; body: string; at: number; time?: string};
type Props = {
  items: Item[];
  platform: 'ios' | 'macos' | 'android' | 'toast';
  layout: 'stack' | 'list';
  position: 'auto' | 'top' | 'bottom';
  theme: 'light' | 'dark';
  maxVisible: number;
  badge: boolean;
  clock: string;
  date: string;
  background: string;
};

const DEFAULT_ITEMS: Item[] = [
  {app: 'Northwind Shop', icon: 'cart', color: '#FF7A45', title: 'New order #1042', body: '2 items · $48.00 — packed and ready to ship', at: 14},
  {app: 'Messages', icon: 'chat', color: '#34C759', title: 'Maya', body: 'Are we still on for Thursday?', at: 46},
  {app: 'Payments', icon: 'card', color: '#4D6BFF', title: 'Payment received', body: '$1,200.00 from Acme Studio', at: 78},
  {app: 'Calendar', icon: 'calendar', color: '#FF4D5E', title: 'Design review in 10 min', body: 'Room 4B · bring the prototype', at: 110},
  {app: 'Mail', icon: 'mail', color: '#2FA8FF', title: 'Your weekly report', body: 'Revenue is up 18% on last week.', at: 142},
];

const NotificationStack: React.FC<Props> = (P) => {
  const frame = useCurrentFrame();
  const {w, h, u, fps, portrait} = useStage();
  const items = (P.items && P.items.length ? P.items : DEFAULT_ITEMS).map((it) => ({time: 'now', ...it})).sort((a, b) => a.at - b.at);
  const dark = P.theme === 'dark';
  const plat = P.platform;
  const pos = P.position === 'auto' ? (plat === 'toast' ? 'bottom' : 'top') : P.position;
  const dir = pos === 'bottom' ? -1 : 1;

  // geometry per platform
  const cw = plat === 'macos' ? (portrait ? w * 0.92 : 580 * u) : plat === 'toast' ? Math.min(w * 0.86, 720 * u) : plat === 'android' ? w * (portrait ? 0.94 : 0.5) : Math.min(w * 0.92, (portrait ? 960 : 780) * u);
  const uq = portrait ? u * 1.3 : u;
  const ch = (plat === 'macos' ? 124 : plat === 'toast' ? 100 : plat === 'android' ? 176 : 148) * uq;
  const left = plat === 'macos' && !portrait ? w - cw - 40 * u : (w - cw) / 2;
  const showClock = plat === 'ios' && !!P.clock;
  const topBase = plat === 'macos' ? 44 * u : plat === 'android' ? h * 0.06 : showClock ? h * (portrait ? 0.27 : 0.3) : h * 0.08;
  const baseY = pos === 'bottom' ? h - h * 0.1 - ch : topBase;
  const radius = (plat === 'macos' ? 26 : plat === 'toast' ? 50 : plat === 'android' ? 44 : 38) * u;
  const off = 7 * u;
  const gap = 16 * u;

  const surface = (() => {
    if (plat === 'android') return dark ? '#2B2930' : '#F6F2FB';
    if (plat === 'toast') return dark ? '#1B1C21' : '#FFFFFF';
    return dark ? 'rgba(44,44,48,0.78)' : 'rgba(250,250,252,0.8)';
  })();
  const fg = dark ? '#F4F4F6' : '#16161A';
  const sub = dark ? 'rgba(244,244,246,0.68)' : 'rgba(22,22,26,0.62)';

  const count = items.filter((it) => frame >= it.at).length;
  const lastAt = items.filter((it) => frame >= it.at).map((it) => it.at).pop() ?? 0;
  const badgePop = springAt(frame, fps, lastAt, 'pop');

  const cards = items.map((it, i) => {
    if (frame < it.at - 1) return null;
    const s = springAt(frame, fps, it.at, 'snappy');
    // how deep this card has been pushed by newer arrivals
    let level = 0;
    for (let j = i + 1; j < items.length; j++) level += clamp(springAt(frame, fps, items[j].at, 'snappy'), 0, 1.12);
    const alphaIn = prog(frame, it.at, it.at + 5, ease.out);
    const stack = P.layout === 'stack';
    const vis = P.maxVisible;
    const fade = clamp(vis - level, 0, 1);
    if (fade <= 0.001) return null;
    const sc = stack ? Math.pow(0.96, level) : 1;
    const dy = dir * (stack ? level * off + ch * (1 - sc) : level * (ch + gap)) + -dir * (1 - s) * (ch + 90 * u);
    const op = alphaIn * (stack ? clamp(1 - level * 0.12, 0, 1) : 1) * fade;
    const z = 100 - Math.round(level * 10) - (items.length - i);
    const key = `n${i}`;
    const iconSize = (plat === 'macos' ? 62 : plat === 'toast' ? 56 : plat === 'android' ? 30 : 78) * uq;
    const iconEl = <NotifIcon name={it.icon} size={iconSize} color={it.color} radius={plat === 'toast' ? iconSize / 2 : undefined} />;
    const clampLines = (n: number): React.CSSProperties => ({display: '-webkit-box', WebkitLineClamp: n, WebkitBoxOrient: 'vertical', overflow: 'hidden'});
    let inner: React.ReactNode;
    if (plat === 'android') {
      inner = (
        <div style={{padding: `${18 * uq}px ${26 * uq}px`, display: 'flex', flexDirection: 'column', gap: 6 * uq, height: '100%', boxSizing: 'border-box', justifyContent: 'center'}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 12 * uq, fontSize: 24 * uq, color: sub, fontWeight: 600}}>
            {iconEl}
            <span>{it.app}</span>
            <span>·</span>
            <span>{it.time}</span>
            <span style={{marginLeft: 'auto', fontSize: 28 * uq}}>⌄</span>
          </div>
          <div style={{fontSize: 32 * uq, fontWeight: 600, color: fg}}>{it.title}</div>
          <div style={{fontSize: 27 * uq, color: sub, ...clampLines(1)}}>{it.body}</div>
        </div>
      );
    } else if (plat === 'toast') {
      inner = (
        <div style={{display: 'flex', alignItems: 'center', gap: 20 * uq, padding: `0 ${28 * uq}px`, height: '100%', boxSizing: 'border-box'}}>
          {iconEl}
          <div style={{minWidth: 0}}>
            <div style={{fontSize: 30 * uq, fontWeight: 700, color: fg, ...clampLines(1)}}>{it.title}</div>
            <div style={{fontSize: 24 * uq, color: sub, ...clampLines(1)}}>{it.body}</div>
          </div>
        </div>
      );
    } else {
      const mac = plat === 'macos';
      inner = (
        <div style={{display: 'flex', alignItems: 'center', gap: (mac ? 18 : 22) * uq, padding: `0 ${(mac ? 22 : 26) * uq}px`, height: '100%', boxSizing: 'border-box'}}>
          {iconEl}
          <div style={{minWidth: 0, flex: 1}}>
            <div style={{display: 'flex', alignItems: 'baseline', gap: 10 * uq}}>
              <span style={{fontSize: (mac ? 26 : 31) * uq, fontWeight: 700, color: fg, ...clampLines(1), flex: 1}}>{it.title}</span>
              {!mac && <span style={{fontSize: 23 * uq, color: sub}}>{it.time}</span>}
            </div>
            {mac && <div style={{fontSize: 19 * uq, color: sub, fontWeight: 600, letterSpacing: 0.4 * uq, marginBottom: 1 * uq}}>{it.app.toUpperCase()}</div>}
            <div style={{fontSize: (mac ? 23 : 28) * uq, color: fg, opacity: 0.86, lineHeight: 1.22, ...clampLines(2)}}>{it.body}</div>
          </div>
        </div>
      );
    }
    return (
      <div
        key={key}
        style={{
          position: 'absolute',
          left,
          top: baseY,
          width: cw,
          height: ch,
          borderRadius: radius,
          background: surface,
          boxShadow: `0 ${10 * u}px ${34 * u}px rgba(0,0,0,${dark ? 0.45 : 0.22})`,
          backdropFilter: plat === 'android' || plat === 'toast' ? undefined : `blur(${34 * u}px) saturate(1.7)`,
          transform: `translateY(${dy}px) scale(${sc})`,
          transformOrigin: pos === 'bottom' ? 'center bottom' : 'center top',
          opacity: op,
          zIndex: z,
          fontFamily: fonts.sans,
          overflow: 'hidden',
        }}
      >
        {inner}
      </div>
    );
  });

  const bg = P.background;
  const isT = bg === 'transparent';
  const bgStyle: React.CSSProperties = isT
    ? {}
    : {
        background: `radial-gradient(ellipse at 20% 15%, ${mix(bg, '#FF6FB5', 0.38)} 0%, transparent 55%), radial-gradient(ellipse at 85% 30%, ${mix(bg, '#4DE0FF', 0.34)} 0%, transparent 55%), radial-gradient(ellipse at 50% 100%, ${mix(bg, '#8B5CFF', 0.4)} 0%, transparent 60%), ${bg}`,
      };

  const clockIn = prog(frame, 0, 20, ease.out);
  const badgeX = left + cw - 14 * u;
  const badgeY = (pos === 'bottom' ? baseY : baseY) - 20 * u;

  return (
    <AbsoluteFill style={bgStyle}>
      {showClock && (
        <div style={{position: 'absolute', left: 0, right: 0, top: h * (portrait ? 0.1 : 0.06), textAlign: 'center', color: '#fff', fontFamily: fonts.sans, opacity: clockIn, transform: `translateY(${(1 - clockIn) * 10 * u}px)`}}>
          <div style={{fontSize: 30 * u, fontWeight: 600, opacity: 0.85}}>{P.date}</div>
          <div style={{fontSize: (portrait ? 190 : 170) * u, fontWeight: 800, lineHeight: 1, letterSpacing: -4 * u}}>{P.clock}</div>
        </div>
      )}
      {cards}
      {P.badge && plat !== 'toast' && count > 0 && (
        <div
          style={{
            position: 'absolute',
            left: badgeX - 24 * u,
            top: badgeY - 6 * u,
            minWidth: 52 * u,
            height: 52 * u,
            padding: `0 ${12 * u}px`,
            boxSizing: 'border-box',
            borderRadius: 26 * u,
            background: '#FF3B30',
            color: '#fff',
            fontFamily: fonts.sans,
            fontWeight: 800,
            fontSize: 30 * u,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transform: `scale(${clamp(badgePop, 0, 1.4)})`,
            boxShadow: `0 ${4 * u}px ${14 * u}px ${rgbaStr('#FF3B30', 0.5)}`,
            zIndex: 500,
          }}
        >
          {count}
        </div>
      )}
    </AbsoluteFill>
  );
};

export const notificationStack = defineMotion<Props>({
  id: 'notification-stack',
  title: 'Notification stack (iOS / macOS / Android / toast)',
  category: 'ui',
  description:
    'System notifications slide in on a 10-frame spring and stack — newest on top, older ones compress behind (7 px offset, 0.96 scale per level, max 4 visible) or list in full — with a red counter badge that pops on each arrival. iOS lock-screen banners with a clock, macOS corner cards, Android heads-up cards or a plain toast pill; light or dark, or transparent as an overlay.',
  source: ['prompt-corpus research: notification-stack (16 cases, ideas only; original implementation)'],
  useFor: 'Social proof ("new order!"), app demos, urgency hooks in ads, "your inbox in 10 seconds" gags; pass your own items.',
  durationInFrames: 200,
  defaultProps: {items: DEFAULT_ITEMS, platform: 'ios', layout: 'stack', position: 'auto', theme: 'light', maxVisible: 4, badge: true, clock: '9:41', date: 'Tuesday, 14 October', background: '#1B2A5E'},
  propDocs: {
    items: 'notifications [{app, icon (bell|chat|mail|cart|heart|check|calendar|card|bolt|user), color, title, body, at (frame), time}]',
    platform: "'ios' | 'macos' | 'android' | 'toast'",
    layout: "'stack' (older cards compress behind) | 'list' (full cards pushed down / up)",
    position: "'auto' | 'top' | 'bottom'",
    theme: "'light' | 'dark' card surfaces",
    maxVisible: 'cards kept visible before the oldest drops out',
    badge: 'counter badge on the stack (hidden for toast)',
    clock: 'ios lock-screen time ("" = hide the clock)',
    date: 'ios lock-screen date line',
    background: "wallpaper base colour, or 'transparent' to use as an overlay",
  },
  component: NotificationStack,
  tags: ['notification', 'notifications', 'toast', 'banner', 'alert', 'ios', 'macos', 'android', 'lock screen', 'stack', 'badge', 'social proof', 'new order', 'ui', 'phone', 'app demo', 'overlay', 'urgency'],
});
