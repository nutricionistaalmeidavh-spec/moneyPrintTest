import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dialogue_voice import make_plan,split_for_tts,SCENES
class PlanTests(unittest.TestCase):
 def test_seven_scenes_and_canonical_duration(self):
  p=make_plan();self.assertEqual(len(p),7);self.assertEqual(round(p[-1]['end']),85)
 def test_speakers_and_lines(self):
  p=make_plan();self.assertEqual(sum(len(x['lines']) for x in p),16)
  self.assertTrue(all(l['speaker'] in {'A','B'} for s in p for l in s['lines']))
 def test_no_silently_paid_dependency(self):
  txt=Path(__file__).resolve().parents[1].joinpath('dialogue_voice.py').read_text()
  self.assertNotIn('elevenlabs',txt.lower());self.assertNotIn('api_key',txt.lower())
 def test_split_keeps_every_word(self):
  txt=SCENES[1]['lines'][1][1]
  pieces=split_for_tts(txt,115)
  self.assertEqual(' '.join(pieces),txt)
  self.assertTrue(all(len(x)<=115 for x in pieces))
if __name__=='__main__':unittest.main()