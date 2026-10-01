#!/usr/bin/env python3
"""Render the manually authored Duke Ding batch; standard library only.

This program does not invent or translate historical prose. It reads the three
reviewed PSV files, verifies immutable source blobs, maps original paragraphs,
and emits reader pages with full quotations, exact line links and audit files.
Run with --check to verify reproducibility without writing any files.
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
BATCH = ROOT / 'chronicle/chunqiu/dinggong'
DATA = BATCH / 'data'
OUT = ROOT / 'chronicle/chunqiu/years'
SOURCE = 'working-texts/zuozhuan-punctuated-years/years'
REPO = 'https://github.com/zhixin0825/history'
BASE = 'f70523e1175281931ccba31a3f8aceba9d870e53'
DATE = '2026-10-01'
INPUTS = ('events-01-05.psv', 'events-06-10.psv', 'events-11-15.psv')
HASHES = {
    1: 'f0c265c0240239872de7978fca77a608ec714b0c',
    2: '213bc823f2019dde772c87c685bd8cec3f364fdc',
    3: 'b4554c8461d1585e147854170de66a5dd6c895e1',
    4: 'bec33fc443d0014b1e68ff6930d78cd3e6afdc98',
    5: '69b91b2c2cffdf8b6af343a4bb6b531edcbc6336',
    6: '31c7e6d927afc40c5fac49ac7301b655873e603d',
    7: '1364e094c8b0178f2e8b2b6753b485aa634fff75',
    8: '0af5718772edba6822d2b651b888e3a6b89cb5af',
    9: 'a61bd3422f870ca2668c6560957e8f875ead55c4',
    10: '9ba206aafb3b2b64262f762877de88194fd2c40f',
    11: 'cf556c9312e5e624947f7d38ce9ab66d932c102c',
    12: '7278011fb3a0a209636fe502aeb42119d26cfe81',
    13: '157ebc07a8da567245615f21d2286c62cbdf25f0',
    14: '099f3b2830f504936ebedb66dc2c2d5036a8e1b2',
    15: '9bfe60f62869926cd4ae7a645315a8ee9c439be5',
}
# These are title/date-only paragraphs, not missing historical narratives.
CALENDAR = {'元年春，王。', '二年春，王正月。', '夏四月。',
            '七年春，王正月。', '冬十月。', '九年春，王正月。'}
NAMES = ['元','二','三','四','五','六','七','八','九','十','十一','十二','十三','十四','十五']


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def dump(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + '\n'


def parse_source(year: int) -> dict:
    path = f'{SOURCE}/bce-{510-year:04d}.md'
    raw = (ROOT/path).read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    require(blob == HASHES[year], f'Source changed: {path}; {blob}')
    text = raw.decode('utf-8')
    url = re.search(r'\[来源原文\]\(([^)]+)\)', text)
    require(url is not None, f'Missing original source URL in {path}')
    records, buf = [], []
    kind = None
    first = last = 0
    count = Counter()

    def flush() -> None:
        nonlocal buf
        if buf:
            require(kind in ('jing','zhuan'), f'Unknown section in {path}')
            value = '\n'.join(buf)
            count[kind] += 1
            records.append({'kind': kind, 'paragraph': count[kind],
                            'text': value, 'start_line': first, 'end_line': last,
                            'sha256': hashlib.sha256(value.encode()).hexdigest()})
            buf = []

    for number, line in enumerate(text.splitlines(), 1):
        if line in ('## 经', '## 传'):
            flush()
            kind = 'jing' if line == '## 经' else 'zhuan'
        elif line.startswith('<a ') or line.startswith('## '):
            flush()
            if line.startswith('## '):
                kind = None
        elif not line.strip():
            flush()
        elif kind:
            if not buf:
                first = number
            buf.append(line)
            last = number
    flush()
    require(count['jing'] and count['zhuan'], f'Empty source section in {path}')
    return {'path': path, 'blob': blob, 'url': url.group(1), 'records': records}


def load_events() -> dict[int, list[dict]]:
    result = {y: [] for y in range(1, 16)}
    for name in INPUTS:
        for n, line in enumerate((DATA/name).read_text(encoding='utf-8').splitlines(), 1):
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            fields = [x.strip() for x in line.split('|')]
            require(len(fields) == 7, f'{name}:{n}: expected seven fields')
            y, title, body, jing, zhuan, note, extra = fields
            year = int(y)
            require(year in result and title and body, f'{name}:{n}: incomplete narrative')
            row = {'title': title, 'body': body.replace('\\n','\n'),
                   'note': note.replace('\\n','\n'),
                   'jing': jing.split('~') if jing else [],
                   'zhuan': zhuan.split('~') if zhuan else [],
                   'extra': extra.split(',') if extra else [],
                   'input_file': name, 'input_line': n}
            require(row['jing'] or row['zhuan'] or row['extra'], f'{name}:{n}: no source')
            result[year].append(row)
    require(all(result.values()), 'A year is empty')
    return result


def source_block(src: dict, p: dict, year: int) -> str:
    book = '《春秋》' if p['kind'] == 'jing' else '《左传》'
    link = f'{REPO}/blob/{BASE}/{src["path"]}#L{p["start_line"]}-L{p["end_line"]}'
    quote = '\n'.join('> ' + line for line in p['text'].splitlines())
    return f'**{book}·定公{NAMES[year-1]}年** · [固定版本原文]({link})\n\n{quote}'


def replace_block(text: str, key: str, body: str) -> str:
    start, end = f'<!-- {key}:start -->', f'<!-- {key}:end -->'
    block = start + '\n\n' + body.strip() + '\n\n' + end
    if start in text:
        require(text.count(start) == text.count(end) == 1, f'Broken markers: {key}')
        return text[:text.index(start)] + block + text[text.index(end)+len(end):]
    require(end not in text, f'Orphan marker: {key}')
    return text.rstrip() + '\n\n' + block + '\n'


def research_links(row: dict, extra: dict) -> list[str]:
    keys = sorted({r for key in row['extra'] for r in extra['excerpts'][key].get('research', [])})
    return [f'**研究参考：** [{extra["research"][key]["title"]}]({extra["research"][key]["url"]})。'
            + extra['research'][key]['read_scope'] + '。' for key in keys]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    check = parser.parse_args().check
    events = load_events()
    extra = json.loads((DATA/'supplemental-sources.json').read_text(encoding='utf-8'))
    excerpts = extra['excerpts']
    # The complete bounded Lu Shijia text must be exhausted by the saved quotes.
    remaining = '\n'.join(extra['lu_scope_blocks'])
    for key, item in excerpts.items():
        require(item['source'] in extra['sources'], f'Unknown source: {key}')
        require(item['quote'], f'Empty quote: {key}')
        if item['source'] == 'lu':
            require(remaining.count(item['quote']) == 1, f'Lu excerpt not unique: {key}')
            remaining = remaining.replace(item['quote'], '', 1)
    require(not remaining.strip(), f'Unassigned Lu Shijia text: {remaining}')
    rendered, mapping, yearly = {}, [], []
    used = defaultdict(list)
    total_calendar = 0
    for year, rows in events.items():
        src = parse_source(year)
        ps = src['records']
        assigned, chosen = {}, defaultdict(list)
        for n, row in enumerate(rows, 1):
            for kind in ('jing','zhuan'):
                for prefix in row[kind]:
                    matches = [i for i, p in enumerate(ps) if p['kind'] == kind and p['text'].startswith(prefix)]
                    require(len(matches) == 1, f'Year {year} event {n}: {kind} {prefix!r}: matches={len(matches)}')
                    i = matches[0]
                    require(i not in assigned, f'Year {year}: duplicate paragraph {prefix!r}')
                    assigned[i] = f'note-{n}'
                    chosen[n].append(i)
            for key in row['extra']:
                require(key in excerpts, f'Unknown excerpt in {year}/{n}: {key}')
                used[key].append({'year': year, 'year_bce': 510-year, 'event': n,
                                  'note': row['note'],
                                  'destination': f'chronicle/chunqiu/years/bce-{510-year:04d}.md#note-{n}'})
        calendar = []
        for i, p in enumerate(ps):
            if i not in assigned and p['kind'] == 'jing' and p['text'] in CALENDAR:
                assigned[i] = 'note-calendar'
                calendar.append(i)
        missing = [f'{p["kind"]}:{p["text"][:60]}' for i, p in enumerate(ps) if i not in assigned]
        require(not missing, f'Year {year}: missing source paragraphs {missing}')
        total_calendar += len(calendar)
        bce = 510-year
        prev = f'[上一年：前{bce+1}](bce-{bce+1:04d}.md)'
        if year < 15:
            nxt = f'[下一年：前{bce-1}](bce-{bce-1:04d}.md)'
        elif (OUT/'bce-0494.md').exists():
            nxt = '[下一年：前494（哀公元年）](bce-0494.md)'
        else:
            nxt = '下一年：前494（哀公元年，白话页待编）'
        nav = f'{prev} · [定公目录](../dinggong/README.md) · [春秋目录](../README.md) · {nxt}'
        page = [f'# 公元前{bce}年（鲁定公{NAMES[year-1]}年）', nav,
                '> 第一轮白话整理，附原文、异说与归年依据。古历月份不直接等同公历月份；段落覆盖不等于逐句翻译或现代学术校勘完成。',
                '## 本年纪事']
        for n, row in enumerate(rows, 1):
            page.extend([f'<a id="event-{n}"></a>', f'{n}. **{row["title"]}**',
                         row['body'] + f' [{n}](#note-{n})'])
        if calendar:
            page.append('[年首与季节题记](#note-calendar)：保留只有年月、没有独立事件的经文，不另造白话史事。')
        refs = [n for n, row in enumerate(rows, 1) if any(excerpts[k]['source'] == 'lu' for k in row['extra'])]
        if refs:
            status = '《鲁周公世家》对应摘录已接入第' + '、'.join(map(str, refs)) + '条同号史料。'
        else:
            status = '已核《鲁周公世家》定公段，本篇没有可另增入本年的明确年事；这不代表整部《史记》没有材料。'
        if year in (12,14):
            status += '孔子离鲁相关异说集中对读，暂编在[前497年十三年](bce-0497.md#event-2)，本年不另造一次相同离去。'
        if year == 1:
            status += '史墨论季氏的同一问答已置[昭公末年](bce-0510.md#event-7)，这里只核对不同叙事位置，不再计一场新问答。'
        page.extend(['## 《鲁周公世家》本年对照', status,
                     '[逐项归年与研究范围](../dinggong/SHIJI-CROSSWALK.md)',
                     '## 本年相关史料',
                     '以下逐段保留古籍原文，并链接到不可变版本的对应行。前事、后事、梦占、人物判断依同号说明阅读，不能把长段中的一切都算作本年事实。工作本原字、疑字及缺字不静默改动。'])
        for n, row in enumerate(rows, 1):
            page.extend([f'<a id="note-{n}"></a>', f'### [{n}] {row["title"]}'])
            for i in chosen[n]:
                page.append(source_block(src, ps[i], year))
            for key in row['extra']:
                item = excerpts[key]
                origin = extra['sources'][item['source']]
                page.extend([f'**{origin["title"]}·{item["label"]}** · [核对来源]({origin["url"]})',
                             '> ' + item['quote']])
                if item['source'] not in ('lu','kong'):
                    page.append('**引文层次：** ' + origin['access'] + '。')
                if item.get('prior_destination'):
                    page.append('[此前的同一问答](bce-0510.md#note-7)，本处仅作编排差异对照。')
            if row['note']:
                page.append('**说明：** ' + row['note'])
            page.extend(research_links(row, extra))
            page.append(f'[返回第{n}条](#event-{n})')
        if calendar:
            page.extend(['<a id="note-calendar"></a>', '### 年首与季节题记',
                         '以下原文只保留年、季或月，没有独立史事。它们有明确去向，但不计入白话事件条数。'])
            page.extend(source_block(src, ps[i], year) for i in calendar)
        page.extend([f'[本年完整经传工作本](../../../{src["path"]}) · [工作本原来源]({src["url"]})', nav])
        text = '\n\n'.join(page) + '\n'
        require(len(re.findall(r'<a id="event-\d+">',text)) == len(rows), 'Event anchor count')
        require(len(re.findall(r'<a id="note-\d+">',text)) == len(rows), 'Note anchor count')
        rendered[OUT/f'bce-{bce:04d}.md'] = text
        for i, p in enumerate(ps):
            mapping.append({'regnal_year': year, 'year_bce': bce, 'source_commit': BASE,
                            'source_file': src['path'], 'source_blob_sha': src['blob'],
                            **{k:p[k] for k in ('kind','paragraph','start_line','end_line','sha256')},
                            'prefix': p['text'][:40],
                            'disposition': 'calendar_heading' if i in calendar else 'narrative_or_same_number_note',
                            'destination': f'chronicle/chunqiu/years/bce-{bce:04d}.md#{assigned[i]}'})
        counts = Counter(p['kind'] for p in ps)
        yearly.append({'regnal_year': year, 'year_bce': bce, 'narrative_entries': len(rows),
                       'jing_paragraphs': counts['jing'], 'zhuan_paragraphs': counts['zhuan'],
                       'calendar_only_paragraphs': len(calendar), 'mapped_paragraphs': len(assigned),
                       'unmapped_paragraphs': 0, 'duplicate_assignments': 0,
                       'source_blob_verified': src['blob'],
                       'supplemental_excerpt_references': sum(len(e['extra']) for e in rows)})
    require(set(used) == set(excerpts), f'Excerpts without destination: {set(excerpts)-set(used)}')
    require(all(len(v) == 1 for v in used.values()), 'An excerpt has more than one primary destination')

    prev_path = OUT/'bce-0510.md'
    prev_text = prev_path.read_text(encoding='utf-8')
    old = '下一年：前509（定公元年，白话页待编）'
    new = '[下一年：前509（定公元年）](bce-0509.md)'
    require(old in prev_text or new in prev_text, 'Unexpected Zhao last-year navigation')
    rendered[prev_path] = prev_text.replace(old, new)

    core_count = sum(item['source'] == 'lu' for item in excerpts.values())
    audit = {'batch': '鲁定公元年至十五年', 'editorial_date': DATE,
             'status': 'first_readable_pass_with_verified_paragraph_mapping',
             'source_commit': BASE, 'year_pages': 15,
             'narrative_entries': sum(y['narrative_entries'] for y in yearly),
             'jing_paragraphs': sum(y['jing_paragraphs'] for y in yearly),
             'zhuan_paragraphs': sum(y['zhuan_paragraphs'] for y in yearly),
             'mapped_unique_paragraphs': len(mapping), 'calendar_only_paragraphs': total_calendar,
             'unmapped_paragraphs': 0, 'duplicate_assignments': 0,
             'source_blob_checks_passed': len(yearly),
             'lu_shijia_excerpts': core_count, 'other_ancient_excerpts': len(excerpts)-core_count,
             'lu_shijia_bounded_text_completely_assigned': True,
             'supplemental_excerpt_destinations': {k:[{q:d[q] for q in ('year','year_bce','event','destination')} for d in ds] for k,ds in used.items()},
             'modern_scholarly_collation_complete': False, 'all_shiji_chapters_reviewed': False,
             'xianggong_review_completed_by_this_batch': False,
             'limitation': 'Every source paragraph has a destination, including calendar headings, backstory and commentary. This is not a count of independent historical events or a claim of full literal translation.',
             'input_sha256': {n:hashlib.sha256((DATA/n).read_bytes()).hexdigest() for n in (*INPUTS, 'supplemental-sources.json')},
             'years': yearly}
    rendered[DATA/'audit-01-15.json'] = dump(audit)
    rendered[DATA/'paragraph-map-01-15.jsonl'] = '\n'.join(json.dumps(p,ensure_ascii=False) for p in mapping) + '\n'
    rendered[DATA/'events-01-15.json'] = dump({'source_commit': BASE, 'years': events})

    cross = ['# 《鲁周公世家》｜定公组逐项对照',
             f'核对日期：{DATE}。范围是本篇定公段及此前的拥立句，不是全篇、全书融合完成。',
             f'[固定版本]({extra["sources"]["lu"]["url"]}) · [逐条原文数据](data/supplemental-sources.json)',
             '本篇范围内每个字句均已被下列摘录覆盖；文字覆盖只说明没有漏掉本篇这一段，不证明各说都已考定。']
    for key, item in excerpts.items():
        d = used[key][0]
        source = extra['sources'][item['source']]
        cross.extend([f'## {key}｜{item["label"]}', f'来源：[{source["title"]}]({source["url"]})。{source["access"]}。',
                      '> ' + item['quote'],
                      f'[安放位置：定公{NAMES[d["year"]-1]}年第{d["event"]}条](../years/bce-{d["year_bce"]:04d}.md#note-{d["event"]})',
                      d['note']])
    cross.extend(['## 研究材料实际阅读范围', '[研究说明](RESEARCH-NOTES.md)',
                  '十二年拆城与十三年离鲁分别编排；十四年页面提示异说，不重复制造一次离鲁。史墨论季氏保留跨组链接，不新增重复对话。',
                  '[返回定公目录](README.md)'])
    rendered[BATCH/'SHIJI-CROSSWALK.md'] = '\n\n'.join(cross) + '\n'

    research = ['# 定公组｜考辨记录与阅读范围',
                f'核对日期：{DATE}。以下区分已读原文、摘要与待进一步校勘事项。']
    for key, item in extra['research'].items():
        research.extend([f'## {item["title"]}', item['bibliography'],
                         f'[原页面]({item["url"]})', '**实际阅读：** ' + item['read_scope'] + '。',
                         '**本批采用范围：** ' + item['summary']])
    research.extend(['## 古注：子期取血盟誓',
                     f'[《五礼通考》卷229]({extra["sources"]["du"]["url"]})转引杜预注，解释为胸前取血以盟。不是杀子期取出心脏，也无需把“心”直接判成工作本错字；本批按此改正初稿，原文不动。',
                     '## 不扩大本批完成范围',
                     '夹谷论文仅获摘要，孔子纪年参考是一个考辨来源，不足以声称现代学界多数或一致。其他《史记》世家、列传只在已列片段范围内使用，尚未全量对读。孔子周游完整路线、各地现代定位和古历换算不在本轮强定。',
                     '[返回定公目录](README.md)'])
    rendered[BATCH/'RESEARCH-NOTES.md'] = '\n\n'.join(research) + '\n'

    table = ['| 年页 | 本年入口 | 条目 |', '|---|---|---:|']
    for y, rows in events.items():
        table.append(f'| [定公{NAMES[y-1]}年｜前{510-y}](../years/bce-{510-y:04d}.md) | {rows[0]["title"]} | {len(rows)} |')
    readme = ['# 鲁定公｜十五年第一轮逐年整理（前509—前495）',
              f'已编 **15张年度页、{audit["narrative_entries"]}条白话条目**。每条先讲事件和经过，再由条末编号看同号原文与异说说明。',
              '\n'.join(table), '## 原文与检查',
              f'本组有{audit["jing_paragraphs"]}段经文、{audit["zhuan_paragraphs"]}段传文，共{len(mapping)}段，均已映射；漏段0，重复归属0。其中特别保留{total_calendar}段只有年月的题记，不虚增为事件。15份原文的实际Git blob哈希全部核验。',
              f'《鲁周公世家》本段及承前继位句拆为{core_count}条摘录，全部安放；另有{len(excerpts)-core_count}条古籍、古注片段辅助纪年与字义核对。史墨同一问答只作跨组对照，不重复计作新事件。',
              '[机器检查结果](data/audit-01-15.json) · [每段去向](data/paragraph-map-01-15.jsonl) · [《史记》对照](SHIJI-CROSSWALK.md) · [研究阅读范围](RESEARCH-NOTES.md)',
              '## 本组保留的关键区别',
              '阳虎囚季桓子、控制盟誓、政变失利、据邑和出奔分年连续写。吴军入郢、秦军援楚及撤军分属前后年，未把多场交战压成一次胜负。',
              '定公七年《史记》“取郓”与《左传》“归郓”保留差异；夹谷的武装逼盟和诛乐属于不同传述，不强行拼接。墮三都只落实郈、费，成未攻克。孔子离鲁暂取十三年，十二、十四年异说集中在同号脚注解释。',
              '“第一轮完成”不等于逐句翻译、现代学术定本或整部《史记》已融合。襄公待收尾复核仍单独记录，不因本组完成而结审。',
              '## 复现',
              '在仓库根目录运行 `python3 scripts/build_dinggong_01_15.py`；加 `--check` 则仅验证输出一致性而不写文件。输入为三份人工PSV和已核摘录；脚本只排版、校验与建索引，不自动生成历史叙述。',
              '## 下一组', '**鲁哀公元年（前494）**。',
              '[接上一组：鲁昭公](../zhaogong/README.md) · [返回春秋目录](../README.md)']
    rendered[BATCH/'README.md'] = '\n\n'.join(readme) + '\n'
    index = ROOT/'chronicle/chunqiu/README.md'
    body = f'## 鲁定公：十五年第一轮已编（前509—前495）\n\n[定公全组阅读入口](dinggong/README.md)。共15页、{audit["narrative_entries"]}条白话条目，{len(mapping)}段经传全部有去向，另完整对照《鲁周公世家》本段。下一组从鲁哀公元年（前494）开始。襄公复核状态未在本批变更。'
    rendered[index] = replace_block(index.read_text(encoding='utf-8'), 'dinggong-01-15', body)
    zhao = ROOT/'chronicle/chunqiu/zhaogong/README.md'
    ztext = zhao.read_text(encoding='utf-8')
    old_next = '从 **鲁定公元年（前509）** 开始。'
    new_next = '[鲁定公组（前509—前495）已完成第一轮](../dinggong/README.md)。'
    require(old_next in ztext or new_next in ztext, 'Unexpected Zhao next-group text')
    rendered[zhao] = ztext.replace(old_next, new_next)

    def target_text(path: Path) -> str:
        if path in rendered:
            return rendered[path]
        return path.read_text(encoding='utf-8')

    # Validate paths and explicit anchors, including cross-year links.
    for path, text in rendered.items():
        if path.suffix != '.md':
            continue
        ids = re.findall(r'<a id="([^"]+)">', text)
        require(len(ids) == len(set(ids)), f'Duplicate anchor: {path}')
        for link in re.findall(r'\]\(([^\s\)]+)\)', text):
            if link.startswith(('https:', 'http:', 'mailto:')):
                continue
            filename, _, anchor = link.partition('#')
            target = (path.parent/unquote(filename)).resolve() if filename else path
            require(target in rendered or target.is_file(), f'Broken local link {path}: {link}')
            if anchor and (anchor.startswith('note-') or anchor.startswith('event-')):
                require(f'<a id="{anchor}"></a>' in target_text(target), f'Broken anchor {path}: {link}')
    changed = [p for p,t in rendered.items() if not p.exists() or p.read_text(encoding='utf-8') != t]
    if check:
        require(not changed, 'Generated output differs:\n' + '\n'.join(str(p.relative_to(ROOT)) for p in changed))
    else:
        for p,t in rendered.items():
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(t,encoding='utf-8')
    print(dump({'check_only':check, 'generated_files':len(rendered), 'changed_files':len(changed),
                'year_pages':15, 'narrative_entries':audit['narrative_entries'],
                'jing_paragraphs':audit['jing_paragraphs'], 'zhuan_paragraphs':audit['zhuan_paragraphs'],
                'mapped_unique_paragraphs':len(mapping), 'calendar_only_paragraphs':total_calendar,
                'lu_shijia_excerpts':core_count, 'other_ancient_excerpts':len(excerpts)-core_count,
                'source_hashes_and_all_local_links_valid':True}))


if __name__ == '__main__':
    main()
