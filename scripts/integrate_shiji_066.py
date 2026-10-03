#!/usr/bin/env python3
"""Apply the manually reviewed Shiji 66 integration to existing year pages.

The immutable base commit is intentional. A changed reader page is never silently
replaced: it must match the base, this run, or the last audited integration run.
Original quotations and unrelated events are preserved. Standard library only.
Run normally to write, or --check for a read-only reproducibility check.
The base commit must be available locally (git fetch origin <base> if needed).
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / 'chronicle/shiji-integration'
SPEC = BATCH / 'data/merge-066.json'
AUDIT = BATCH / 'data/audit-066.json'
REPO = 'https://github.com/zhixin0825/history'


def require(test: bool, message: str) -> None:
    if not test:
        raise ValueError(message)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def event_pattern(n: int) -> re.Pattern:
    return re.compile(r'<a id="event-' + str(n) + r'"></a>\s*\n' + str(n)
                      + r'\. \*\*(?P<title>.*?)\*\*\s*\n(?P<body>.*?)'
                      + r'\[' + str(n) + r'\]\(#note-' + str(n) + r'\)', re.S)


def event_ids(text: str) -> set[int]:
    return {int(n) for n in re.findall(r'<a id="event-(\d+)"></a>', text)}


def quoted_blocks(text: str) -> Counter:
    return Counter(m.group(0).strip() for m in re.finditer(r'(?m)^>[^\n]*(?:\n>[^\n]*)*', text))


def marked(text: str, key: str, body: str) -> str:
    a, b = f'<!-- {key}:start -->', f'<!-- {key}:end -->'
    block = a + '\n\n' + body.strip() + '\n\n' + b
    if a in text:
        require(text.count(a) == text.count(b) == 1, f'Broken markers {key}')
        return text[:text.index(a)] + block + text[text.index(b)+len(b):]
    require(b not in text, f'Orphan marker {key}')
    return text.rstrip() + '\n\n' + block + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    check = parser.parse_args().check
    spec = json.loads(SPEC.read_text(encoding='utf-8'))
    base = spec['base_commit']
    require(re.fullmatch(r'[0-9a-f]{40}', base) is not None, 'Invalid base commit')
    baseline: dict[str, bytes | None] = {}
    repository_paths = set(subprocess.check_output(['git','ls-tree','-r','--name-only',base], cwd=ROOT, text=True).splitlines())

    def original(path: str, optional: bool = False) -> str | None:
        require(not path.startswith('/') and '..' not in Path(path).parts, f'Unsafe path: {path}')
        if path not in baseline:
            p = subprocess.run(['git', 'show', f'{base}:{path}'], cwd=ROOT, capture_output=True)
            if p.returncode:
                if optional:
                    baseline[path] = None
                else:
                    raise ValueError(f'Cannot read immutable baseline {base}:{path}. Fetch that commit first.\n' + p.stderr.decode(errors='replace'))
            else:
                baseline[path] = p.stdout
        data = baseline[path]
        if data is None:
            return None
        return data.decode('utf-8')

    raw = (ROOT/spec['source_path']).read_bytes()
    require(blob(raw) == spec['source_blob'], 'Original Shiji TXT changed; revalidate line numbers')
    lines = raw.decode('utf-8-sig').splitlines()
    begin, end = lines.index('*01-066*')+1, lines.index('*01-067*')
    substantive = [n+1 for n in range(begin, end) if lines[n].strip() and lines[n] != '評論']
    require(substantive == spec['substantive_lines'], 'Chapter 66 scope changed')
    require(lines[4658] == '*01-066*' and lines[4682] == '評論', 'Chapter metadata mismatch')
    paragraphs = {n: lines[n-1] for n in substantive}
    destinations: dict[int, list[dict]] = defaultdict(list)
    ops_by_year: dict[int, list[dict]] = defaultdict(list)
    seen_ops = set()
    for op in spec['operations']:
        key = (op['year'], op['event'])
        require(key not in seen_ops, f'Duplicate edit for event {key}')
        require(op['mode'] in ('replace', 'append', 'note', 'new'), f'Unknown edit mode: {op}')
        require(bool(op['lines']) and bool(op['note']), f'Missing sources/editorial note {key}')
        seen_ops.add(key)
        ops_by_year[op['year']].append(op)
        for n in op['lines']:
            require(n in paragraphs, f'Invalid Shiji source line {n}')
            destinations[n].append({'path': f'chronicle/chunqiu/years/bce-{op["year"]:04d}.md',
                                    'anchor': f'note-{op["event"]}', 'role': op['mode'],
                                    'year_bce': op['year'], 'event': op['event']})
    context_ids = {c['id'] for c in spec['contexts']}
    for context in spec['contexts']:
        for n in context['lines']:
            require(n in paragraphs, f'Unknown context source line {n}')
            destinations[n].append({'path': 'chronicle/shiji-integration/CONTEXT-066.md',
                                    'anchor': context['id'], 'role': 'undated_or_author_comment'})
    require(set(destinations) == set(paragraphs), f'Unassigned chapter paragraphs: {set(paragraphs)-set(destinations)}')

    rendered: dict[str, str] = {}
    old_page_counts, new_page_counts = {}, {}
    old_quote_count = 0
    reference_count = 0
    page_audit = []

    def quote_block(n: int) -> str:
        link = f'{REPO}/blob/{base}/{spec["source_path"]}#L{n}-L{n}'
        quote = '\n'.join('> ' + s for s in paragraphs[n].splitlines())
        return f'**《史记·伍子胥列传》·原TXT第{n}行** · [固定版本原文]({link})\n\n{quote}'

    def source_note(op: dict) -> str:
        blocks = ['**本次汇入《伍子胥列传》：**']
        if any(len(destinations[n]) > 1 for n in op['lines']):
            blocks.append('下引原段有的跨年或兼记数事；本条采用范围见说明，[全部去向另列](../../shiji-integration/CHAPTER-066.md)。共用原段不重复计为新的史事。')
        blocks.extend(quote_block(n) for n in op['lines'])
        for key in op.get('external', []):
            ext = spec['external_sources'][key]
            blocks.extend([f'**对读：{ext["title"]}** · [原文]({ext["url"]})', '> ' + ext['quote'],
                           '**核读范围：** ' + ext['read_scope']])
        blocks.append('**汇入说明：** ' + op['note'])
        if op.get('links'):
            links = [f'[前{y}年第{n}条](bce-{y:04d}.md#event-{n})' for y,n in op['links']]
            blocks.append('**前后关联：** ' + ' · '.join(links))
        if op.get('context'):
            require(op['context'] in context_ids, 'Undefined context')
            blocks.append(f'[未确年材料或作者评论](../../shiji-integration/CONTEXT-066.md#{op["context"]})')
        return '\n\n'.join(blocks)

    for year in sorted(ops_by_year, reverse=True):
        path = f'chronicle/chunqiu/years/bce-{year:04d}.md'
        before = original(path)
        require(before is not None, f'Missing existing year {year}')
        page = before
        old_ids = event_ids(before)
        old_page_counts[year] = len(old_ids)
        edited, additions = set(), []
        for op in ops_by_year[year]:
            n = op['event']
            if op['mode'] == 'new':
                require(n not in old_ids, f'New event overwrites old anchor {year}/{n}')
                additions.append(op)
                continue
            require(n in old_ids, f'No original event {year}/{n}')
            pattern = event_pattern(n)
            matches = list(pattern.finditer(page))
            require(len(matches) == 1, f'Ambiguous event body {year}/{n}')
            m = matches[0]
            title = op.get('title', m['title'])
            body = m['body'].strip()
            if op['mode'] == 'replace':
                body = op['body']
            elif op['mode'] == 'append':
                body += '\n\n' + op['body']
            if op['mode'] != 'note':
                new_block = f'<a id="event-{n}"></a>\n\n{n}. **{title}**\n\n{body} [{n}](#note-{n})'
                page = page[:m.start()] + new_block + page[m.end():]
                edited.add(n)
            if 'title' in op:
                header = re.compile(r'(?m)^### \[' + str(n) + r'\] [^\n]+$')
                page, changed = header.subn(f'### [{n}] {title}', page)
                require(changed == 1, f'Footnote heading not unique {year}/{n}')
            start = page.index(f'<a id="note-{n}"></a>')
            return_link = re.compile(r'(?m)^\[[^\]\n]+\]\(#event-' + str(n) + r'\)[ \t]*$')
            returns = list(return_link.finditer(page, start))
            require(len(returns) == 1, f'Missing/duplicate footnote return {year}/{n}')
            at = returns[0].start()
            page = page[:at] + source_note(op) + '\n\n' + page[at:]
            reference_count += len(op['lines'])
        additions.sort(key=lambda x: x['event'])
        require([x['event'] for x in additions] == list(range(max(old_ids)+1, max(old_ids)+1+len(additions))),
                f'New event anchors are not a contiguous extension in {year}')
        if additions:
            at = page.index('\n## ', page.index('## 本年纪事')+len('## 本年纪事'))
            new_events = []
            new_notes = []
            for op in additions:
                n = op['event']
                new_events.extend([f'<a id="event-{n}"></a>', f'{n}. **{op["title"]}**',
                                   op['body'] + f' [{n}](#note-{n})'])
                new_notes.extend([f'<a id="note-{n}"></a>', f'### [{n}] {op["title"]}', source_note(op),
                                  f'[返回第{n}条](#event-{n})'])
                reference_count += len(op['lines'])
            page = page[:at].rstrip() + '\n\n' + '\n\n'.join(new_events) + '\n' + page[at:]
            at = page.index('[本年完整经传工作本]')
            page = page[:at].rstrip() + '\n\n' + '\n\n'.join(new_notes) + '\n\n' + page[at:]
        require(event_ids(page) == old_ids | {op['event'] for op in additions}, f'Lost/repeated event anchors {year}')
        for n in old_ids-edited:
            require(event_pattern(n).search(page).group(0) == event_pattern(n).search(before).group(0),
                    f'Unrelated event changed {year}/{n}')
        quoted_before, quoted_after = quoted_blocks(before), quoted_blocks(page)
        require(not (quoted_before - quoted_after), f'Existing ancient quotations lost in {year}')
        old_quote_count += sum(quoted_before.values())
        new_page_counts[year] = len(event_ids(page))
        rendered[path] = page
        page_audit.append({'year_bce':year, 'path':path, 'base_git_blob':blob(baseline[path]),
                           'old_entries':len(old_ids), 'current_entries':new_page_counts[year],
                           'rewritten_or_expanded_entries':len(edited), 'new_entries':len(additions),
                           'source_only_enrichments':sum(op['mode']=='note' for op in ops_by_year[year]),
                           'old_event_anchors_preserved':True, 'old_quote_blocks_preserved':sum(quoted_before.values())})

    context_text = ['# 《伍子胥列传》｜未确年材料与作者评论',
                    '这里不是另一套年表。能对应已有年事的内容已写回原页；只有无法硬定某年的后事、来源冲突和作者评论另列。']
    for c in spec['contexts']:
        context_text.extend([f'<a id="{c["id"]}"></a>', f'## {c["title"]}', c['body']])
        context_text.extend(quote_block(n) for n in c['lines'])
        for y in c['years']:
            context_text.append(f'[返回前{y}年主年表](../chunqiu/years/bce-{y:04d}.md)')
    context_text.append('[回到本批汇入目录](README.md)')
    rendered['chronicle/shiji-integration/CONTEXT-066.md'] = '\n\n'.join(context_text)+'\n'

    mapping = []
    cross = ['# 卷六十六《伍子胥列传》｜每段原文的主年表去向',
             f'固定底本 `{base}`，原TXT Git blob `{spec["source_blob"]}`。24个正文段和2个结构标记分别登记。',
             '同一长段可能包含数年、旧事及评论；所有引用去向明确列出。覆盖不等于24件独立史事，也不是逐句翻译或学术定论。',
             '| 原文行 | 摘要起句 | 去向 |\n|---|---|---|']
    for n in paragraphs:
        links = []
        for d in destinations[n]:
            rel = '../chunqiu/years/' + Path(d['path']).name if '/years/' in d['path'] else 'CONTEXT-066.md'
            label = f'前{d["year_bce"]}年·{d["event"]}' if 'event' in d else d['anchor']
            links.append(f'[{label}]({rel}#{d["anchor"]})')
        cross.append(f'| {n} | {paragraphs[n][:24]}… | ' + ' · '.join(links) + ' |')
        mapping.append({'chapter':66, 'line':n, 'text_sha256':sha(paragraphs[n].encode()),
                        'source_commit':base, 'source_path':spec['source_path'],
                        'source_blob':spec['source_blob'], 'explicitly_shared':len(destinations[n])>1,
                        'destinations':destinations[n]})
    cross.extend(['## 结构标记', '4659行为章号标记；4683行为“評論”标题。标题不生成历史事件。',
                  '## 未取得全文的现代研究',
                  '本次只检得鞭尸／鞭墓相关现代论文书目线索，没有取得完整论文，未以未读论文断言证伪成功或学界多数。古籍对读采用实际读到的《吕氏春秋·首时》原话，见前506年第15条。',
                  '[返回汇入目录](README.md)'])
    rendered['chronicle/shiji-integration/CHAPTER-066.md'] = '\n\n'.join(cross)+'\n'
    rendered['chronicle/shiji-integration/data/paragraph-map-066.jsonl'] = ''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in mapping)

    # Retain old identifiers and provide destinations rather than treating the old
    # standalone trial as already integrated or reassigning its uncertain dates.
    legacy = []
    records_path = ROOT/'chronicle/shiji-trial/data/records.jsonl'
    for s in records_path.read_text(encoding='utf-8').splitlines():
        r = json.loads(s)
        cited = set()
        for e in r.get('evidence', []):
            if e.get('path') == spec['source_path'] and e.get('start_line') and e.get('end_line'):
                cited.update(set(range(e['start_line'],e['end_line']+1)) & set(paragraphs))
        if not cited:
            continue
        dest = {(d['path'],d['anchor']) for n in cited for d in destinations[n]}
        legacy.append({'old_record_id':r['id'], 'old_year_bce':r.get('year_bce'),
                       'original_lines':sorted(cited), 'destinations':[{'path':p,'anchor':a} for p,a in sorted(dest)],
                       'old_identifier_preserved':True, 'old_date_not_automatically_adopted':True})
    rendered['chronicle/shiji-integration/data/legacy-record-map-066.jsonl'] = ''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in legacy)

    by_mode = Counter(op['mode'] for op in spec['operations'])
    total_new = sum(p['new_entries'] for p in page_audit)
    rows = ['| 已有年度页 | 正文改写/扩写 | 新增条目 | 仅补充史料注 |','|---|---:|---:|---:|']
    for p in page_audit:
        y=p['year_bce']
        rows.append(f'| [前{y}年](../chunqiu/years/bce-{y:04d}.md) | {p["rewritten_or_expanded_entries"]} | {p["new_entries"]} | {p["source_only_enrichments"]} |')
    readme = ['# 《史记》汇入现有主年表',
              '阅读正文仍在 `chronicle/chunqiu/years/`，本目录只保存汇入索引、原文去向和检查记录，不另造一套按年的《史记》页面。',
              '## 第一批：卷六十六《伍子胥列传》整篇',
              f'本批更新{len(page_audit)}张已有年度页；改写或扩写{by_mode["replace"]+by_mode["append"]}条已有正文，{by_mode["note"]}条仅补充互见及异文说明，新增{total_new}条。全篇24段正文均有去向，原经传引文及旧事件锚点保留。',
              '\n'.join(rows),
              '新增两条分别是前512年攻舒（按本篇君年暂编）与前506年平王墓前报复（保留鞭坟／鞭尸分歧）。这不是宣称两件事已完成独立史实考证。',
              '[逐段去向](CHAPTER-066.md) · [未确年与作者评论](CONTEXT-066.md) · [真实运行审计](data/audit-066.json) · [原始行号快照](sources/066.md)',
              '## 已处理的几类冲突',
              '伍员出亡与赴吴过程不全部压进前522年；取钟离、荐专诸只对读，不制造第二次荐举。豫章年差、艾陵前后叙次、齐悼公与阳生、托子鲍牧、伯嚭终局、白公归楚年数与救王者名字，分别放在相应史料注中。',
              '## 进度口径与下一批',
              '本轮实际汇入为1篇；旧试编所称9篇初审是另外的进度，不能等同9篇已经并入主年表。《鲁周公世家》此前分组融合也另记范围，不在这里冒算整部《史记》已完。',
              '下一批优先《吴太伯世家》，与本篇涉及的同一吴楚战事、吴王继位、季札活动逐条合并；随后《楚世家》《越王勾践世家》《晋世家》《齐太公世家》，再推进本纪、列传及年表。襄公仍有独立待收尾缺口，不因汇入本篇而消失。',
              '## 复现与防覆盖',
              f'本批以Git提交 `{base}` 中的原年页为输入。运行 `python3 scripts/integrate_shiji_066.py`，或加 `--check` 只验证。若缺底本对象，先 `git fetch origin {base}`。原年页有人继续编辑时脚本会停止，不悄悄覆盖。',
              '旧昭公末段、定公、哀公生成器已加防覆盖提示；不再允许用只认识经传初稿的旧脚本抹掉后加的《史记》内容。旧分组审计保留初稿范围，当前篇章汇入的计数见本批审计。',
              spec['research_limits'], '[返回春秋主目录](../chunqiu/README.md)']
    rendered['chronicle/shiji-integration/README.md'] = '\n\n'.join(readme)+'\n'

    banner = '《史记》现已开始逐篇汇入[现有主年表](../shiji-integration/README.md)。下面的9篇、74年等数字是历史试编进度，不代表已经全部汇入；旧文件和编号保留用于回查。'
    old_trial = 'chronicle/shiji-trial/README.md'
    rendered[old_trial] = marked(original(old_trial), 'shiji066-canonical', banner)
    for y in sorted(ops_by_year, reverse=True):
        path = f'chronicle/shiji-trial/years/bce-{y:04d}.md'
        old = original(path, optional=True)
        if old is not None:
            rendered[path] = '> 本页为历史试编；本轮《伍子胥列传》的主阅读与异说请见[同年主年表](../../chunqiu/years/bce-' + f'{y:04d}' + '.md)。旧条号保留，未把本页未核年说自动移入。\n\n' + old

    index_path = 'chronicle/chunqiu/README.md'
    rendered[index_path] = marked(original(index_path), 'shiji-integration',
        f'## 《史记》开始汇入已有年页\n\n[汇入目录](../shiji-integration/README.md)。首批《伍子胥列传》24段正文更新{len(page_audit)}个已有年份，保留经传全文与旧锚点。新增{total_new}条，原分组统计的历史审计不改写。不是额外建立一套年表。')
    for path in ('chronicle/README.md','chronicle/PROGRESS.md'):
        old = original(path)
        rendered[path] = marked(old, 'shiji066-integration',
            f'## {spec["date"]}：《史记》汇入现有年表，第一批\n\n[实际汇入入口](shiji-integration/README.md)。完成卷66《伍子胥列传》整篇的主年表去向与引用整合，更新{len(page_audit)}个已有年份；旧试编9篇初审不等于9篇均已汇入。原文24段、新增{total_new}条，未确年材料及争议另有明确说明。后续先核《吴太伯世家》与本批去重。')

    # Update live reader counts, while preserving the original first-pass audits.
    for group in ('zhaogong','dinggong'):
        path=f'chronicle/chunqiu/{group}/README.md'
        text=original(path)
        delta = 1
        if group == 'zhaogong':
            text=text.replace('288条白话叙述','289条白话叙述')
        else:
            text=text.replace('125条白话条目','126条白话条目')
        changed_lines=[]
        for line in text.splitlines():
            m=re.search(r'\(\.\./years/bce-(\d{4})\.md\)',line)
            if m and int(m[1]) in new_page_counts and line.startswith('|'):
                parts=line.rsplit('|',2)
                require(len(parts)==3, 'Malformed reader table')
                line=parts[0]+'| '+str(new_page_counts[int(m[1])])+' |'+parts[2]
            changed_lines.append(line)
        text='\n'.join(changed_lines)+'\n'
        rendered[path]=marked(text,'shiji066-reader-counts',
            '## 《史记》汇入后的阅读计数\n\n上述年度条目数已包含本轮新增内容；原初稿审计JSON保留当时的检查范围，不据新计数改写历史审计。[最新汇入记录](../../shiji-integration/README.md)。')

    # Old generators know only the first-pass data. Fail closed rather than
    # silently deleting new source material when somebody runs one of them.
    for filename in ('build_zhaogong_21_32.py','build_dinggong_01_15.py','build_aigong_01_27.py'):
        path='scripts/'+filename
        code=original(path)
        needle="if __name__ == '__main__':\n"
        require(code.count(needle)==1, f'Cannot safely guard {filename}')
        guard=needle + "    # Later Shiji overlays must not be discarded by this historical renderer.\n" + \
            "    if (Path(__file__).resolve().parents[1] / 'chronicle/shiji-integration/data/audit-066.json').exists():\n" + \
            "        raise SystemExit('已有史记汇入层；为防覆盖，请改运行 python3 scripts/integrate_shiji_066.py --check。需重建初稿时请使用汇入前的独立Git工作树。')\n"
        rendered[path]=code.replace(needle,guard,1)
        compile(rendered[path],path,'exec')

    # Verify explicit file targets and cross-year note anchors (not just filenames).
    link_count=0
    for path,text in rendered.items():
        if not path.endswith('.md'):
            continue
        ids=re.findall(r'<a id="([^"]+)"></a>',text)
        require(len(ids)==len(set(ids)), f'Duplicate anchor: {path}')
        for link in re.findall(r'\]\(([^\s\)]+)\)',text):
            if link.startswith(('https:','http:','mailto:')):
                continue
            filename,_,anchor=link.partition('#')
            target=(ROOT/path).parent/unquote(filename) if filename else ROOT/path
            target=target.resolve()
            require(target.is_relative_to(ROOT), f'Link escapes root: {path}:{link}')
            rel=str(target.relative_to(ROOT))
            require(rel in rendered or target == AUDIT or target.is_file() or rel in repository_paths, f'Broken local link {path}:{link}')
            target_data=rendered.get(rel)
            if target_data is None and target.is_file() and target.suffix=='.md':
                target_data=target.read_text(encoding='utf-8')
            if anchor and (anchor.startswith(('event-','note-')) or anchor in context_ids):
                require(target_data is not None and f'<a id="{anchor}"></a>' in target_data,
                        f'Broken cross-page anchor {path}:{link}')
            link_count+=1
    for n,ds in destinations.items():
        for d in ds:
            page=rendered[d['path']]
            marker=f'<a id="{d["anchor"]}"></a>'
            pos=page.index(marker)
            after=page.find('<a id="',pos+len(marker))
            block=page[pos:] if after<0 else page[pos:after]
            require('> '+paragraphs[n] in block, f'Source {n} missing from declared note {d}')

    rendered['chronicle/shiji-integration/data/baselines-066.json'] = dumps({
        'base_commit':base, 'year_pages':[{'path':p['path'],'git_blob':p['base_git_blob']} for p in page_audit]})
    audit={'batch':spec['batch'],'date':spec['date'],'base_commit':base,'chapter':66,
           'status':'first_full_chapter_integration_with_lossless_existing_page_checks',
           'updated_existing_year_pages':len(page_audit),'rewritten_or_expanded_existing_events':by_mode['replace']+by_mode['append'],
           'existing_events_with_note_only_additions':by_mode['note'],'new_events':total_new,
           'substantive_source_paragraphs':len(paragraphs),'mapped_unique_paragraphs':len(destinations),
           'unmapped_paragraphs':0,'metadata_records':len(spec['metadata_lines']),
           'source_references_in_year_notes':reference_count,
           'explicitly_shared_paragraphs':sum(len(ds)>1 for ds in destinations.values()),
           'original_shiji_blob_verified':spec['source_blob'],'original_quote_blocks_preserved':old_quote_count,
           'old_event_anchors_preserved':True,'unrelated_event_bodies_preserved':True,
           'legacy_records_crosswalked':len(legacy),'validated_local_links':link_count,
           'modern_scholarly_collation_complete':False,'all_shiji_chapters_integrated':False,
           'xianggong_gap_closed':False,'spec_sha256':sha(SPEC.read_bytes()),'pages':page_audit,
           'generated_file_sha256':{p:sha(t.encode()) for p,t in rendered.items()},
           'limitations':spec['research_limits']}
    rendered[str(AUDIT.relative_to(ROOT))]=dumps(audit)

    previous=json.loads(AUDIT.read_text(encoding='utf-8')) if AUDIT.exists() else {}
    previous_hashes=previous.get('generated_file_sha256',{})
    changes=[]
    for path,text in rendered.items():
        p=ROOT/path; data=text.encode()
        if p.exists():
            current=p.read_bytes()
            if current==data:
                continue
            is_audit=(p==AUDIT)
            base_data=baseline.get(path)
            acceptable=(current==base_data or sha(current)==previous_hashes.get(path) or is_audit)
            require(acceptable, f'Local edits detected; refusing to overwrite {path}. Reconcile the integration data first.')
        changes.append(path)
    if check:
        require(not changes, 'Generated files differ:\n'+'\n'.join(changes))
    else:
        for path,text in rendered.items():
            p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
    print(dumps({'check_only':check,'changed_files':len(changes),'year_pages':len(page_audit),
                 'expanded_existing_events':by_mode['replace']+by_mode['append'],'note_only':by_mode['note'],
                 'new_events':total_new,'all_24_paragraphs_assigned':True,
                 'original_quote_blocks_preserved':old_quote_count,'local_links_checked':link_count,
                 'legacy_records_crosswalked':len(legacy)}))


if __name__ == '__main__':
    main()
