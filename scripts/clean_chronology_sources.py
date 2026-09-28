#!/usr/bin/env python3
"""Deterministic layout cleaning, not textual emendation or automatic dating.
Python standard library only. Source files are never overwritten.
Maps use Unicode character offsets, 0-based and end-exclusive. Output offsets
refer to the whitespace-free stream, not the inserted display line breaks.
"""
from __future__ import annotations
import argparse
import bisect
import collections
import gzip
import hashlib
import json
import re
from pathlib import Path

SOURCE_REF = '13eac0731e3a1233d04da261c1534f42bfdb87d0'
DEST = 'working-texts/chronology-clean'
LU = ['隐公', '桓公', '庄公', '闵公', '僖公', '文公', '宣公', '成公', '襄公', '昭公', '定公', '哀公']
META = re.compile(r'^#(?:\+| -\*-)[^\r\n]*(?:\r\n|\n|\r|$)', re.M)
PAGE = re.compile(r'<pb:[^>\r\n]+>')
YEAR = re.compile(r'G\*(\d+)\*Y\*(\d+)')
TIME = re.compile(r'([QZ])S\*(\d+)\*[QZ]M\*(\d+)')
YEAR_ONLY = re.compile(r'[元一二三四五六七八九十百有]+年。?')

def check(condition, message):
    if not condition:
        raise ValueError(message)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def write_json(p, obj, compressed=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
    p.write_bytes(gzip.compress(data, mtime=0) if compressed else data)

def runs(offsets):
    """Each run = [output_start, output_end, source_start, source_end]."""
    result = []
    for j, offset in enumerate(offsets):
        if result and result[-1][3] == offset:
            result[-1][1] += 1
            result[-1][3] += 1
        else:
            result.append([j, j + 1, offset, offset + 1])
    return result

def render(chars, offsets, cuts):
    out = []
    thresholds = iter(sorted(set(cuts)))
    next_cut = next(thresholds, None)
    for ch, pos in zip(chars, offsets):
        if next_cut is not None and pos >= next_cut:
            if out and out[-1] != '\n':
                out.append('\n')
            while next_cut is not None and pos >= next_cut:
                next_cut = next(thresholds, None)
        out.append(ch)
    return ''.join(out).strip() + '\n'

def clean_kanripo(text):
    chars, offsets, removed, cuts, metadata = [], [], [], [], []
    counts = collections.Counter()
    char_counts = collections.Counter()
    meta = {m.start(): m for m in META.finditer(text)}
    header_ranges = []
    # Only explicit layout hints; these breaks are NOT sentence/date decisions.
    for m in re.finditer(r'^[ \u3000]*(欽定四庫全書|資治通鑑卷|胡三省|臣光曰)[^\r\n]*', text, re.M):
        cuts.append(m.start())
        if m.group(1) != '臣光曰':
            cuts.append(m.end())
            header_ranges.append((m.start(), m.end()))
    line_start = 0
    for ln, line in enumerate(text.splitlines(keepends=True), 1):
        head = line.lstrip(' \u3000')
        if re.match(r'(?:[元一二三四五六七八九十百]+年|[^\s(#<]{1,6}[元一二三四五六七八九十百]+年)', head):
            cuts.append(line_start)
        # The source labels between author and opening year stay separate.
        if 8 <= ln <= 12 and line.startswith('\u3000') and not head.startswith('('):
            cuts.extend([line_start, line_start + len(line)])
            header_ranges.append((line_start, line_start + len(line)))
        line_start += len(line)
    i = 0
    parens, square = 0, 0
    def drop(kind, start, end):
        removed.append([kind, start, end])
        counts[kind] += 1
        char_counts[kind] += end - start
    while i < len(text):
        if i in meta:
            m = meta[i]
            metadata.append(text[i:m.end()].rstrip('\r\n'))
            drop('metadata', i, m.end()); i = m.end(); continue
        if text.startswith('<pb:', i):
            m = PAGE.match(text, i)
            check(m is not None, f'Unclosed page marker at {i}')
            drop('page_marker', i, m.end()); i = m.end(); continue
        c = text[i]
        if c == '\ufeff' and i == 0:
            drop('initial_bom', i, i + 1); i += 1; continue
        if c == '¶':
            drop('printed_line_marker', i, i + 1); i += 1; continue
        if c.isspace():
            a = i
            while i < len(text) and text[i].isspace():
                i += 1
            chunk = text[a:i]
            # An inline full-width gap often separates items. Printed newlines
            # alone do not: this is what reconnects names split across pages.
            preceding = text[text.rfind('\n', 0, a) + 1:a]
            if '\u3000' in chunk and '\n' not in chunk and parens == 0 and preceding.strip() and not any(x <= a < y for x, y in header_ranges):
                cuts.append(i)
            drop('layout_whitespace', a, i); continue
        if c == '/' and parens > 0 and square == 0:
            drop('small_type_wrap_slash', i, i + 1); i += 1; continue
        if c == '[':
            square += 1
        elif c == ']':
            square -= 1
            check(square >= 0, f'Unmatched square bracket at {i}')
        elif c == '(':
            parens += 1
        elif c == ')':
            parens -= 1
            check(parens >= 0, f'Unmatched closing parenthesis at {i}')
        chars.append(c); offsets.append(i); i += 1
    check(parens == 0 and square == 0, 'Unclosed parenthetical or character-description bracket')
    canonical = ''.join(chars)
    # Every input character must have exactly one disposition.
    ranges = sorted([(a, b) for _, a, b in removed] + [(a, b) for _, _, a, b in runs(offsets)])
    end = 0
    for a, b in ranges:
        check(a == end, 'Cleaning partition has a gap/overlap')
        end = b
    check(end == len(text), 'Cleaning partition does not cover input')
    check(''.join(text[a:b] for _, _, a, b in runs(offsets)) == canonical, 'Annotated source map failed')
    main_chars, main_offsets, notes = [], [], []
    depth = 0
    start = 0
    newlines = [m.start() for m in re.finditer('\n', text)]
    for j, (c, pos) in enumerate(zip(chars, offsets)):
        if c == '(':
            if depth == 0:
                start = j
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                a, b = offsets[start], pos + 1
                notes.append({'id': len(notes) + 1, 'main_anchor': len(main_chars),
                              'source_span': [a, b],
                              'source_lines': [bisect.bisect_left(newlines, a) + 1, bisect.bisect_left(newlines, b - 1) + 1],
                              'text': canonical[start + 1:j]})
        elif depth == 0:
            main_chars.append(c); main_offsets.append(pos)
    # Reinsert every parenthetical at its anchor, recovering annotated text.
    grouped = collections.defaultdict(list)
    for n in notes:
        grouped[n['main_anchor']].append('(' + n['text'] + ')')
    rebuilt = ''.join(''.join(grouped[j]) + (main_chars[j] if j < len(main_chars) else '') for j in range(len(main_chars) + 1))
    check(rebuilt == canonical, 'Main + parentheticals does not reconstruct annotated stream')
    check(''.join(text[a:b] for _, _, a, b in runs(main_offsets)) == ''.join(main_chars), 'Main source map failed')
    return {'with_notes': render(chars, offsets, cuts),
            'main': render(main_chars, main_offsets, cuts),
            'notes': notes, 'metadata': metadata,
            'map': {'coordinate_system': 'Unicode code points; end exclusive; output offsets ignore display whitespace',
                    'with_notes': runs(offsets), 'main': runs(main_offsets), 'removed': removed},
            'stats': {'removed_tokens': dict(counts), 'removed_characters': dict(char_counts),
                      'parentheticals': len(notes), 'with_notes_characters': len(chars),
                      'outside_parentheses_characters': len(main_chars),
                      'remaining_square_descriptions': len(re.findall(r'\[[^\]]+\]', canonical))}}

def clean_ccdh(text, title):
    """Drop structural tokens only; preserve original punctuation/content."""
    rows, blocks, markers = text.lstrip('\ufeff').splitlines(), [], []
    active = None
    kept_lines = []
    for ln, s in enumerate(rows, 1):
        stripped = s.strip()
        y = YEAR.fullmatch(stripped)
        t = TIME.fullmatch(stripped)
        if y:
            g, year = map(int, y.groups())
            check(1 <= g <= 12, 'Unexpected ruler index')
            active = {'ruler_index': g, 'regnal_year': year, 'label': f'鲁{LU[g-1]}第{year}年',
                      'source_start_line': ln, 'lines': [], 'time_markers': []}
            blocks.append(active); markers.append({'line': ln, 'raw': s}); continue
        if t:
            check(active is not None, 'Time marker without a year')
            item = {'line': ln, 'raw': s, 'season_index': int(t[2]), 'month_index': int(t[3])}
            active['time_markers'].append(item); markers.append(item); continue
        check(not re.match(r'^(?:G\*|[QZ]S\*)', stripped), f'Unrecognized structural marker: {s}')
        if stripped:
            check(active is not None, 'Content before first year')
            active['lines'].append({'line': ln, 'text': s}); kept_lines.append(s)
    for b in blocks:
        b['has_prose'] = any(not YEAR_ONLY.fullmatch(x['text'].strip()) for x in b['lines'])
    expected = [s for s in rows if s.strip() and not YEAR.fullmatch(s.strip()) and not TIME.fullmatch(s.strip())]
    check(kept_lines == expected, 'A CCDH content line changed')
    return blocks, markers

def build(root, out, source_ref=SOURCE_REF):
    check(re.fullmatch('[0-9a-f]{40}', source_ref) is not None, 'Use a fixed input commit')
    check(out.resolve() == (root / DEST).resolve(), f'Output must be {DEST}, never original source directories')
    out.mkdir(parents=True, exist_ok=True)
    volumes = [root / f'zizhi-tongjian/kanripo/KR2b0007_{v:03d}.txt' for v in range(295)]
    check(all(p.is_file() for p in volumes), 'Expected preface 000 and volumes 001--294')
    manifests = []
    total = collections.Counter()
    all_removed = collections.Counter()
    for p in volumes:
        raw = p.read_bytes(); text = raw.decode('utf-8'); result = clean_kanripo(text)
        name = p.name; rel = str(p.relative_to(root))
        for folder in ['with-notes', 'main', 'parentheticals', 'source-maps']:
            (out / 'tongjian' / folder).mkdir(parents=True, exist_ok=True)
        (out / 'tongjian/with-notes' / name).write_text(result['with_notes'], encoding='utf-8')
        # 000 contains prefatory inline honorifics: do not advertise note removal
        # from front matter as main text. Keep its complete cleaned rendition.
        if name != 'KR2b0007_000.txt':
            (out / 'tongjian/main' / name).write_text(result['main'], encoding='utf-8')
        payload = {'source_path': rel, 'source_commit': source_ref, 'source_sha256': sha(raw),
                   'note_type': 'parenthetical layer; not all spans are Hu notes', 'notes': result['notes']}
        write_json(out / 'tongjian/parentheticals' / (p.stem + '.json.gz'), payload, True)
        write_json(out / 'tongjian/source-maps' / (p.stem + '.json.gz'), result['map'], True)
        manifests.append({'path': rel, 'source_sha256': sha(raw), 'source_bytes': len(raw),
                          'with_notes_sha256': sha(result['with_notes'].encode()),
                          'metadata': result['metadata'], **result['stats']})
        if name != 'KR2b0007_000.txt':
            total.update({k: v for k, v in result['stats'].items() if isinstance(v, int)})
            all_removed.update(result['stats']['removed_tokens'])
        check(p.read_bytes() == raw, 'Original unexpectedly changed')
    cqstats = {}
    for key, title in [('cq', '春秋经'), ('zz', '左传')]:
        rel = f'classics/ccdh/13_{key}_mod.txt'; p = root / rel; raw = p.read_bytes()
        blocks, markers = clean_ccdh(raw.decode('utf-8'), title)
        prefix = f'https://github.com/zhixin0825/history/blob/{source_ref}/{rel}'
        output = [f'# {title}｜去标记工作本', '只清除语料标签；原有句号保留，未重新断句。年标题是标签的展开，不是新增史料。']
        empty = []
        for b in blocks:
            if not b['has_prose']:
                empty.append(b); continue
            label = b['label']
            if key == 'cq' and b['ruler_index'] == 12 and b['regnal_year'] == 14:
                label += '（含获麟后续经，原样保留）'
            elif key == 'cq' and b['ruler_index'] == 12 and b['regnal_year'] in [15,16]:
                label += '（续经）'
            output += ['## ' + label, f'[原文行 {b["source_start_line"]}]({prefix}#L{b["source_start_line"]})']
            output += [x['text'] for x in b['lines']]
        (out / (key + '.md')).write_text('\n\n'.join(output) + '\n', encoding='utf-8')
        # Token-stripped text retains all non-token lines, including empty-year titles.
        (out / (key + '.txt')).write_text('\n'.join(x['text'] for b in blocks for x in b['lines']) + '\n', encoding='utf-8')
        write_json(out / (key + '-structure.json'), {'source': rel, 'sha256': sha(raw), 'years': blocks, 'markers': markers})
        cqstats[key] = {'year_markers': len(blocks), 'nonempty_years': len(blocks) - len(empty),
                        'empty_year_labels': [b['label'] for b in empty], 'removed_structural_lines': len(markers)}
        check(p.read_bytes() == raw, 'Original unexpectedly changed')
        manifests.append({'path': rel, 'source_sha256': sha(raw), 'source_bytes': len(raw), **cqstats[key]})
    summary = {'source_commit': source_ref, 'scope': '295 Tongjian files including front matter; Chunqiu and Zuozhuan',
               'tongjian_body_volumes': 294, 'tongjian_front_matter_files': 1,
               'tongjian_body_totals': dict(total), 'tongjian_body_removed_tokens': dict(all_removed),
               'ccdh': cqstats, 'checks': ['297 originals byte-preserved', 'full character disposition',
                  'source-map reconstruction', 'main + parentheticals reconstruction', 'CCDH content line equality'],
               'limitations': ['not new punctuation', 'not a new edition', 'not semantic validation of note boundaries',
                               'main retains author commentary and headings', 'unknown characters/placeholders preserved']}
    write_json(out / 'manifest.json', manifests); write_json(out / 'audit.json', summary)
    (out / 'README.md').write_text(f'''# 春秋、左传、资治通鉴｜代码清洁工作本

本目录只清理现有文件的版面与语料标记，**没有更换底本，没有GPT补字或断句，没有修改原始TXT和旧编年引用**。
输入固定提交：`{source_ref}`。`audit.json`和`manifest.json`记录范围、计数和哈希。

## 直接阅读

- [《通鉴》卷七：正文候选](tongjian/main/KR2b0007_007.txt) · [同卷保留夹注的清洁版](tongjian/with-notes/KR2b0007_007.txt)
- [《春秋经》按君年阅读](cq.md) · [《左传》按君年阅读](zz.md)
- 《通鉴》正文候选：`tongjian/main/`，294卷；去版面保留夹注版：`tongjian/with-notes/`，另含卷000前置材料。

《春秋经》末尾11个无正文的年份标签保留在`cq-structure.json`和`cq.txt`，不伪装成阅读版里有记载的年份。
经文获麟后续文没有被删；获麟所在年和后续两年单独提示层次。

## 清理规则

清除通鉴`<pb:...>`、`¶`、已识别的`#+`元数据和版式空白；印刷换行不充当句号。
只清除圆括号内、且不在方括号缺字描述里的小字折行`/`；例如`[雨/單]`原样保留。
拆开相邻括注，合回被夹注或跨页打断的正文，例如`荆`和`軻`重新相连。
《春秋》《左传》的`G*...`、`QS*...`、`ZS*...`从阅读文本中移出，原标签与行号进入结构文件。
**原有句号、古字、异体字、□、空书名号与疑似错字都不擅自删除或改写。**

## 括注不是垃圾

`main/`是“圆括号外层”候选，不是已经校定的纯司马光正文。卷首纪年说明等也可能在括号内。
`parentheticals/*.json.gz`逐条保留全部括注、主流位置和原文范围；包括胡注、考异、版本说明等，未进行语义强制归类。
`with-notes/`始终是完整的去版面工作本。卷000中的“(臣/)”“(中謝/)”等不能简单当脚注丢弃，故卷000不生成所谓纯正文版。
“臣光曰”及其他史家评论仍在正文候选中，后续提取事件时需要区分，不能当作当年人物发言。

## 溯源与检查

`source-maps/*.json.gz`含保留片段和移出的版面片段位置，坐标按Python字符串Unicode字符计，从0开始、右端不含。
输出坐标针对不含显示换行的字符流；正文和保留括注版都能按这些范围逐字回查原文件。
每卷检查所有输入字符都有去向，括注按位置插回后可复原保留括注版；这不是声称史书本身没有错漏。
新增显示换行只依据原版式提示，不代表已经完成现代标点或确定新的事件边界。

## 重建

在仓库根目录运行：

```sh
python scripts/clean_chronology_sources.py
python -m unittest discover -s tests -p 'test_clean_chronology_sources.py' -v
```

仅Python标准库；不调用模型或外部网站，不产生API费用。新输入需要重核版本、标记规则及语义问题。
这些新文件没有直接替换`chronicle/`中既有年份页的历史依据，原来的固定版本链接继续有效。
原始语料来源与许可仍见仓库`README.md`和`provenance/`，清理版保留来源，不另主张额外权利。
''', encoding='utf-8')
    return summary

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--source-ref', default=SOURCE_REF)
    args = p.parse_args()
    root = args.root.resolve()
    print(json.dumps(build(root, root / DEST, args.source_ref), ensure_ascii=False, indent=2))
