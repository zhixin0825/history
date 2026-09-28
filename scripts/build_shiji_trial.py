#!/usr/bin/env python3
"""Build the deliberately partial Shiji chronology trial. Python 3.10+, standard library.
This script does not call a model. reviewed.psv contains GPT's separately reviewed text.
"""
from __future__ import annotations
import argparse, bisect, collections, hashlib, json, re
from pathlib import Path
SNAPSHOT='1bf386bcb1873c5389fa640ac3bb11ec1ab3ba54'
SHIJI_BLOB='e3fdd88dc0dad8e918fb99979f759cf4a17ff144'
PREFIX=f'https://github.com/zhixin0825/history/blob/{SNAPSHOT}/'
SJ='texts/01_shiji_full.txt'
CQ='classics/ccdh/13_cq_mod.txt'
REVIEWED=[29,48,62,63,86]
TITLES={1:'五帝本纪',2:'夏本纪',3:'殷本纪',4:'周本纪',5:'秦本纪',6:'秦始皇本纪',7:'项羽本纪',8:'高祖本纪',9:'吕太后本纪',10:'孝文本纪',11:'孝景本纪',12:'孝武本纪',13:'三代世表',14:'十二诸侯年表',15:'六国年表',16:'秦楚之际月表',22:'汉兴以来将相名臣年表',26:'历书',29:'河渠书',31:'吴太伯世家',32:'齐太公世家',33:'鲁周公世家',42:'郑世家',45:'韩世家',48:'陈涉世家',62:'管晏列传',63:'老子韩非列传',86:'刺客列传',129:'货殖列传',130:'太史公自序'}
LU=[(1,'隐公',722),(2,'桓公',711),(3,'庄公',693),(4,'闵公',661),(5,'僖公',659),(6,'文公',626),(7,'宣公',608),(8,'成公',590),(9,'襄公',572),(10,'昭公',541),(11,'定公',509),(12,'哀公',494)]
META={'太史公曰','索隐述赞','評論','晏婴','莊子','申不害','韓非','專諸','豫讓','聶政','荊軻'}

def span(s):
    v=list(map(int,s.split('-')))
    if not 1<=len(v)<=2 or v[0]<1 or v[0]>v[-1]: raise ValueError(s)
    return v[0],v[-1]

def run(root):
    out=root/'chronicle/shiji-trial'
    for d in ('years','appendix','data'): (out/d).mkdir(parents=True,exist_ok=True)
    def write(p,s): (out/p).write_text(s.rstrip()+'\n',encoding='utf-8')
    def jw(p,x): write(p,json.dumps(x,ensure_ascii=False,indent=2))
    def jl(p,x): write(p,'\n'.join(json.dumps(v,ensure_ascii=False) for v in x))
    raw=(root/SJ).read_bytes()
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    assert blob==SHIJI_BLOB,'Source changed: revalidate offsets before rebuilding.'
    lines=raw.decode('utf-8-sig').splitlines()
    starts=[(int(m[1]),i) for i,s in enumerate(lines,1) if (m:=re.fullmatch(r'\*01-(\d{3})\*',s.strip()))]
    assert [a for a,b in starts]==list(range(1,131))
    boundaries=[b for a,b in starts]
    def chapter(n): return bisect.bisect_right(boundaries,n)
    sources={SJ:lines,CQ:(root/CQ).read_text(encoding='utf-8-sig').splitlines()}
    cl=sources[CQ]
    heads=[(int(m[1]),int(m[2]),i) for i,s in enumerate(cl,1) if (m:=re.fullmatch(r'G\*(\d+)\*Y\*(\d+)',s.lstrip('\ufeff')))]
    cqmap={}; cqrows=[]
    for k,(g,y,a) in enumerate(heads):
        b=heads[k+1][2]-1 if k+1<len(heads) else len(cl)
        _,name,first=LU[g-1]
        content=[s for s in cl[a:b] if s.strip() and not s.startswith('QS*') and not re.fullmatch(r'[元一二三四五六七八九十百有]+年。?',s.strip())]
        layer='经及同年续经混合' if g==12 and y==14 else ('续经' if g==12 and 15<=y<=16 else ('空年标记' if not content else '经'))
        row={'g':g,'regnal_year':y,'label':f'鲁{name}{y}年','bce_year_label':first-y+1,'start_line':a,'end_line':b,'layer':layer,'has_prose':bool(content),'text':'\n'.join(cl[a-1:b])}
        cqmap[f'{g}.{y}']=row; cqrows.append(row)
    assert len(cqrows)==255 and sum(r['has_prose'] for r in cqrows)==244
    def evidence(key):
        book,loc=key.split(':',1)
        if book=='sj': path=SJ; a,b=span(loc)
        elif book=='cq':
            r=cqmap[loc]; path=CQ; a,b=r['start_line'],r['end_line']
        elif re.fullmatch(r'tj\d{3}',book): path=f'zizhi-tongjian/kanripo/KR2b0007_{book[2:]}.txt'; a,b=span(loc)
        else: raise ValueError(key)
        if path not in sources: sources[path]=(root/path).read_text(encoding='utf-8-sig').splitlines()
        src=sources[path]
        assert 1<=a<=b<=len(src),f'Invalid evidence range: {key}'
        title=f'《史记》卷{chapter(a)} {TITLES.get(chapter(a),"")}' if path==SJ else ('《春秋》 '+cqmap[loc]['label'] if book=='cq' else f'《资治通鉴》卷{int(book[2:])}')
        return {'key':key,'path':path,'start_line':a,'end_line':b,'title':title,'quote':'\n'.join(src[a-1:b]),'url':PREFIX+path+f'#L{a}-L{b}'}
    records=[]; counts=collections.Counter(); coverage=collections.defaultdict(list)
    for rownum,s in enumerate((out/'reviewed.psv').read_text(encoding='utf-8').splitlines(),1):
        if not s.strip() or s.startswith('#'): continue
        f=s.split('|')
        if len(f)!=8: raise ValueError(f'PSV row {rownum} must contain eight fields')
        loc,year,time,kind,title,plain,extra,note=f
        keys=['sj:'+p for p in loc.split(';')]+([p for p in extra.split(';') if p] if extra else [])
        ev=[evidence(p) for p in dict.fromkeys(keys)]
        a=span(loc.split(';')[0])[0]; ch=chapter(a); counts[a]+=1
        rid=f'sj-{ch:03d}-L{a:04d}-{counts[a]:02d}'
        y=None if year=='?' else int(year)
        rec={'id':rid,'source_line_specs':loc,'chapter':ch,'year_bce':y,'time_raw_or_editor_label':time,'type':kind,'title':title,'plain':plain,'editor_note':note,'evidence':ev,'processing':'GPT逐段初审；非独立复核','date_method':'未确年/相对时间保留' if y is None else '依据所列年条或关联事件初步同步','source_psv_line':rownum}
        if y is not None and len(ev)==len(loc.split(';')) and '二世二年' not in time: rec['date_method']='上下文暂编，尚需逐事复核'
        records.append(rec)
        for p in loc.split(';'):
            a,b=span(p)
            for n in range(a,b+1): coverage[n].append(rid)
    assert len({r['id'] for r in records})==len(records)
    chapters=[]; ledger=[]; reviewed_lines=0
    for idx,(ch,a) in enumerate(starts):
        b=starts[idx+1][1]-1 if idx+1<len(starts) else len(lines)
        missing=[]; prose=0
        for n in range(a+1,b+1):
            text=lines[n-1]; meta=text.strip() in META
            state='已分流初审' if n in coverage else ('小标题' if meta and ch in REVIEWED else '待逐段处理')
            if ch in REVIEWED and not meta:
                prose+=1
                if n not in coverage: missing.append(n)
            ledger.append({'id':f'sj-L{n:04d}','chapter':ch,'line':n,'chars':len(text),'sha256':hashlib.sha256(text.encode()).hexdigest(),'status':state,'record_ids':coverage.get(n,[]),'date_cue':bool(re.search(r'[元一二三四五六七八九十百]+年|其後|明年|初，|歲',text)),'empty_title':'《》' in text,'text':text})
        if ch in REVIEWED:
            assert not missing,f'Unrouted reviewed lines: {missing}'
            reviewed_lines+=prose
        genre='本纪' if ch<=12 else '表' if ch<=22 else '书' if ch<=30 else '世家' if ch<=60 else '列传' if ch<=129 else '自序'
        status='逐段分流初审完成；非逐字翻译完毕' if ch in REVIEWED else ('含局部抽查；其余待处理' if any(n in coverage for n in range(a+1,b+1)) else '仅结构入库；未逐段解读')
        chapters.append({'chapter':ch,'title':TITLES.get(ch,f'卷{ch}（篇名尚待补齐）'),'genre':genre,'start_line':a,'end_line':b,'body_lines':b-a,'chars':sum(len(t) for t in lines[a:b]),'status':status})
    tab=[]
    for ch,a,b,y in [(14,840,1204,841),(15,1213,1482,476)]:
        for offset,n in enumerate(range(a,b+1)):
            extra='\n'+lines[1204] if ch==14 and n==1204 else ''
            tab.append({'id':f'table-{ch}-L{n}','chapter':ch,'year_bce_source_row':y-offset,'start_line':n,'end_line':1205 if extra else n,'status':'表行候选；各国空格列及段内回叙未校','text':lines[n-1]+extra,'basis':'由首行与连续年行定位，不代表行内每个事件同年；年表自身纪年未同现代考证统一'})
    assert len(tab)==635 and tab[364]['year_bce_source_row']==477 and tab[-1]['year_bce_source_row']==207
    assert '穿地相見' in lines[959] and '阿房宮' in lines[1469] and '三十五年' in lines[389]
    jl('data/source-ledger.jsonl',ledger); jw('data/chapter-inventory.json',chapters)
    jw('data/chunqiu-spine.json',cqrows); jl('data/shiji-table-year-candidates.jsonl',tab); jl('data/records.jsonl',records)
    cards={e['key']:e for r in records for e in r['evidence']}
    def ek(key): return 'ref-'+re.sub(r'[^a-zA-Z0-9-]','-',key)
    text=['# 逐条原文与固定版本','原文由固定输入文件按行提取；《通鉴》的音注、页码标记也保留，不混称都是正文。']
    for k,e in cards.items():
        text += [f'<a id="{ek(k)}"></a>',f'## {e["title"]} · 第{e["start_line"]}—{e["end_line"]}行',f'[完整原文件与上下文]({e["url"]})','```text',e['quote'],'```']
    write('appendix/sources.md','\n\n'.join(text))
    def body(r,prefix,number=None):
        refs=' · '.join(f'[{e["title"]} L{e["start_line"]}]({prefix}#{ek(e["key"])})' for e in r['evidence'])
        num=str(number)+'. ' if number else ''
        return f'<a id="{r["id"]}"></a>\n\n### {num}{r["title"]}\n\n**时间：{r["time_raw_or_editor_label"]}** · {r["type"]}\n\n{r["plain"]}\n\n{refs}\n\n<details><summary>归年依据与待核问题</summary>\n\n{r["editor_note"]}\n\n</details>'
    years=sorted({r['year_bce'] for r in records if r['year_bce'] is not None},reverse=True)
    for i,y in enumerate(years):
        rows=[r for r in records if r['year_bce']==y]; nav=['[目录](../README.md)']
        if i: nav.insert(0,f'[上一张已有页：前{years[i-1]}](bce-{years[i-1]:04d}.md)')
        if i+1<len(years): nav.append(f'[下一张已有页：前{years[i+1]}](bce-{years[i+1]:04d}.md)')
        text=[f'# 公元前{y}年｜《史记》编年试编',' · '.join(nav),'**范围：仅本轮已审材料，不是这一年的全部史事。** 页面采用传统年条标签；古历岁首与现代公历不同，尚未逐日换算。同一故事跨年部分另存，未记月事件不强造先后顺序。']
        def month_key(r):
            m=re.search(r'(十二|十一|十|端|正|[一二三四五六七八九])月',r['time_raw_or_editor_label'])
            if not m: return 99
            x={'端':1,'正':1,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'十一':11,'十二':12}[m[1]]
            # Trial years only. Do not extend this rule across the Taichu reform.
            return (x-10)%12 if 109<=y<=246 else x
        rows=sorted(rows,key=month_key); header=False
        for n,r in enumerate(rows,1):
            if month_key(r)==99 and not header:
                text.append('## 本年相关记录（未定月，不推定彼此先后）'); header=True
            text.append(body(r,'../appendix/sources.md',n))
        text+=['---',' · '.join(nav),'[未确年、跨年及背景](../appendix/unplaced.md) · [文献、评论与异说](../appendix/documents.md)']
        write(f'years/bce-{y:04d}.md','\n\n'.join(text))
    unplaced=[r for r in records if r['year_bce'] is None and r['type'] in ('事件','背景','记载')]
    docs=[r for r in records if r['year_bce'] is None and r['type'] not in ('事件','背景','记载')]
    write('appendix/unplaced.md','# 未确年、跨年与人物背景\n\n[返回目录](../README.md)\n\n这些记录没有被丢弃，只是不伪造年份。保留原篇次序，继续寻找年代锚点。\n\n'+'\n\n'.join(body(r,'sources.md') for r in unplaced))
    write('appendix/documents.md','# 文献、评论、异说和后补\n\n[返回目录](../README.md)\n\n长篇引文目前只完成内容概述，未完成逐句白话。\n\n'+'\n\n'.join(body(r,'sources.md') for r in docs))
    stats={'source_commit':SNAPSHOT,'source_bytes':len(raw),'source_blob':blob,'source_sha256':hashlib.sha256(raw).hexdigest(),'source_lines':len(lines),'chapter_count':130,'full_chapters_first_review':REVIEWED,'reviewed_substantive_source_lines':reviewed_lines,'review_records':len(records),'dated_records':sum(r['year_bce'] is not None for r in records),'undated_records':sum(r['year_bce'] is None for r in records),'year_pages':len(years),'evidence_cards':len(cards),'chunqiu_year_markers':len(cqrows),'chunqiu_nonempty_years':sum(r['has_prose'] for r in cqrows),'empty_year_markers':[r['label'] for r in cqrows if not r['has_prose']],'table_candidate_rows':len(tab),'empty_title_line_count':sum('《》' in s for s in lines),'pending_source_lines':sum(r['status']=='待逐段处理' for r in ledger),'kind_counts':dict(collections.Counter(r['type'] for r in records)),'status':'全书结构入库；5篇分流初审；绝非全书编年完成；未调用外部GPT批处理API'}
    jw('data/audit.json',stats)
    pending=[]
    for ch in chapters:
        if ch['chapter'] in REVIEWED: continue
        for a in range(ch['start_line']+1,ch['end_line']+1,8):
            pending.append({'chapter':ch['chapter'],'start_line':a,'end_line':min(a+7,ch['end_line']),'status':'待GPT逐段解读','must_check':['段内多事件','回叙预叙','书名缺损','世系论说','定年证据','同书重复和异说'],'instruction':'逐段阅读；每项保存原文片段和时间判断，未确年用null，不以著名事件或关键词搜索代替。'})
    jl('data/pending-review-queue.jsonl',pending)
    md=['# 《史记》编年试编｜第一轮实际结果',f'全书 **130篇** 建立原文行索引；逐段初审 **5篇**（河渠书、陈涉世家、管晏列传、老子韩非列传、刺客列传），另抽查相关本纪、世家、年表。形成 **{len(records)}条初审记录、{len(years)}张年份页**，其中 **{stats["dated_records"]}条暂系年、{stats["undated_records"]}条未确年或保留相对时间**。','**不是《史记》全书已经编年完成，也不是这些年份已经搜齐全书。** 结构入库与逐段解读分别计数；诗歌、长篇论说还没有逐句翻译完。','[问题与暂定办法](REPORT.md) · [原文卡片](appendix/sources.md) · [未确年材料](appendix/unplaced.md) · [文献与评论](appendix/documents.md) · [审计统计](data/audit.json)','## 已有年份页（非连续年表）','| 年条标签 | 本轮记录数 |\n|---|---:|']
    md[-1] += '\n' + '\n'.join([f'| [公元前{y}年](years/bce-{y:04d}.md) | {sum(r["year_bce"]==y for r in records)} |' for y in years])
    md += ['## 骨架和完成度','《春秋》255个年标记中244个有正文。哀公十四年含获麟后续文，十五、十六年是续经；十七至二十七年为空标签。空标签不表示那年没有历史事件。','《十二诸侯年表》《六国年表》另生成635条年表行候选；不计入完成事件，各国空白列、段内回叙与纪年冲突仍待校对。卷十四最后一个年行跨两行，已合成一个候选。','严格以获麟为《春秋》终点时，前480—404年无法直接由这两部编年书提供连续年条。《左传》可补一部分；上古和其余缺口暂保留年表补轴来源，不冒称《通鉴》已有这些年条。','## 重建方法','仓库根目录运行 `python scripts/build_shiji_trial.py`。仅标准库，无模型API调用。`reviewed.psv` 是本轮GPT初审结果；程序检查输入哈希、原文去向、引用范围和页面链接，然后生成可读页面与全书待处理队列。','原始文本不改，引用固定到输入提交；更换底本必须重新核对行号。所有诗文、评论和不明年代的故事保留原文，不被静默删除。','[原有逐年读史入口](../README.md)']
    write('README.md','\n\n'.join(md))
    broken=[]
    for f in out.rglob('*.md'):
        for href in re.findall(r'\]\(([^)]+)\)',f.read_text(encoding='utf-8')):
            if href.startswith(('https://','http://')): continue
            filepart,_,anchor=href.partition('#')
            target=(f.parent/filepart).resolve() if filepart else f
            if not target.exists():
                if href=='../README.md' and f==out/'README.md': continue
                broken.append(f'{f}: {href}'); continue
            if anchor and f'id="{anchor}"' not in target.read_text(encoding='utf-8'): broken.append(f'Invalid anchor: {href}')
    if broken: raise AssertionError('\n'.join(broken))
    assert (root/SJ).read_bytes()==raw
    return stats

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path('.'))
    print(json.dumps(run(p.parse_args().root.resolve()),ensure_ascii=False,indent=2))
