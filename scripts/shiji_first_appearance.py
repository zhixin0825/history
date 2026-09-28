"""Add source-reviewed backstories at provisional first appearances.

This changes reading placement, never the occurrence dates or original records.
Python 3.10+, standard library only. Called by build_shiji_trial.run().
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path
from typing import Any


def plan_placements(records: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate explicit editorial assignments; never infer 'earlier' from null dates."""
    if config.get('schema_version') != 1:
        raise ValueError('Unsupported first-appearance schema')
    by_id = {r['id']: r for r in records}
    if len(by_id) != len(records):
        raise ValueError('Duplicate record IDs')
    plans: list[dict[str, Any]] = []
    used: set[str] = set()
    entities: set[str] = set()
    for entry in config['entries']:
        entity = entry['entity_id']
        if entity in entities:
            raise ValueError(f'Duplicate entity: {entity}')
        entities.add(entity)
        anchor = by_id[entry['anchor_record_id']]
        if anchor['year_bce'] is None or anchor['type'] != '事件':
            raise ValueError('First appearance must reference a dated event, not a comment')
        if entry.get('anchor_scope') != 'current_reviewed_corpus_provisional':
            raise ValueError('This partial corpus cannot establish a definitive global first appearance')
        for item in entry['backstories']:
            rid = item['record_id']
            record = by_id[rid]
            if rid in used:
                raise ValueError(f'Duplicate backstory placement: {rid}')
            used.add(rid)
            if record['year_bce'] is not None:
                raise ValueError('Dated records stay in their own year; add a link rather than moving them')
            if record['type'] not in ('事件', '背景'):
                raise ValueError('Comments, documents and uncertain identities require separate treatment')
            if item.get('relation') != 'before_anchor' or not item.get('basis', '').strip():
                raise ValueError('An explicit source-based before-anchor justification is required')
            keys = {e['key'] for e in record['evidence']}
            evidence_keys = item.get('basis_source_keys', [])
            if not evidence_keys or not set(evidence_keys).issubset(keys):
                raise ValueError('Before-anchor basis must reference this backstory\'s actual evidence')
            plans.append({
                'record_id': rid,
                'entity_id': entity,
                'person_label': entry['person_label'],
                'occurrence_year_bce': record['year_bce'],
                'occurrence_time_label': record['time_raw_or_editor_label'],
                'reading_year_bce': anchor['year_bce'],
                'reading_anchor_record_id': anchor['id'],
                'reading_mode': 'first_appearance_backstory',
                'relation': 'before_anchor',
                'basis': item['basis'],
                'basis_source_keys': evidence_keys,
                'anchor_scope': entry['anchor_scope'],
                'anchor_note': entry['anchor_note'],
                'counts_as_new_event': False,
            })
    return plans


def apply_placements(root: Path, stats: dict[str, Any]) -> dict[str, Any]:
    """Apply to freshly rebuilt year pages; existing source IDs and dates stay intact."""
    out = root / 'chronicle/shiji-trial'
    record_file = out / 'data/records.jsonl'
    record_bytes = record_file.read_bytes()
    records = [json.loads(s) for s in record_bytes.decode('utf-8').splitlines()]
    by_id = {r['id']: r for r in records}
    config = json.loads((out / 'first-appearance.json').read_text(encoding='utf-8'))
    plans = plan_placements(records, config)
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for p in plans:
        grouped[p['reading_anchor_record_id']].append(p)

    def ref_anchor(key: str) -> str:
        return 'ref-' + re.sub(r'[^a-zA-Z0-9-]', '-', key)

    def backstory_html_id(rid: str) -> str:
        return 'backstory-' + rid

    def insert_after_record(page: str, rid: str, extra: str) -> str:
        start = page.index(f'<a id="{rid}"></a>')
        end = page.index('</details>', start) + len('</details>')
        return page[:end] + '\n\n' + extra + page[end:]

    index = ['# 人物首次登场与前事补叙',
             '[返回试编目录](../README.md) · [已确认编写规则](../../EDITORIAL_RULES.md)',
             '这里记录阅读位置，不是新的定年结果。下列往事仍未确年；只因原文支持其发生在登场事件之前，才在该事件旁补叙。当前只处理了部分篇章，登场位置均为暂定。',
             '| 人物 | 补叙所在页 | 往事 |\n|---|---|---|']
    for anchor_id, items in grouped.items():
        year = items[0]['reading_year_bce']
        year_path = out / f'years/bce-{year:04d}.md'
        page = year_path.read_text(encoding='utf-8')
        chunks = []
        for p in items:
            r = by_id[p['record_id']]
            hid = backstory_html_id(r['id'])
            refs = ' · '.join(
                f'[{e["title"]} L{e["start_line"]}](../appendix/sources.md#{ref_anchor(e["key"])})'
                for e in r['evidence'])
            chunks.append('\n\n'.join([
                f'<a id="{hid}"></a>',
                f'#### 登场前事｜{p["person_label"]}：{r["title"]}',
                f'> 此前的经历，确切年月未详。这里补叙，不表示事情发生于公元前{year}年。',
                r['plain'], refs,
                '<details><summary>补叙位置与时间依据</summary>',
                p['basis'] + '\n\n' + p['anchor_note'],
                f'[原记录与原有时间说明](../appendix/unplaced.md#{r["id"]})；此次补叙不新增事件编号或归年结果。',
                '</details>'
            ]))
            href = f'../years/bce-{year:04d}.md#{hid}'
            index.append(f'| {p["person_label"]} | [前{year}年]({href}) | {r["title"]} |')
        page = insert_after_record(page, anchor_id, '\n\n'.join(chunks))
        year_path.write_text(page, encoding='utf-8')

    unplaced_path = out / 'appendix/unplaced.md'
    unplaced = unplaced_path.read_text(encoding='utf-8')
    for p in plans:
        href = f'../years/bce-{p["reading_year_bce"]:04d}.md#{backstory_html_id(p["record_id"])}'
        extra = f'**阅读位置：**已在[人物首次登场处]({href})补叙。实际年份仍未确定；不是两条不同事件。'
        unplaced = insert_after_record(unplaced, p['record_id'], extra)
    unplaced_path.write_text(unplaced, encoding='utf-8')
    (out / 'appendix/first-appearances.md').write_text('\n\n'.join(index[:3]) + '\n\n' + '\n'.join(index[3:]) + '\n', encoding='utf-8')
    (out / 'data/reading-placements.json').write_text(json.dumps({
        'schema_version': 1, 'source_records': 'records.jsonl',
        'description': '阅读位置与实际发生时间分开；不增加已定年计数。',
        'placements': plans,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    stats = dict(stats)
    stats.update({
        'first_appearance_backstories': len(plans),
        'people_with_first_appearance_backstories': len({p['entity_id'] for p in plans}),
        'first_appearance_year_pages': len({p['reading_year_bce'] for p in plans}),
        'occurrence_dates_changed_by_backstory_placement': 0,
    })
    (out / 'data/audit.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    readme_path = out / 'README.md'
    readme = readme_path.read_text(encoding='utf-8').replace('[问题与暂定办法](REPORT.md)', '[试做问题与已确认办法](REPORT.md)')
    notice = ('## 已确认规则与登场前事\n\n'
              '[编写规则](../EDITORIAL_RULES.md)已按用户意见确认。人物首次登场时补叙此前经历；展示位置不等于发生年份。\n\n'
              f'本轮将{len(plans)}条已初审往事，放到{len({p["entity_id"] for p in plans})}个人的暂定首次登场处；原{stats["dated_records"]}条归年记录和{stats["undated_records"]}条未确年记录的口径不变。'
              '[查看人物与补叙入口](appendix/first-appearances.md)。这不是新增篇章的内容审读。\n\n')
    readme = readme.replace('## 已有年份页（非连续年表）', notice + '## 已有年份页（非连续年表）')
    readme_path.write_text(readme, encoding='utf-8')
    if record_file.read_bytes() != record_bytes:
        raise AssertionError('Backstory placement must not mutate occurrence records')
    return stats
