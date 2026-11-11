/** Independent, native Remotion composition; no Video Talkcraft imports/assets. */
import React from 'react';
import {
  AbsoluteFill, Composition, Img, Sequence, interpolate, spring, staticFile,
  useCurrentFrame, useVideoConfig,
} from 'remotion';
import {Audio, Video} from '@remotion/media';

type Scene = {
  id: string; title: string; text: string; eyebrow: string; layout: string;
  animation: 'cut' | 'fade' | 'slide'; framing: string; repoUrl: string;
  startFrame: number; durationFrames: number; media: string | null;
  mediaKind: 'image' | 'video' | null;
};
type Project = {
  fps: number; aspect: string; width: number; height: number;
  totalFrames: number; scenes: Scene[];
};

const example: Project = {
  fps: 30, aspect: '16:9', width: 1920, height: 1080, totalFrames: 150,
  scenes: [{id: 'scene-001', title: 'MoneyPrint', text: 'Renderização local e animada',
    eyebrow: 'ARTISYS · OPEN SOURCE', layout: 'hero', animation: 'cut',
    framing: 'contain', repoUrl: '', startFrame: 0, durationFrames: 150,
    media: null, mediaKind: null}],
};

const colors = {
  paper: '#F6EEDB', ink: '#17243C', violet: '#6453C8',
  muted: '#526079', mutedPurple: '#D8CCF4', edge: '#D8CFBE',
  white: '#FFFFFF', cyan: '#D1ECE9',
};
const font = 'Lato, Inter, Arial, sans-serif';

const copy = (text: string, max: number) =>
  text.length > max ? text.slice(0, max - 1).trimEnd() + '…' : text;

const MediaWindow: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const drift = interpolate(frame, [0, Math.max(1, scene.durationFrames)],
    [1.01, 1.07], {extrapolateRight: 'clamp'});
  const media = scene.media ? staticFile(scene.media) : null;
  return (
    <div style={{width: '100%', height: '100%', overflow: 'hidden', borderRadius: 24,
      border: '2px solid #C6C1BB', boxShadow: '0 32px 80px #17243C1F',
      background: '#F0F0EC', display: 'flex', flexDirection: 'column'}}>
      <div style={{height: 58, flexShrink: 0, background: '#EBEAE7',
        borderBottom: '1px solid #CFCCCA', display: 'flex', alignItems: 'center',
        gap: 12, paddingLeft: 22, color: colors.muted, fontSize: 21}}>
        <span style={{color: '#AA6666'}}>●</span>
        <span style={{color: '#C8A15B'}}>●</span><span style={{color: '#64A291'}}>●</span>
        <span style={{paddingLeft: 26, overflow: 'hidden', whiteSpace: 'nowrap',
          textOverflow: 'ellipsis'}}>{scene.repoUrl || 'Captura licenciada'}</span>
      </div>
      <div style={{flex: 1, position: 'relative', overflow: 'hidden'}}>
        {media && scene.mediaKind === 'image' ? (
          <Img src={media} style={{width: '100%', height: '100%',
            objectFit: scene.framing === 'cover' ? 'cover' : 'contain',
            objectPosition: 'top center', transform: `scale(${drift})`}} />
        ) : media && scene.mediaKind === 'video' ? (
          <Video src={media} loop muted style={{width: '100%', height: '100%',
            objectFit: scene.framing === 'contain' ? 'contain' : 'cover'}} />
        ) : (
          <div style={{height: '100%', display: 'grid', placeItems: 'center',
            color: colors.muted, fontSize: 26, textAlign: 'center', padding: 32}}>
            Sem captura real selecionada
          </div>
        )}
      </div>
    </div>
  );
};

const FlowGraphic: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const txt = (scene.title + ' ' + scene.text).toLowerCase();
  const steps = /pentest|seguran|vulnerabil/.test(txt)
    ? ['ALVO AUTORIZADO', 'VERIFICAÇÃO', 'RELATÓRIO']
    : /github|reposit/.test(txt)
      ? ['REPOSITÓRIO', 'CÓDIGO', 'APLICAÇÃO']
      : /cliente|crm|venda/.test(txt)
        ? ['CONTATO', 'PROPOSTA', 'RESULTADO']
        : ['ENTRADA', 'PROCESSAMENTO', 'RESULTADO'];
  return <div style={{display: 'flex', alignItems: 'center', gap: 16, width: '100%'}}>
    {steps.map((step, i) => {
      const delay = i * 11 + 8;
      const p = frame < delay ? 0 : spring({frame: frame - delay, fps,
        config: {damping: 20, stiffness: 140}});
      return <React.Fragment key={step}>
        <div style={{flex: 1, minWidth: 0, height: 214, borderRadius: 20,
          background: colors.white, border: '2px solid ' + colors.edge,
          padding: 27, opacity: p,
          transform: `translateY(${Math.round((1-p)*50)}px)`,
          boxShadow: '0 15px 40px #17243C12'}}>
          <div style={{background: colors.violet, color: colors.white,
            borderRadius: 13, width: 53, height: 53, display: 'grid',
            placeItems: 'center', fontWeight: 800, fontSize: 25}}>{i+1}</div>
          <div style={{fontSize: 23, fontWeight: 800, paddingTop: 28,
            overflowWrap: 'anywhere'}}>{step}</div>
        </div>
        {i < steps.length - 1 && <div style={{fontSize: 42, color: colors.violet}}>→</div>}
      </React.Fragment>;
    })}
  </div>;
};

const Slide: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const intro = frame < 1 ? 0 : spring({frame: frame - 1, fps,
    config: {damping: 22, stiffness: 160}});
  const opacity = scene.animation === 'fade'
    ? interpolate(frame, [0, Math.min(14, scene.durationFrames-1)], [0, 1],
      {extrapolateRight: 'clamp'}) : 1;
  const offset = scene.animation === 'slide' ? (1-intro)*60 : (1-intro)*32;
  const isPortrait = height > width;
  const pad = isPortrait ? 70 : 112;
  const showMedia = scene.media !== null || scene.layout === 'browser';
  const mediaFirst = scene.layout === 'browser';
  const titleSize = isPortrait ? 66 : scene.title.length > 42 ? 64 : 79;
  return <AbsoluteFill style={{background: colors.paper, overflow: 'hidden',
    color: colors.ink, fontFamily: font}}>
    <AbsoluteFill style={{pointerEvents: 'none', opacity: .6,
      background: 'radial-gradient(circle at 94% 6%,#DFD6F4,transparent 36%),radial-gradient(circle at 0% 100%,#DCEEE5,transparent 42%)'}}/>
    <div style={{position: 'absolute', inset: 0, padding: pad,
      display: 'flex', flexDirection: 'column', opacity,
      transform: `translateY(${offset}px)`}}>
      <div style={{fontSize: isPortrait ? 23 : 24, letterSpacing: 3.6,
        color: colors.violet, fontWeight: 800, marginBottom: isPortrait ? 45 : 40}}>
        {copy(scene.eyebrow || 'MONEYPRINT · ARTISYS', 52)}
      </div>
      <h1 style={{fontSize: titleSize, lineHeight: 1.07, margin: 0,
        maxWidth: isPortrait ? '100%' : '92%', letterSpacing: -1.4,
        overflowWrap: 'anywhere', fontWeight: 900}}>
        {copy(scene.title, isPortrait ? 85 : 115)}
      </h1>
      <div style={{width: 170, height: 6, background: colors.violet,
        borderRadius: 6, margin: '33px 0'}}/>
      <div style={{fontSize: isPortrait ? 31 : 32, lineHeight: 1.4,
        maxWidth: '95%', color: colors.muted, fontWeight: 500}}>
        {copy(scene.text, scene.layout === 'minimal' ? 250 : isPortrait ? 195 : 205)}
      </div>
      <div style={{flex: 1, minHeight: 50, display: 'flex', alignItems: 'center',
        justifyContent: 'center', marginTop: 35}}>
        {showMedia || mediaFirst
          ? <div style={{width: '100%', height: isPortrait ? '72%' : '90%', maxHeight: 540}}>
              <MediaWindow scene={scene}/>
            </div>
          : scene.layout === 'flow' || scene.layout === 'hero'
            ? <FlowGraphic scene={scene}/>
            : <div style={{width: '85%', height: 2, background: colors.edge}}/>}
      </div>
      <div style={{paddingTop: 18, fontSize: 19, fontWeight: 700,
        color: colors.muted, letterSpacing: 1.2}}>ARTISYS · MONEYPRINT</div>
    </div>
  </AbsoluteFill>;
};

export const MoneyPrint: React.FC<Project> = ({scenes}) => (
  <AbsoluteFill style={{background: colors.paper}}>
    {scenes.map(scene => <Sequence key={scene.id} from={scene.startFrame}
      durationInFrames={scene.durationFrames} name={scene.id}>
      <Slide scene={scene}/>
    </Sequence>)}
    <Audio src={staticFile('narration.wav')}/>
  </AbsoluteFill>
);

export const RemotionRoot: React.FC = () => (
  <Composition id="MoneyPrint" component={MoneyPrint}
    defaultProps={example} durationInFrames={example.totalFrames}
    fps={example.fps} width={example.width} height={example.height}
    calculateMetadata={({props}) => ({
      durationInFrames: props.totalFrames, fps: props.fps,
      width: props.width, height: props.height,
    })} />
);
