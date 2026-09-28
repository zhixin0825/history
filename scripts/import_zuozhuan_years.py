#!/usr/bin/env python3
"""Fetch public, already-punctuated ORIGINAL text only; never generate punctuation.
Standard library. Serial, cached requests; stop on refusal/rate limiting. Source HTML
is retained as gzip. The imported text is a working transcription, not a critical edition.
"""
from __future__ import annotations
import argparse, collections, datetime, gzip, hashlib, json, re, time
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin

INDEX='https://m.gushiwen.cn/guwen/book_5138229e537e.aspx'
OUT=Path('working-texts/zuozhuan-punctuated-years')
LU=[('隐公',722,11),('桓公',711,18),('庄公',693,32),('闵公',661,2),('僖公',659,33),('文公',626,18),('宣公',608,18),('成公',590,18),('襄公',572,31),('昭公',541,32),('定公',509,15),('哀公',494,27)]
TRANS=str.maketrans('隱莊閔','隐庄闵')
PUNCT='。，、；：？！“”‘’「」『』'
class Node:
    def __init__(self,tag='',attrs=()):self.tag=tag;self.attrs=dict(attrs);self.children=[]
    def walk(self):
        yield self
        for c in self.children:
            if isinstance(c,Node):yield from c.walk()
    def text(self):
        if self.tag in {'script','style','noscript'}:return ''
        content=''.join(c.text() if isinstance(c,Node) else c for c in self.children)
        return ('\n'+content+'\n') if self.tag in {'p','div','br','h1','h2','h3'} else content
class DOM(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.root=Node();self.stack=[self.root]
    def handle_starttag(self,tag,attrs):
        n=Node(tag,attrs);self.stack[-1].children.append(n)
        if tag not in {'br','hr','img','meta','link','input','source','wbr','area','base','embed','param'}:self.stack.append(n)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:self.stack=self.stack[:i];break
    def handle_data(self,s):self.stack[-1].children.append(s)
def parse(s):
    p=DOM();p.feed(s);return p.root

def cn(s):
    s=s.replace('有','');d={c:i for i,c in enumerate('零一二三四五六七八九')};d['元']=1
    if s in d:return d[s]
    if '十' in s:
        a,b=s.split('十');return (d[a] if a else 1)*10+(d[b] if b else 0)
    raise ValueError(s)
def decode_label(label):
    label=re.sub(r'\s','',label).translate(TRANS)
    m=re.fullmatch(r'(隐公|桓公|庄公|闵公|僖公|文公|宣公|成公|襄公|昭公|定公|哀公)([元一二三四五六七八九十有]+)年?',label)
    if not m:return None
    g=next(i for i,x in enumerate(LU,1) if x[0]==m[1]);y=cn(m[2]);return g,y

def savejson(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def fetch(url,path):
    if path.exists():return gzip.decompress(path.read_bytes()).decode('utf-8')
    time.sleep(1.0)
    req=Request(url,headers={'User-Agent':'HistoryCorpusResearch/0.1 (limited serial original-text archival)'})
    with urlopen(req,timeout=35) as r:
        data=r.read();charset=r.headers.get_content_charset() or 'utf-8'
        text=data.decode(charset)
    path.write_bytes(gzip.compress(text.encode('utf-8'),mtime=0));return text

def original_text(doc):
    candidates=[n for n in doc.walk() if 'contson' in n.attrs.get('class','').split()]
    candidates=[n.text() for n in candidates if any(x in n.text() for x in ['〖经〗','〖傳〗','〖传〗','【经】','【傳】','【传】'])]
    if len(candidates)!=1:raise ValueError(f'Expected one original-text container, got {len(candidates)}')
    # Remove display indentation and blank lines only; retain all characters and punctuation.
    return '\n\n'.join(s.strip() for s in candidates[0].splitlines() if s.strip())

def run(limit=255):
    OUT.mkdir(parents=True,exist_ok=True)
    for d in ['raw','years','data']:(OUT/d).mkdir(exist_ok=True)
    html=fetch(INDEX,OUT/'raw/index.html.gz');doc=parse(html);links={}
    for n in doc.walk():
        if n.tag!='a':continue
        href=n.attrs.get('href','');label=decode_label(n.text())
        if label and re.search(r'bookv_[0-9a-f]+\.aspx',href):
            url=urljoin(INDEX,href)
            if label in links and links[label]!=url:raise ValueError(f'Duplicate year label {label}')
            links[label]=url
    expected={(g,y) for g,(_,_,count) in enumerate(LU,1) for y in range(1,count+1)}
    if set(links)!=expected:raise ValueError(f'Index incomplete: {len(links)}, missing {sorted(expected-set(links))}')
    savejson(OUT/'data/index.json',[{'ruler_index':g,'regnal_year':y,'url':url} for (g,y),url in sorted(links.items())])
    rows=[];errors=[]
    for (g,y),url in sorted(links.items())[:limit]:
        stem=f'zz-{g:02d}-{y:02d}';name,first,_=LU[g-1];year=first-y+1
        try:
            raw=fetch(url,OUT/'raw'/f'{stem}.html.gz');doc=parse(raw);text=original_text(doc)
            titles=[n.text() for n in doc.walk() if n.tag=='h1']
            if len(titles)!=1 or name not in titles[0].translate(TRANS):raise ValueError('Page heading does not match index')
            markers=list(re.finditer(r'[〖【](经传|经|經|传|傳)[〗】]',text));layers=[]
            for i,m in enumerate(markers):
                end=markers[i+1].start() if i+1<len(markers) else len(text)
                layers.append({'kind':'jing' if m[1] in ('经','經') else 'zhuan','source_heading':m[1],'text':text[m.end():end].strip(),'raw_start':m.end(),'raw_end':end})
            if any(x.get('source_heading')=='经传' for x in layers) and (g,y)!=(7,14):raise ValueError('Unexpected combined heading: needs explicit review')
            if not layers or any(not x['text'] for x in layers):raise ValueError('Missing or empty explicit textual layer')
            if len([x for x in layers if x['kind']=='zhuan'])!=1:raise ValueError('Missing or repeated Zhuan layer')
            if g<12 or y<=16:
                if len([x for x in layers if x['kind']=='jing'])!=1:raise ValueError('Missing Jing layer')
            if g==12 and y>=17 and any(x['kind']=='jing' for x in layers):raise ValueError('Unexpected Jing after Ai16')
            chars=len(re.findall(r'[\u3400-\u9fff]',text));pc=collections.Counter(c for c in text if c in PUNCT)
            if chars<8 or not pc['。']:raise ValueError('Empty/insufficient original text or punctuation')
            if '．' in text or '{{' in text or re.search(r'<[^>]+>',text):raise ValueError('Unprocessed markup/separator dots')
            # A comma is not obligatory in a very short year. Long runs are only structural warnings.
            runs=re.findall(r'[^。！？!?\n]{1001,}',text)
            meta={'id':stem,'ruler_index':g,'ruler':name,'regnal_year':y,'year_bce':year,'source_url':url,'fetched_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'text':text,'layers':layers,'cjk_characters':chars,'punctuation_counts':dict(pc),'long_sentence_warnings':len(runs),'status':'punctuated_structure_checked_not_critical_edition'}
            # Store continuation explicitly; never silently label it all as the canonical Jing.
            for layer in layers:
                layer['scope']='zhuan' if layer['kind']=='zhuan' else ('jing_and_continuation' if g==12 and y==14 else 'continuation' if g==12 and y>14 else 'jing')
            savejson(OUT/'data'/f'{stem}.json',meta)
            heading=f'# 公元前{year}年｜鲁{name}{y}年（有标点原文）'
            body=[heading,'**这是编年依据页，不是白话史事已经整理完成。** 文字、标点沿用来源；经、传、续经分层保存。简体为来源页面的原有显示，不是本程序转换。',f'[来源原文]({url}) · [来源目录]({INDEX}) · [本地目录](../README.md)','下载时间、原始HTML哈希及分层位置见同名 data 文件；不是杨伯峻或中华书局授权电子版。']
            for layer in layers:
                label={'jing':'经','zhuan':'传','jing_and_continuation':'经（含获麟后续经）','continuation':'续经'}[layer['scope']]
                body.extend([f'<a id="{layer["kind"]}"></a>',f'## {label}',layer['text']])
            (OUT/'years'/f'bce-{year:04d}.md').write_text('\n\n'.join(body)+'\n',encoding='utf-8')
            rows.append({k:v for k,v in meta.items() if k not in {'text','layers'}})
        except Exception as exc:
            errors.append({'id':stem,'url':url,'error':str(exc)});break
    savejson(OUT/'manifest.json',rows)
    audit={'index_years':len(links),'requested_this_run':min(limit,255),'imported_years':len(rows),'complete_requested_range':not errors and len(rows)==min(limit,255),'complete_255_year_backbone':not errors and len(rows)==255,'errors':errors,'scope':'Original-text transcription and punctuation checks only, not full historical interpretation or character collation.'}
    savejson(OUT/'audit.json',audit)
    table='\n'.join(f'| [前{r["year_bce"]}年](years/bce-{r["year_bce"]:04d}.md) | 鲁{r["ruler"]}{r["regnal_year"]}年 |' for r in rows)
    (OUT/'README.md').write_text('# 《春秋／左传》按年标点工作本\n\n原文来源：古诗文网／古文岛《左传》。仅处理公开的古籍原文，不导入现代译文或赏析；原文网页和下载哈希随条保存。本目录不是正式出版社的校勘本。\n\n'+f'目录应有255个年条，本轮实际通过结构检查 {len(rows)} 条。'+ ('已形成连续前722—468年的原文年条入口。' if len(rows)==255 else '尚未完成全部255条；不得以目录齐全冒充正文齐全。')+'\n\n**文字有标点不等于内容已经校勘正确。** 原有维基文库文本、CCDH和Kanripo不覆盖；不同来源不自动投票改字。获麟后续经明确标层，传内回叙和预叙不自动改成当年事件。\n\n[导入与检查统计](audit.json) · [来源清单](manifest.json) · [原目录]('+INDEX+')\n\n| 年份 | 古史年条 |\n|---|---|\n'+table+'\n',encoding='utf-8')
    print(json.dumps(audit,ensure_ascii=False,indent=2))
    if errors:raise SystemExit(1)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=255);args=p.parse_args();run(args.limit)
