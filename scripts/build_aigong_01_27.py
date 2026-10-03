#!/usr/bin/env python3
"""Render human-authored Aigong 1-27, with fail-closed provenance checks.

Input has eight pipe-delimited fields: year, E/N, title, prose, physical
annal-paragraph indices, transmission-paragraph indices, note, excerpt keys.
E is a narrative entry; N is a non-event source/time-boundary note.
This program does not generate or translate historical prose.
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
BATCH = ROOT / 'chronicle/chunqiu/aigong'
DATA = BATCH / 'data'
OUT = ROOT / 'chronicle/chunqiu/years'
SOURCE = 'working-texts/zuozhuan-punctuated-years/years'
REPO = 'https://github.com/zhixin0825/history'
BASE = 'dac36d55ba97f526532c06d8bc2a005583bdb849'
DATE = '2026-10-03'
INPUTS = ('events-01-07.psv', 'events-08-14.psv', 'events-15-20.psv', 'events-21-27.psv')
HASHES = {
1:'215522d6ce4ea7ebcae86be48de4a1c2aaf1b77e',
2:'4d1b9eace516ab55e0419963c7b8c10f919a9b53',
3:'442a095c9c684a4b9985f6a2a2cf1b5e72594698',
4:'ce06e190c92038ac22c27a4e5be309110fb0ca01',
5:'6d7f3c7c4f9415e15a7597210b849edfb78f2550',
6:'131550256b98f80ab81c3f097864356e067a946c',
7:'48ea85a2bc74bc50ba7e3cc27e6f874b4a709287',
8:'05e915a8b54ad91609000409f03d54fd14e0c1f8',
9:'efb41085b63953976ff61fb1a409164f80ff8c23',
10:'b6bb09d2f5f9d8b3563663a1bd2fc078a69b9b05',
11:'a72aa6024ad89099c7384a1b6fc304020e6aa906',
12:'54e778cd872d6fdecb3a139727803a05373679ce',
13:'e6005820884f8016045dc26cb6027f50de867c96',
14:'5a3693d6632ce4e5a572a894b96be86a5c3cbd8e',
15:'16f7bb1e1e3db5f71a14be5af7728d990ef79fc5',
16:'0665289715f3e0311f07190c6f5288db3bf5aeb2',
17:'f9e00bbd4634dd0bb30b1ce187a5fb7916cfceda',
18:'1818f334fd18f5b71991ff829f05623aa0739dbd',
19:'578a4a794ff299edd95266fdfd5320a4d97fc790',
20:'a7a2f7fc48d06ce8e6e2c88484b69e6f5d442ba0',
21:'6cb7bca7e1ce0d0683e2918fbab7e3f46d047137',
22:'e5ef82b7a6d6e9e73c9a4aafff160d7f438b1ae7',
23:'c976bd4b6d59308fe338182d4009aa651d456745',
24:'5a2bbe4fa5bc6893e0bd4661395be531c91e5b08',
25:'83c61b980d02877aa418ab9da278bd74008422d7',
26:'8df4a696e53f82c29a2b49dba58f7b31e60674b0',
27:'b7fe366abfbf6dd617bcffbdf13b659bf8f4da38',
}
# Counts concern physical paragraphs, not independent events or truth judgments.
COUNTS = {1:(6,8),2:(8,8),3:(9,5),4:(11,4),5:(6,6),6:(10,11),7:(7,8),
8:(7,10),9:(5,7),10:(13,5),11:(7,9),12:(6,7),13:(12,5),14:(17,11),
15:(8,5),16:(4,9),17:(0,11),18:(0,3),19:(0,3),20:(0,3),21:(0,2),
22:(0,2),23:(0,3),24:(0,4),25:(0,3),26:(0,4),27:(0,5)}
CALENDAR = {(8,5):'秋，七月。', (9,5):'冬，十月。', (10,1):'十年春，王二月。'}
# A physical paragraph can contain several real subjects. These shared citations
# are declared, counted once in source coverage, and disclosed beside every quote.
SHARED = {(2,'annal',3):2, (2,'zhuan',3):2, (11,'zhuan',8):2,
          (13,'zhuan',4):3, (15,'zhuan',5):2, (16,'zhuan',8):2,
          (17,'zhuan',2):2}
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


def dump(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + '\n'


def parse_source(year: int) -> dict:
    path = f'{SOURCE}/bce-{495-year:04d}.md'
    raw = (ROOT/path).read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    require(blob == HASHES[year], f'Changed source year {year}: expected {HASHES[year]}, actual {blob}')
    text = raw.decode('utf-8')
    url = re.search(r'\[来源原文\]\(([^)]+)\)', text)
    require(url is not None, f'Missing original URL: {path}')
    section = None
    heading = None
    buf: list[str] = []
    first = last = 0
    counts: Counter = Counter()
    records: list[dict] = []

    def flush() -> None:
        nonlocal buf
        if not buf:
            return
        require(section in ('annal','zhuan'), f'Unknown source section {path}')
        counts[section] += 1
        idx = counts[section]
        value = '\n'.join(buf)
        if section == 'zhuan':
            layer = 'zhuan'
        elif year <= 13 or (year == 14 and idx == 1):
            layer = 'jing'
        else:
            layer = 'continued_jing'
        records.append({'section':section,'paragraph':idx,'layer':layer,'source_heading':heading,
                        'text':value,'start_line':first,'end_line':last,
                        'sha256':hashlib.sha256(value.encode('utf-8')).hexdigest()})
        buf = []

    allowed = {'## 经','## 续经','## 经（含获麟后续经）','## 传'}
    for num, line in enumerate(text.splitlines(), 1):
        if line.startswith('## '):
            flush()
            require(line in allowed, f'Unexpected heading {path}: {line}')
            heading = line
            section = 'zhuan' if line == '## 传' else 'annal'
        elif line.startswith('<a '):
            flush()
        elif not line.strip():
            flush()
        elif section:
            if not buf:
                first = num
            last = num
            buf.append(line)
    flush()
    require((counts['annal'],counts['zhuan']) == COUNTS[year],
            f'Paragraph counts year {year}: {dict(counts)} != {COUNTS[year]}')
    if year == 14:
        require(records[0]['text'] == '十有四年春，西狩获麟。', 'Changed end-of-jing boundary')
    if year >= 17:
        require(all(p['layer']=='zhuan' for p in records), 'Invented jing after year 16')
    return {'path':path,'url':url.group(1),'blob':blob,'records':records,
            'by_key':{(p['section'],p['paragraph']):p for p in records}}


def read_events() -> dict[int,list[dict]]:
    years = {y:[] for y in range(1,28)}
    for name in INPUTS:
        for lineno, line in enumerate((DATA/name).read_text(encoding='utf-8').splitlines(),1):
            if not line.strip() or line.startswith('#'):
                continue
            cols = [x.strip() for x in line.split('|')]
            require(len(cols)==8, f'{name}:{lineno}: expected 8 fields, got {len(cols)}')
            year, role, title, body, annals, zhuan, note, extra = cols
            y = int(year)
            require(y in years and role in ('E','N') and title and body, f'Bad input {name}:{lineno}')
            row = {'role':role,'title':title,'body':body.replace('\\n','\n'),
                   'note':note.replace('\\n','\n'),'extra':extra.split(',') if extra else [],
                   'input_file':name,'input_line':lineno}
            for section, value in (('annal',annals),('zhuan',zhuan)):
                row[section] = [int(v) for v in value.split(',')] if value else []
                require(len(row[section])==len(set(row[section])), f'Duplicate selector {name}:{lineno}')
            years[y].append(row)
    for y, rows in years.items():
        require(any(r['role']=='E' for r in rows), f'Year {y} has no annual narrative')
        counters: Counter = Counter()
        for row in rows:
            counters[row['role']] += 1
            n = counters[row['role']]
            row['number'] = n
            row['anchor'] = f'event-{n}' if row['role']=='E' else f'context-{n}'
            row['note_anchor'] = f'note-{n}' if row['role']=='E' else f'note-context-{n}'
            row['display'] = str(n) if row['role']=='E' else f'补注{n}'
    return years


def source_block(src: dict, p: dict, year: int) -> str:
    book = {'jing':'《春秋》本经','continued_jing':'获麟后续经','zhuan':'《左传》'}[p['layer']]
    link = f'{REPO}/blob/{BASE}/{src["path"]}#L{p["start_line"]}-L{p["end_line"]}'
    quote = '\n'.join('> '+s for s in p['text'].splitlines())
    return f'**{book}·哀公{cn(year)}年** · [固定版本原文]({link})\n\n{quote}'


def replace_block(text: str, name: str, body: str) -> str:
    begin, end = f'<!-- {name}:start -->', f'<!-- {name}:end -->'
    block = begin+'\n\n'+body.strip()+'\n\n'+end
    if begin in text:
        require(text.count(begin)==text.count(end)==1, f'Broken markers {name}')
        return text[:text.index(begin)] + block + text[text.index(end)+len(end):]
    require(end not in text, f'Orphan marker {name}')
    return text.rstrip()+'\n\n'+block+'\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Validate tracked output without writing')
    check = parser.parse_args().check
    events = read_events()
    sources = {y:parse_source(y) for y in range(1,28)}
    extra = json.loads((DATA/'supplemental-sources.json').read_text(encoding='utf-8'))
    excerpts = extra['excerpts']
    # Exhaust the bounded Lu Shijia text, rather than merely count saved excerpts.
    remainder = '\n'.join(extra['lu_scope_blocks'])
    for key, item in excerpts.items():
        require(item['source'] in extra['sources'], f'Unknown supplemental source {key}')
        if item['source']=='lu':
            require(remainder.count(item['quote'])==1, f'Lu excerpt missing/duplicated: {key}')
            remainder = remainder.replace(item['quote'],'',1)
    require(not remainder.strip(), f'Unassigned bounded Lu text: {remainder}')

    rendered: dict[Path,str] = {}
    mapping, yearly = [], []
    used = defaultdict(list)
    shared_seen = set()
    cal_count = 0
    for year, rows in events.items():
        src = sources[year]
        assigned = defaultdict(list)
        row_by_note = {r['note_anchor']:r for r in rows}
        for row in rows:
            require(row['annal'] or row['zhuan'] or row['extra'], f'{year}/{row["anchor"]}: no source')
            for section in ('annal','zhuan'):
                for idx in row[section]:
                    require((section,idx) in src['by_key'], f'{year}/{row["anchor"]}: no {section}/{idx}')
                    assigned[(section,idx)].append(row['note_anchor'])
            for key in row['extra']:
                require(key in excerpts, f'Unknown excerpt {year}/{key}')
                used[key].append({'year':year,'year_bce':495-year,'role':row['role'],
                                  'title':row['title'],'anchor':row['note_anchor'],'note':row['note'],
                                  'destination':f'chronicle/chunqiu/years/bce-{495-year:04d}.md#{row["note_anchor"]}'})
        calendar = []
        for p in src['records']:
            key = (p['section'],p['paragraph'])
            if key not in assigned and (year,p['paragraph']) in CALENDAR and p['section']=='annal':
                require(re.sub(r'[，。\s]', '', p['text'])==re.sub(r'[，。\s]', '', CALENDAR[(year,p['paragraph'])]), f'Unexpected calendar text {year}/{key}')
                assigned[key] = ['note-calendar']
                calendar.append(p)
        missing = [f'{p["section"]}/{p["paragraph"]}:{p["text"][:55]}' for p in src['records'] if (p['section'],p['paragraph']) not in assigned]
        require(not missing, f'Unmapped year {year}: {missing}')
        for (section,idx), dests in assigned.items():
            if len(dests)>1:
                require(SHARED.get((year,section,idx))==len(dests), f'Undeclared shared paragraph {year}/{section}/{idx}: {dests}')
                require(len(set(dests))==len(dests), 'Repeated destination')
                shared_seen.add((year,section,idx))
        require(not (year==27 and 'note-context-2' not in assigned[('zhuan',5)]), 'Later Dao paragraph must be a boundary note')
        annual = [r for r in rows if r['role']=='E']
        boundaries = [r for r in rows if r['role']=='N']
        bce = 495-year
        prev = f'[上一年：前{bce+1}](bce-{bce+1:04d}.md)'
        nxt = f'[下一年：前{bce-1}](bce-{bce-1:04d}.md)' if year<27 else '[本组终点与后续底本](../aigong/NEXT-STEPS.md)'
        nav = f'{prev} · [哀公目录](../aigong/README.md) · [春秋目录](../README.md) · {nxt}'
        if year<=13:
            layer_note = '本页以《春秋》本经与《左传》对读。'
        elif year==14:
            layer_note = '《春秋》本经止于本页“西狩获麟”；同年后续年事分别标明“获麟后续经”及《左传》。'
        elif year<=16:
            layer_note = '本页经类材料属于获麟后续经，不再标为《春秋》本经；与《左传》分别标注。'
        else:
            layer_note = '本页只有《左传》年条及明确列出的补充史料，没有虚构经文。'
        page = [f'# 公元前{bce}年（鲁哀公{cn(year)}年）',nav,
                '> 第一轮白话整理。古历月日不直接等同公历月日；出处覆盖不等于逐句翻译或现代学术定本。',
                layer_note,'## 本年纪事']
        for row in annual:
            page.extend([f'<a id="{row["anchor"]}"></a>',f'{row["number"]}. **{row["title"]}**',
                         row['body']+f' [{row["display"]}](#{row["note_anchor"]})'])
        if boundaries:
            page.append('## 前后年与史料界线（不计为本年新增事件）')
            for row in boundaries:
                page.extend([f'<a id="{row["anchor"]}"></a>',f'### {row["title"]}',
                             row['body']+f' [{row["display"]}](#{row["note_anchor"]})'])
        lurows = [r for r in rows if any(excerpts[k]['source']=='lu' for k in r['extra'])]
        if lurows:
            status = '《鲁周公世家》本段已对照；相关原文在'+'、'.join(f'[{r["display"]}](#{r["note_anchor"]})' for r in lurows)+'号史料中，不另造同一事件。'
        else:
            status = '已核对《鲁周公世家》哀公段，未见可单独补入本年的明确年事。此结论仅限已核本篇，不代表整部《史记》都没有材料。'
        if year==11:
            status += ' 本篇接在归鲁后的陈常弑简公，依经传移读[前481年](bce-0481.md#event-5)，不在本年重复。'
        page.extend(['## 《鲁周公世家》本年对照',status,
                     '[逐项对照与归年](../aigong/SHIJI-CROSSWALK.md)',
                     '## 本年相关史料',
                     '原文逐段保存。回叙、后事、占候与人物判断依同号说明区分。原工作本的缺字、网页残标不静默改写；明确共用一段的条目列出所有去向。'])
        for row in rows:
            page.extend([f'<a id="{row["note_anchor"]}"></a>',f'### [{row["display"]}] {row["title"]}'])
            for section in ('annal','zhuan'):
                for idx in row[section]:
                    p = src['by_key'][(section,idx)]
                    page.append(source_block(src,p,year))
                    dests = assigned[(section,idx)]
                    if len(dests)>1:
                        page.append('**同段共用：** '+'、'.join(f'[{row_by_note[d]["display"]}](#{d})' for d in dests)+'；覆盖统计仅计一段原文。')
            for key in row['extra']:
                item = excerpts[key]
                source = extra['sources'][item['source']]
                page.extend([f'**{source["title"]}·{item["label"]}** · [所核固定版本]({source["url"]})',
                             '> '+item['quote']])
                if item.get('limit'):
                    page.append('**引文层次：** '+item['limit'])
            if row['note']:
                page.append('**说明：** '+row['note'])
            page.append(f'[返回{row["display"]}](#{row["anchor"]})')
        if calendar:
            page.extend(['<a id="note-calendar"></a>','### 年首、季首题记（不计独立事件）'])
            for p in calendar:
                page.append(source_block(src,p,year))
            page.append('此处只有年月，没有可单独编写的事件；仍保留原文去向，不因数字统计而虚增史事。')
        page.extend([f'[本年完整经传工作本](../../../{src["path"]}) · [工作本原来源]({src["url"]})',nav])
        text = '\n\n'.join(page)+'\n'
        require(len(re.findall(r'<a id="event-\d+">',text))==len(annual), 'Event count mismatch')
        require(len(re.findall(r'<a id="context-\d+">',text))==len(boundaries), 'Boundary count mismatch')
        rendered[OUT/f'bce-{bce:04d}.md'] = text
        for p in src['records']:
            dests = assigned[(p['section'],p['paragraph'])]
            mapping.append({'regnal_year':year,'year_bce':bce,'source_commit':BASE,
                            'source_file':src['path'],'source_blob_sha':src['blob'],
                            **{k:p[k] for k in ('section','paragraph','layer','source_heading','start_line','end_line','sha256')},
                            'prefix':p['text'][:45], 'destinations':[f'chronicle/chunqiu/years/bce-{bce:04d}.md#{d}' for d in dests],
                            'intentional_shared':len(dests)>1,
                            'disposition':'calendar_only' if dests==['note-calendar'] else ('source_boundary' if all(d.startswith('note-context-') for d in dests) else 'annual_narrative_and_same_number_note')})
        counts = Counter(p['layer'] for p in src['records'])
        cal_count += len(calendar)
        yearly.append({'regnal_year':year,'year_bce':bce,'narrative_entries':len(annual),
                       'non_event_boundary_notes':len(boundaries),'jing_paragraphs':counts['jing'],
                       'continued_jing_paragraphs':counts['continued_jing'],'zhuan_paragraphs':counts['zhuan'],
                       'mapped_unique_paragraphs':len(assigned),'source_paragraph_references':sum(map(len,assigned.values())),
                       'calendar_only_paragraphs':len(calendar),'unmapped_paragraphs':0,
                       'source_blob_verified':src['blob']})
    require(shared_seen==set(SHARED), f'Declared shared paragraph absent: {set(SHARED)-shared_seen}')
    require(set(used)==set(excerpts), f'Supplemental excerpt has no destination: {set(excerpts)-set(used)}')
    require(all(len(v)==1 for v in used.values()), 'Duplicate primary excerpt destination')

    total_entries = sum(y['narrative_entries'] for y in yearly)
    core_count = sum(v['source']=='lu' for v in excerpts.values())
    audit = {'batch':'鲁哀公元年至二十七年','editorial_date':DATE,
             'status':'first_readable_pass_with_explicit_text_layers_and_paragraph_mapping',
             'source_commit':BASE,'year_pages':27,'narrative_entries':total_entries,
             'non_event_boundary_notes':sum(y['non_event_boundary_notes'] for y in yearly),
             'jing_paragraphs':sum(y['jing_paragraphs'] for y in yearly),
             'continued_jing_paragraphs':sum(y['continued_jing_paragraphs'] for y in yearly),
             'zhuan_paragraphs':sum(y['zhuan_paragraphs'] for y in yearly),
             'mapped_unique_paragraphs':len(mapping),
             'source_paragraph_references':sum(y['source_paragraph_references'] for y in yearly),
             'unmapped_paragraphs':0,'intentional_shared_paragraphs':len(shared_seen),
             'undeclared_duplicate_assignments':0,'calendar_only_paragraphs':cal_count,
             'source_blob_checks_passed':27,'lu_shijia_excerpts':core_count,
             'other_ancient_excerpts':len(excerpts)-core_count,
             'bounded_lu_shijia_text_completely_assigned':True,
             'aigong_14_jing_ends_after_first_annal_paragraph':True,
             'aigong_15_16_annals_labelled_as_continuation':True,
             'aigong_17_27_no_invented_jing':True,
             'appended_dao4_and_zhibo_end_excluded_from_aigong27_events':True,
             'shiji_death_return_dispute_retained_as_boundary_note':True,
             'modern_scholarly_collation_complete':False,'all_shiji_chapters_reviewed':False,
             'xianggong_review_completed_by_this_batch':False,
             'input_sha256':{name:hashlib.sha256((DATA/name).read_bytes()).hexdigest() for name in (*INPUTS,'supplemental-sources.json')},
             'supplemental_excerpt_destinations':{k:[{q:d[q] for q in ('year','year_bce','role','anchor','destination')} for d in vs] for k,vs in used.items()},
             'limitations':'A mapped paragraph may include earlier or later events, speeches, predictions and commentary. Counts are not independent event counts, literal-translation completeness, or historical consensus.',
             'years':yearly}
    rendered[DATA/'audit-01-27.json'] = dump(audit)
    rendered[DATA/'paragraph-map-01-27.jsonl'] = '\n'.join(json.dumps(r,ensure_ascii=False) for r in mapping)+'\n'
    rendered[DATA/'events-01-27.json'] = dump({'source_commit':BASE,'years':events})

    cross = ['# 《鲁周公世家》｜哀公组逐项对照',
             f'核对日期：{DATE}。范围为本篇哀公段及承前继位句，包含出亡后有争议的终局；不是整部《史记》已融合。',
             '所核有限范围逐字分配到摘录，再核对摘录去向。字句覆盖不代表每一版本均已被判定真实。',
             f'[固定原文]({extra["sources"]["lu"]["url"]}) · [摘录数据](data/supplemental-sources.json)']
    for key, item in excerpts.items():
        src = extra['sources'][item['source']]
        d = used[key][0]
        cross.extend([f'## {key}｜{item["label"]}',f'来源：[{src["title"]}]({src["url"]})。{src["access"]}。',
                      '> '+item['quote'],f'[安放位置：哀公{cn(d["year"])}年，{d["title"]}](../years/bce-{d["year_bce"]:04d}.md#{d["anchor"]})',d['note']])
        if item.get('limit'):
            cross.append('引文限制：'+item['limit'])
    cross.extend(['## 未另增年事的年份',
                  '本篇哀公段没有单独覆盖的年份仍逐年检查；并不从本篇缺载推论整部《史记》无事。无另补年事的页面都保留了范围说明。',
                  '[实际研究阅读范围](RESEARCH-NOTES.md) · [回哀公目录](README.md)'])
    rendered[BATCH/'SHIJI-CROSSWALK.md'] = '\n\n'.join(cross)+'\n'
    research = ['# 哀公组｜考辨与实际阅读范围',f'核对日期：{DATE}。',
                '## 已读的古籍与古注',
                '\n\n'.join(f'**{s["title"]}**：{s["access"]}。[固定版本]({s["url"]})' for s in extra['sources'].values()),
                '古籍段落全部引用的是古文，不是现代译者的译文。注、音义、疏与原经传分别署名标注，不把古注等同现代研究结论。',
                '## 影响年度编排的取舍',
                '百牢交涉：《左传》七年明确最后供给，《鲁周公世家》写以礼使吴乃止，子贡参与事项也不同。本批按传文分别讲百牢与召季康子，异说在同注。齐取鲁邑数量，经传列二邑、世家称三邑，不补造第三地。',
                '黄池争先：《左传》先晋，《国语》先吴；正文只写争先和结盟，注中对列相反结局，不冒称现代学界多数。',
                '获麟与续经：十四年第一条属于本经，后续年事另标续经；十五、十六年为续经；十七至二十七年仅传。借古注说明传统分层，不据此判定所有篇章作者及成书年代。',
                '卫国政变：传文在十五年闰月，续经在十六年春。参考杜预从告录的解释，详细过程只编一次，十六年保留非事件性对读注。',
                '孔子卒日、敬王卒年：保留原文及古注指出的问题，不未经独立历算强换公历。',
                '哀公终局：《史记》返归卒于有山与《左传》国人施有山存在张力，孔颖达疏明确质疑；本批保留两层而未将返归和死亡计成已核本年事件。末段悼公四年及智伯败亡独立列为后事。',
                '## 只检索到书目的现代研究',
                '\n\n'.join(f'**{x["title"]}**：{x["status"]}。' for x in extra['research_scope']['metadata_only']),
                '上述条目未取得全文，因此没有据其裁定黄池盟序、器物铭文或学界倾向。本批并未完成现代文献的系统审查。',
                '## 仍需后续核校',
                '；'.join(extra['research_scope']['unresolved'])+'。其他《史记》世家、列传的对应段落仍需逐篇融合。',
                '[返回目录](README.md)']
    rendered[BATCH/'RESEARCH-NOTES.md'] = '\n\n'.join(research)+'\n'
    rendered[BATCH/'NEXT-STEPS.md'] = '''# 《左传》年条之后怎样继续

本组读至鲁哀公二十七年，按现有年条口径对应前468年。这里是本项目现存《左传》逐年工作本的终点，不是中国历史或所有相关材料的终点。

## 紧接的历史线

鲁悼公、智伯与赵韩魏的关系，需要对读《史记·鲁周公世家》《晋世家》《赵世家》《六国年表》等，重新核定相互纪年后再逐年编排。不能直接把附在哀公末页的“悼之四年”套上哀公二十七年的公元年份。哀公返归、卒年及悼公起年也仍须保留争议。

## 既有稿件的缺口

襄公末段的独立复核尚未收尾；哀公组完成不自动改变它的状态。其他已编君主虽有春秋左传叙事，也不代表《鲁周公世家》以外所有史记篇章已经完整融合。

## 更换编年底本的界限

《资治通鉴》主体从周威烈王二十三年（前403）开始，见[卷一首年原文](https://zh.wikisource.org/w/index.php?title=資治通鑑/卷001&oldid=2489405)；从当前终点到该处之间，必须另外整理史记年表及世家材料，不能虚构现有通鉴年度原文已覆盖这段。开始下一批前先完成源文件及年表对照，再沿用一年一页和同号脚注。

[回到哀公目录](README.md) · [春秋目录](../README.md)
'''
    table = ['| 年页 | 本年入口 | 白话条目 | 非事件补注 |','|---|---|---:|---:|']
    for y, rows in events.items():
        first = next(r for r in rows if r['role']=='E')
        yr = yearly[y-1]
        table.append(f'| [哀公{cn(y)}年｜前{495-y}](../years/bce-{495-y:04d}.md) | {first["title"]} | {yr["narrative_entries"]} | {yr["non_event_boundary_notes"]} |')
    readme = ['# 鲁哀公｜二十七年第一轮逐年整理（前494—前468）',
              f'已编 **27张年度页、{total_entries}条白话条目**，另有{audit["non_event_boundary_notes"]}条跨年或来源界线补注，不计作新事件。每条正文由编号链接到完整古文原段与异说说明。',
              '\n'.join(table),'## 不能混淆的三种来源层次',
              '元年至十三年：本经与传；十四年“西狩获麟”为本经终条，其后是续经；十五、十六年仍为续经与传；十七年至二十七年只有传及明确列出的补充古籍。页面逐段标注，不将获麟后的记录冒称全部出于本经。',
              '## 原文与检查',
              f'本经{audit["jing_paragraphs"]}段、续经{audit["continued_jing_paragraphs"]}段、传文{audit["zhuan_paragraphs"]}段，合计{len(mapping)}段，全部有去向。未分配0段。{len(shared_seen)}段因包含不同事项而明确共用，出处引用总数{audit["source_paragraph_references"]}；未声明重复0处。{cal_count}段纯年月题记另存，不虚增事件。27份原文实际Git blob哈希全部核验。',
              f'《鲁周公世家》哀公整段及承前继位句拆为{core_count}条摘录，全部分配，包括有争议的终局；另有{len(excerpts)-core_count}条古籍或古注辅助。',
              '[检查结果](data/audit-01-27.json) · [逐段去向](data/paragraph-map-01-27.jsonl) · [《史记》及古注对照](SHIJI-CROSSWALK.md) · [研究阅读范围](RESEARCH-NOTES.md)',
              '## 重要归年与叙述界线',
              '吴越战争保留会稽议和、北上、越入吴、笠泽、围吴、灭吴各阶段；卫国蒯聩与辄多次出入分别写，政变与跨年告录只算一次。齐国荼、阳生、壬三次君位变动分清，陈乞与陈恒不混同。',
              '黄池盟序保留左传先晋、国语先吴；百牢及取邑数量保留世家差异。孔子归鲁、田赋筹划与施行、孔子去世不合并。哀公是否返归、卒于有山仍为争议；悼公四年及智伯败亡放入末页后事注。',
              '“第一轮完成”不等于逐句翻译、现代学术定本或全部史记融合。襄公待收尾复核仍单独记录，不能因此宣称全书所有年份已连续终审。',
              '## 复现',
              '在仓库根目录运行 `python3 scripts/build_aigong_01_27.py`。加 `--check` 仅校验，不写入。输入为四份人工PSV及补充原文JSON；脚本只排版和检查，不生成历史叙述。',
              '## 之后的阅读',
              '[《左传》终点、鲁悼公线与后续底本](NEXT-STEPS.md)。',
              '[上一组：鲁定公](../dinggong/README.md) · [返回春秋目录](../README.md)']
    rendered[BATCH/'README.md'] = '\n\n'.join(readme)+'\n'

    # Link the older batch without changing its historical narrative.
    prev = OUT/'bce-0495.md'
    old = '下一年：前494（哀公元年，白话页待编）'
    new = '[下一年：前494（哀公元年）](bce-0494.md)'
    text = prev.read_text(encoding='utf-8')
    require(old in text or new in text, 'Unexpected Dinggong final-page navigation')
    rendered[prev] = text.replace(old,new)
    ding = ROOT/'chronicle/chunqiu/dinggong/README.md'
    old_group = '**鲁哀公元年（前494）**。'
    new_group = '[鲁哀公全组（前494—前468）](../aigong/README.md)。'
    text = ding.read_text(encoding='utf-8')
    require(old_group in text or new_group in text, 'Unexpected Dinggong group navigation')
    rendered[ding] = text.replace(old_group,new_group)
    index = ROOT/'chronicle/chunqiu/README.md'
    text = index.read_text(encoding='utf-8')
    text = text.replace('下一组从鲁哀公元年（前494）开始。','鲁哀公续编见下方独立入口。')
    body = f'## 鲁哀公：二十七年第一轮已编（前494—前468）\n\n[哀公全组阅读入口](aigong/README.md)。27页、{total_entries}条白话条目，另有{audit["non_event_boundary_notes"]}条非事件补注；{len(mapping)}段本经、续经及传文全部有去向。明确区分获麟终经、续经和左传末年。襄公复核状态未在本批变更。后续请见[底本与纪年交接](aigong/NEXT-STEPS.md)。'
    rendered[index] = replace_block(text,'aigong-01-27',body)
    # Preserve the same navigation if the previous batch is regenerated later.
    script = ROOT/'scripts/build_dinggong_01_15.py'
    st = script.read_text(encoding='utf-8')
    hook = '    # Preserve Aigong handoff once the next batch exists.\n'
    if hook not in st:
        target = '    def target_text(path: Path) -> str:\n'
        require(target in st, 'Cannot safely patch prior renderer handoff')
        patch = hook + "    if (ROOT/'chronicle/chunqiu/aigong/README.md').exists():\n" + \
            "        rendered[BATCH/'README.md'] = rendered[BATCH/'README.md'].replace('**鲁哀公元年（前494）**。', '[鲁哀公全组（前494—前468）](../aigong/README.md)。')\n" + \
            "        rendered[index] = rendered[index].replace('下一组从鲁哀公元年（前494）开始。', '鲁哀公续编见下方独立入口。')\n\n"
        st = st.replace(target,patch+target,1)
    rendered[script] = st

    def target_text(path: Path) -> str:
        return rendered[path] if path in rendered else path.read_text(encoding='utf-8')

    link_count = 0
    for path, text in rendered.items():
        if path.suffix!='.md':
            continue
        anchors = re.findall(r'<a id="([^"]+)">',text)
        require(len(anchors)==len(set(anchors)), f'Duplicate anchor {path}')
        for link in re.findall(r'\]\(([^\s\)]+)\)',text):
            if link.startswith(('https:','http:','mailto:')):
                continue
            filename,_,anchor = link.partition('#')
            destination = (path.parent/unquote(filename)).resolve() if filename else path
            require(destination in rendered or destination.is_file(), f'Broken local link {path}: {link}')
            if anchor.startswith(('event-','note-','context-')):
                require(f'<a id="{anchor}"></a>' in target_text(destination), f'Broken target anchor {path}: {link}')
            link_count += 1
    # Verify exact ancient text survives rendering, including declared repeated quotes.
    for year, src in sources.items():
        page = rendered[OUT/f'bce-{495-year:04d}.md']
        expected_quotes = Counter()
        for p in src['records']:
            quote = '\n'.join('> '+line for line in p['text'].splitlines())
            expected_quotes[quote] += SHARED.get((year,p['section'],p['paragraph']),1)
        for quote, expected in expected_quotes.items():
            require(page.count(quote+'\n\n')==expected, f'Original quote mismatch {year}: {quote[:60]}')
    audit['validated_local_links'] = link_count
    audit['full_source_quote_checks_passed'] = len(mapping)
    rendered[DATA/'audit-01-27.json'] = dump(audit)
    changed = [p for p,t in rendered.items() if not p.exists() or p.read_text(encoding='utf-8')!=t]
    if check:
        require(not changed, 'Generated output differs:\n'+'\n'.join(str(p.relative_to(ROOT)) for p in changed))
    else:
        for path, text in rendered.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(text,encoding='utf-8')
    print(dump({'check_only':check,'generated_files':len(rendered),'changed_files':len(changed),
                'year_pages':27,'narrative_entries':total_entries,
                'jing':audit['jing_paragraphs'],'continued_jing':audit['continued_jing_paragraphs'],
                'zhuan':audit['zhuan_paragraphs'],'unique_source_paragraphs':len(mapping),
                'intentional_shared_paragraphs':len(shared_seen),'calendar_only':cal_count,
                'boundary_notes':audit['non_event_boundary_notes'],'lu_excerpts':core_count,
                'other_excerpts':len(excerpts)-core_count,'validated_local_links':link_count,
                'source_hashes_full_quotes_and_links_valid':True}))


if __name__ == '__main__':
    main()
