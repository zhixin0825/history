#!/usr/bin/env python3
"""Render the manually edited Zhao 1–10 batch; fail closed on source omissions.

The program does not translate or invent events. The PSV files contain the
editor's narratives and exact paragraph-prefix selectors. Every source paragraph
must have exactly one destination. Coverage is not a claim of scholarly accuracy.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'ee3959bcc3fd321dc5fa9d316ebb6d3526533305'
REPO = 'https://github.com/zhixin0825/history'
BATCH = ROOT / 'chronicle/chunqiu/zhaogong'
OUT = ROOT / 'chronicle/chunqiu/years'
SOURCE_DIR = 'working-texts/zuozhuan-punctuated-years/years'
NAMES = ['元', '二', '三', '四', '五', '六', '七', '八', '九', '十']
HASHES = [
    'c13617e04ec4152c2b4c667d68d280adf931f697',
    '07fc4c3f87195fc7728cf123774f43416637eb2a',
    'cfecbc579d03b582c1dce8a920f9f67d7f65c50e',
    '438ea066cfc3bcf5e577d240ac1d8d1fb44f48f0',
    'fe2cd0c8d98f11290d5515016856d30f10c1ed03',
    'a0c96157f7bec173655697abadbe99edec1d3c2e',
    '5e4bfa17203897e8a24a2b6184011323ddb3259e',
    '6d4a2b892e166d27be3eeaa702d61ba7c088836b',
    '37f45a6db99978c3cfdd1455e857229d7b8a99ba',
    'd44b96323a36013023e04dca381b937b31802a30',
]
MODES = {'E': 'event', 'B': 'retrospective_background',
         'C': 'commentary_or_belief', 'M': 'mixed_time_or_commentary'}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def parse_source(year: int) -> tuple[str, str, list[dict]]:
    path = f'{SOURCE_DIR}/bce-{542-year:04d}.md'
    raw = (ROOT / path).read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    require(blob == HASHES[year-1], f'Source changed: {path}, {blob}')
    text = raw.decode('utf-8')
    found = re.search(r'\[来源原文\]\(([^)]+)\)', text)
    require(found is not None, f'Missing source URL: {path}')
    paragraphs: list[dict] = []
    section = None
    buf: list[str] = []
    begin = 0
    end = 0

    def flush() -> None:
        nonlocal buf
        if buf:
            value = '\n'.join(buf)
            paragraphs.append({'kind': section, 'text': value, 'start_line': begin,
                               'end_line': end, 'sha256': hashlib.sha256(value.encode()).hexdigest()})
            buf = []

    for number, line in enumerate(text.splitlines(), 1):
        if line in ('## 经', '## 传'):
            flush()
            section = 'jing' if line == '## 经' else 'zhuan'
        elif line.startswith('<a ') or line.startswith('## '):
            flush()
            if line.startswith('## '):
                section = None
        elif not line.strip():
            flush()
        elif section:
            if not buf:
                begin = number
            buf.append(line)
            end = number
    flush()
    require(any(p['kind'] == 'jing' for p in paragraphs), f'No jing: {path}')
    require(any(p['kind'] == 'zhuan' for p in paragraphs), f'No zhuan: {path}')
    return path, found.group(1), paragraphs


def read_events() -> dict[int, list[dict]]:
    result: dict[int, list[dict]] = {year: [] for year in range(1, 11)}
    for file in (BATCH / 'data' / n for n in ('events-01-05.psv', 'events-06-10.psv')):
        for lineno, line in enumerate(file.read_text(encoding='utf-8').splitlines(), 1):
            if not line.strip() or line.startswith('#'):
                continue
            parts = line.split('|')
            require(len(parts) == 7, f'{file.name}:{lineno}: expected seven fields, got {len(parts)}')
            year, title, body, jing, zhuan, note, shiji = parts
            y = int(year)
            require(y in result, f'Unexpected year: {y}')
            require(bool(title.strip()) and bool(body.strip()), f'Empty narrative: {file}:{lineno}')
            result[y].append({'title': title, 'body': body.replace('\\n', '\n'),
                              'jing': jing.split('~') if jing else [],
                              'zhuan': zhuan.split('~') if zhuan else [],
                              'note': note.replace('\\n', '\n'),
                              'shiji': shiji.split('~') if shiji else []})
    require(all(result.values()), 'One or more years have no narratives')
    return result


def select(paragraphs: list[dict], kind: str, selector: str) -> tuple[int, str]:
    mode = 'E'
    if len(selector) > 3 and selector[1:3] == '::':
        mode, selector = selector[0], selector[3:]
    require(mode in MODES, f'Unknown disposition: {mode}')
    matches = [i for i, p in enumerate(paragraphs) if p['kind'] == kind and p['text'].startswith(selector)]
    require(len(matches) == 1, f'{kind} selector must match exactly once: {selector!r}; got {len(matches)}')
    return matches[0], MODES[mode]


def write(path: Path, text: str) -> None:
    # Preserve cumulative metadata when later batches exist.
    if (BATCH / 'data/audit-11-20.json').exists():
        if path in (BATCH / 'README.md', BATCH / 'SHIJI-CROSSWALK.md', ROOT / 'chronicle/chunqiu/README.md'):
            return
        if path == OUT / 'bce-0532.md' and (OUT / 'bce-0531.md').exists():
            text = text.replace('下一年：前531（昭公十一年，尚未编写）', '[下一年：前531](bce-0531.md)')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + '\n', encoding='utf-8')


def shiji_status(year: int) -> str:
    if year == 1:
        return '已把《鲁周公世家》襄公末年的继位前事接入第1条；这些前事不另计为本年事件。'
    if year == 2:
        return '本篇所载“三年，朝晋至河”与经传二年条对读后，归入本页第5条；差异与暂取经传纪年的理由见同号史料。'
    if year == 3:
        return '《鲁周公世家》本年标签下的“朝晋至河”，已与[前540年（二年）第5条](bce-0540.md#event-5)合并。本页不再编出第二次相同出行。'
    if year == 4:
        return '本篇申会条已接入第2条；“称病不往”与传文“辞以时祭”分别保留，不拼成一个确定借口。'
    if year == 7:
        return '本篇“七年，季武子卒”已接入第12条；本篇标签为八年的章华台故事，与经传七年条合并在第3条。'
    if year == 8:
        return '《鲁周公世家》本年标签下的章华台故事，已与[前535年（七年）第3条](bce-0535.md#event-3)合并，不在本年再写一次。'
    return '已检查《鲁周公世家》昭公前十年的相关段落，未见可另补入本年的明确年事。这不表示《史记》其他篇章没有本年材料；其他世家、列传尚未在本批逐篇审读。'


def main() -> None:
    events = read_events()
    extras = json.loads((BATCH / 'data/shiji-excerpts.json').read_text(encoding='utf-8'))
    rendered: dict[Path, str] = {}
    mapping: list[dict] = []
    yearly: list[dict] = []
    used_extra: Counter = Counter()
    for y, rows in events.items():
        source_path, source_url, paras = parse_source(y)
        assigned: dict[int, tuple[int, str]] = {}
        chosen: dict[int, list[int]] = {}
        for n, event in enumerate(rows, 1):
            chosen[n] = []
            for kind in ('jing', 'zhuan'):
                for selector in event[kind]:
                    idx, mode = select(paras, kind, selector)
                    require(idx not in assigned, f'Year {y}: duplicate source paragraph {paras[idx]["text"][:30]}')
                    assigned[idx] = (n, mode)
                    chosen[n].append(idx)
            require(chosen[n] or event['shiji'], f'Year {y} event {n}: no source')
            for key in event['shiji']:
                require(key in extras['excerpts'], f'Unknown Shiji key: {key}')
                used_extra[key] += 1
        missing = [p['text'][:60] for i, p in enumerate(paras) if i not in assigned]
        require(not missing, f'Year {y} unmapped source paragraphs: {missing}')
        year_bce = 542 - y
        regnal = NAMES[y-1]
        if y == 1:
            prev = f'[上一年：前542（襄公复核稿，尚未结审）]({REPO}/blob/604211235a7cc43c755a6e5cd55f519a999a9aa9/chronicle/chunqiu/years/bce-0542.md)'
        else:
            prev = f'[上一年：前{year_bce+1}](bce-{year_bce+1:04d}.md)'
        nxt = f'[下一年：前{year_bce-1}](bce-{year_bce-1:04d}.md)' if y < 10 else '下一年：前531（昭公十一年，尚未编写）'
        nav = f'{prev} · [本批目录](../zhaogong/README.md) · [春秋目录](../README.md) · {nxt}'
        page = [f'# 公元前{year_bce}年（鲁昭公{regnal}年）', nav,
                '> 本页完成第一轮白话整理与逐段去向登记；不是现代学术校勘定本。古历月份不直接换算成同号公历月份。',
                '## 本年纪事']
        for n, event in enumerate(rows, 1):
            page.extend([f'<a id="event-{n}"></a>', f'{n}. **{event["title"]}**',
                         event['body'] + f' [{n}](#note-{n})'])
        page.extend(['## 《鲁周公世家》本批对照', shiji_status(y),
                     '[所核原文与归年登记](../zhaogong/SHIJI-CROSSWALK.md)',
                     '## 本年相关史料',
                     '以下逐段保留本页采用的古籍原文。段中夹有回叙、占候、人物判断或后事的，依同号说明理解，不把整段都算作本年事实。来源工作本的缺字标记原样保留。'])
        for n, event in enumerate(rows, 1):
            page.extend([f'<a id="note-{n}"></a>', f'### [{n}] {event["title"]}'])
            for idx in chosen[n]:
                p = paras[idx]
                kindname = '《春秋》' if p['kind'] == 'jing' else '《左传》'
                link = f'{REPO}/blob/{BASE}/{source_path}#L{p["start_line"]}-L{p["end_line"]}'
                page.extend([f'**{kindname}·昭公{regnal}年** · [固定版本原文]({link})',
                             '\n'.join('> ' + line for line in p['text'].splitlines())])
                mapping.append({'regnal_year': y, 'year_bce': year_bce, 'kind': p['kind'],
                                'source_file': source_path, 'source_commit': BASE,
                                'start_line': p['start_line'], 'end_line': p['end_line'],
                                'sha256': p['sha256'], 'prefix': p['text'][:40],
                                'event': n, 'disposition': assigned[idx][1],
                                'destination': f'chronicle/chunqiu/years/bce-{year_bce:04d}.md#note-{n}'})
            for key in event['shiji']:
                item = extras['excerpts'][key]
                page.extend([f'**《史记·鲁周公世家》·{item["label"]}** · [所核网页固定版本]({extras["source_url"]})',
                             '> ' + item['quote']])
            if event['note']:
                page.append('**说明：** ' + event['note'])
            page.append(f'[返回第{n}条](#event-{n})')
        page.extend([f'[本年完整经传工作本](../../../{source_path}) · [工作本来源网页]({source_url})', nav])
        text = '\n\n'.join(page) + '\n'
        require(text.count('<a id="event-') == len(rows), 'Event anchor mismatch')
        require(text.count('<a id="note-') == len(rows), 'Note anchor mismatch')
        rendered[OUT / f'bce-{year_bce:04d}.md'] = text
        counts = Counter(p['kind'] for p in paras)
        yearly.append({'regnal_year': y, 'year_bce': year_bce, 'narrative_entries': len(rows),
                       'jing_paragraphs': counts['jing'], 'zhuan_paragraphs': counts['zhuan'],
                       'mapped_paragraphs': len(assigned), 'unmapped_paragraphs': 0,
                       'source_blob_verified': HASHES[y-1],
                       'shiji_excerpt_references': sum(len(e['shiji']) for e in rows)})
    require(set(used_extra) == set(extras['excerpts']), 'A saved Shiji excerpt has no destination')
    audit = {'batch': '鲁昭公元年至十年', 'editorial_date': '2026-09-30',
             'status': 'first_readable_pass_with_paragraph_mapping',
             'source_commit': BASE, 'year_pages': 10,
             'narrative_entries': sum(r['narrative_entries'] for r in yearly),
             'jing_paragraphs': sum(r['jing_paragraphs'] for r in yearly),
             'zhuan_paragraphs': sum(r['zhuan_paragraphs'] for r in yearly),
             'mapped_paragraphs': len(mapping), 'unmapped_paragraphs': 0,
             'duplicate_assignments': 0, 'source_blob_checks_passed': 10,
             'shiji_unique_excerpts': len(extras['excerpts']),
             'modern_scholarly_collation_complete': False,
             'all_shiji_chapters_reviewed': False,
             'xianggong_review_completed_by_this_batch': False,
             'limitation': '段落有去向不等于逐句翻译或学术定论；长篇赋诗、占候、评论保留在原文及说明。',
             'years': yearly}
    table = ['| 页面 | 本年入口 | 条目 |', '|---|---|---|']
    for y, rows in events.items():
        bce = 542-y
        table.append(f'| [昭公{NAMES[y-1]}年｜前{bce}](../years/bce-{bce:04d}.md) | {rows[0]["title"]} | {len(rows)} |')
    readme = f'''# 鲁昭公第一段｜元年至十年（前541—前532）

本批已写成 **10张年度页面、{audit['narrative_entries']}条白话叙述**。不是32年昭公组全部完成；十一年至三十二年尚未在本批编写。

每条先列事件，再讲过程，末尾链接到同号原文。经传不拆成两套故事；《鲁周公世家》的同一事件合并叙述，不另造一次出行。

{chr(10).join(table)}

## 可核查范围

十年来源工作本的Git blob校验全部通过。共{audit['jing_paragraphs']}段经文、{audit['zhuan_paragraphs']}段传文，{audit['mapped_paragraphs']}段全部登记到具体条目与页尾原文，未分配0段，重复分配0段。这个数字包括年首题记、前事和评论，**不是独立历史事件数，也不是逐句翻译完成率**。

[检查结果](data/audit-01-10.json) · [逐段去向](data/paragraph-map-01-10.jsonl) · [《鲁周公世家》归年对照](SHIJI-CROSSWALK.md)

## 本批保留的问题

《史记》把至河而返、章华台之行分别写在三年、八年；本批依经传明确年条分别编在二年、七年，原说在同号史料内保留。申会不赴的“称病”与“时祭”不硬拼。陈哀公死日、楚灭陈月份的经传差异仍列两说。

梦、鬼神和占候作为记载中的信念与解释展示，不确认为客观因果。孟僖子将死托孤属于传文预叙，不改写成七年已去世；叔孙豹早年遭遇属于回叙，不算四年新发生。

本批核对的是既有公开古籍原文工作本及《鲁周公世家》相关段落；尚未完成现代整理本、专题研究的独立校勘，也未完成《史记》其他篇章的本段全量融合。不能据此声称学界多数支持某项取舍。

## 与襄公组分开记账

襄公末段仍是另一分支的待收尾复核稿，本批没有把它标为终审完成，也未覆盖该分支。元年页面的上一年链接明确指向[襄公三十一年复核稿]({REPO}/blob/604211235a7cc43c755a6e5cd55f519a999a9aa9/chronicle/chunqiu/years/bce-0542.md)。

## 复现

在仓库根目录运行 `python3 scripts/build_zhaogong_01_10.py`。脚本读取人工编写的 `data/events-*.psv` 与既有年条，遇到漏段、重复归属、找不到原文、原始文本变更或未安放的《史记》摘录即停止。脚本只排版和检查，不自动生成历史叙述。

[返回春秋总目录](../README.md)
'''
    cross = ['# 《鲁周公世家》｜昭公前十年对照',
             '查阅日期：2026-09-30。以下是从维基文库固定版本实际核读的相关古籍原文摘录；不是整部《史记》TXT的校勘结果。',
             f'[原文固定版本]({extras["source_url"]}) · [摘录数据](data/shiji-excerpts.json)',
             '涉及错年时，本批以经传明确的年度及出返月份作暂定编排依据，不声称完成现代学界意见调查。']
    for key, item in extras['excerpts'].items():
        cross.extend([f'## {item["label"]}', '> ' + item['quote'], item['treatment']])
    cross.extend(['## 没有单独年事的年份',
                  '本篇相关段落未提供另可安放在五年、六年、九年、十年的明确新增年事；三年、八年的记载已与二年、七年同一事件合并。此结论只限本篇所核段落，不能扩展为整部《史记》没有材料。',
                  '[返回本批目录](README.md)'])
    rendered[BATCH / 'README.md'] = readme
    rendered[BATCH / 'SHIJI-CROSSWALK.md'] = '\n\n'.join(cross)
    rendered[BATCH / 'data/audit-01-10.json'] = json.dumps(audit, ensure_ascii=False, indent=2)
    rendered[BATCH / 'data/paragraph-map-01-10.jsonl'] = '\n'.join(json.dumps(row, ensure_ascii=False) for row in mapping)
    index = ROOT / 'chronicle/chunqiu/README.md'
    old = index.read_text(encoding='utf-8')
    start, finish = '<!-- zhaogong-01-10:start -->', '<!-- zhaogong-01-10:end -->'
    block = f'{start}\n\n## 鲁昭公：第一段已编写（前541—前532）\n\n[元年至十年：阅读与检查入口](zhaogong/README.md)。本批10页，{audit["narrative_entries"]}条叙述；十一年至三十二年尚未编写。襄公待收尾复核稿与本批分开统计，不因新增昭公页面而视为已经终审。\n\n{finish}'
    if start in old:
        require(finish in old, 'Broken batch markers in index')
        old = old[:old.index(start)] + block + old[old.index(finish)+len(finish):]
    else:
        old = old.rstrip() + '\n\n' + block + '\n'
    rendered[index] = old
    for path, text in rendered.items():
        write(path, text)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    print(f'Wrote {len(rendered)} files; all paragraph destinations validated.')


if __name__ == '__main__':
    main()
