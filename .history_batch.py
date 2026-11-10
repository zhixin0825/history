#!/usr/bin/env python3
"""Conservative, source-verified note repair for BCE 700–601; never edits main."""
import hashlib, json, re, subprocess
from pathlib import Path
from urllib.parse import unquote
ROOT=Path('.')
YEARS=ROOT/'years/bce-0700-0601'
SOURCES=ROOT/'sources/春秋左传/有标点原文'
RUN='20261109'
TAG='century-0700-0601-primary'
PLACEHOLDER='本条的直接引文待核。'
NOTE=re.compile(r'<a id="((?:reading-)?note-(\d+))"></a>([\s\S]*?)(?=<a id="(?:reading-)?note-\d+"></a>|\Z)')
ANCHOR=re.compile(r'<a\s+id="([^"]+)"[^>]*></a>')
def norm(s):
    return ''.join(c for c in re.sub(r'<[^>]*>', '', s) if c.isalnum())
def anchors(s): return ANCHOR.findall(s)
def read(p): return p.read_text(encoding='utf-8')
def write(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8')
def split_page(s):
    a=s.index('<a id="sources-start"></a>'); b=s.index('<a id="appendix-start"></a>',a)
    return s[:a],s[a:b],s[b:]
def get_legacy(t,id):
    m=re.search(r'<a id="'+re.escape(id)+r'"></a>',t)
    if not m: return ''
    tail=t[m.end():]
    tail=re.sub(r'\A(?:\s*<a id="[^"]+"></a>)+','',tail)
    nxt=re.search(r'\n<a id="',tail)
    return tail[:nxt.start()] if nxt else tail.split('\n---')[0]
def prepare_source(y,t,data):
    out=[]; layer=None; seq={}; pars=[]
    for block in re.split(r'(\n\s*\n)',t):
        heading=re.fullmatch(r'##\s*(经|傳|传|续经|續經)\s*',block.strip())
        if heading:
            layer={'经':'j','传':'t','傳':'t','续经':'x','續經':'x'}[heading.group(1)]
        elif block.strip().startswith('## '): layer=None
        if layer and block.strip() and not block.lstrip().startswith(('#','<a ','[','<!--')):
            seq[layer]=seq.get(layer,0)+1
            aid=f'batch-{RUN}-{layer}{seq[layer]:03d}'
            out.append(f'<a id="{aid}"></a>\n\n')
            pars.append({'id':aid,'layer':layer,'text':block.strip(),'norm':norm(block)})
        out.append(block)
    updated=''.join(out)
    if data:
        updated=re.sub(r'^\[来源原文\]\(https?://[^\n]+\) · \[来源目录\]\(https?://[^\n]+\) · \[本地目录\]\(\.\./README\.md\)$',
            f'[本地目录](../README.md) · [同年采集与校验记录](../data/{data})',updated,flags=re.M)
    updated=re.sub(r'(<a id="(batch-'+RUN+r'-[jtx]\d+)"></a>\s*)\1',r'\1',updated)
    return updated,pars

def snippets(legacy):
    for m in re.finditer(r'[“「]([\s\S]*?)[”」]',legacy):
        for piece in re.split(r'…+|\.{3,}',m.group(1)):
            q=norm(piece)
            if len(q)>=5: yield q

def select_paragraphs(note,legacy,pars):
    picked=[]
    probes=list(dict.fromkeys(snippets(legacy)))
    short=[norm(m.group(1)) for m in re.finditer(r'[“「]([^”」]{1,12})[”」]',legacy)]
    for p in pars:
        if any(q in p['norm'] for q in probes) or p['norm'] in short:
            picked.append(p)
    return picked

def heading_slug(s):
    s=re.sub(r'<[^>]+>','',s)
    s=re.sub(r'\[([^]]+)\]\([^)]*\)',r'\1',s)
    s=s.lower().strip()
    return ''.join(c for c in s if c.isalnum() or c in '_- ' or ord(c)>127 and not __import__('unicodedata').category(c).startswith('P')).replace(' ','-')
def known_ids(text):
    ids=set(anchors(text)); seen={}
    for m in re.finditer(r'^#{1,6}\s+(.+?)\s*#*$',text,re.M):
        h=heading_slug(m.group(1)); n=seen.get(h,0); seen[h]=n+1; ids.add(h if not n else h+'-'+str(n))
    return ids

data_map={}
for p in (ROOT/'sources/春秋左传/data').glob('*.json'):
    try:
        d=json.loads(read(p)); data_map[int(d['year_bce'])]=p.name
    except (ValueError,KeyError,TypeError): pass
expected=[YEARS/f'bce-{y:04d}.md' for y in range(700,600,-1)]
assert all(p.is_file() for p in expected),'Missing year page'
source_info={}; source_before={}; report=[]; pending=[]; coverage=[]; failures=[]
for y in range(700,600,-1):
    p=SOURCES/f'bce-{y:04d}.md'
    if not p.is_file(): raise RuntimeError(f'Missing primary text {p}')
    raw=read(p); raw=re.sub(r'<a id="batch-'+RUN+r'-[jtx]\d+"></a>\n\n','',raw)
    changed,pars=prepare_source(y,raw,data_map.get(y)); source_before[y]=raw
    old=set(anchors(raw)); assert old<=set(anchors(changed)),f'Lost source anchors {y}'
    assert len(anchors(changed))==len(set(anchors(changed))),f'Duplicate source anchor {y}'
    write(p,changed); source_info[y]=pars

for p in expected:
    y=int(p.stem[4:]); original=read(p)
    body,notes,appendix=split_page(original)
    notes=re.sub(r'\n?<!-- '+TAG+r' -->[\s\S]*?<!-- /'+TAG+r' -->\n?', '', notes)
    pars=source_info[y]; inserted=0; removed=0; events=0
    def repair(m):
        global inserted,removed,events
        id,num,seg=m.groups(); events+=1
        legacy_ids=re.findall(r'\]\(#(history-legacy-source-\d+)\)',seg)
        legacy='\n'.join(get_legacy(appendix,i) for i in legacy_ids)
        picked=select_paragraphs(seg,legacy,pars)
        title=re.search(r'^###\s+\d+[.．]\s*(.+)$',seg,re.M)
        title=title.group(1) if title else id
        count=seg.count(PLACEHOLDER)
        if picked:
            blocks=[]
            for q in picked:
                label='《春秋》本年经文' if q['layer']=='j' else '《左传》本年传文'
                target=f'../../sources/春秋左传/有标点原文/bce-{y:04d}.md#{q["id"]}'
                blocks.append(f'**[{label}]({target})**\n\n> '+q['text'].replace('\n','\n> '))
                coverage.append({'year':y,'note':int(num),'source':str(SOURCES/f'bce-{y:04d}.md'),'anchor':q['id'],'sha256':hashlib.sha256(q['text'].encode()).hexdigest()})
            added='<!-- '+TAG+' -->\n\n'+'\n\n'.join(blocks)+'\n\n<!-- /'+TAG+' -->\n\n'
            pos=re.search(r'\[返回正文第\d+条\]\(#[^)]+\)\s*\n',seg)
            if not pos: raise RuntimeError(f'No return link {y}/{id}')
            seg=seg[:pos.end()]+'\n'+added+seg[pos.end():]
            seg=seg.replace(PLACEHOLDER,''); inserted+=len(picked); removed+=count
        else:
            bi=re.search(r'(?m)^'+num+r'\. \*\*[^\n]+',body)
            story=bi.group(0) if bi else title
            grams={norm(story)[i:i+2] for i in range(max(0,len(norm(story))-1))}
            candidates=sorted(pars,key=lambda q:sum(g in q['norm'] for g in grams),reverse=True)[:3]
            rec={'year':y,'note':int(num),'id':id,'title':title,'placeholder':bool(count),'existing_quote':bool(re.search(r'^> ',seg,re.M)),'story':story,'legacy':legacy[:900], 'candidates':[{'id':q['id'],'text':q['text']} for q in candidates]}
            pending.append(rec)
        return '<a id="'+id+'"></a>'+seg
    notes=NOTE.sub(repair,notes)
    updated=body+notes+appendix
    assert set(anchors(original))<=set(anchors(updated)),f'Lost page anchors {y}'
    assert len(anchors(updated))==len(set(anchors(updated))),f'Duplicate page anchors {y}'
    assert split_page(updated)[0]==body,f'Body changed {y}'
    assert split_page(updated)[2]==appendix,f'Appendix changed {y}'
    assert not re.search(r'https?://',body+notes),f'External URL in reading surface {y}'
    write(p,updated)
    report.append({'year':y,'notes':events,'primary_paragraphs_added':inserted,'placeholders_removed':removed,'placeholders_remaining':updated.count(PLACEHOLDER)})

summary={'pages':len(report),'note_groups':sum(x['notes'] for x in report),'primary_paragraph_placements':len(coverage),'placeholders_removed':sum(x['placeholders_removed'] for x in report),'placeholders_remaining':sum(x['placeholders_remaining'] for x in report),'notes_without_new_primary':len(pending),'source_pages':len(source_info),'baseline':'cf8302804e604ea939f5a95ae1aca4b41401643b','status':'draft-needs-review'}
path=ROOT/'meta/记录/2026-11-09-前700至601年-直引工作核验.json'
write(path,json.dumps({'summary':summary,'years':report,'pending':pending,'coverage':coverage},ensure_ascii=False,indent=2)+'\n')
brief=['# 前700—601年｜本轮直引审校工作清单（未验收）','',json.dumps(summary,ensure_ascii=False),'']
for r in pending:
    brief+=['## '+str(r['year'])+' / '+str(r['note'])+('｜缺直引' if r['placeholder'] else '｜有旧引，待检查'),r['title'],'',r['story'],'',r['legacy'],'']
    for q in r['candidates']: brief +=['### 候选 '+q['id'],q['text'],'']
write(ROOT/'meta/记录/2026-11-09-前700至601年-人工审校清单.md','\n'.join(brief)+'\n')
print('BATCH_SUMMARY '+json.dumps(summary,ensure_ascii=False))
print('GAP_KEYS '+json.dumps([str(r['year'])+'/'+str(r['note']) for r in pending if r['placeholder']]))
