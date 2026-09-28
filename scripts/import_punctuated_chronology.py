#!/usr/bin/env python3
"""Fetch punctuated public texts, preserving revisions and all original wikitext.
No model, no inferred punctuation, no silent corrections. Standard library only.
Unknown markup is retained and flagged; a structural pass is not scholarly approval.
"""
from __future__ import annotations
import argparse, collections, datetime, gzip, hashlib, html, json, re, time
from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

API = 'https://zh.wikisource.org/w/api.php'
OUT = Path('working-texts/chronology-punctuated')
DUKES = ['隱公','桓公','莊公','閔公','僖公','文公','宣公','成公','襄公','昭公','定公','哀公']
PUNCT = '。，、；：？！「」『』'
# These templates contain page navigation/licensing, not the work's body.
PAGE_TEMPLATES = {'header','pd-old','pd-old-100','pd-old-auto','license','licenses','defaultsort','author','noexport'}

def dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def gz_dump(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    data=(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n').encode()
    path.write_bytes(gzip.compress(data,mtime=0))

def get_json(params):
    q={'format':'json','formatversion':2,'maxlag':5,**params}
    req=Request(API+'?'+urlencode(q),headers={'User-Agent':'HistoryChronicle/1.0 (https://github.com/zhixin0825/history; public scholarly-text export)'})
    # Access denials, rate limits, and API errors stop this run. No bypass/retry.
    with urlopen(req,timeout=45) as r:
        data=json.load(r)
    if 'error' in data: raise RuntimeError(str(data['error']))
    return data

def spans(raw):
    """Top-level template partition; concatenation reconstructs raw exactly."""
    out=[]; cursor=0; i=0
    while i<len(raw):
        if raw.startswith('{{',i):
            a=i; depth=1; i+=2
            while i<len(raw) and depth:
                if raw.startswith('{{',i): depth+=1; i+=2
                elif raw.startswith('}}',i): depth-=1; i+=2
                else: i+=1
            if depth: raise ValueError('unbalanced template')
            if a>cursor: out.append({'kind':'text','a':cursor,'b':a,'raw':raw[cursor:a]})
            token=raw[a:i]; name=token[2:-2].split('|',1)[0].strip()
            if name=='*': kind='annotation'
            elif name.lower() in PAGE_TEMPLATES or name.lower().startswith('defaultsort:'): kind='page_metadata'
            else: kind='unknown_template'
            out.append({'kind':kind,'name':name,'a':a,'b':i,'raw':token}); cursor=i
        else: i+=1
    if cursor<len(raw): out.append({'kind':'text','a':cursor,'b':len(raw),'raw':raw[cursor:]})
    assert ''.join(x['raw'] for x in out)==raw
    return out

def display_markup(s):
    # Only explicit markup syntax is removed. Unknown tags/templates survive.
    s=re.sub(r'<!--.*?-->','',s,flags=re.S)
    s=re.sub(r'</?(?:onlyinclude|includeonly|noinclude)>','',s,flags=re.I)
    s=re.sub(r'<br\s*/?>','\n',s,flags=re.I)
    s=re.sub(r'\[\[(?:Category|分類|分类):[^\]]*\]\]','',s,flags=re.I)
    s=re.sub(r'\[\[([^\[\]]+)\]\]',lambda m:m[1].split('|')[-1],s)
    s=re.sub(r'^(={2,6})\s*(.*?)\s*\1\s*$',lambda m:'#'*min(len(m[1])+1,6)+' '+m[2],s,flags=re.M)
    s=s.replace("'''''",'').replace("'''",'').replace("''",'')
    s=html.unescape(s)
    return re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+','\n\n',s).strip()+'\n'

def make_one(stem,page):
    if 'missing' in page or not page.get('revisions'): return {'stem':stem,'title':page.get('title'),'status':'missing'}
    rev=page['revisions'][0]; slot=rev['slots']['main']; raw=slot.get('content',slot.get('*',''))
    rid=rev['revid']; title=page['title']; url=f'https://zh.wikisource.org/w/index.php?oldid={rid}'
    meta={'stem':stem,'title':title,'pageid':page['pageid'],'revision_id':rid,'revision_timestamp':rev.get('timestamp'),'source_url':url,'history_url':'https://zh.wikisource.org/w/index.php?title='+quote(title)+'&action=history','raw_sha256':hashlib.sha256(raw.encode()).hexdigest()}
    dump(OUT/'raw'/f'{stem}.json',{'metadata':meta,'wikitext':raw})
    try: parts=spans(raw)
    except ValueError as e:
        return {**meta,'status':'parse_failed','reason':str(e)}
    unknown=[p['name'] for p in parts if p['kind']=='unknown_template']
    source_body=''.join(p['raw'] for p in parts if p['kind'] in ('text','unknown_template'))
    main=display_markup(source_body)
    notes=[p for p in parts if p['kind']=='annotation']
    punctuation=collections.Counter(c for c in main if c in PUNCT)
    cjk=len(re.findall(r'[\u3400-\u9fff\U00020000-\U000323af]',main))
    residue=bool(re.search(r'\{\{|</?[a-zA-Z][^>]*>|\[\[',main))
    long_runs=[m for m in re.finditer(r'[^。，、；：？！「」『』\n]{251,}',main) if len(re.findall(r'[\u3400-\u9fff]',m[0]))>200]
    checks={'raw_template_partition_reconstructs':True,'main_has_full_stops':punctuation['。']>0,'main_has_commas':punctuation['，']>0,'punctuation_count':sum(punctuation.values()),'cjk_characters':cjk,'punctuation_counts':dict(punctuation),'annotation_templates':len(notes),'unknown_templates':dict(collections.Counter(unknown)),'markup_remaining':residue,'long_unpunctuated_runs':len(long_runs)}
    passed=cjk>500 and punctuation['。']>10 and punctuation['，']>5 and not residue and not long_runs
    state='punctuated_structural_pass_not_scholarly_review' if passed else 'needs_structural_review'
    gz_dump(OUT/'layers'/f'{stem}.json.gz',{'metadata':meta,'spans':parts,'checks':checks,'offset_unit':'Unicode code points, zero-based end-exclusive, relative to raw wikitext'})
    heading=f'# {title}\n\n[原页面固定版本]({url}) · [修订历史与贡献者]({meta["history_url"]}) · [本卷注释](../notes/{stem}.md)\n\n> 标点沿用来源，不由GPT新添；正文仍含史家评论与回叙。结构检查不等于句读和年代已校定。\n\n'
    (OUT/'main').mkdir(parents=True,exist_ok=True)
    (OUT/'main'/f'{stem}.md').write_text(heading+main,encoding='utf-8')
    (OUT/'notes').mkdir(parents=True,exist_ok=True)
    ns=[f'# {title}｜来源标注层',f'[返回正文](../main/{stem}.md) · [原页面]({url})','含年条补注、音注、考异和校语；不将这些内容全部归给同一作者。原模板逐字保存在raw与layers中。']
    for i,n in enumerate(notes,1):
        ns.extend([f'<a id="note-{i}"></a>\n\n## {i} · 原页面字符位置 {n["a"]}—{n["b"]}',n['raw'][4:-2]])
    (OUT/'notes'/f'{stem}.md').write_text('\n\n'.join(ns)+'\n',encoding='utf-8')
    return {**meta,'status':state,'checks':checks,'main_sha256':hashlib.sha256(main.encode()).hexdigest()}

def run(cache=None):
    OUT.mkdir(parents=True,exist_ok=True)
    wanted=[(f'tj-{i:03d}',f'資治通鑒 (胡三省音注)/卷{i:03d}') for i in range(1,295)]
    wanted += [(f'zz-{i:02d}',f'春秋左氏傳/{d}') for i,d in enumerate(DUKES,1)]
    results=[]; errors=[]
    for start in range(0,len(wanted),20):
        batch=wanted[start:start+20]
        cache_path=OUT/'responses'/f'{start//20+1:02d}.json'
        if cache and cache_path.exists(): data=json.loads(cache_path.read_text())
        else:
            try:
                data=get_json({'action':'query','prop':'revisions','rvprop':'ids|timestamp|content','rvslots':'main','titles':'|'.join(t for _,t in batch)})
                dump(cache_path,data)
            except Exception as e:
                errors.append({'batch_start':start,'error':str(e)}); break
            time.sleep(1)
        pages={p['title']:p for p in data['query']['pages']}
        norm={x['from']:x['to'] for x in data['query'].get('normalized',[])}
        for stem,title in batch:
            results.append(make_one(stem,pages.get(norm.get(title,title),{'title':title,'missing':True})))
        print('Processed',len(results),'of',len(wanted),flush=True)
    summary={'requested':len(wanted),'received':sum(r['status']!='missing' for r in results),'tongjian_requested':294,'zuozhuan_requested':12,'status_counts':dict(collections.Counter(r['status'] for r in results)),'errors':errors,'fetch_time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'limits':['Not a scholarly critical edition.','No translation, LLM punctuation, or silent character correction.','Markup checks cannot establish completeness or correctness of sentence interpretation.','Jing/Zhuan headings preserved; post-lin continuation not reclassified here.','Old raw sources and chronology citations are not replaced.']}
    dump(OUT/'manifest.json',results);dump(OUT/'audit.json',summary)
    front=['# 有标点的编年候选底本','**无标点清洁版只作中间文件与校核对照，不是正式编年输入。** 本目录下载已有标点本，保留原有句读和段落；不是给旧TXT机械加逗号。',f'实际取得 {summary["received"]}/{len(wanted)} 个页面。状态统计：`{json.dumps(summary["status_counts"],ensure_ascii=False)}`。','[标点要求](PUNCTUATION_RULES.md) · [来源与修订号](manifest.json) · [结构检查](audit.json)','《通鉴》采用维基文库单列的《資治通鑒 (胡三省音注)》；《春秋》采用《春秋左氏傳》中的经文并保留传文。它们是开放转录候选，不能冒称中华书局正式授权电子版。','标点与段落沿用上游；注释、年条补注和页头元数据分层保存。所有原始wikitext、修订号、哈希和贡献者历史链接保留。遇到不认识的模板不删内容，标为待检查。','文本来源：中文维基文库，适用其来源页面及[版权说明](https://zh.wikisource.org/wiki/Wikisource:版权信息)所示许可（通常CC BY-SA；古籍原文本身可能属于公有领域）。改动为下载、格式转换、显式模板分层；本文不对整理者的现代标点另主张权利。再分发请保留署名、来源链接、许可及修改说明。','## 《资治通鉴》','| 卷 | 结构状态 |\n|---|---|']
    for r in results:
        if not r['stem'].startswith('tj-'):continue
        label='有标点；初筛通过' if r['status'].startswith('punctuated_') else '待检查：'+r['status']
        dest=f'main/{r["stem"]}.md'
        front.append(f'| [{r["title"].split("/")[-1]}]({dest}) | {label} |' if (OUT/dest).exists() else f'| {r["title"]} | 未生成 |')
    front+=['','## 《春秋左氏传》：经、传依原标题保留','| 部分 | 结构状态 |\n|---|---|']
    for r in results:
        if not r['stem'].startswith('zz-'):continue
        label='有标点；初筛通过' if r['status'].startswith('punctuated_') else '待检查：'+r['status']
        front.append(f'| [{r["title"].split("/")[-1]}](main/{r["stem"]}.md) | {label} |')
    (OUT/'README.md').write_text('\n\n'.join(front[:7])+'\n\n'+'\n'.join(front[7:])+'\n',encoding='utf-8')
    rules='''# 标点是编年输入的必要条件

用户明确要求：无标点文本不能作为可用成品。

1. 首选已有标点、引号和段落的可靠整理文本。代码只处理明确版面杂项，不把标点删掉。
2. 无标点TXT仅作原始记录、校核对照或断句前的中间材料，不以“清洁版完成”代替“可读底本完成”。
3. 不使用固定字数、印刷换行、每见年/月便断句等机械办法伪造标点。
4. 不得把不同版本的标点跨越人名、异文或缺句强行贴回。需先对齐正文，实质差异单列。
5. 只有确实缺少可用标点本时，才另作明确标注的GPT标点稿，并经过独立核对；它不是权威点校本。
6. 结构检查只发现无标点、模板残留、长无标点段等明显问题；不能证明句读、引语边界和历史年代全部正确。
7. 尚未完成语义检查的来源必须标为候选，不改变已经固定的旧史料引用。
'''
    (OUT/'PUNCTUATION_RULES.md').write_text(rules,encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if errors: raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cached',action='store_true');args=p.parse_args();run(args.cached)
