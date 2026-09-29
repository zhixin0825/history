#!/usr/bin/env python3
"""Render traceable source views; validate and publish a manually reviewed Xiang batch.
No language model or external text service is called. Original JSON files are read-only.
A coverage link records editorial routing, not independent proof of historical truth.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'chronicle/chunqiu'
SRC = ROOT / 'working-texts/zuozhuan-punctuated-years/data'
REVIEW = BASE / 'review/xiang-gong'
MAP = REVIEW / 'routing.json'
PIN = '3dce2172b7c6ebd9c2e1aa4045e46eccd031b7f4'


def cn(n: int) -> str:
    ds = '零一二三四五六七八九'
    if n == 1:
        return '元'
    if n < 10:
        return ds[n]
    if n < 20:
        return '十' + (ds[n % 10] if n % 10 else '')
    return ds[n // 10] + '十' + (ds[n % 10] if n % 10 else '')


def put(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def source_view(y: int):
    path = SRC / f'zz-09-{y:02}.json'
    raw = path.read_bytes()
    obj = json.loads(raw)
    assert obj['regnal_year'] == y and obj['year_bce'] == 573-y
    text_hash = hashlib.sha256(obj['text'].encode()).hexdigest()
    assert text_hash == obj['text_sha256'], f'Changed original text: {path}'
    paras = {}
    lines = [f'# 襄公{cn(y)}年｜前{573-y}年：经传原文', '',
             f'[年度白话](../years/bce-{573-y:04}.md) · [原始 JSON](../../../working-texts/zuozhuan-punctuated-years/data/{path.name})', '',
             f'原文版本固定于 `{PIN}`；本页只分段编号、分行显示，不校改字词。', '',
             f'原始文本 SHA-256：`{text_hash}`。', '']
    prefixes = {'jing':'j', 'zhuan':'t'}
    counters = {}
    for layer in obj['layers']:
        kind = layer['kind']
        prefix = prefixes.get(kind, 'm')
        lines += [f'## {layer.get("source_heading", kind)}', '']
        for para in re.split(r'\n\s*\n', layer['text']):
            if not para.strip():
                continue
            counters[prefix] = counters.get(prefix, 0) + 1
            pid = f'{prefix}{counters[prefix]:03}'
            para = para.strip()
            paras[pid] = para
            lines += [f'<a id="{pid}"></a>', f'### {pid}', '']
            # Wrapping is presentation-only: join these lines to recover the paragraph.
            lines += ['> ' + para[i:i+90] for i in range(0, len(para), 90)]
            lines += ['']
    put(BASE / 'sources' / f'zz-09-{y:02}.md', '\n'.join(lines))
    return obj, paras, hashlib.sha256(raw).hexdigest()


def events_from_page(text: str):
    parts = text.split('\n## 本年相关史料\n', 1)
    assert len(parts) == 2, 'Missing annual source section'
    body = parts[0]
    found = list(re.finditer(r'^(\d+)\.\s+\*\*(.+?)\*\*', body, re.M))
    ids = [int(m.group(1)) for m in found]
    assert ids == list(range(1, len(ids)+1)), f'Broken event numbers: {ids}'
    assert found, 'No annual entries'
    return body, found


def main():
    REVIEW.mkdir(parents=True, exist_ok=True)
    routes = json.loads(MAP.read_text()) if MAP.exists() else {}
    status, index, review = [], [], []
    errors = []
    for y in range(1, 32):
        obj, paras, raw_hash = source_view(y)
        bce = 573-y
        page = BASE / 'years' / f'bce-{bce:04}.md'
        original = page.read_text(encoding='utf-8')
        body, found = events_from_page(original)
        n_events = len(found)
        counts = {p:sum(k.startswith(p) for k in paras) for p in ('j','t','m')}
        row = {'regnal_year':y, 'year_bce':bce, 'entries':n_events,
               'original_file_sha256':raw_hash, 'source_paragraphs':counts,
               'routing_status':'not_yet_registered'}
        index += [f'| {y} | [{bce}](../../years/bce-{bce:04}.md) | {n_events} | {counts["j"]} | {counts["t"]} | [原文](../../sources/zz-09-{y:02}.md) |']
        review += [f'## 襄公{cn(y)}年｜前{bce}', '']
        review += [f'- {m.group(1)}. {m.group(2)}' for m in found]
        review += ['', '### 经文逐条', '']
        for pid, para in paras.items():
            if pid.startswith('j'):
                review += [f'- `{pid}` {para}']
        review += ['', '### 传文段落入口', '']
        for pid, para in paras.items():
            if not pid.startswith('j'):
                review += [f'- `{pid}` {para[:80]}'+('……' if len(para)>80 else '')]
        review += ['']
        route = routes.get(str(y))
        if route is not None:
            # j/t arrays are in original paragraph order. Each value is an event
            # number, a list of numbers, or {note: n, reason: ...} for note-only use.
            assigned = {}
            for prefix in ('j','t','m'):
                keys = [p for p in paras if p.startswith(prefix)]
                vals = route.get(prefix, [])
                if len(keys) != len(vals):
                    errors.append(f'{y}: {prefix} has {len(keys)} paragraphs but {len(vals)} routes')
                    continue
                assigned.update(zip(keys, vals))
            per_event = {n:[] for n in range(1,n_events+1)}
            notes = {int(k):v for k,v in route.get('notes',{}).items()}
            ledger = []
            for pid, dest in assigned.items():
                is_note = isinstance(dest, dict)
                ids = dest.get('note') if is_note else dest
                ids = ids if isinstance(ids,list) else [ids]
                if is_note and not dest.get('reason'):
                    errors.append(f'{y}/{pid}: note-only source needs a reason')
                for n in ids:
                    if not isinstance(n,int) or n not in per_event:
                        errors.append(f'{y}/{pid}: invalid entry {n}')
                    else:
                        per_event[n].append(pid)
                ledger.append({'paragraph':pid, 'entries':ids,
                               'route':'note' if is_note else 'narrative',
                               'reason':dest.get('reason','') if is_note else '',
                               'sha256':hashlib.sha256(paras[pid].encode()).hexdigest()})
            for n, ids in per_event.items():
                if not ids:
                    errors.append(f'{y}: entry {n} has no original paragraph')
            row['routing_status'] = 'registered'
            row['routing'] = ledger
            if len(assigned)==len(paras) and all(per_event.values()):
                # Only turn this batch's inline reference markers into genuine links.
                body = re.sub(r'\[(\d+)\](?!\()', r'[\1](#source-\1)', body)
                foot = ['## 本年相关史料','']
                for n in range(1,n_events+1):
                    foot += [f'<a id="source-{n}"></a>', f'{n}. ']
                    for pid in dict.fromkeys(per_event[n]):
                        book = '春秋' if pid.startswith('j') else '左传'
                        para = paras[pid]
                        label = f'《{book}·襄公{cn(y)}年》'
                        target = f'../sources/zz-09-{y:02}.md#{pid}'
                        # Short exact excerpt; the linked paragraph retains every word.
                        excerpt = para if len(para)<=260 else para[:220]+'……'
                        foot += [f'   **{label}**（[原文 {pid}]({target})）：', '']
                        foot += ['   > '+s for s in excerpt.splitlines()]
                        foot += ['']
                    extra = notes.get(n)
                    reasons = [v['reason'] for k,v in assigned.items() if isinstance(v,dict) and n in (v['note'] if isinstance(v['note'],list) else [v['note']])]
                    if extra or reasons:
                        foot += ['   **说明：** '+' '.join(([extra] if extra else [])+list(dict.fromkeys(reasons))), '']
                foot += [f'[本年完整经传原文](../sources/zz-09-{y:02}.md) · [底本网页]({obj["source_url"]})','']
                put(page, body.rstrip()+'\n\n'+'\n'.join(foot))
        status.append(row)
    report = {'base_source_commit':PIN, 'years':31,
              'year_pages_found':len(status),
              'annual_entries':sum(s['entries'] for s in status),
              'source_hashes_verified':31,
              'routing_years_registered':sum(s['routing_status']=='registered' for s in status),
              'errors':errors, 'annual_status':status,
              'limits':'Routing verifies that source paragraphs have an editorial destination. It is not a proof of exhaustive clause extraction, translation correctness, or independent historical corroboration. Shiji integration is not included.'}
    put(REVIEW/'audit.json', json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    put(REVIEW/'source-checklist.md', '# 襄公原文与年度条目对照\n\n这是一份复核工作表，不把自动匹配当作史学认证。\n\n'+'\n'.join(review))
    intro = ['# 鲁襄公三十一年：复核记录','',
             f'范围：前572—前542年。年度页 {len(status)}；年度叙述条目 {report["annual_entries"]}；原文哈希核验 31／31。',
             f'逐段去向登记：{report["routing_years_registered"]}／31 年。','',
             '每条经、传原段均有固定编号。正文只叙事，编年差异、回叙和评论处理放在对应史料注。',
             '登记完成不等于逐字白话、没有遗漏任何分句，或完成独立学术校勘。《史记》融合另行计算。','',
             '| 鲁襄公纪年 | 公元前年份页 | 叙述条目 | 经段 | 传段 | 原文 |',
             '|---|---|---:|---:|---:|---|']
    put(REVIEW/'README.md', '\n'.join(intro+index)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='annual_status'},ensure_ascii=False,indent=2))
    if errors:
        raise SystemExit('Source routing errors; generated output must not be published.')

if __name__=='__main__':
    main()
