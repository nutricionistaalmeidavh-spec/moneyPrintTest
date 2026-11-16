"""Publish Studio V3-compatible storyboard metadata; Blender layers stay external.

This *does not* claim Studio V3 can edit Blender keyframes; scene objects are
linked by exact file names and individual overlays so downstream UI can show
planned layers and users can selectively rerender individual shots.
"""
import json
from pathlib import Path
HERE=Path(__file__).resolve()
ROOT=HERE.parents[2] if HERE.parent.name=='blender_pdv' else HERE.parents[1]

def main():
    src=json.loads((ROOT/'projects/pdv-artisys-quaternius-v1.json').read_text())
    seen={}
    for entry in src['scenes']:
        for f in entry['assets_referenced']:
            seen[f]=True
    media={f:(f.replace('assets/','').replace('.mp4','').replace('-','_')) for f in sorted(seen)}
    assets=[]
    for path,id in media.items():
        assets.append({'id':id,'path':path,'title':'Tutorial real: '+id.replace('_',' '),
                       'description':'Vídeo original do PDV ArtiSys fornecido pelo proprietário',
                       'license':'Proprietary; use by owner only','attribution':'ArtiSys — tutorial oficial',
                       'verified':True,'tags':['pdv','artisys','tutorial']})
    scenes=[]
    for item in src['scenes']:
        sid=item['id'];v=item.get('video_texture')
        scenes.append({'id':'scene-'+sid,'track_id':'video',
                       'title':item['typography']['title'][:90],
                       'text':item['typography']['accent']+' '+str(item.get('narration','')),
                       'kind':'media' if v else 'text',
                       'asset_id':media[v['file']] if v else None,
                       'start_frame':item['start_frame'],'duration_frames':item['duration_frames'],
                       'animation':'cut','framing':'contain','layout':'browser',
                       'blender_scene_id':sid,
                       'blender_source':'output/pdv_artisys_scene_'+sid+'.blend',
                       'character_actions':item['acting_timeline'],
                       'media_screens':item['assets_referenced'],
                       'overlay_layers':['overlays/scene_'+sid+'/'+n+'.png' for n in
                                          ['eyebrow','title','accent','footer','scene_number']]})
    bridge={
      'schema_version':3,'id':'pdv-artisys-blender-82s','revision':1,
      'topic':'Sistemas que construí — PDV ArtiSys (Blender)',
      'script':'\n'.join(s['text'] for s in scenes),
      'fps':30,'aspect':'9:16','total_frames':2460,
      'tracks':[{'id':'video','kind':'video'},{'id':'voice','kind':'audio'},
                {'id':'effects','kind':'audio'},{'id':'graphics','kind':'overlay'}],
      'assets':assets,'scenes':scenes,
      'blender_delivery':'This file links Blender shots but the Studio editor does NOT edit bone keyframes.',
      'autopublish':False
    }
    path=ROOT/'projects/pdv-artisys-studio-v3-bridge.json'
    path.write_text(json.dumps(bridge,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Studio bridge exported:',path,len(scenes),'scenes,',len(assets),'assets')
if __name__=='__main__':main()
