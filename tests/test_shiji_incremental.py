"""Integrity tests; not a claim that historical readings have been independently verified."""
import hashlib,json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'chronicle/shiji-trial'
def loadl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
class IncrementalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=loadl(OUT/'data/records.jsonl');cls.byid={r['id']:r for r in cls.records}
        cls.lines=(ROOT/'texts/01_shiji_full.txt').read_text(encoding='utf-8-sig').splitlines()
    def test_original_and_quotes(self):
        raw=(ROOT/'texts/01_shiji_full.txt').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'5d14f1bb43b30fa18eda0580a35c99e82b9a0543567a34e2ed8f39de5dc992eb')
        for r in self.records:
            for e in r['evidence']:
                if e['key'].startswith('sj:'):
                    self.assertEqual(e['quote'],'\n'.join(self.lines[e['start_line']-1:e['end_line']]))
    def test_all_255_source_years_are_real_text(self):
        folder=ROOT/'working-texts/zuozhuan-punctuated-years'
        files=list((folder/'data').glob('zz-*.json'));self.assertEqual(len(files),255)
        years=[]
        for p in files:
            x=json.loads(p.read_text());years.append(x['year_bce'])
            self.assertIn('。',x['text']);self.assertNotIn('．',x['text'])
            self.assertEqual(sum(z['kind']=='zhuan' for z in x['layers']),1)
            self.assertEqual(hashlib.sha256(x['text'].encode()).hexdigest(),x['text_sha256'])
        self.assertEqual(sorted(years),list(range(468,723)))
    def test_reviewed_chapter_coverage(self):
        expected=[29,31,48,62,63,64,65,66,86]
        stats=json.loads((OUT/'data/audit.json').read_text());self.assertEqual(stats['full_chapters_first_review'],expected)
        for row in loadl(OUT/'data/source-ledger.jsonl'):
            if row['chapter'] in expected:self.assertNotEqual(row['status'],'待逐段处理')
    def test_backstory_is_not_redated(self):
        plans=json.loads((OUT/'data/reading-placements.json').read_text())['placements']
        self.assertEqual(len(plans),11)
        for p in plans:
            self.assertIsNone(self.byid[p['record_id']]['year_bce'])
            self.assertIsNone(p['occurrence_year_bce']);self.assertFalse(p['counts_as_new_event'])
            page=(OUT/f'years/bce-{p["reading_year_bce"]:04d}.md').read_text()
            self.assertIn('id="backstory-'+p['record_id']+'"',page)
    def test_merge_aliases_preserved_once(self):
        groups=loadl(OUT/'data/event-groups.jsonl')
        aliases=[i for g in groups for i in g['aliases']]
        self.assertEqual(len(aliases),len(set(aliases)));self.assertEqual(set(aliases),set(self.byid))
        for group in groups:
            if group['year_bce'] is None:continue
            page=(OUT/f'years/bce-{group["year_bce"]:04d}.md').read_text()
            for rid in group['aliases']:self.assertEqual(page.count(f'<a id="{rid}"></a>'),1)
    def test_old_record_ids_and_dates(self):
        old_count=sum(r.get('batch')=='initial' for r in self.records);self.assertEqual(old_count,122)
        s=json.loads((OUT/'data/audit.json').read_text());self.assertTrue(s['old_ids_preserved']);self.assertTrue(s['old_occurrence_dates_preserved'])
if __name__=='__main__':unittest.main()
