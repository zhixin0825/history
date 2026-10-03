#!/usr/bin/env python3
"""One-shot, loss-aware migration. Kept only on the temporary work branch."""
import os,re,json,subprocess,posixpath,urllib.parse,hashlib,collections,sys
from pathlib import Path
BASE='32ef7a8731e048333941ef65498a4adbef776f6b'
REFS={'main':BASE,'han':'a485252f253a5063a4f5f63175418a55f8716f76','laterhan':'1367dbae8672cc480589f11a5748b483c4f4345a','jin':'2b9716ab9562c352b9ae4a0d8d463455c4d3dae9'}
LOCAL='--local' in sys.argv
HERE=Path('/mnt/data/history_migration') if LOCAL else Path('_migration')
INPUT=HERE/'inputs' if LOCAL else HERE/'export'
if not LOCAL:
    import runpy
    runpy.run_path('_migration/audit.py')
TREES={k:json.loads((INPUT/(k+'-tree.json')).read_text()) for k in REFS}
NEW={}; MAP={}; REPORT={'base':BASE,'input_commits':REFS,'year_inputs':[],'trial_routing':[],'historical_links':[],'missing_old_links':[],'source_moves':[]}
REPO='https://github.com/zhixin0825/history'
def git(*args, input=None,env=None):
    return subprocess.check_output(['git',*args],input=input,env=env)
def read(label,p):
    f=INPUT/label/p
    if f.exists(): return f.read_bytes()
    if LOCAL: raise FileNotFoundError((label,p))
    return git('show',REFS[label]+':'+p)
def text(label,p):return read(label,p).decode('utf-8-sig')
def blob_id(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def put(p,s): NEW[p]={'content':s if isinstance(s,bytes) else s.encode('utf-8'),'mode':'100644'}
def copy(label,old,new,source=False):
    if new in NEW: raise ValueError('destination collision '+new)
    NEW[new]={'sha':TREES[label][old]['sha'],'mode':TREES[label][old]['mode'],'origin':[label,old]};MAP[(label,old)]=new
    if source: REPORT['source_moves'].append({'from':old,'to':new,'blob':NEW[new]['sha']})
def body(p):
    n=NEW[p]
    if 'content' in n:return n['content'].decode('utf-8-sig')
    return text(*n['origin'])
def fixed(label,old,frag=''):
    return REPO+'/blob/'+REFS[label]+'/'+urllib.parse.quote(old,safe='/')+('#'+frag if frag else '')
def yname(n):return ('bce-' if n<0 else 'ce-')+f'{abs(n):04d}.md'
def ynum(p):
    m=re.search(r'(bce|ce)-(\d{4})\.md$',p);return int(m[2])*(-1 if m[1]=='bce' else 1)
def ytitle(p):
    n=ynum(p);return ('公元前' if n<0 else '公元')+str(abs(n))+'年'
def anchors(s): return set(re.findall(r'\bid=[\"\x27]([^\"\x27]+)',s))
PREFIX={'texts/':'sources/二十四史/txt/','中华书局二十四史/':'sources/二十四史/中华书局/','zizhi-tongjian/kanripo/':'sources/资治通鉴/','classics/ccdh/':'sources/先秦典籍/','working-texts/zuozhuan-punctuated-years/years/':'sources/春秋左传/有标点原文/','working-texts/zuozhuan-punctuated-years/data/':'sources/春秋左传/data/'}
for old in TREES['main']:
    for pre,dst in PREFIX.items():
        if old.startswith(pre):copy('main',old,dst+old[len(pre):],source=True);break
copy('main','史记 (9).pdf','sources/参考材料/史记 (9).pdf',source=True)
KEEP={
('main','chronicle/EDITORIAL_RULES.md'):'meta/编辑规则.md',
('main','README.md'):'meta/来源说明.md',
('main','chronicle/shiji-trial/appendix/sources.md'):'sources/摘录/史记-条目原文.md',
('main','chronicle/shiji-trial/appendix/unplaced.md'):'meta/未定年材料.md',
('main','chronicle/shiji-trial/appendix/documents.md'):'meta/文献与评论.md',
('main','chronicle/shiji-trial/appendix/first-appearances.md'):'meta/人物登场说明.md',
('main','chronicle/shiji-integration/CHAPTER-066.md'):'meta/史记66-引文去向.md',
('main','chronicle/shiji-integration/CONTEXT-066.md'):'meta/伍子胥-异说与未定年.md',
('main','chronicle/shiji-integration/sources/066.md'):'sources/摘录/史记-伍子胥列传.md',
('han','chronicle/hanshu-integration/CHAPTER-001.md'):'meta/汉书1-引文去向.md',
('han','chronicle/hanshu-integration/sources/001.md'):'sources/摘录/汉书-高帝纪.md',
('laterhan','chronicle/houhanshu/CHAPTER-001.md'):'meta/后汉书1-引文去向.md',
('laterhan','chronicle/houhanshu/CONTEXT-001.md'):'meta/后汉书1-异说说明.md',
('jin','chronicle/jinshu/UNPLACED.md'):'meta/宣帝纪-未定年材料.md',
('jin','chronicle/jinshu/juan001-notes.md'):'meta/宣帝纪-归年说明.md',
}
for ruler,cn in [('zhaogong','昭公'),('dinggong','定公'),('aigong','哀公')]:
    KEEP['main',f'chronicle/chunqiu/{ruler}/SHIJI-CROSSWALK.md']=f'meta/鲁世家-{cn}段核对.md'
    r=f'chronicle/chunqiu/{ruler}/RESEARCH-NOTES.md'
    if r in TREES['main']:KEEP['main',r]=f'meta/{cn}段-考证.md'
    for p in TREES['main']:
        if p.startswith(f'chronicle/chunqiu/{ruler}/data/') and ('excerpts' in p or 'supplemental-sources' in p):
            KEEP['main',p]='sources/摘录/'+cn+'-'+Path(p).name
KEEP['main','chronicle/chunqiu/aigong/NEXT-STEPS.md']='meta/前468年后衔接说明.md'
for p in TREES['main']:
    if p.startswith('provenance/'):
        KEEP['main',p]='meta/来源材料/'+(Path(p).name if '/edition-audit-' not in p else '版本核查.md')
for key,dst in KEEP.items(): MAP[key]=dst
for label in REFS:
    for old in TREES[label]:
        if re.match(r'chronicle/.*/years/(?:bce|ce)-\d{4}\.md$',old) or re.match(r'chronicle/years/(?:bce|ce)-\d{4}\.md$',old): MAP[label,old]='years/'+Path(old).name
        if old.endswith(('/README.md','/README-01-20.md')) and old.startswith('chronicle/') and (label,old) not in KEEP:MAP[label,old]='README.md'
MAP['main','working-texts/zuozhuan-punctuated-years/README.md']='sources/春秋左传/README.md'
ALIASES={}; REVIEW=[]
def target(label,old,frag=''):
    k=(old,urllib.parse.unquote(frag))
    if k in ALIASES:return ALIASES[k]
    p=MAP.get((label,old),MAP.get(('main',old)))
    if p:return p,frag
    for pre,dst in PREFIX.items():
        if old.startswith(pre):return dst+old[len(pre):],frag
    if old.startswith('chronicle/') and old.endswith('.md') and re.search(r'(bce|ce)-\d{4}\.md$',old):return 'years/'+Path(old).name,frag
    if old in TREES[label]:
        REPORT['historical_links'].append([old,frag]);return fixed(label,old,frag),''
    if old in TREES['main']:
        REPORT['historical_links'].append([old,frag]);return fixed('main',old,frag),''
    REPORT['missing_old_links'].append([label,old,frag]);return 'README.md','unwritten'
def links(s):
    found=[];i=0
    while True:
        a=s.find('](',i)
        if a<0:break
        j=a+2;depth=1;escaped=False
        while j<len(s) and depth:
            c=s[j]
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c=='(':depth+=1
            elif c==')':depth-=1
            j+=1
        if not depth:found.append((a+2,j-1,s[a+2:j-1]));i=j
        else:i=a+2
    return found
def rewire(s,label,old,new):
    for a,b,v in reversed(links(s)):
        v0=v.strip();wrapped=v0.startswith('<') and v0.endswith('>');vv=v0[1:-1] if wrapped else v0
        mt=re.match(r'^(.*?)\s+([\"\x27].*[\"\x27])$',vv);tail=''
        if mt:vv,tail=mt[1],' '+mt[2]
        if vv.startswith(('https://','http://','mailto:','data:')):continue
        p,sep,f=vv.partition('#');p=urllib.parse.unquote(p).replace('\\(','(').replace('\\)',')')
        resolved=posixpath.normpath(posixpath.join(posixpath.dirname(old),p)) if p else old
        dest,frag=target(label,resolved,f)
        if dest.startswith('https://'):nv=dest
        else:nv=('#'+frag if dest==new and frag else posixpath.relpath(dest,posixpath.dirname(new) or '.'))+('' if dest==new and frag else ('#'+frag if frag else ''))
        if ' ' in nv:nv='<'+nv+'>'
        s=s[:a]+nv+tail+s[b:]
    return s
NAV=re.compile(r'^(?:\[|前一年|后一年|上一年|下一年).*?(?:上一|下一|前一年|后一年|回到|回读|返回|继续|年份目录|春秋目录|昭公目录|《晋书》工作入口)')
def stripnav(s):
    ls=s.splitlines();ls=[l for l in ls if not NAV.search(l)]
    s='\n'.join(ls).strip();s=re.sub(r'^> 本页为历史试编[^\n]*\n+','',s)
    s=re.sub(r'^\*\*覆盖：当前已审篇章[^\n]*\n+','',s,flags=re.M)
    s=s.replace('这一年的《晋书》增量：','本页已整理的内容：')
    s=s.replace('## 《鲁周公世家》本年对照','## 史料核对说明').replace('## 《鲁周公世家》本段对照','## 史料核对说明').replace('## 《鲁周公世家》本批对照','## 史料核对说明')
    return re.sub(r'\n{4,}','\n\n\n',s).rstrip('-\n ')+ '\n'
def ensure_numbers(s):
    marker='## 本年相关史料'
    if marker not in s:return s
    a,b=s.split(marker,1)
    ids=anchors(s)
    a=re.sub(r'^(\d+)\. \*\*',lambda m:('' if 'event-'+m[1] in ids else '<a id="event-'+m[1]+'"></a>\n\n')+m[0],a,flags=re.M)
    b=re.sub(r'^(\d+)\. \*\*',lambda m:('' if 'note-'+m[1] in ids else '<a id="note-'+m[1]+'"></a>\n\n')+m[0],b,flags=re.M)
    return a+marker+b
PRIMARY={}; ORIG={}
for label,pre in [('main','chronicle/years/'),('main','chronicle/chunqiu/years/'),('han','chronicle/years/'),('jin','chronicle/jinshu/years/')]:
    for p in TREES[label]:
        if p.startswith(pre) and re.search(r'(?:bce|ce)-\d{4}\.md$',p):
            if label=='han' and p in TREES['main'] and TREES[label][p]['sha']==TREES['main'][p]['sha']:continue
            dst='years/'+Path(p).name
            if dst in PRIMARY:raise ValueError('two primary texts '+dst)
            PRIMARY[dst]=ensure_numbers(stripnav(text(label,p)));ORIG[dst]=(label,p)
            REPORT['year_inputs'].append([label,p,dst])
legacy=[json.loads(l) for l in text('main','chronicle/shiji-integration/data/legacy-record-map-066.jsonl').splitlines()]
LEGACY={r['old_record_id']:r for r in legacy}
MATCH={
'sj-031-L2992-02':(475,3),'sj-031-L2991-01':(478,2),'sj-031-L2990-01':(481,5),'sj-031-L2988-01':(483,3),'sj-031-L2985-03':(485,2),
'sj-086-L5387-01':(515,2),'sj-086-L5388-01':(515,3),'sj-031-L2975-01':(515,3),'sj-031-L2972-01':(519,9),'sj-031-L2971-01':(522,3),
'sj-031-L2970-01':(525,6),'sj-031-L2968-01':(527,1),'sj-031-L2967-01':(529,4),'sj-031-L2964-04':(536,8),'sj-031-L2964-03':(537,10),
'sj-031-L2964-02':(538,4),'sj-031-L2964-01':(541,13),'sj-031-L2951-01':(584,6),'sj-031-L2948-02':(655,7),'sj-062-L4595-01':(656,2),
'sj-062-L4595-02':(664,7),'sj-062-L4595-03':(681,3),'sj-062-L4591-02':(685,5),'sj-062-L4593-01':(685,5),'sj-042-L3772-01':(722,3)}
NOTE_ONLY={'sj-031-L2965-01','sj-031-L2985-02','sj-042-L3772-02'}
BLOCKS=[]; BACK=[]
pat=re.compile(r'(?P<anchors>(?:<a id="[^"]+"></a>\s*)+)### (?P<title>\d+\. [^\n]+)\n')
for p in sorted(TREES['main']):
    if not p.startswith('chronicle/shiji-trial/years/') or not p.endswith('.md'):continue
    s=stripnav(text('main',p)); ms=list(pat.finditer(s));name=Path(p).name;dst='years/'+name
    for i,m in enumerate(ms):
        stop=ms[i+1].start() if i+1<len(ms) else len(s)
        chunk=s[m.start():stop].rstrip();chunk=re.split(r'\n---\s*\n',chunk)[0].rstrip()
        chunk=re.sub(r'\n\[人物背景与未确年材料\][\s\S]*$','',chunk)
        ids=re.findall(r'id="([^"]+)"',m['anchors']);title=re.sub(r'^\d+\. ','',m['title'])
        BLOCKS.append({'old':p,'dst':dst,'ids':ids,'title':title,'chunk':chunk})
    REPORT['year_inputs'].append(['main',p,dst])
    if dst not in PRIMARY:
        PRIMARY[dst]='# '+ytitle(dst)+'｜年度记事\n\n';ORIG[dst]=('main',p)
ADDITIONS=collections.defaultdict(list); NOTEADDS=collections.defaultdict(list); EVENTADDS=collections.defaultdict(list)
def choose_legacy(r):
    ds=r['destinations'];oldy=r['old_year_bce']
    d=next((d for d in ds if oldy and d['path'].endswith(yname(-oldy))),ds[0]);return target('main',d['path'],d['anchor'])
for r in legacy:
    d,f=choose_legacy(r)
    for old in ['chronicle/shiji-trial/years/'+yname(-r['old_year_bce'])] if r['old_year_bce'] else []:ALIASES[old,r['old_record_id']]=(d,f)
def annotate(kind,b,dst,anchor):
    REPORT['trial_routing'].append({'old_path':b['old'],'old_ids':b['ids'],'action':kind,'destination':dst,'anchor':anchor})
    for a in b['ids']:ALIASES[b['old'],a]=(dst,a)
    for a in b['ids']:
        if a not in anchors(PRIMARY.get(dst,'')):NOTEADDS[dst,anchor].append('<a id="'+a+'"></a>')
for b in BLOCKS:
    g=b['ids'][0];match=next((LEGACY[i] for i in b['ids'] if i in LEGACY),None)
    if match:
        dst,a=choose_legacy(match);annotate('already_integrated_keep_corrected_date',b,dst,a)
        bs=re.search(r'(<a id="backstory-[^"]+"></a>\s*#### 登场前事[\s\S]*?)(?=<!-- backstory-end:|\Z)',b['chunk'])
        if bs:
            aid=re.search(r'id="([^"]+)"',bs[1])[1]
            if aid=='backstory-sj-066-L4660-01':NOTEADDS[dst,a].append('<a id="'+aid+'"></a>')
            else:
                loc='years/'+Path(b['old']).name;dest_anchor=a.replace('note-','event-')
                if loc==dst:EVENTADDS[loc,dest_anchor].append(('main',b['old'],bs[1]))
                else:EVENTADDS[dst,dest_anchor].append(('main',b['old'],bs[1]))
            ALIASES[b['old'],aid]=(dst,aid)
        continue
    if g in MATCH:
        year,no=MATCH[g];dst='years/'+yname(-year);a='note-'+str(no);annotate('same_event_add_source_note',b,dst,a)
        c=b['chunk'];bs=re.search(r'(<a id="backstory-[^"]+"></a>\s*#### 登场前事[\s\S]*?)(?=<!-- backstory-end:|\Z)',c)
        if bs:
            EVENTADDS[dst,'event-'+str(no)].append(('main',b['old'],bs[1]));c=c.replace(bs[1],'');aid=re.search(r'id="([^"]+)"',bs[1])[1];ALIASES[b['old'],aid]=(dst,aid)
        c=re.sub(r'^(?:<a id="[^"]+"></a>\s*)+','',c)
        c=re.sub(r'^### \d+\. [^\n]+','#### 补充互见｜'+b['title'],c)
        NOTEADDS[dst,a].append(('main',b['old'],c));continue
    dst=b['dst'];a=g
    if g in NOTE_ONLY:
        NOTEADDS[dst,'__end__'].append(('main',b['old'],b['chunk'].replace('### ','### 年次与异说｜',1)))
        REPORT['trial_routing'].append({'old_path':b['old'],'old_ids':b['ids'],'action':'retain_chronology_dispute_in_notes_not_duplicate_event','destination':dst,'anchor':g})
        for z in b['ids']:ALIASES[b['old'],z]=(dst,z)
    elif dst in ['years/bce-0208.md'] and g in ['sj-048-L4222-01','sj-048-L4223-02']:
        NOTEADDS[dst,'__end__'].append(('main',b['old'],b['chunk'].replace('### ','### 补充互见｜',1)))
        REPORT['trial_routing'].append({'old_path':b['old'],'old_ids':b['ids'],'action':'same_event_source_note_han','destination':dst,'anchor':g})
    else:
        ADDITIONS[dst].append(('main',b['old'],b['chunk']))
        REPORT['trial_routing'].append({'old_path':b['old'],'old_ids':b['ids'],'action':'retain_distinct_event','destination':dst,'anchor':g})
lhp='chronicle/houhanshu/BATCH-001.md';lh=text('laterhan',lhp)
foot=lh[lh.index('[^hh-3]:'):];defs={m[1]:m[0] for m in re.finditer(r'^\[\^([^]]+)\]:[^\n]*(?:\n(?!\[\^)[^\n]+)*',foot,re.M)}
pre=lh[lh.index('## 刘秀第一次登场以前'):lh.index('## 22年')]
ms=list(re.finditer(r'^## (2[2-5])年：([^\n]+)',lh,re.M))
for i,m in enumerate(ms):
    stop=ms[i+1].start() if i+1<len(ms) else lh.index('\n---',m.start());part=lh[m.start():stop].strip()
    if m[1]=='22':part=pre+'\n'+part
    used=set(re.findall(r'\[\^([^]]+)\]',part));missing=used-set(defs)
    if missing:raise ValueError(('footnotes',missing))
    part += '\n\n## 原文与出处\n\n'+'\n\n'.join(defs[k] for k in defs if k in used)
    dst='years/'+yname(int(m[1]));PRIMARY[dst]='# '+ytitle(dst)+'｜'+m[2]+'\n\n'+part+'\n';ORIG[dst]=('laterhan',lhp)
    REPORT['year_inputs'].append(['laterhan',lhp+'#'+m[1],dst])
for dst in PRIMARY:
    s=PRIMARY[dst]
    lab,old=ORIG[dst];s=rewire(s,lab,old,dst)
    def render(x):return x if isinstance(x,str) else rewire(x[2],x[0],x[1],dst)
    for (d,a),items in list(EVENTADDS.items()):
        if d!=dst:continue
        token='<a id="'+a+'"></a>';start=s.find(token)
        if start<0:raise ValueError(('event target missing',dst,a))
        rest=s[start+len(token):];n=re.search(r'\n<a id="event-\d+"|\n## ',rest);end=start+len(token)+(n.start() if n else len(rest))
        ins='\n\n'+'\n\n'.join(render(x) for x in items)+'\n\n';s=s[:end]+ins+s[end:]
    if ADDITIONS[dst]:
        ins='\n\n## 本年其他已整理纪事\n\n'+'\n\n'.join(render(x) for x in ADDITIONS[dst])+'\n\n'
        m=re.search(r'^## (?:本年相关史料|原文与出处|史料核对说明)',s,re.M);pos=m.start() if m else len(s);s=s[:pos]+ins+s[pos:]
    for (d,a),items in list(NOTEADDS.items()):
        if d!=dst:continue
        ins='\n\n'+'\n\n'.join(render(x) for x in items)+'\n\n'
        ids=anchors(s);ins=re.sub(r'<a id="([^"]+)"></a>',lambda m:'' if m[1] in ids else m[0],ins)
        if a=='__end__':s+='\n## 补充史料与归年说明\n'+ins;continue
        token='<a id="'+a+'"></a>';start=s.find(token)
        if start<0:raise ValueError(('note target missing',dst,a))
        rest=s[start+len(token):];n=re.search(r'\n<a id="note-\d+"|\n## ',rest);end=start+len(token)+(n.start() if n else len(rest));s=s[:end]+ins+s[end:]
    s=s.replace('｜逐年读《史记》','｜年度记事')
    put(dst,s)
p='years/bce-0209.md';s=body(p)
sections=list(re.finditer(r'^## ([^\n]+)\n',s,re.M))
parts={m[1]:s[m.start():sections[i+1].start() if i+1<len(sections) else len(s)] for i,m in enumerate(sections)}
intro=s[:sections[0].start()]
background=parts['登场前事：先认识还叫“刘季”的刘邦']
setup=parts['七月以后，反秦已经不是一处地方的乱子'].split('\n\n')
summary=setup[1];peixian='\n\n'.join(setup[2:]).strip()
county=parts['县令反悔，事情反而把刘邦推到了前台'].split('\n',1)[1]
regional=parts['同一个月，项梁、田儋等人也都起来了'].split('\n',1)[1]
revolt=parts['本年其他已整理纪事'].replace('## 本年其他已整理纪事','## 七月至九月：陈胜、吴广起兵，各地相继响应',1)
sources=parts['原文与出处'];sources += '\n\n### 两批材料原有概述与互见\n\n'+summary+'\n\n'+regional
put(p,intro+revolt+'\n'+background+'\n## 九月：沛县从响应起事到推举沛公\n\n'+peixian+'\n\n'+county+'\n'+sources)
p='years/bce-0208.md';put(p,body(p).replace('## 本年其他已整理纪事','## 陈地及各国的战事'))
for (label,old),dst in KEEP.items():
    raw=read(label,old)
    if dst.endswith('.md'):put(dst,rewire(raw.decode('utf-8-sig'),label,old,dst))
    else:put(dst,raw)
for (dst,a),items in NOTEADDS.items():
    if dst in PRIMARY:continue
    if dst not in NEW:raise ValueError(('metadata destination missing',dst))
    s=body(dst);tags=[x for x in items if isinstance(x,str) and re.search(r'id="([^"]+)"',x)[1] not in anchors(s)]
    token='<a id="'+a+'"></a>'
    if token not in s:raise ValueError(('metadata anchor missing',dst,a))
    put(dst,s.replace(token,'\n'.join(tags)+'\n'+token,1))
over=body('meta/来源说明.md')
for pre,new in PREFIX.items():over=over.replace('`'+pre,'`'+new)
over=over.replace('# 中国古籍 TXT 语料','# 史料来源、版本与许可');put('meta/来源说明.md',over)
rules=body('meta/编辑规则.md')
put('meta/编辑规则.md','# 唯一编年正文与编辑规则\n\n**所有正式叙事只写入根目录 `years/`，同一年只能有一个 Markdown 文件。书名只标识来源，不是项目、目录层级或另一套年表。**\n\n`sources/` 保存史料；`meta/` 只保存来源、考证、归年和编写规则。不要重新建立 scripts、tests、working-texts、按史书分开的年份目录或长期生成流程。增量资料应先找既有年份和事件再补写；不得用旧分支的生成器重建整页。\n\n'+rules)
put('sources/春秋左传/README.md','# 《春秋》《左传》史料原文\n\n本目录只保存有标点的古籍原文和原采集记录，不是另一套白话编年史。\n\n[有标点原文](有标点原文/) · [采集与分段记录](data/) · [唯一的编年正文目录](../../README.md#year-list)\n\n文字来自原仓库已保存的古诗文网／古文岛年条，经、传、续经分层；不是中华书局或杨伯峻授权电子文本。文件字节保持迁移前原样。JSON中的原路径、下载时间及哈希是历史采集记录；旧路径变更见[迁移说明](../../meta/迁移说明.md)。不保留网页响应缓存、重复清洗输出或生成程序。\n')
put('sources/README.md','# 史料\n\n这里放书和实际引用的原文，不放独立的“某书编年史”。\n\n- [二十四史 TXT](二十四史/txt/) 与 [中华书局点校本](二十四史/中华书局/)\n- [《资治通鉴》原文及胡三省注](资治通鉴/)\n- [先秦典籍](先秦典籍/) 与 [《春秋》《左传》有标点原文](春秋左传/)\n- [已引用的原文摘录](摘录/) 与 [参考材料](参考材料/)\n\n[版本、来源与许可](../meta/来源说明.md) · [逐年阅读](../README.md#year-list)\n')
sha=text('main','SHA256SUMS.txt')
for pre,new in PREFIX.items():sha=re.sub(r'(?m)([a-f0-9]{64}  )'+re.escape(pre),lambda m:m[1]+new,sha)
put('meta/SHA256SUMS.txt',sha)
put('.gitattributes','sources/** -text\nmeta/** text eol=lf\nyears/*.md text eol=lf\nREADME.md text eol=lf\n')
YEARS=sorted(PRIMARY,key=ynum)
for i,p in enumerate(YEARS):
    prev=YEARS[i-1] if i else None;nxt=YEARS[i+1] if i+1<len(YEARS) else None
    nav=('['+'← 上一张已编年页：'+ytitle(prev)+']('+Path(prev).name+') · ' if prev else '')+'[总目录](../README.md#year-list)'+(' · [下一张已编年页：'+ytitle(nxt)+' →]('+Path(nxt).name+')' if nxt else '')
    s=body(p);first,sep,tail=s.partition('\n');s=first+'\n\n'+nav+'\n\n'+tail.strip()+'\n\n---\n\n'+nav+'\n';put(p,s)
readme='# 逐年读史\n\n**只按年份组织历史，一年一个页面。** 同一事件的《春秋》《左传》《史记》《汉书》《后汉书》《晋书》《资治通鉴》等材料在同页合并；不同说法留在对应史料说明，不再按史书开平行年表。\n\n```text\nhistory/\n├── sources/  史书、版本和实际引用的原文\n├── years/    唯一的逐年 Markdown 正文\n├── meta/     来源说明、编辑规则、归年与考证\n└── README.md 年份总目录\n```\n\n[史料](sources/README.md) · [编写规则与来源说明](meta/README.md) · [本次迁移核对](meta/迁移说明.md)\n\n现有 **'+str(len(YEARS))+'** 个不同年份页。页数表示已有材料，不等于每年全部史事或所有史书已经整理完毕。导航中的“上一张／下一张”只指已编页面，不表示相邻公历年；古历年条仍保留原来的归年口径。\n\n<a id="unwritten"></a>\n## 尚未编写与复核边界\n\n目录中没有的年份不造空页。此次合并 main 及汉书、后汉书、晋书三条首批工作分支；其他历史分支不覆盖当前正文。原主线所记的襄公复核缺口、旧年次争议及未确年材料仍保留，不把目录整理宣称为内容补全。\n\n<a id="year-list"></a>\n## 年份目录\n\n| 年份 | 本页开头 |\n|---|---|\n'
for p in YEARS:
    h=body(p).splitlines()[0].lstrip('# ');h=h.replace('|','｜');readme+='| ['+ytitle(p)+']('+p+') | '+h+' |\n'
put('README.md',readme)
metafiles=[p for p in NEW if p.startswith('meta/') and p.endswith('.md') and p!='meta/README.md']
put('meta/README.md','# 编写依据\n\n这里只保存来源、许可、版本核查、归年依据和无法硬定年份的材料；不放第二套年度正文，也不保存一次性生成器和缓存。\n\n[返回唯一年份目录](../README.md#year-list) · [编辑规则](编辑规则.md) · [来源与许可](来源说明.md) · [迁移说明](迁移说明.md)\n\n'+ '\n'.join('- ['+Path(p).stem+']('+posixpath.relpath(p,'meta')+')' for p in sorted(metafiles) if p not in ['meta/编辑规则.md','meta/来源说明.md'])+'\n')
REPORT['unique_years']=len(YEARS);REPORT['root_directories']=['meta','sources','years'];REPORT['primary_year_pages']=len(PRIMARY)
REPORT['trial_action_counts']=dict(collections.Counter(x['action'] for x in REPORT['trial_routing']))
REPORT['source_blob_count']=len(REPORT['source_moves']);REPORT['deleted_process_directories']=['.github','scripts','tests','working-texts','chronicle','provenance','texts','classics','zizhi-tongjian','中华书局二十四史']
route='\n'.join('| `'+r['old_path']+'#'+r['old_ids'][0]+'` | '+r['action']+' | ['+r['destination']+'#'+r['anchor']+'](../'+r['destination']+'#'+r['anchor']+') |' for r in REPORT['trial_routing'])
put('meta/迁移说明.md','# 三目录重整与内容核对\n\n## 范围\n\n原 main：`'+BASE+'`。并入三条首批分支：\n\n'+'\n'.join('- '+k+'：`'+v+'`' for k,v in REFS.items() if k!='main')+'\n\n最终只保留 `sources/`、`years/`、`meta/` 三个内容目录，另有根 README 与防止原文换行被转换的 `.gitattributes`。正式年度正文 '+str(len(YEARS))+' 页；没有按史书另建年份目录。22—25年多年份审读稿已拆入四张全局页。\n\n## 保全方式\n\n原始语料与PDF通过Git对象原样移动，共 '+str(REPORT['source_blob_count'])+' 个来源文件；不重新扫描、不重新编码。正在被引用的有标点原文及采集记录归入 sources；未被采用的响应缓存、重复清洗产物、旧生成脚本和 workflow 不进入新结构。\n\n较新的主年页正文优先保留。旧试编已有明确整合映射的条目只保留现有正确落点和旧标识，不恢复旧错误年份；其余同一事件的互见材料放入该事件史料说明，独有事件进入唯一同年页。改目录不等于重做了所有历史考证。\n\n完整旧稿、旧脚本和一次性审计仍可从迁移前提交查阅，不在当前目录再复制一份。书源核对文件保留书名是为了识别引文来源，不是另一个编年项目。\n\n## 原目录去向\n\n| 旧目录 | 新位置／处理 |\n|---|---|\n| texts | sources/二十四史/txt |\n| 中华书局二十四史 | sources/二十四史/中华书局 |\n| zizhi-tongjian/kanripo | sources/资治通鉴 |\n| classics/ccdh | sources/先秦典籍 |\n| working-texts/zuozhuan-punctuated-years 的原文年条、data | sources/春秋左传 |\n| chronicle 下各套年份页 | years，重名按事件合并 |\n| 原文摘录 | sources/摘录 |\n| 来源、版本、归年、考证 | meta |\n| 脚本、测试、workflow、重复缓存、旧进度看板 | 从当前树删除，Git历史可追溯 |\n\n## 旧试编条目去向\n\n| 旧位置与标识 | 处理 | 当前落点 |\n|---|---|---|\n'+route+'\n')
def norm(s):
    for a,b,_ in reversed(links(s)):s=s[:a]+s[b:]
    s=re.sub(r'<[^>]+>','',s)
    return ''.join(re.findall(r'[\u3400-\u9fffA-Za-z0-9]',s))
conservation=[];paragraph_count=0
for dst,(lab,old) in ORIG.items():
    if '/shiji-trial/years/' in old or lab=='laterhan':continue
    before=stripnav(text(lab,old));after=norm(body(dst))
    for par in re.split(r'\n\s*\n',before):
        if par.lstrip().startswith(('#','<a','<!--')):continue
        n=norm(par)
        if len(re.findall(r'[\u3400-\u9fff]',n))<8:continue
        paragraph_count+=1
        if n not in after:conservation.append([old,dst,par[:200]])
alias_errors=[];old_anchor_count=0
for lab,old,dst in REPORT['year_inputs']:
    if '#' in old:continue
    for a in anchors(text(lab,old)):
        old_anchor_count+=1;d,f=target(lab,old,a)
        if d not in NEW or f not in anchors(body(d)):alias_errors.append([lab,old,a,d,f])
REPORT['primary_paragraphs_checked']=paragraph_count
REPORT['primary_paragraphs_missing']=conservation
REPORT['old_year_anchors_checked']=old_anchor_count
REPORT['old_year_anchor_errors']=alias_errors
def slug(t):
    t=re.sub(r'<[^>]+>','',t);t=re.sub(r'!?(\[([^]]+)\])\([^)]*\)',r'\2',t);t=t.replace('`','').replace('*','');t=re.sub(r'[^\w\-\s\u4e00-\u9fff]','',t.lower());return t.replace(' ','-')
def allanchors(s):
    out=anchors(s);counts=collections.Counter()
    for h in re.findall(r'^#{1,6}\s+(.+)',s,re.M):
        a=slug(h);n=counts[a];counts[a]+=1;out.add(a if not n else a+'-'+str(n))
    return out
errors=[['paragraph_conservation',*e] for e in conservation]+[['old_anchor_relocation',*e] for e in alias_errors];checked=0;raw_md_checked=0
for p,n in NEW.items():
    if not p.endswith('.md'):continue
    if 'content' not in n and LOCAL:continue
    s=body(p)
    ids=re.findall(r'\bid=[\"\x27]([^\"\x27]+)',s)
    if len(ids)!=len(set(ids)):errors.append(['duplicate_ids',p,[a for a,c in collections.Counter(ids).items() if c>1]])
    for _,_,u in links(s):
        u=u.strip('<>')
        if re.match(r'^\w+:',u):continue
        u=u.replace('\\(','(').replace('\\)',')');path,_,frag=u.partition('#');path=urllib.parse.unquote(path)
        dest=posixpath.normpath(posixpath.join(posixpath.dirname(p),path)) if path else p
        checked+=1
        if dest not in NEW and not any(q.startswith(dest.rstrip('/')+'/') for q in NEW):errors.append(['missing_path',p,u,dest]);continue
        if frag and dest in NEW and dest.endswith('.md'):
            if LOCAL and 'content' not in NEW[dest]:continue
            if urllib.parse.unquote(frag) not in allanchors(body(dest)):errors.append(['missing_anchor',p,u,dest])
    if 'content' not in n:raw_md_checked+=1
assert {p.split('/')[0] for p in NEW if '/' in p}=={'sources','years','meta'}
assert all(re.fullmatch(r'years/(?:bce|ce)-\d{4}\.md',p) for p in NEW if p.startswith('years/'))
assert not any('/years/' in p for p in NEW if not p.startswith('years/'))
assert not any(p.endswith(('.py','.pyc','.yml','.yaml')) for p in NEW)
assert len({ynum(p) for p in YEARS})==len(YEARS) and not any(ynum(p)==0 for p in YEARS)
for r in REPORT['source_moves']:
    assert NEW[r['to']].get('sha')==r['blob'],r
REPORT['relative_links_checked']=checked;REPORT['raw_source_markdown_checked']=raw_md_checked;REPORT['validation_errors']=len(errors)
REPORT['output_files']=len(NEW)
(HERE/'validation-errors.json').write_text(json.dumps(errors,ensure_ascii=False,indent=2))
(HERE/'result-summary.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2))
if LOCAL:
    out=HERE/'result';out.mkdir(exist_ok=True)
    for p,n in NEW.items():
        if 'content' in n:
            f=out/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(n['content'])
    print(json.dumps({k:REPORT[k] for k in ['unique_years','source_blob_count','trial_action_counts','relative_links_checked','validation_errors','output_files']},ensure_ascii=False,indent=2));print('Errors:',errors[:20]);sys.exit(bool(errors))
if errors:raise RuntimeError(json.dumps(errors[:20],ensure_ascii=False))
idx=str(Path(os.environ['RUNNER_TEMP'])/'history-unified-index');env=os.environ.copy();env['GIT_INDEX_FILE']=idx
try:Path(idx).unlink()
except FileNotFoundError:pass
git('read-tree','--empty',env=env)
rows=[]
for p,n in sorted(NEW.items()):
    sha=n.get('sha') or git('hash-object','-w','--stdin',input=n['content']).decode().strip();rows.append(n['mode']+' '+sha+'\t'+p+'\0')
git('update-index','-z','--index-info',input=''.join(rows).encode(),env=env)
tree=git('write-tree','--missing-ok',env=env).decode().strip()
remote=git('ls-remote','origin','refs/heads/work/unified-history-result').decode().split()
if remote:
    prior=remote[0];git('fetch','--filter=blob:none','--depth=1','origin',prior);parents=['-p',prior]
else:parents=sum((['-p',v] for v in REFS.values()),[])
commit=git('commit-tree',tree,*parents,input='Unify chronology into sources, years and meta; preserve source blobs and merge year overlaps\n'.encode()).decode().strip()
git('push','origin',commit+':refs/heads/work/unified-history-result')
REPORT['result_commit']=commit;REPORT['result_tree']=tree
(HERE/'result-summary.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2))
print(json.dumps({k:REPORT[k] for k in ['result_commit','result_tree','unique_years','source_blob_count','relative_links_checked','validation_errors','output_files']},ensure_ascii=False,indent=2))
