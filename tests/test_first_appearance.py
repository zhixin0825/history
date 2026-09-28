"""Regression tests: reading placement must not fabricate historical dates."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_shiji_trial import run
from shiji_first_appearance import plan_placements


class FirstAppearanceTests(unittest.TestCase):
    def setUp(self):
        self.base = ROOT / 'chronicle/shiji-trial'
        self.records = [json.loads(s) for s in (self.base / 'data/records.jsonl').read_text(encoding='utf-8').splitlines()]
        self.config = json.loads((self.base / 'first-appearance.json').read_text(encoding='utf-8'))

    def test_placement_preserves_unknown_dates(self):
        before = copy.deepcopy(self.records)
        plans = plan_placements(self.records, self.config)
        self.assertEqual(6, len(plans))
        self.assertTrue(all(p['occurrence_year_bce'] is None for p in plans))
        self.assertTrue(all(not p['counts_as_new_event'] for p in plans))
        self.assertEqual(before, self.records)

    def test_dated_backstory_must_not_be_moved(self):
        rid = self.config['entries'][0]['backstories'][0]['record_id']
        next(r for r in self.records if r['id'] == rid)['year_bce'] = 210
        with self.assertRaises(ValueError):
            plan_placements(self.records, self.config)

    def test_unknown_does_not_imply_earlier(self):
        self.config['entries'][0]['backstories'][0]['relation'] = 'unknown'
        with self.assertRaises(ValueError):
            plan_placements(self.records, self.config)

    def test_bogus_evidence_is_rejected(self):
        self.config['entries'][0]['backstories'][0]['basis_source_keys'] = ['sj:999999']
        with self.assertRaises(ValueError):
            plan_placements(self.records, self.config)

    def test_comments_cannot_anchor_appearance(self):
        self.config['entries'][2]['anchor_record_id'] = 'sj-063-L4622-01'
        with self.assertRaises(ValueError):
            plan_placements(self.records, self.config)

    def test_duplicate_record_placement_is_rejected(self):
        item = copy.deepcopy(self.config['entries'][0]['backstories'][0])
        self.config['entries'][1]['backstories'].append(item)
        with self.assertRaises(ValueError):
            plan_placements(self.records, self.config)

    def test_anchor_year_is_not_hardcoded(self):
        anchor_id = self.config['entries'][0]['anchor_record_id']
        next(r for r in self.records if r['id'] == anchor_id)['year_bce'] = 210
        p = plan_placements(self.records, self.config)[0]
        self.assertEqual(210, p['reading_year_bce'])
        self.assertIsNone(p['occurrence_year_bce'])

    def test_complete_rebuild_is_idempotent_and_retains_counts(self):
        def snapshot():
            return {str(p.relative_to(self.base)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.base.rglob('*') if p.is_file()}
        run(ROOT)
        before = snapshot()
        stats = run(ROOT)
        self.assertEqual(before, snapshot())
        self.assertEqual((122, 54, 68, 26), tuple(stats[k] for k in ('review_records','dated_records','undated_records','year_pages')))
        page = (self.base / 'years/bce-0209.md').read_text(encoding='utf-8')
        self.assertEqual(1, page.count('<a id="backstory-sj-048-L4206-01"></a>'))
        self.assertIn('此前的经历，确切年月未详', page)


if __name__ == '__main__':
    unittest.main()
