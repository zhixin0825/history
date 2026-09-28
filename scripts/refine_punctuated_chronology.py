#!/usr/bin/env python3
"""Offline rendering of explicitly recognized markup; no punctuation inference.
Run after import_punctuated_chronology.py. Failed texts are separated into review/.
"""
from __future__ import annotations
import collections, hashlib, json, re
from pathlib import Path
import import_punctuated_chronology as imp

META = imp.PAGE_TEMPLATES | {'header2','footer','textquality'}
INLINE = {'propernoun','+','yl','另'}

def params(token):
    s=token[2:-2]; out=[]; start=0; i=0; depth=0
    while i<len(s):
        if s.startswith('{{',i): depth+=1; i+=2
        elif s.startswith('}}',i): depth-=1; i+=2
        elif s[i]=='|' and depth==0: out.append(s[start:i]);i+=1;start=i
        else:i+=1
    out.append(s[start:]);return out

def inline(s):
    out=[]
    for p in imp.spans(s):
        if p['kind']=='text':out.append(p['raw']);continue
        a=params(p['raw']);name=a[0].strip().lower()
        if name in ('propernoun','+') and len(a)==2:out.append(inline(a[1]))
        elif name=='yl' and len(a)==3:
            # YL is a display-year label with a target year. All arguments remain in raw/layers.
            out.append(inline(a[1]))
        elif name=='另' and len(a)==3:
            # Default unconverted reading is the first argument; the alternate is retained separately.
            out.append(inline(a[1]))
        else:out.append(p['raw'])
    return ''.join(out)

def run():
    root=imp.OUT;manifest=json.loads((root/'manifest.json').read_text());rows=[]
    for old in manifest:
        stem=old['stem'];src=json.loads((root/'raw'/f'{stem}.json').read_text());raw=src['wikitext']
        parts=imp.spans(raw);body=[];unresolved=[];quality=[];variants=[]
        for p in parts:
            if p['kind']=='text':body.append(p['raw']);continue
            a=params(p['raw']);name=a[0].strip().lower()
            if name in META:
                p['kind']='page_metadata'
                if name=='textquality':quality.append(p['raw'])
            elif name=='*':p['kind']='annotation'
            elif name in INLINE:
                p['kind']='inline_markup';body.append(inline(p['raw']))
                if name=='另':variants.append({'start':p['a'],'end':p['b'],'raw':p['raw'],'display':a[1],'alternate':a[2]})
            else:
                body.append(p['raw']);unresolved.append(p.get('name',name))
        main=imp.display_markup(''.join(body))
        punct=collections.Counter(c for c in main if c in imp.PUNCT)
        dot_count=main.count('．')
        residue=bool(re.search(r'\{\{|</?[a-zA-Z][^>]*>|\[\[',main))
        longruns=[m[0] for m in re.finditer(r'[^。，、；：？！「」『』\n]{251,}',main) if len(re.findall(r'[\u3400-\u9fff]',m[0]))>200]
        reasons=[]
        if punct['。']<=10 or punct['，']<=5:reasons.append('缺少充分的句号或逗号；仅有句读分隔点不合要求')
        if dot_count>30:reasons.append('大段使用全角分隔点，未具备统一现代句读')
        if residue or unresolved:reasons.append('尚有未展开模板、嵌入页面或其他标记，不能视为正文已经齐备')
        if longruns:reasons.append('含长串无现代句读的正文，需要进一步核查')
        ok=not reasons;dest='main' if ok else 'review';target=root/dest/f'{stem}.md';target.parent.mkdir(exist_ok=True)
        alt=root/('review' if ok else 'main')/f'{stem}.md'
        if alt.exists():alt.unlink()
        state='标点与结构初筛通过；不是独立校勘完成' if ok else '未通过；禁止作为正式编年输入'
        md=[f'# {old["title"]}',f'**状态：{state}。**',f'[来源固定版本]({old["source_url"]}) · [贡献者与修订历史]({old["history_url"]}) · [原注释](../notes/{stem}.md)', '标点、引号和段落沿用来源，不由模型新添；正文中的史家评论、回叙仍需在编年时区分。']
        if reasons:md+=['> '+'；'.join(reasons)+'。']
        if quality:md+=['> 来源另有校对状态标记：`'+'; '.join(quality)+'`，不因结构初筛而视为全书文字已校定。']
        if variants:md+=['> 字形转换模板使用原网页默认字形，备选字形保留在 layers 和 manifest，不当作编者校改。']
        md+=[main];target.write_text('\n\n'.join(md),encoding='utf-8')
        # Notes retain original annotation content, with the correct new return link.
        np=root/'notes'/f'{stem}.md'
        if np.exists():
            ns=np.read_text().replace(f'../main/{stem}.md',f'../{dest}/{stem}.md').replace(f'../review/{stem}.md',f'../{dest}/{stem}.md')
            np.write_text(ns,encoding='utf-8')
        checks={'raw_partition_reconstructs':''.join(p['raw'] for p in parts)==raw,'punctuation_counts':dict(punct),'punctuation_total':sum(punct.values()),'unresolved_templates':unresolved,'fullwidth_separator_dots':dot_count,'long_unpunctuated_runs':len(longruns),'remaining_markup':residue}
        assert checks['raw_partition_reconstructs']
        r={**old,'status':'punctuated_structural_pass_not_scholarly_review' if ok else 'rejected_as_working_input','display_path':f'{dest}/{stem}.md','review_reasons':reasons,'source_quality_templates':quality,'glyph_template_variants':variants,'checks':checks,'main_sha256':hashlib.sha256(main.encode()).hexdigest()}
        rows.append(r)
        imp.gz_dump(root/'layers'/f'{stem}.json.gz',{'metadata':src['metadata'],'spans':parts,'checks':checks,'variants':variants,'offset_unit':'Unicode code points, zero-based, end-exclusive; raw wikitext'})
    imp.dump(root/'manifest.json',rows)
    audit=json.loads((root/'audit.json').read_text());audit['status_counts']=dict(collections.Counter(r['status'] for r in rows))
    audit['tongjian_punctuated_structure_pass']=sum(r['stem'].startswith('tj-') and r['status'].startswith('punctuated') for r in rows)
    audit['zuozhuan_punctuated_structure_pass']=sum(r['stem'].startswith('zz-') and r['status'].startswith('punctuated') for r in rows)
    audit['rejected_as_working_input']=[{'title':r['title'],'stem':r['stem'],'reasons':r['review_reasons']} for r in rows if r['status'].startswith('rejected')]
    imp.dump(root/'audit.json',audit)
    front=['# 有标点的编年候选底本','**无标点清洁版仅作中间文件、校核对照，不作为正式编年输入。** 本目录采用已有标点文本；程序只处理明确网页标记，不新造句读。',f'《通鉴》已取得294卷，其中 {audit["tongjian_punctuated_structure_pass"]} 卷通过标点与结构初筛。《春秋左氏传》取得十二公，{audit["zuozhuan_punctuated_structure_pass"]} 部分初筛通过，其余进入 review/，不可作为合格底本。','**初筛只排除无标点、密集分隔点、模板残留等明显问题，不证明文字、句读、引号和年代全部正确。** 未解决的《左传》部分没有凑进可用目录；上古经传续文也未在这一步重新划分。','[标点要求](PUNCTUATION_RULES.md) · [来源修订号及逐卷结果](manifest.json) · [检查统计](audit.json)','来源为中文维基文库《資治通鑒 (胡三省音注)》及《春秋左氏傳》。每页保留固定修订号和贡献者历史；不是中华书局正式电子版。原始 wikitext、显式注释层及所有元数据均保留，原仓库文件和已有编年引用不覆盖。','现代标点及录入文字的再分发遵循[维基文库版权说明](https://zh.wikisource.org/wiki/Wikisource:版权信息)和各来源页面许可。保留贡献者历史、许可链接及修改说明；改动仅为格式转换和显式标记分层。','## 《资治通鉴》\n\n| 卷 | 状态 |\n|---|---|']
    for r in rows:
        if r['stem'].startswith('tj-'):front.append(f'| [{r["title"].split("/")[-1]}]({r["display_path"]}) | '+('标点初筛通过' if r['status'].startswith('punctuated') else '不合格，待处理')+' |')
    front+=['\n## 《春秋左氏传》\n\n| 部分 | 状态 |\n|---|---|']
    for r in rows:
        if r['stem'].startswith('zz-'):front.append(f'| [{r["title"].split("/")[-1]}]({r["display_path"]}) | '+('标点初筛通过' if r['status'].startswith('punctuated') else '不合格，待处理')+' |')
    (root/'README.md').write_text('\n\n'.join(front[:7])+'\n\n'+'\n'.join(front[7:])+'\n',encoding='utf-8')
    # Only admitted working texts are subjected to the no-residual-markup assertion.
    for r in rows:
        assert (root/r['display_path']).exists()
        if r['status'].startswith('punctuated'):
            assert not r['checks']['remaining_markup'] and not r['checks']['long_unpunctuated_runs']
            assert r['checks']['punctuation_counts'].get('，',0)>5
    print(json.dumps(audit,ensure_ascii=False,indent=2))

if __name__=='__main__':run()
