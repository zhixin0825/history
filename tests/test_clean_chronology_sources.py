import importlib.util
from pathlib import Path
import unittest
P = Path(__file__).resolve().parents[1] / 'scripts/clean_chronology_sources.py'
spec = importlib.util.spec_from_file_location('clean_sources', P)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class CleaningTests(unittest.TestCase):
    def test_split_name_and_adjacent_notes(self):
        r=m.clean_kanripo('荆(注/文)\n(續/注)荆¶\n<pb:KR2b0007_WYG_007-1b>¶\n軻')
        self.assertEqual(r['main'].strip(), '荆荆軻')
        self.assertEqual([n['text'] for n in r['notes']], ['注文','續注'])
    def test_character_description_not_a_wrap(self):
        r=m.clean_kanripo('子[雨/單](音/灣[雨/單])及□□𤣥䝉《》')
        self.assertEqual(r['main'].strip(), '子[雨/單]及□□𤣥䝉《》')
        self.assertEqual(r['notes'][0]['text'], '音灣[雨/單]')
    def test_nested_multiline_note(self):
        r=m.clean_kanripo('甲(注(再注)¶\n<pb:x>\n文)乙')
        self.assertEqual(r['main'].strip(), '甲乙')
        self.assertEqual(r['notes'][0]['text'], '注(再注)文')
    def test_unbalanced_fails(self):
        for s in ['甲(乙','甲)乙','甲[雨/單']:
            with self.assertRaises(ValueError): m.clean_kanripo(s)
    def test_metadata_and_crlf(self):
        r=m.clean_kanripo('#+TITLE: 書\r\n甲¶\r\n乙')
        self.assertEqual(r['main'].strip(), '甲乙')
        self.assertEqual(r['metadata'], ['#+TITLE: 書'])
    def test_unknown_punctuation_preserved(self):
        r=m.clean_kanripo('甲/乙《》□【丙】。？！')
        self.assertEqual(r['main'].strip(), '甲/乙《》□【丙】。？！')
    def test_ccdh_preserves_prose_and_time(self):
        blocks, markers=m.clean_ccdh('\ufeffG*1*Y*1\nQS*1*QM*1\n元年。\n春。王正月。\nG*12*Y*17\nQS*0*QM*0\n十七年\n','春秋')
        self.assertEqual(blocks[0]['lines'][1]['text'],'春。王正月。')
        self.assertEqual(blocks[0]['time_markers'][0]['month_index'],1)
        self.assertFalse(blocks[1]['has_prose'])
        self.assertEqual(len(markers),4)
    def test_ccdh_unknown_marker_fails(self):
        with self.assertRaises(ValueError): m.clean_ccdh('G*13*Y*1\n某事','春秋')

if __name__ == '__main__': unittest.main()
