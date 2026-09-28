#!/usr/bin/env python3
"""Render human-readable annual pages from explicitly authored GPT paragraph reviews.
No model calls, no newly inferred punctuation, and no inferred historical dates.
Original punctuated sources are preserved; text and IDs are checked paragraph by paragraph.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

SOURCE_COMMIT = 'adc0cfcbc165d2a17d40b1bb77354b78e7a28020'
REPO = 'https://github.com/zhixin0825/history/blob/'
ALLOWED = {'事件', '时序', '残记'}

def dump(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + '\n', encoding='utf-8')

def run(root: Path) -> dict:
    root = root.resolve()
    out = root / 'chronicle/chunqiu'
    data_dir = root / 'working-texts/zuozhuan-punctuated-years/data'
    sources = {}
    all_years = []
    original_hashes = {}
    for p in sorted(data_dir.glob('zz-*.json')):
        raw = p.read_bytes()
        original_hashes[p] = hashlib.sha256(raw).hexdigest()
        d = json.loads(raw)
        g, y = int(d['ruler_index']), int(d['regnal_year'])
        jing = '\n\n'.join(x['text'] for x in d['layers'] if x['kind'] == 'jing')
        if not jing.strip():
            continue  # Later Zhuan-only years are not invented Jing chapters.
        paras = jing.split('\n\n')
        all_years.append((g, y, int(d['year_bce']), d, paras))
        for n, quote in enumerate(paras, 1):
            sources[(g, y, n)] = (p, d, quote)
    assert len(all_years) == 244, ('unexpected source scope', len(all_years))
    assert len(sources) == 1850, ('source paragraph count changed', len(sources))
    authored = {}
    for p in sorted((out / 'batches').glob('*.psv')):
        for rowno, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
            if not line.strip() or line.startswith('#'):
                continue
            f = line.split('|')
            if len(f) != 6:
                raise ValueError(f'{p}:{rowno}: expected six fields, got {len(f)}')
            gy, number, kind, title, plain, note = f
            g, y = map(int, gy.split('.'))
            key = (g, y, int(number))
            if key in authored or key not in sources:
                raise ValueError(f'{p}:{rowno}: duplicated or unknown source paragraph {key}')
            if kind not in ALLOWED or not title.strip() or not plain.strip():
                raise ValueError(f'{p}:{rowno}: empty or invalid review')
            sp, sd, quote = sources[key]
            continuation = g == 12 and (y > 14 or (y == 14 and key[2] > 1))
            authored[key] = {
                'id': f'cq-{g:02d}-{y:02d}-p{key[2]:03d}',
                'ruler_index': g, 'ruler': sd['ruler'], 'regnal_year': y,
                'year_bce': int(sd['year_bce']), 'source_paragraph': key[2],
                'layer': '获麟后续经' if continuation else '春秋经',
                'type': kind, 'title': title, 'plain': plain, 'editor_note': note,
                'quote': quote, 'quote_sha256': hashlib.sha256(quote.encode()).hexdigest(),
                'source_path': str(sp.relative_to(root)), 'source_url': sd['source_url'],
                'source_html_sha256': sd['raw_sha256'],
                'source_json_sha256': original_hashes[sp],
                'review_path': str(p.relative_to(root)), 'review_line': rowno,
                'review_status': '逐段白话初稿；未独立校勘，未作公历日换算',
            }
    missing = sorted(set(sources) - set(authored))
    if missing:
        dump(out / 'data/missing-paragraphs.json', missing)
        raise ValueError(f'{len(missing)} source paragraphs still lack an authored review: {missing[:20]}')
    (out / 'data').mkdir(parents=True, exist_ok=True)
    records = [authored[key] for key in sorted(authored)]
    write(out / 'data/records.jsonl', '\n'.join(json.dumps(r, ensure_ascii=False) for r in records))
    dump(out / 'data/missing-paragraphs.json', [])
    uncertain = [r for r in records if r['type'] == '残记']
    year_index = []
    for i, (g, y, bce, sd, paras) in enumerate(all_years):
        filename = f'bce-{bce:04d}.md'
        nav = ['[年份目录](../README.md)']
        if i:
            prev = all_years[i-1][2]
            nav.insert(0, f'[← 前{prev}年](bce-{prev:04d}.md)')
        if i + 1 < len(all_years):
            nxt = all_years[i+1][2]
            nav.append(f'[前{nxt}年 →](bce-{nxt:04d}.md)')
        rows = [authored[(g, y, j)] for j in range(1, len(paras)+1)]
        page = [f'# 公元前{bce}年｜鲁{sd["ruler"]}{y}年', ' · '.join(nav),
                '本页逐条解释《春秋》经文；严格经文、获麟后续经和只有季月的时间提示分别标明。年题沿用古史年条与传统公元年对照，不是现代公历逐日换算。',
                f'[本年完整经传原文](../../../working-texts/zuozhuan-punctuated-years/years/{filename})']
        sj = root / 'chronicle/shiji-trial/years' / filename
        if sj.exists():
            page.append(f'[《史记》本年补充与异说](../../shiji-trial/years/{filename})')
        last_layer = None
        for r in rows:
            if r['layer'] != last_layer:
                page.append('## ' + r['layer'])
                if r['layer'] == '获麟后续经':
                    page.append('以下内容属于获麟以后的续经，仍完整保留，但不冒称都在严格《春秋经》的原终点以前。')
                last_layer = r['layer']
            rid = r['id']
            label = '〔时间提示〕' if r['type'] == '时序' else ('〔残记待核〕' if r['type'] == '残记' else '')
            page += [f'<a id="{rid}"></a>', f'### {r["source_paragraph"]}. {label}{r["title"]}', r['plain'], f'[看对应原文](#source-{rid})']
            if r['editor_note']:
                page += ['<details><summary>字句与编年说明</summary>', r['editor_note'], '</details>']
        page += ['---', '## 本年相关史料',
                 f'[来源原网页]({sd["source_url"]}) · [已保存的固定版本]({REPO}{SOURCE_COMMIT}/working-texts/zuozhuan-punctuated-years/data/zz-{g:02d}-{y:02d}.json)',
                 '下列文字直接取自保存的有标点原文，不由模型默写；网页旧字、缺字和句读疑点未静默改掉。']
        for r in rows:
            page += [f'<a id="source-{r["id"]}"></a>', f'### 史料 {r["source_paragraph"]}｜{r["layer"]}',
                     '\n'.join('> ' + s for s in r['quote'].splitlines()), f'[返回白话条目](#{r["id"]})']
        page += ['---', ' · '.join(nav)]
        write(out / 'years' / filename, '\n\n'.join(page))
        year_index.append({'year_bce': bce, 'ruler': sd['ruler'], 'regnal_year': y,
                           'paragraphs': len(rows), 'path': f'years/{filename}',
                           'strict_jing_paragraphs': sum(r['layer'] == '春秋经' for r in rows),
                           'continuation_paragraphs': sum(r['layer'] != '春秋经' for r in rows)})
    dump(out / 'data/year-index.json', year_index)
    dump(out / 'data/unresolved-records.json', uncertain)
    counts = dict(collections.Counter(r['type'] for r in records))
    audit = {'source_years_with_jing': len(all_years), 'all_source_paragraphs': len(sources),
             'authored_source_paragraphs': len(records), 'missing_source_paragraphs': 0,
             'strict_jing_years': len({r['year_bce'] for r in records if r['layer'] == '春秋经'}),
             'strict_jing_paragraphs': sum(r['layer'] == '春秋经' for r in records),
             'post_lin_continuation_paragraphs': sum(r['layer'] != '春秋经' for r in records),
             'year_pages': len(year_index), 'record_types': counts,
             'explicit_residual_records': len(uncertain), 'originals_unchanged': True,
             'every_paragraph_has_exact_quote_and_backlink': True,
             'complete_paragraph_vernacular_first_draft': True,
             'complete_zuozhuan_vernacular': False,
             'independent_textual_or_historical_review_complete': False,
             'scope': '《春秋经》全部现存工作本段落与获麟后续经；不是《左传》全部传文白话译本。'}
    for path, digest in original_hashes.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, ('source modified', path)
    for p in (out / 'years').glob('*.md'):
        txt = p.read_text(encoding='utf-8')
        for href in re.findall(r'\]\(([^)]+)\)', txt):
            if href.startswith(('https://', 'http://')):
                continue
            part, _, frag = href.partition('#')
            target = (p.parent / part).resolve() if part else p.resolve()
            if target == (out / 'README.md').resolve():
                continue
            assert target.exists(), (p, href)
            if frag:
                assert f'id="{frag}"' in target.read_text(encoding='utf-8'), (p, href)
    dump(out / 'data/audit.json', audit)
    front = ['# 逐年读《春秋》',
             f'本工作本全部 **{len(records)}段经文及续经** 已完成逐段白话初稿，生成 **{len(year_index)}张年页**。严格《春秋经》从前722年到前481年，共242年；获麟后同年及前480、479年的续经另作标识。',
             '每条白话都能跳到本页对应原文，再返回正文。纯季月句按时间提示处理，不伪造事件；缺字、残记和年代异说明确保留。',
             '**这里完成的是《春秋经》的逐段白话初稿，不是《左传》传文全译，也不是独立学术校勘完成。** 《史记》补充入口随各年度连接；整个全史编年项目的完成度另见总进度。',
             '[总进度](../PROGRESS.md) · [逐条数据](data/records.jsonl) · [覆盖检查](data/audit.json) · [残记清单](data/unresolved-records.json) · [底本质量说明](../../working-texts/zuozhuan-punctuated-years/QUALITY_NOTES.md)',
             '来源是仓库已保存的古籍原文及现有标点，不复制来源网站的现代译文、注释或赏析。本目录白话为本项目逐段新写；有疑字仍保留来源字样。',
             '## 年份目录', '| 年份 | 鲁国君年 | 原文段数 |\n|---|---|---:|']
    front += [f'| [前{x["year_bce"]}年]({x["path"]}) | {x["ruler"]}{x["regnal_year"]}年 | {x["paragraphs"]} |' for x in year_index]
    front += ['\n## 重建', '`python scripts/build_chunqiu_reader.py`。只排版和验证已写入的白话，不调用模型，不把程序扫描冒充内容解读。']
    write(out / 'README.md', '\n\n'.join(front[:7]) + '\n\n' + '\n'.join(front[7:]))
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return audit

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    run(parser.parse_args().root)
