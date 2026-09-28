#!/usr/bin/env python3
"""Rebuild reviewed batches, merge only explicitly identified events, preserve IDs.
No model calls: semantic extraction is the checked-in PSV review, not a regex claim.
Python >=3.10, standard library. Source originals are never changed.
"""
from __future__ import annotations
import argparse, bisect, collections, hashlib, json, re, shutil, tempfile
from pathlib import Path
import build_shiji_trial as legacy
from shiji_first_appearance import plan_placements
from shiji_sequence import order_units, check_pages

NEW_CHAPTERS = [31,64,65,66]
PUNCT_SNAPSHOT='a6576d718e55971fddf11e6c26023e8c241a9362'
TITLES={**legacy.TITLES,64:'司马穰苴列传',65:'孙子吴起列传',66:'伍子胥列传'}
META_LINES={2950,2953,2956,2966,2969,2976,2983,2993,2995,4639,4647,4657,4683}
OLD_MERGES={'sj-086-L5387-01':'wu-coup-prep-515','sj-086-L5388-01':'wu-coup-515'}

def loadl(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
def jwrite(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def jlwrite(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in x),encoding='utf-8')
def anchor(key):return 'ref-'+re.sub(r'[^a-zA-Z0-9-]','-',key)
def yearpage(y):return f'bce-{y:04d}.md'

def initial_data(root):
    # Isolate the first-batch renderer: do not validate its old sources against newer pages.
    with tempfile.TemporaryDirectory(prefix='shiji-initial-') as folder:
        temp=Path(folder)
        for name in ('texts','classics','zizhi-tongjian'):
            (temp/name).symlink_to(root/name,target_is_directory=True)
        dst=temp/'chronicle/shiji-trial';dst.mkdir(parents=True)
        for name in ('reviewed.psv','first-appearance.json','REPORT.md'):
            shutil.copyfile(root/'chronicle/shiji-trial'/name,dst/name)
        for name in ('README.md','EDITORIAL_RULES.md'):
            shutil.copyfile(root/'chronicle'/name,temp/'chronicle'/name)
        legacy.run(temp)
        result={name:loadl(dst/'data'/name) for name in ('records.jsonl','source-ledger.jsonl','pending-review-queue.jsonl')}
        result['chapter-inventory.json']=json.loads((dst/'data/chapter-inventory.json').read_text())
        return result

def run(root:Path):
    out=root/'chronicle/shiji-trial'
    # Rebuild the immutable first batch first: backwards-compatible IDs and citations.
    initial=initial_data(root)
    records=initial['records.jsonl'];old_ids={r['id'] for r in records}
    olddates={r['id']:r['year_bce'] for r in records}
    raw=(root/legacy.SJ).read_bytes();lines=raw.decode('utf-8-sig').splitlines()
    chapters=initial['chapter-inventory.json']
    boundaries=[c['start_line'] for c in chapters]
    chapter=lambda n:bisect.bisect_right(boundaries,n)
    cards={e['key']:e for r in records for e in r['evidence']}
    def evidence(key):
        if key in cards:return cards[key]
        book,loc=key.split(':',1)
        if book=='sj':
            a,b=legacy.span(loc);assert 1<=a<=b<=len(lines)
            e={'key':key,'path':legacy.SJ,'start_line':a,'end_line':b,'title':f'《史记》卷{chapter(a)} {TITLES.get(chapter(a),"")}', 'quote':'\n'.join(lines[a-1:b]),'url':legacy.PREFIX+legacy.SJ+f'#L{a}-L{b}','source_sha256':hashlib.sha256(raw).hexdigest()}
        elif book=='zz':
            g,y=map(int,loc.split('.'));p=root/f'working-texts/zuozhuan-punctuated-years/data/zz-{g:02d}-{y:02d}.json'
            d=json.loads(p.read_text(encoding='utf-8'));assert d['status']=='punctuated_structure_checked_not_critical_edition'
            text='\n\n'.join(('经（含续经时见原页）' if z['kind']=='jing' else '传')+'\n'+z['text'] for z in d['layers'])
            e={'key':key,'path':str(p.relative_to(root)),'start_line':None,'end_line':None,'title':f'《春秋／左传》鲁{d["ruler"]}{y}年','quote':text,'url':d['source_url'],'raw_sha256':d['raw_sha256'],'source_text_sha256':d['text_sha256'],'local_link':f'../../../working-texts/zuozhuan-punctuated-years/years/{yearpage(d["year_bce"])}'}
        elif re.fullmatch('tp[0-9]{3}',book):
            a,b=legacy.span(loc);path=f'working-texts/chronology-punctuated/main/tj-{book[2:]}.md';text=(root/path).read_text(encoding='utf-8').splitlines();assert 1<=a<=b<=len(text)
            e={'key':key,'path':path,'start_line':a,'end_line':b,'title':f'《资治通鉴》卷{int(book[2:])}（有标点工作本）','quote':'\n'.join(text[a-1:b]),'url':f'https://github.com/zhixin0825/history/blob/{PUNCT_SNAPSHOT}/{path}#L{a}-L{b}'}
        else:raise ValueError(f'Unsupported new evidence: {key}')
        cards[key]=e;return e
    counts=collections.Counter()
    for r in records:
        counts[int(r['id'].split('-L')[1].split('-')[0])]=max(counts[int(r['id'].split('-L')[1].split('-')[0])],int(r['id'].rsplit('-',1)[1]));r['batch']='initial';r['merge_key']=OLD_MERGES.get(r['id'],'')
    for number,s in enumerate((out/'batches/round2.psv').read_text(encoding='utf-8').splitlines(),1):
        if not s.strip() or s.startswith('#'):continue
        f=s.split('|');assert len(f)==10,f'Bad batch fields at {number}'
        loc,year,time,kind,title,plain,extra,note,merge,people=f
        a=legacy.span(loc.split(';')[0])[0];counts[a]+=1
        keys=['sj:'+p for p in loc.split(';')]+[p for p in extra.split(';') if p]
        r={'id':f'sj-{chapter(a):03d}-L{a:04d}-{counts[a]:02d}','source_line_specs':loc,'chapter':chapter(a),'year_bce':None if year=='?' else int(year),'time_raw_or_editor_label':time,'type':kind,'title':title,'plain':plain,'editor_note':note,'evidence':[evidence(k) for k in dict.fromkeys(keys)],'processing':'GPT逐段分流初审；未独立复核；长篇引文仍为内容概述','date_method':'未确年或相对次序' if year=='?' else '依据所列年条或明确写出的推算暂编','source_psv_line':number,'batch':'round2','merge_key':merge,'people':[p for p in people.split(';') if p]}
        records.append(r)
    assert len({r['id'] for r in records})==len(records)
    # Curated equivalence is explicit, not inferred from name/date proximity.
    groups={}
    for r in records:groups.setdefault(r.get('merge_key') or r['id'],[]).append(r)
    units=[]
    for key,members in groups.items():
        years={r['year_bce'] for r in members};assert len(years)==1,('Conflicting merge years',key,years)
        preferred=next((r for r in reversed(members) if r['batch']=='round2' and r['type']=='事件'),members[0])
        units.append({'id':members[0]['id'],'aliases':[r['id'] for r in members],'year_bce':preferred['year_bce'],'type':preferred['type'],'preferred_record_id':preferred['id'],'merge_key':key if len(members)>1 else None,'members':members})
    coverage=collections.defaultdict(list)
    for r in records:
        for spec in r['source_line_specs'].split(';'):
            a,b=legacy.span(spec)
            for n in range(a,b+1):coverage[n].append(r['id'])
    ledger=initial['source-ledger.jsonl'];all_reviewed=sorted(legacy.REVIEWED+NEW_CHAPTERS)
    for row in ledger:
        n=row['line']
        if n in coverage:row.update(status='已分流初审',record_ids=coverage[n])
        elif n in META_LINES:row.update(status='小标题',record_ids=[])
    for c in chapters:
        ch=c['chapter'];c['title']=TITLES.get(ch,c['title'])
        if ch in all_reviewed:
            missing=[n for n in range(c['start_line']+1,c['end_line']+1) if n not in coverage and n not in META_LINES and lines[n-1].strip() not in legacy.META]
            assert not missing,('Unrouted chapter',ch,missing)
            c['status']='逐段分流初审完成；非逐句全译或独立复核完成'
        c['reviewed_body_lines']=sum(n in coverage for n in range(c['start_line']+1,c['end_line']+1))
    jlwrite(out/'data/records.jsonl',records);jlwrite(out/'data/source-ledger.jsonl',ledger);jwrite(out/'data/chapter-inventory.json',chapters)
    jlwrite(out/'data/event-groups.jsonl',[{k:v for k,v in u.items() if k!='members'} for u in units])
    pending=initial['pending-review-queue.jsonl'];pending=[x for x in pending if x['chapter'] not in NEW_CHAPTERS];jlwrite(out/'data/pending-review-queue.jsonl',pending)
    # Complete originals, never quotations retyped by a language model.
    source_page=['# 原文卡片与逐项出处','引文由固定原文范围提取。新《左传》引用采用已有标点的逐年原文；旧引用保留，不将旧年表依据悄悄更换。']
    for key,e in cards.items():
        source_page += [f'<a id="{anchor(key)}"></a>',f'## {e["title"]} · {key}',f'[原出处与上下文]({e["url"]})']
        if e.get('local_link'):source_page.append(f'[本地有标点年条]({e["local_link"]})；原始网页SHA256：`{e["raw_sha256"]}`。')
        source_page += ['```text',e['quote'],'```']
    (out/'appendix/sources.md').write_text('\n\n'.join(source_page)+'\n',encoding='utf-8')
    def refs(r,prefix):return ' · '.join(f'[{e["title"]}]({prefix}#{anchor(e["key"])})' for e in r['evidence'])
    def render(u,prefix,number=None):
        r=next(r for r in u['members'] if r['id']==u['preferred_record_id'])
        text=[* [f'<a id="{rid}"></a>' for rid in u['aliases']],f'### {str(number)+". " if number else ""}{r["title"]}',f'**时间：{r["time_raw_or_editor_label"]}** · {u["type"]}',r['plain'],refs(r,prefix),'<details><summary>归年依据、同书互见与待核问题</summary>',r['editor_note']]
        for other in u['members']:
            if other['id']==r['id']:continue
            text += [f'**同一事件的另一条初审记录：{other["title"]}**',other['plain'],refs(other,prefix),other['editor_note']]
        text+=['</details>'];return '\n\n'.join(text)
    years=sorted({u['year_bce'] for u in units if u['year_bce'] is not None},reverse=True)
    for i,y in enumerate(years):
        nav=['[年份目录](../README.md)']
        if i:nav.insert(0,f'[上一张已有页：前{years[i-1]}]({yearpage(years[i-1])})')
        if i+1<len(years):nav.append(f'[下一张已有页：前{years[i+1]}]({yearpage(years[i+1])})')
        text=[f'# 公元前{y}年｜逐年读《史记》',' · '.join(nav),'**覆盖：当前已审篇章的相关记载，不是这一年全《史记》材料已经收齐。** 古史年条不等于现代公历逐日换算；未定月条目不强造先后。']
        baseline=root/f'working-texts/zuozhuan-punctuated-years/years/{yearpage(y)}'
        if baseline.exists():text.append(f'[本年《春秋／左传》有标点原文](../../../working-texts/zuozhuan-punctuated-years/years/{yearpage(y)})')
        rows=[u for u in units if u['year_bce']==y]
        def month(u):
            r=next(r for r in u['members'] if r['id']==u['preferred_record_id'])
            m=re.search(r'(十二|十一|十|正|端|[一二三四五六七八九])月',r['time_raw_or_editor_label'])
            if not m:return 99
            n={'正':1,'端':1,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'十一':11,'十二':12}[m[1]]
            return (n-10)%12 if 109<=y<=246 else n
        rows=order_units(rows,month)
        for n,u in enumerate(rows,1):text.append(render(u,'../appendix/sources.md',n))
        text += ['---',' · '.join(nav),'[人物背景与未确年材料](../appendix/unplaced.md) · [文献与评论](../appendix/documents.md)']
        (out/'years'/yearpage(y)).write_text('\n\n'.join(text)+'\n',encoding='utf-8')
    for fname,kinds,title in [('unplaced.md',{'事件','背景','记载'},'未确年、跨年与人物背景'),('documents.md',{'文献','评论','后补','异说'},'文献、评论、后补与异说')]:
        rows=[u for u in units if u['year_bce'] is None and u['type'] in kinds]
        (out/'appendix'/fname).write_text('# '+title+'\n\n[返回年份目录](../README.md)\n\n'+ '\n\n'.join(render(u,'sources.md') for u in rows)+'\n',encoding='utf-8')
    # Existing six plus new, explicitly justified backstory placements.
    config=json.loads((out/'first-appearance.json').read_text())
    byid={r['id']:r for r in records}
    def pick(loc,title):
        hits=[r for r in records if r['batch']=='round2' and r['source_line_specs']==loc and title in r['title']];assert len(hits)==1,(loc,title)
        return hits[0]
    extra=[('sun-wu','孙武',pick('2978;4668','吴攻舒'),[pick('4642','在宫中')],'本篇先叙训练与获任，再总述伐楚；《吴世家》在阖闾三年已经称孙武为将。只作此年军议前的补叙。'),('sun-bin','孙膑',pick('4645','桂陵'),[pick('4643','在魏受刑'),pick('4644','秘密'),pick('4644','赛马')],'《孙子吴起列传》先叙在魏受刑、归齐与赛马，再以“其后魏伐赵”接入桂陵之役。保留前因，不给早年故事补年份。'),('wu-zixu','伍子胥',pick('4664','伍尚赴楚'),[pick('4660','父兄和先世')],'本篇开头交代出身和先世，随后才进入伍氏父兄被杀、伍员逃亡；补叙不是把伍举的经历定在前522年。')]
    for eid,label,event,backs,basis in extra:
        config['entries'].append({'entity_id':'person-'+eid,'person_label':label,'anchor_record_id':event['id'],'anchor_scope':'current_reviewed_corpus_provisional','anchor_note':'暂以当前已审材料中的最早有据参与事件作阅读入口；后续发现更早事件可调整。','backstories':[{'record_id':b['id'],'relation':'before_anchor','basis_source_keys':[b['evidence'][0]['key']],'basis':basis} for b in backs]})
    plans=plan_placements(records,config);jwrite(out/'data/first-appearance-combined.json',config)
    index=['# 人物首次登场与前事补叙','[返回目录](../README.md)','前事没有被改定到登场年。以下都是当前已审范围的暂定入口。','| 人物 | 阅读位置 | 前事 |\n|---|---|---|']
    for p in plans:
        r=byid[p['record_id']];y=p['reading_year_bce'];file=out/'years'/yearpage(y);s=file.read_text();start=s.index(f'<a id="{p["reading_anchor_record_id"]}"></a>');end=s.index('</details>',start)+len('</details>')
        hid='backstory-'+r['id'];chunk='\n\n'.join([f'<a id="{hid}"></a>',f'#### 登场前事｜{p["person_label"]}：{r["title"]}',f'> 此前经历，确切年月未详；放在这里补叙，不表示发生于前{y}年。',r['plain'],refs(r,'../appendix/sources.md'),'<details><summary>补叙依据</summary>',p['basis'],f'[原记录](../appendix/unplaced.md#{r["id"]})','</details>'])
        # Repeated backstories follow the existing insertion block in source order.
        marker='<!-- backstory-end:'+p['reading_anchor_record_id']+' -->'
        if marker in s:
            pos=s.index(marker);s=s[:pos]+chunk+'\n\n'+s[pos:]
        else:s=s[:end]+'\n\n'+chunk+'\n\n'+marker+s[end:]
        file.write_text(s,encoding='utf-8')
        index.append(f'| {p["person_label"]} | [前{y}年](../years/{yearpage(y)}#{hid}) | {r["title"]} |')
    (out/'appendix/first-appearances.md').write_text('\n\n'.join(index[:3])+'\n\n'+'\n'.join(index[3:])+'\n',encoding='utf-8');jwrite(out/'data/reading-placements.json',{'schema_version':1,'placements':plans})
    stats={'source_commit':legacy.SNAPSHOT,'source_sha256':hashlib.sha256(raw).hexdigest(),'chapter_count':130,'full_chapters_first_review':all_reviewed,'new_chapters_this_batch':NEW_CHAPTERS,'prior_review_records':len(old_ids),'new_review_records':sum(r['batch']=='round2' for r in records),'review_records':len(records),'dated_records':sum(r['year_bce'] is not None for r in records),'undated_records':sum(r['year_bce'] is None for r in records),'narrative_units_after_curated_merges':len(units),'merged_groups':sum(len(u['members'])>1 for u in units),'merged_source_records':sum(len(u['members']) for u in units if len(u['members'])>1),'year_pages':len(years),'evidence_cards':len(cards),'reviewed_substantive_source_lines':sum(x['status']=='已分流初审' and x['chapter'] in all_reviewed for x in ledger),'pending_source_lines':sum(x['status']=='待逐段处理' for x in ledger),'first_appearance_backstories':len(plans),'people_with_first_appearance_backstories':len({p['entity_id'] for p in plans}),'old_ids_preserved':old_ids.issubset(byid),'old_occurrence_dates_preserved':all(byid[k]['year_bce']==v for k,v in olddates.items()),'originals_changed':False,'status':'9篇逐段分流初审；并非全书完成；未独立复核；诗文与长篇对话尚非逐句全译；没有外部模型批处理'}
    jwrite(out/'data/audit.json',stats)
    readme=['# 逐年读《史记》｜累计进度',f'原文130篇全部建立索引；目前 **{len(all_reviewed)}篇逐段分流初审**。累计 **{len(records)}条来源记录**，明确合并后 **{len(units)}个叙述单元、{len(years)}张年份页**。','**不是全书编年完成，也不是这些年份已搜齐所有史料。** 源记录包含事件、背景、评论与异说；这些数字不是经过独立复核的原子事件总数。','本轮增加《吴太伯世家》《司马穰苴列传》《孙子吴起列传》《伍子胥列传》，重点处理互见、跨年、人物登场。原有五篇及旧链接保留。','[详细进度](../PROGRESS.md) · [已确认规则](../EDITORIAL_RULES.md) · [原文卡片](appendix/sources.md) · [未确年材料](appendix/unplaced.md) · [文献与评论](appendix/documents.md) · [人物登场](appendix/first-appearances.md) · [初轮问题报告（历史记录）](REPORT.md)','[《春秋／左传》逐年有标点原文](../../working-texts/zuozhuan-punctuated-years/README.md)是原文底本入口，不计作已经完成的白话年度正文。','## 年份目录（仅已审记载）','| 年份 | 叙述单元 |\n|---|---|']
    readme += [f'| [前{y}年](years/{yearpage(y)}) | {sum(u["year_bce"]==y for u in units)} |' for y in years]
    readme+=['\n## 重建与检查','执行 `python scripts/build_shiji_incremental.py`，随后执行 `python -m unittest discover -s tests -p "test_shiji_incremental.py" -v`。内容审读保存在 reviewed.psv 与 batches/round2.psv；代码不调用模型，不冒称正则扫描等于GPT逐段阅读。','旧 `build_shiji_trial.py` 只重建首轮，累计编排须使用本页新入口。原始TXT不改，新引文逐项指向实际采用的版本。']
    (out/'README.md').write_text('\n\n'.join(readme[:7])+'\n\n'+'\n'.join(readme[7:])+'\n',encoding='utf-8')
    baseline=json.loads((root/'working-texts/zuozhuan-punctuated-years/audit.json').read_text())
    progress=['# 全量整理进度与继续执行规则','用户已授权按已确认规则连续分批处理，无须逐批审批。仅对无法自行解决、会改变编辑口径的问题集中询问。此文件保存检查点，不是无人值守任务已经启动的说明。','## 本轮实际结果',f'- 《春秋／左传》已导入有标点原文年条 {baseline["imported_years"]}/255；来源为古诗文网／古文岛原文页，经、传与续经分层。没有导入现代白话译文。\n- 《史记》累计初审9/130篇：'+ '、'.join(TITLES[x] for x in all_reviewed)+f'。\n- 来源记录{len(records)}条，叙述单元{len(units)}个，年份正文{len(years)}页。\n- 新增孙武、孙膑、伍子胥的登场前事，共{len(plans)}条补叙、{stats["people_with_first_appearance_backstories"]}个人。','## 已解决而未打断用户的问题','宣公十四年原页第二层标题写“经传”，核对实际内容后按传层识别，保留原HTML及 source_heading，不把正文改写。','同一刺僚事件原分散在《刺客列传》《吴世家》《伍传》，合并展示并保留原编号。孙武的宫中训练、孙膑的受刑与赛马作为前事展示，发生年仍未知。','## 仍保留的实质疑点','余祭死亡纪年两说；豫章之战相差一年；《史记》减灶末数三万、《通鉴》二万；太史儋、聂政、伍氏流亡及齐君称号等既有问题继续保留，不为页面整齐抹去。','## 完成与未完成分开','“初审完成一篇”表示该篇每个实质原文段落都已有去向，不表示每句都已逐字译出或独立考证正确。长篇观乐评论、兵法对话仍可能采用内容概述；逐句细化、独立复核、全书去重和全人物识别未完成。255张有标点原文页也不等于255年的白话编年已经完成。','## 下一批检查点','优先继续《越王勾践世家》《齐太公世家》《鲁周公世家》《晋世家》《楚世家》等与当前吴楚材料互见的篇章，随后依待处理队列覆盖其余所有篇章，不只摘录著名事件。','[累计阅读入口](shiji-trial/README.md) · [机器可核查统计](shiji-trial/data/audit.json) · [逐篇进度](shiji-trial/data/chapter-inventory.json) · [剩余队列](shiji-trial/data/pending-review-queue.jsonl)']
    (root/'chronicle/PROGRESS.md').write_text('\n\n'.join(progress)+'\n',encoding='utf-8')
    # Source equality, preserved occurrence dates, and all Markdown local references.
    assert (root/legacy.SJ).read_bytes()==raw and stats['old_occurrence_dates_preserved']
    for f in out.rglob('*.md'):
        for href in re.findall(r'\]\(([^)]+)\)',f.read_text(encoding='utf-8')):
            if href.startswith(('https://','http://')):continue
            part,_,frag=href.partition('#');target=(f.parent/part).resolve() if part else f.resolve()
            assert target.exists(),(f,href)
            if frag:assert f'id="{frag}"' in target.read_text(encoding='utf-8'),(f,href)
    jwrite(out/'data/validation.json',{'source_preserved':True,'all_local_links_and_anchors_resolve':True,'old_record_ids_preserved':True,'old_dates_preserved':True,'reviewed_chapter_paragraph_coverage':True,'new_source_record_count':stats['new_review_records'],'no_semantic_accuracy_estimate':True})
    check_pages(root)
    print(json.dumps(stats,ensure_ascii=False,indent=2));return stats
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'));run(p.parse_args().root.resolve())
