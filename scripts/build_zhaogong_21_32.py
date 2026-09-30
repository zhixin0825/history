#!/usr/bin/env python3
"""Render manually authored Zhaogong 21-32, preserving complete source paragraphs.

No machine translation or historical event generation happens here.  All prose,
source selections, and editorial decisions are stored in reviewed PSV files.
Use --check to verify tracked output without writing. Standard library only.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / 'chronicle/chunqiu/zhaogong'
YEARS = ROOT / 'chronicle/chunqiu/years'
DATA = BATCH / 'data'
SOURCE = 'working-texts/zuozhuan-punctuated-years/years'
BASE = '107ccf2d8ec383dc0f7c4ae0e6ff0f1b55dcdcf0'
REPO = 'https://github.com/zhixin0825/history'
DATE = '2026-09-30'
HASHES = {
 21: '5b69a0126317dd1ae626264796540ea627a8e034',
 22: 'fcb6275e5995e27fa5ad7f380ef7e6650465a3e3',
 23: '5db7d2d7d93becae67976cd47f49c7248efbcca6',
 24: '015515bf64dfe57f354aa965a9e59d8754c2f617',
 25: '8460733e15e5bf5c62d88a7081d8f21c37528d04',
 26: 'fea9882a9ecd06af572638a72d42ddafe745c042',
 27: '7086429e7fad2c11827d10f0c74b138a97df20e7',
 28: '33caee5e19b86a3dc5dce73249d8ef46f017ba1c',
 29: 'c67f554b6e97707279773e2a9449d6e86641c508',
 30: '75b10f5992fe73bda7bd0306e95d6d1a514a9a14',
 31: '79344b7966a448b939cb2d6b8764c3a23d2466f5',
 32: '85bbfa7c430351b148884af79721a2d718e9943e',
 33: 'f0c265c0240239872de7978fca77a608ec714b0c',
}
EXPECTED_COUNTS = {
 21:(7,9),22:(10,9),23:(13,12),24:(6,10),25:(8,16),26:(8,13),
 27:(9,11),28:(6,9),29:(6,7),30:(4,6),31:(7,6),32:(6,7)
}
INPUTS = ('events-21-26.psv', 'events-27-32.psv')
# A single physical paragraph contains two independent events. Both destinations
# are intentional and visible, not a hidden duplicate or a claimed second event.
ALLOWED_SHARED = {(24, 'jing', 6): {6, 8}}
EXTRA = {(32, 5): [('zhuan', 3)], (32, 6): [('jing', 3), ('jing', 4)]}
DIGITS = '一二三四五六七八九'


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def cn(n: int) -> str:
    if n == 1:
        return '元'
    if n < 10:
        return DIGITS[n-1]
    return ('' if n < 20 else DIGITS[n//10-1]) + '十' + (DIGITS[n%10-1] if n%10 else '')


def dump(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def parse_source(year: int) -> dict:
    bce = 542-year
    path = f'{SOURCE}/bce-{bce:04d}.md'
    raw = (ROOT/path).read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    require(blob == HASHES[year], f'Changed source {path}: {blob}')
    text = raw.decode('utf-8')
    found = re.search(r'\[来源原文\]\(([^)]+)\)', text)
    require(found is not None, f'Missing original source URL: {path}')
    records = []
    section = None
    buf = []
    first = last = 0
    counters = Counter()

    def flush() -> None:
        nonlocal buf
        if buf:
            require(section in ('jing', 'zhuan'), 'Unknown source section')
            value = '\n'.join(buf)
            counters[section] += 1
            records.append({'kind': section, 'paragraph': counters[section],
                            'text': value, 'start_line': first, 'end_line': last,
                            'sha256': hashlib.sha256(value.encode()).hexdigest()})
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
                first = number
            buf.append(line)
            last = number
    flush()
    if year in EXPECTED_COUNTS:
        require((counters['jing'], counters['zhuan']) == EXPECTED_COUNTS[year],
                f'Unexpected paragraph segmentation in {path}: {counters}')
    return {'path': path, 'url': found.group(1), 'blob': blob,
            'records': records, 'by_key': {(p['kind'], p['paragraph']): p for p in records}}


def load_events() -> dict[int, list[dict]]:
    events = {n: [] for n in range(21, 33)}
    for name in INPUTS:
        for number, line in enumerate((DATA/name).read_text(encoding='utf-8').splitlines(), 1):
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            cells = [c.strip() for c in line.split('|')]
            require(len(cells) == 7, f'{name}:{number}: expected 7 fields')
            y, title, body, jing, zhuan, note, shiji = cells
            year = int(y)
            require(year in events and title and body, f'{name}:{number}: missing narrative/year')
            row = {'title': title, 'body': body.replace('\\n', '\n'),
                   'note': note.replace('\\n', '\n'), 'shiji': shiji.split(',') if shiji else [],
                   'input_file': name, 'input_line': number}
            for kind, value in (('jing', jing), ('zhuan', zhuan)):
                row[kind] = [int(x) for x in value.split(',')] if value else []
                require(len(row[kind]) == len(set(row[kind])), f'Duplicate index in {name}:{number}')
            events[year].append(row)
    require(all(events.values()), 'A year has no authored narratives')
    return events


def source_block(src: dict, p: dict, title: str) -> str:
    book = '《春秋》' if p['kind'] == 'jing' else '《左传》'
    link = f'{REPO}/blob/{BASE}/{src["path"]}#L{p["start_line"]}-L{p["end_line"]}'
    quoted = '\n'.join('> ' + s for s in p['text'].splitlines())
    return f'**{book}·{title}** · [固定版本原文]({link})\n\n{quoted}'


def replace_block(text: str, name: str, body: str) -> str:
    start, end = f'<!-- {name}:start -->', f'<!-- {name}:end -->'
    block = start + '\n\n' + body.strip() + '\n\n' + end
    if start in text:
        require(text.count(start) == text.count(end) == 1, f'Broken markers {name}')
        return text[:text.index(start)] + block + text[text.index(end)+len(end):]
    require(end not in text, f'Orphan end marker {name}')
    return text.rstrip() + '\n\n' + block + '\n'


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--check', action='store_true', help='Verify without writing files')
    check = args.parse_args().check
    events = load_events()
    sources = {year: parse_source(year) for year in range(21, 34)}
    extras = json.loads((DATA/'shiji-excerpts-21-32.json').read_text(encoding='utf-8'))
    excerpts = extras['excerpts']
    output: dict[Path, str] = {}
    mapping, yearly, supplemental = [], [], []
    used = defaultdict(list)
    shared_found = set()

    for year, rows in events.items():
        src = sources[year]
        assignments = defaultdict(list)
        for n, row in enumerate(rows, 1):
            require(row['jing'] or row['zhuan'] or row['shiji'], f'{year}/{n}: no source')
            for kind in ('jing', 'zhuan'):
                for idx in row[kind]:
                    require((kind, idx) in src['by_key'], f'{year}/{n}: no {kind} paragraph {idx}')
                    assignments[(kind, idx)].append(n)
            for key in row['shiji']:
                require(key in excerpts, f'{year}/{n}: unknown Shiji key {key}')
                used[key].append({'year': year, 'event': n, 'note': row['note']})
        require(set(assignments) == set(src['by_key']),
                f'{year}: unmapped paragraphs {set(src["by_key"])-set(assignments)}')
        for (kind, idx), destinations in assignments.items():
            if len(destinations) > 1:
                require(set(destinations) == ALLOWED_SHARED.get((year, kind, idx)),
                        f'{year}: undeclared shared paragraph {kind}/{idx}: {destinations}')
                shared_found.add((year, kind, idx))
        bce = 542-year
        prev = f'[上一年：前{bce+1}](bce-{bce+1:04d}.md)'
        if year < 32:
            nxt = f'[下一年：前{bce-1}](bce-{bce-1:04d}.md)'
        elif (YEARS/'bce-0509.md').exists():
            nxt = '[下一年：前509（定公元年）](bce-0509.md)'
        else:
            nxt = '下一年：前509（定公元年，白话页待编）'
        nav = f'{prev} · [昭公目录](../zhaogong/README.md) · [春秋目录](../README.md) · {nxt}'
        page = [f'# 公元前{bce}年（鲁昭公{cn(year)}年）', nav,
                '> 第一轮白话整理，附逐段原文与归年说明。古历月份不直接等同公历月份；段落覆盖不等于现代学术校勘完成。',
                '## 本年纪事']
        for n, row in enumerate(rows, 1):
            page.extend([f'<a id="event-{n}"></a>', f'{n}. **{row["title"]}**',
                         row['body'] + f' [{n}](#note-{n})'])
        used_here = [n for n, row in enumerate(rows, 1) if row['shiji']]
        if used_here:
            status = '《鲁周公世家》相关原文已接入第' + '、'.join(map(str, used_here)) + '条同号史料；同一事件不另造一条重复年事。'
        else:
            status = '已对照《鲁周公世家》本段，未见需单独增入本年的明确年事。此结论只限本篇已核段落，不代表《史记》其他篇章没有本年材料。'
        page.extend(['## 《鲁周公世家》本段对照', status,
                     '[所核摘录与逐项去向](../zhaogong/SHIJI-CROSSWALK.md)',
                     '## 本年相关史料',
                     '以下保留所用古籍原文。回叙、后事、梦占及人物评论依同号说明区分，不将整段都算作本年事实。原工作本的疑字、缺字不静默改写。'])
        if year == 24:
            page.append('本页第6、8条共引同一段经文，因该段同时记吴灭巢和葬杞平公。审计登记为1处明确共用出处，不计作两段原文。')
        for n, row in enumerate(rows, 1):
            page.extend([f'<a id="note-{n}"></a>', f'### [{n}] {row["title"]}'])
            for kind in ('jing', 'zhuan'):
                for idx in row[kind]:
                    p = src['by_key'][(kind, idx)]
                    page.append(source_block(src, p, f'昭公{cn(year)}年'))
            for key in row['shiji']:
                item = excerpts[key]
                page.extend([f'**《史记·鲁周公世家》·{item["label"]}** · [固定版本原文]({extras["source_url"]})',
                             '> ' + item['quote']])
            if (year, n) in EXTRA:
                page.append('**跨年核对：以下是下一年材料，只用于界定后事，不并作本年事件。**')
                for key in EXTRA[(year, n)]:
                    p = sources[33]['by_key'][key]
                    page.append(source_block(sources[33], p, '定公元年'))
                    supplemental.append({'year': year, 'event': n, 'source_file': sources[33]['path'],
                                         'source_blob': sources[33]['blob'], 'kind': key[0],
                                         'paragraph': key[1], 'sha256': p['sha256'], 'role': 'next_year_boundary_only'})
            if row['note']:
                page.append('**说明：** ' + row['note'])
            page.append(f'[返回第{n}条](#event-{n})')
        page.extend([f'[本年完整经传工作本](../../../{src["path"]}) · [工作本来源网页]({src["url"]})', nav])
        text = '\n\n'.join(page) + '\n'
        require(text.count('<a id="event-') == text.count('<a id="note-') == len(rows), 'Anchor mismatch')
        output[YEARS/f'bce-{bce:04d}.md'] = text
        for p in src['records']:
            dests = assignments[(p['kind'], p['paragraph'])]
            mapping.append({'regnal_year': year, 'year_bce': bce,
                            'source_file': src['path'], 'source_commit': BASE, 'source_blob_sha': src['blob'],
                            **{k: p[k] for k in ('kind','paragraph','start_line','end_line','sha256')},
                            'prefix': p['text'][:40], 'events': dests,
                            'intentional_shared': len(dests)>1,
                            'destinations': [f'chronicle/chunqiu/years/bce-{bce:04d}.md#note-{n}' for n in dests],
                            'time_classification': 'see_authored_same_number_note; not_all_text_is_current_year_event'})
        yearly.append({'regnal_year': year, 'year_bce': bce, 'narrative_entries': len(rows),
                       'jing_paragraphs': EXPECTED_COUNTS[year][0], 'zhuan_paragraphs': EXPECTED_COUNTS[year][1],
                       'mapped_unique_paragraphs': len(assignments),
                       'paragraph_references': sum(map(len, assignments.values())),
                       'unmapped_paragraphs': 0, 'source_blob_verified': src['blob'],
                       'shiji_excerpts': sum(len(row['shiji']) for row in rows)})
    require(shared_found == set(ALLOWED_SHARED), 'Declared shared paragraph was not exercised')
    require(set(used) == set(excerpts), f'Unused Shiji excerpts: {set(excerpts)-set(used)}')
    require(all(len(v) == 1 for v in used.values()), 'Shiji excerpt has multiple primary destinations')

    # The last page of the earlier batch must actually point into this new batch.
    prev_path = YEARS/'bce-0522.md'
    prev_text = prev_path.read_text(encoding='utf-8')
    old_next = '下一年：前521（昭公二十一年，尚未编写）'
    new_next = '[下一年：前521](bce-0521.md)'
    require(old_next in prev_text or new_next in prev_text, 'Unexpected previous-page navigation')
    output[prev_path] = prev_text.replace(old_next, new_next)

    # Small correction found during review: Qi Gui is the duke's mother. Do not
    # replace the ancient text's ritual title "夫人"; change only our own wording.
    correction_paths = [YEARS/'bce-0531.md', DATA/'events-11-20.json']
    for path in correction_paths:
        old = path.read_text(encoding='utf-8')
        new = old.replace('鲁昭公夫人齐归', '鲁昭公的母亲齐归').replace('昭公夫人齐归', '昭公的母亲齐归')
        output[path] = new

    # Stop the older batch renderer from consuming new-format PSV inputs or
    # overwriting cumulative navigation/crosswalks created by later batches.
    old_script = ROOT/'scripts/build_zhaogong_01_10.py'
    compat = old_script.read_text(encoding='utf-8')
    compat = compat.replace("for file in sorted((BATCH / 'data').glob('events-*.psv')):",
                            "for file in (BATCH / 'data' / n for n in ('events-01-05.psv', 'events-06-10.psv')):")
    hook = "    # Preserve cumulative metadata when later batches exist.\n"
    if hook not in compat:
        target = 'def write(path: Path, text: str) -> None:\n'
        require(target in compat, 'Cannot safely patch old renderer')
        insertion = target + hook + "    if (BATCH / 'data/audit-11-20.json').exists():\n" + \
            "        if path in (BATCH / 'README.md', BATCH / 'SHIJI-CROSSWALK.md', ROOT / 'chronicle/chunqiu/README.md'):\n" + \
            "            return\n" + \
            "        if path == OUT / 'bce-0532.md' and (OUT / 'bce-0531.md').exists():\n" + \
            "            text = text.replace('下一年：前531（昭公十一年，尚未编写）', '[下一年：前531](bce-0531.md)')\n"
        compat = compat.replace(target, insertion, 1)
    output[old_script] = compat

    audit = {'batch': '鲁昭公二十一年至三十二年', 'editorial_date': DATE,
             'status': 'first_readable_pass_with_source_and_link_validation',
             'source_commit': BASE, 'year_pages': len(events),
             'narrative_entries': sum(r['narrative_entries'] for r in yearly),
             'jing_paragraphs': sum(r['jing_paragraphs'] for r in yearly),
             'zhuan_paragraphs': sum(r['zhuan_paragraphs'] for r in yearly),
             'mapped_unique_paragraphs': len(mapping), 'unmapped_paragraphs': 0,
             'source_paragraph_references': sum(r['paragraph_references'] for r in yearly),
             'intentional_shared_paragraphs': len(shared_found), 'undeclared_duplicate_assignments': 0,
             'source_blob_checks_passed': len(events), 'next_year_blob_checks_passed': 1,
             'shiji_unique_excerpts': len(excerpts),
             'shiji_excerpt_destinations': {k: [{'year': v['year'], 'event': v['event']} for v in vs] for k, vs in used.items()},
             'next_year_boundary_quotes': supplemental,
             'modern_scholarly_collation_complete': False, 'all_shiji_chapters_reviewed': False,
             'xianggong_review_completed_by_this_batch': False,
             'limitations': '215 unique source paragraphs include backstory, predictions and commentary, not 215 independent events. Coverage is not a claim of literal full translation or scholarly consensus.',
             'correction_to_prior_batch': '昭公十一年齐归身份：母亲，而非昭公夫人；古籍原文不改。',
             'input_sha256': {name: hashlib.sha256((DATA/name).read_bytes()).hexdigest() for name in (*INPUTS, 'shiji-excerpts-21-32.json')},
             'years': yearly}
    require(audit['mapped_unique_paragraphs'] == 215, 'Unexpected source total')
    output[DATA/'audit-21-32.json'] = dump(audit)
    output[DATA/'paragraph-map-21-32.jsonl'] = '\n'.join(json.dumps(r, ensure_ascii=False) for r in mapping) + '\n'
    output[DATA/'events-21-32.json'] = dump({'source_commit': BASE, 'years': events})

    cross_path = BATCH/'SHIJI-CROSSWALK.md'
    cross = cross_path.read_text(encoding='utf-8')
    block = ['## 二十一年至三十二年：逐项归年与异文',
             '以下15条摘录分别接入具体年度的同号原文注。同一段中涉及继位后事的，明确保留跨年界限；未完成现代学术意见的系统调查。',
             f'[固定原文]({extras["source_url"]}) · [摘录数据](data/shiji-excerpts-21-32.json)']
    for key, item in excerpts.items():
        d = used[key][0]
        bce = 542-d['year']
        block.extend([f'### {key}｜{item["label"]}', '> ' + item['quote'],
                      f'[正文与同号说明：昭公{cn(d["year"])}年第{d["event"]}条](../years/bce-{bce:04d}.md#note-{d["event"]})',
                      d['note']])
    block.extend(['### 未另增年事的年份',
                  '二十二、二十三、二十四、二十七、三十年：本篇所核段落无可独立另加的本年年事。此范围不扩张为整部《史记》均无材料。'])
    output[cross_path] = replace_block(cross, 'zhaogong-21-32', '\n\n'.join(block))

    # Keep the earlier cumulative index as an archive rather than delete its notes.
    archive = BATCH/'README-01-20.md'
    if not archive.exists():
        archived = (BATCH/'README.md').read_text(encoding='utf-8')
        require('元年至二十年' in archived, 'Unexpected prior index; refusing to overwrite it')
        output[archive] = archived
    else:
        output[archive] = archive.read_text(encoding='utf-8')
    tables, all_counts = {}, {}
    for year in range(1, 33):
        path = YEARS/f'bce-{542-year:04d}.md'
        text = output[path] if path in output else path.read_text(encoding='utf-8')
        title = re.search(r'1\.\s+\*\*(.+?)\*\*', text)
        require(title is not None, f'No first event in {path}')
        n = len(re.findall(r'<a id="event-\d+">', text))
        require(n > 0, f'No narrative anchors: {path}')
        all_counts[year] = n
        tables[year] = f'| [昭公{cn(year)}年｜前{542-year}](../years/bce-{542-year:04d}.md) | {title.group(1)} | {n} |'
    readme = ['# 鲁昭公｜三十二年第一轮逐年整理（前541—前510）',
              f'目前共 **32张年度页面、{sum(all_counts.values())}条白话叙述**。本次新增二十一年至三十二年12页、{audit["narrative_entries"]}条。每年先读事件和经过，再从条末编号查看同号具体原文。',
              '“第一轮完成”表示本组年度叙事与原文去向齐备，不表示全部《史记》篇章、现代专题研究和逐句校勘已完成。襄公末段仍单独待收尾，不因本组完成而自动结审。']
    for label, lo, hi, audit_name in [('第一段',1,10,'01-10'), ('第二段',11,20,'11-20'), ('第三段',21,32,'21-32')]:
        readme.extend([f'## {label}｜{cn(lo)}年至{cn(hi)}年（前{542-lo}—前{542-hi}）',
                       '| 页面 | 本年入口 | 条目 |\n|---|---|---:|\n' + '\n'.join(tables[y] for y in range(lo, hi+1)),
                       f'[本段检查结果](data/audit-{audit_name}.json) · [逐段去向](data/paragraph-map-{audit_name}.jsonl)'])
    readme.extend(['## 本次检查与需要保留的区别',
                  f'第三段{audit["jing_paragraphs"]}段经文、{audit["zhuan_paragraphs"]}段传文，共{len(mapping)}段原文均有去向，未分配0段。昭公二十四年有1段经文兼记“吴灭巢、葬杞平公”，故明确共用在两条注中；出处引用共{audit["source_paragraph_references"]}次，未声明重复0处。另核验定公元年原文，用于标出后事边界，不计入本批年度覆盖。',
                  '昭公出奔按积怨、围季氏、叔孙家臣出兵、孟氏参战、赴齐求援连续展开，不缩成一次斗鸡纠纷。齐军围郓、取得郓、昭公入居分属前后年；住回鲁地不等于恢复君位。乾侯斡旋保留晋卿、季氏、昭公及从者各自行动。',
                  '王子朝携典籍奔楚只按原文范围叙述，不扩写为全部周典籍灭失。吴楚轮番用兵与后来入郢分开。昭公卒于乾侯之后，定公正式即位、成周工程完工均须接至下一年。',
                  '补正上一批昭公十一年一处身份错误：齐归是昭公的母亲，原文礼称“夫人”不改。',
                  '[《鲁周公世家》累计对照](SHIJI-CROSSWALK.md) · [前二十年原目录与旧说明](README-01-20.md)',
                  '## 复现',
                  '在仓库根目录运行 `python3 scripts/build_zhaogong_21_32.py`；只验证而不写入则加 `--check`。脚本核验固定来源的真实Git blob、段落索引、明确共用关系、15条世家摘录去向、导航与本页锚点。人工叙述在两份PSV中，脚本只排版和验证。',
                  '## 下一组', '从 **鲁定公元年（前509）** 开始。', '[返回春秋总目录](../README.md)'])
    output[BATCH/'README.md'] = '\n\n'.join(readme) + '\n'
    index = ROOT/'chronicle/chunqiu/README.md'
    summary = f'## 鲁昭公：三十二年第一轮已编（前541—前510）\n\n[昭公全组阅读入口](zhaogong/README.md)。共32页、{sum(all_counts.values())}条叙述；第三段12页、{audit["narrative_entries"]}条，215段经传全部有去向（1段明确共用）。下一组为鲁定公元年（前509）。襄公待收尾复核稿仍单独统计，未因此结审。'
    output[index] = replace_block(index.read_text(encoding='utf-8'), 'zhaogong-01-10', summary)

    # Check real file destinations and within-page anchors before writing anything.
    for path, text in output.items():
        if path.suffix != '.md' or path == archive:
            continue
        ids = set(re.findall(r'<a id="([^"]+)">', text))
        for anchor in re.findall(r'\]\(#([^\)]+)\)', text):
            require(anchor in ids, f'Broken page anchor {path}: #{anchor}')
        for link in re.findall(r'\]\(([^\s\)]+)\)', text):
            if link.startswith(('http:', 'https:', '#', 'mailto:')):
                continue
            target = (path.parent/unquote(link.split('#',1)[0])).resolve()
            require(target in output or target.exists(), f'Broken local link {path}: {link}')
    changed = [p for p, text in output.items() if not p.exists() or p.read_text(encoding='utf-8') != text]
    if check:
        require(not changed, 'Generated files differ:\n' + '\n'.join(str(p.relative_to(ROOT)) for p in changed))
    else:
        for path, text in output.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
    print(dump({'check_only': check, 'generated_files': len(output), 'changed_files': len(changed),
                'new_year_pages': len(events), 'new_narratives': audit['narrative_entries'],
                'unique_source_paragraphs': len(mapping), 'source_references': audit['source_paragraph_references'],
                'intentional_shared_paragraphs': len(shared_found), 'shiji_excerpts': len(excerpts),
                'all_source_hashes_and_links_passed': True}))


if __name__ == '__main__':
    main()
