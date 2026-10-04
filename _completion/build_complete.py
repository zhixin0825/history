#!/usr/bin/env python3
"""One-shot Spring/Autumn completion. Final tree contains no build tools."""
from pathlib import Path
import json,re,os,sys,subprocess,posixpath,collections,urllib.parse,hashlib
LOCAL='--local' in sys.argv
W=Path('/mnt/data/chunqiu_complete') if LOCAL else Path('_completion')
BASE='db58207ff8cb4cbd6f3a8bb385ad19d0d6e9ed41'
OLD='604211235a7cc43c755a6e5cd55f519a999a9aa9'
REF='work/complete-chunqiu-result-20261004'
C=W/'input/current'
def git(*a,input=None,env=None):return subprocess.check_output(['git',*a],input=input,env=env)
def tree(ref):
 d={}
 for r in git('ls-tree','-rz',ref).split(b'\0'):
  if r:
   m,p=r.split(b'\t',1);mode,kind,sha=m.decode().split();d[p.decode()]={'mode':mode,'type':kind,'sha':sha}
 return d
T=json.loads((C/'tree.json').read_text()) if LOCAL else tree(BASE)
CACHE={}
def oldtext(p,ref=BASE):
 key=(ref,p)
 if key in CACHE:return CACHE[key]
 if LOCAL:
  f=(C if ref==BASE else W/'input/xiang_review')/p
  s=f.read_text(encoding='utf-8-sig')
 else:s=git('show',ref+':'+p).decode('utf-8-sig')
 CACHE[key]=s;return s
OUT={};MOD={};AUDIT={'base':BASE,'xiang_input':OLD,'annual_before':0,'events':{},'patches':[],'replaced':[],'preserved_shiji':[]}
def put(p,s):OUT[p]=s.rstrip()+'\n'
def text(p):return OUT[p] if p in OUT else oldtext(p)
def mdpath(y):
 high=((y-1)//100+1)*100;return f'years/bce-{high:04d}-{high-99:04d}/bce-{y:04d}.md'
def srcpath(y):return f'sources/春秋左传/有标点原文/bce-{y:04d}.md'
def link(old,new,frag=''):return posixpath.relpath(new,posixpath.dirname(old))+('#'+frag if frag else '')
def ids(s):return re.findall(r'\bid=[\"\x27]([^\"\x27]+)',s)
def norm(s):
 s=re.sub(r'<[^>]+>','',s)
 return ''.join(re.findall(r'[\u3400-\u9fffA-Za-z0-9]',s))
D={};DP={}
for p in T:
 if re.fullmatch(r'sources/春秋左传/data/zz-\d{2}-\d{2}\.json',p):
  d=json.loads(oldtext(p));D[d['year_bce']]=d;DP[d['year_bce']]=p
assert set(D)==set(range(468,723))
def paras(y,k):return next(x['text'] for x in D[y]['layers'] if x['kind']=={'j':'jing','t':'zhuan'}[k]).split('\n\n')
def add_source_anchors(y):
 p=srcpath(y);s=text(p)
 for k in ('j','t'):
  ps=paras(y,k)
  for n,raw in enumerate(ps,1):
   aid=f'{k}{n:03}'
   if aid in ids(s):continue
   start=s.find('## 经') if k=='j' else s.find('## 传')
   assert start>=0,(y,k,'layer')
   at=s.find(raw,start);assert at>=0,(y,k,n,raw[:30])
   s=s[:at]+f'<a id="{aid}"></a>\n\n'+s[at:]
 assert norm(s)==norm(oldtext(p)),('source text changed',p)
 put(p,s)
B={}
for f in ['01-06.json','07-12.json','13-18.json','19-24.json','25-28.json']:
 B.update(json.loads(oldtext('chronicle/chunqiu/review/xiang-gong/batches/'+f,OLD)))
routing=json.loads(oldtext('chronicle/chunqiu/review/xiang-gong/routing.json',OLD))
for n in routing:B[n].update(routing[n])
for n,c in json.loads(oldtext('chronicle/chunqiu/review/xiang-gong/corrections.json',OLD)).items():
 for k,v in c.get('replace_entries',{}).items():B[n]['entries'][int(k)-1]=v
 for v in c.get('append_entries',[]):B[n]['entries'].append(v)
B.update(json.loads((W/'tail.json').read_text()))
MUSIC=json.loads((W/'music.json').read_text())
PATCH=json.loads((W/'outside_patches.json').read_text())
def dest(v):
 if isinstance(v,int):return [v]
 if isinstance(v,dict):return [v['note']]
 return v
for n in range(1,32):
 b=B[str(n)];y=573-n
 for k in ('j','t'):
  assert len(b[k])==len(paras(y,k)),(n,k)
  for v in b[k]:assert v and all(1<=e<=len(b['entries']) for e in dest(v)),(n,k,v)
 add_source_anchors(y)
MERGE={570:{'sj-031-L2951-02':1},561:{'sj-031-L2952-01':3},560:{'sj-031-L2954-01':6},557:{'sj-031-L2954-02':1},548:{'sj-062-L4604-01':4,'sj-031-L2955-01':18},545:{'sj-031-L2957-01':13},544:{'sj-031-L2958-01':12,'sj-031-L2958-02':12,'sj-031-L2959-01':13,'sj-031-L2960-01':13,'sj-031-L2961-01':14,'sj-031-L2962-01':14}}
OLDNOTES=collections.defaultdict(list)
for y,amap in MERGE.items():
 p=mdpath(y);s=oldtext(p)
 marks=list(re.finditer(r'<a id="(sj-[^"]+)"></a>\s*\n### ([^\n]+)\n',s))
 for i,m in enumerate(marks):
  end=marks[i+1].start() if i+1<len(marks) else s.find('\n---',m.end())
  if end<0:end=len(s)
  chunk=s[m.start():end].strip();aid=m[1];assert aid in amap,(y,aid)
  chunk=re.sub(r'### \d+\. (.*)',r'#### 《史记》互见｜\1',chunk,count=1)
  if y==560:
   chunk='''<a id="sj-031-L2954-01"></a>
#### 让位年次与吴楚交战的分离

旧稿按《吴太伯世家》诸樊元年，将除丧让季札、季札以子臧为例拒位、离家耕田，以及秋吴攻楚一并归在前560年。《左传》却把诸樊让位放在襄公十四年春，即前559年；吴楚庸浦之战仍在本年。让位过程的正文现在见[前559年同一事件](bce-0559.md#event-3)，不在两个年份重复发生。

[《史记》原有引文](../../sources/摘录/史记-条目原文.md#ref-sj-2954) · [原有归年对读](../../sources/摘录/史记-条目原文.md#ref-zz-9-13)
'''
  elif y==570:chunk='**称谓说明：**《左传》记楚子重、婴齐领兵；《史记》按楚共王年次述攻吴，不因此推定楚王本人必定亲征。\n\n'+chunk
  elif y==557:chunk='**年次说明：**晋悼公去世与接立在前558年，前557年是平公元年；即位动作与逾年纪元不混成同一日。\n\n'+chunk
  elif y==545:chunk='**跨年说明：**逃奔吴国、受邑与日后致富是一个人物去向的连续叙事，后来的家财规模不全算作本年取得。\n\n'+chunk
  OLDNOTES[y,amap[aid]].append(chunk)
  AUDIT['preserved_shiji'].append({'year':y,'id':aid,'event':amap[aid]})
assert '婴齐' in B['3']['entries'][0][0]
assert '庸浦' in B['13']['entries'][5][0]
for y,d in MERGE.items():
 b=B[str(573-y)]
 for aid,e in d.items():assert e<=len(b['entries']),(y,e)
CROSS_EXTRA={(559,3):'《史记》以诸樊元年系让位，《左传》明列在本年春。参见[前560年保留的年差说明](bce-0560.md#sj-031-L2954-01)。季札以子臧为例、离家耕田属于同一次让位叙事。',(544,14):'卫国朋友名单中，公开工作源一字以私用区字符显示（史）；缺字原样可查，没有假称已完成点校。'}
COVER=[]
for n in range(1,32):
 y=573-n;b=B[str(n)];p=mdpath(y);count=len(b['entries']);AUDIT['events'][str(y)]=count
 s=f'# 公元前{y}年（鲁襄公{n}年）\n\n'
 s+='> 本页合并本年《春秋》《左传》及已核《史记》互见；月份沿用古史年条。回叙、后续与作者评论在相应史料注中区分，不据叙述位置强造发生年。\n\n## 本年纪事\n\n'
 for e,(h,detail) in enumerate(b['entries'],1):
  s+=f'<a id="event-{e}"></a>\n\n{e}. **{h}** {detail} [看原文与说明](#note-{e})\n\n'
  if n==29 and e==12:
   s+='<details>\n<summary>季札观乐：各组歌诗与乐舞的评语</summary>\n\n以下都是季札在传文中的看法，不是本编年史对国家或人物所作的优劣排序。歌诗与乐舞按原叙事先后列出，未给郐以下补造评语。\n\n| 歌诗或乐舞 | 季札的评语大意 |\n|---|---|\n'
   for a,v in MUSIC:s+=f'| {a} | {v} |\n'
   s+='\n[本段完整原文]('+link(p,srcpath(y),'t014')+')\n\n</details>\n\n'
 s+='## 本年相关史料\n\n'+f'[本年经传原文]({link(p,srcpath(y))}) · [原始采集记录]({link(p,DP[y])}) · [逐段去向]({link(p,"meta/记录/春秋-襄公-经传去向.md","year-"+str(y))})\n\n'
 printed={}
 for e,(h,detail) in enumerate(b['entries'],1):
  s+=f'<a id="note-{e}"></a>\n<a id="source-{e}"></a>\n### {e}. {h.rstrip("。")}\n\n'
  note=b.get('notes',{}).get(str(e),'')
  if note:s+='**说明：**'+note+'\n\n'
  why=[]
  for k in ('j','t'):
   for i,v in enumerate(b[k],1):
    if isinstance(v,dict) and v['note']==e:why.append(v['reason'])
  if why:s+='**段落层次：**'+' '.join(why)+'\n\n'
  for k in ('j','t'):
   ps=paras(y,k)
   for i,v in enumerate(b[k],1):
    if e not in dest(v):continue
    key=(k,i);label=('《春秋》经' if k=='j' else '《左传》传')+f' {k.upper()}{i:03}'
    url=link(p,srcpath(y),f'{k}{i:03}');COVER.append([y,k,i,e,'注释' if isinstance(v,dict) else '正文及注'])
    if key in printed:s+=f'[{label}完整原文]({url})；本页引文共用[第{printed[key]}条史料](#note-{printed[key]})。\n\n';continue
    printed[key]=e
    s+=f'<details>\n<summary>{label}｜原文</summary>\n\n'+'\n'.join('> '+l for l in ps[i-1].splitlines())+f'\n\n[回到原文位置]({url})\n\n</details>\n\n'
  if (y,e) in CROSS_EXTRA:s+='**互见：**'+CROSS_EXTRA[y,e]+'\n\n'
  if OLDNOTES[y,e]:s+='\n\n'.join(OLDNOTES[y,e])+'\n\n'
 put(p,s)
def event_span(s,e):
 start=s.find(f'<a id="event-{e}"></a>');assert start>=0,('event missing',e)
 candidates=[m.start() for m in re.finditer(r'<a id="event-\d+"></a>|^## ',s,re.M) if m.start()>start]
 end=min(candidates) if candidates else len(s);return start,end
def source_note(o,e):
 y=o['year'];p=mdpath(y);s=f'<a id="cq-source-{e}"></a>\n### 核对{e}｜{o["heading"].rstrip("。")}\n\n'
 if o['note']:s+='**说明：**'+o['note']+'\n\n'
 for k,n in o['refs']:
  raw=paras(y,k)[n-1];s+=f'<details>\n<summary>{"经" if k=="j" else "传"} {k.upper()}{n:03}｜原文</summary>\n\n'+'\n'.join('> '+l for l in raw.splitlines())+f'\n\n[本段出处]({link(p,srcpath(y),k+str(n).zfill(3))})\n\n</details>\n\n'
 return s
PATCH_NOTES=collections.defaultdict(list)
for i,o in enumerate(PATCH['ops'],1):
 y=o['year'];p=mdpath(y);s=text(p);add_source_anchors(y)
 h,d=o['heading'],o['detail'];endlink=f' [看原文与说明](#cq-source-{i})'
 if o['into'] is None:
  es=[int(n) for n in re.findall(r'<a id="event-(\d+)"></a>',s)];e=max(es)+1
  at=s.find('## 本年相关史料');assert at>=0,('notes section',y)
  new=f'<a id="event-{e}"></a>\n\n{e}. **{h}** {d}{endlink}\n\n'
  s=s[:at]+new+s[at:];o['assigned_event']=e
 else:
  e=o['into'];start,end=event_span(s,e);part=s[start:end]
  if o['replace']:
   pat=re.compile(r'(?m)^'+str(e)+r'\. \*\*[^\n]+')
   m=pat.search(part);assert m,(y,e,'body line')
   before=m[0];part=part[:m.start()]+f'{e}. **{h}** {d}{endlink}'+part[m.end():]
   AUDIT['replaced'].append([p,e,before])
  else:part=part.rstrip()+f'\n\n**{h}** {d}{endlink}\n\n'
  s=s[:start]+part+s[end:];o['assigned_event']=e
 PATCH_NOTES[p].append(source_note(o,i));AUDIT['patches'].append({'year':y,'event':e,'type':'修正' if o['replace'] else ('新增' if o['into'] is None else '扩写'),'heading':h,'refs':o['refs']})
 put(p,s)
for p,ns in PATCH_NOTES.items():
 s=text(p);nav=re.search(r'\n---\s*\n\s*\[← 上一张|\n---\s*\n\s*\[本世纪目录',s)
 pos=nav.start() if nav else len(s)
 s=s[:pos]+'\n\n## 补充核对的史料\n\n'+''.join(ns)+s[pos:];put(p,s)
for p,changes in PATCH['text_fixes'].items():
 s=text(p)
 for a,b in changes:
  assert a in s,(p,'literal correction absent',a);s=s.replace(a,b)
 put(p,s)
for y in range(722,467,-1):
 p=mdpath(y);s=text(p)
 def repl(m):return f'[[{m[1]}]](#note-{m[1]})' if 'note-'+m[1] in ids(s) else m[0]
 s=re.sub(r'(?<![\[!])\[(\d+)\](?![\](])',repl,s)
 if s!=text(p):put(p,s)
FINAL=set(T)|set(OUT)
ANNUAL=sorted([p for p in FINAL if re.fullmatch(r'years/(?:bce|ce)-\d{4}-\d{4}/(?:bce|ce)-\d{4}\.md',p)],key=lambda p:(-int(Path(p).stem[4:]) if Path(p).name.startswith('bce-') else int(Path(p).stem[3:])))
assert len(ANNUAL)==290,len(ANNUAL)
for y in range(722,467,-1):assert mdpath(y) in FINAL
def display(p):
 n=Path(p).stem;return ('公元前'+str(int(n[4:])) if n.startswith('bce') else '公元'+str(int(n[3:])))+'年'
for i,p in enumerate(ANNUAL):
 old=text(p);prev=ANNUAL[i-1] if i else None;nxt=ANNUAL[i+1] if i+1<len(ANNUAL) else None
 nav=('['+'← 上一张已编年页：'+display(prev)+']('+link(p,prev)+') · ' if prev else '')+'[本世纪目录](README.md) · [全部世纪](../README.md)'+(' · [下一张已编年页：'+display(nxt)+' →]('+link(p,nxt)+')' if nxt else '')
 lines=old.splitlines();lines=[l for l in lines if not (l.startswith('[') and ('上一张已编年页' in l or '下一张已编年页' in l) and '全部世纪' in l)]
 s='\n'.join(lines).strip();s=re.sub(r'\n---\s*$','',s)
 first,sep,rest=s.partition('\n');new=first+'\n\n'+nav+'\n\n'+rest.strip()+'\n\n---\n\n'+nav+'\n'
 if re.sub(r'\s+','',new)!=re.sub(r'\s+','',old) or p in OUT:put(p,new)
cent='years/bce-0600-0501/README.md';s=oldtext(cent);s=s.replace('现有 **76** 张','现有 **100** 张')
start=s.index('| 年份 |');end=s.index('\n\n',start)
rows='| 年份 | 本页主线 |\n|---|---|\n'
for y in range(600,500,-1):
 p=mdpath(y);title=text(p).splitlines()[0].lstrip('# ');rows+=f'| [公元前{y}年](bce-{y:04}.md) | {title.replace("|","｜")} |\n'
s=s[:start]+rows.rstrip()+s[end:];put(cent,s)
for p in ['README.md','years/README.md']:
 s=oldtext(p).replace('| 公元前600—501年 | 76 |','| 公元前600—501年 | 100 |').replace('**266**','**290**')
 if p=='README.md':
  a=s.index('**《春秋／左传》还不能称为全部完成。**');b=s.index('\n\n',a)
  s=s[:a]+'**《春秋／左传》逐年整理已补齐前722—前468年，共255张连续年页。** 本轮完成襄公三十一年、保留七张旧《史记》增量页的全部入口，并补核早期漏条与误读。原经到哀公十四年获麟为止，续经、后段传文另标范围，不把255年都称为《春秋》原经。[完成范围与核对记录](meta/记录/春秋-完整覆盖核对.md)。'+s[b:]
 else:s+='\n\n## 春秋年页\n\n前722—前468年已连续补齐，共255年。完成范围是经传材料的白话编年整理，不是声称一切古史争议已定。原经与续经、传文后段分层见[核对记录](../meta/记录/春秋-完整覆盖核对.md)。\n'
 put(p,s)
r='meta/记录/春秋-襄公-经传去向.md'
s='# 春秋襄公时期｜经传逐段去向\n\n[记录目录](README.md) · [完成核对](春秋-完整覆盖核对.md) · [前600—501年](../../years/bce-0600-0501/README.md)\n\n| 字段 | 内容 |\n|---|---|\n| 类型 | 记录 |\n| 范围 | 襄公元年至三十一年，前572—前542年 |\n| 状态 | 31年正文、286段经、421段传均有去向；原始JSON未改 |\n\n## 内容\n\n“注释”表示论赞、结构、回叙或不能独立归年的材料进入对应注释，不是又产生一件本年事件。共享段落只引一次，其他条目回链；J/T编号是来源页的稳定定位符，不是古籍卷号。\n\n'
for n in range(1,32):
 y=573-n;b=B[str(n)];p=mdpath(y)
 s+=f'<a id="year-{y}"></a>\n### 前{y}年｜襄公{n}年\n\n[阅读正文]({link(r,p)})\n\n| 原文段 | 去向 | 处理 |\n|---|---|---|\n'
 for k in ('j','t'):
  for i,v in enumerate(b[k],1):
   ds=' · '.join(f'[第{e}条]({link(r,p,"note-"+str(e))})' for e in dest(v))
   why=v['reason'] if isinstance(v,dict) else '正文或共享史料'
   s+=f'| [{k.upper()}{i:03}]({link(r,srcpath(y),k+str(i).zfill(3))}) | {ds} | {why.replace("|","｜")} |\n'
 s+='\n'
s+='## 关联入口\n\n[完成范围](春秋-完整覆盖核对.md) · [记录目录](README.md)\n';put(r,s)
r='meta/记录/春秋-完整覆盖核对.md';s='# 春秋经传｜完整覆盖核对\n\n[记录目录](README.md) · [全部时间入口](../../years/README.md)\n\n| 字段 | 内容 |\n|---|---|\n| 类型 | 记录 |\n| 范围 | 前722—前468年，经、传与续经分层 |\n| 状态 | 全时段255年已成连续白话年页；本次补缺与复核已完成 |\n\n## 内容\n\n### 完成范围\n\n所有正式叙事都在`years/对应世纪/`，没有另建春秋或史记年表。主分支本次从266张年度页增至290张，新增24张缺年页；其中春秋时段前722—前468年255年连续无缺。其他年度材料及3张上古时期页保持原有范围。\n\n原《春秋》经到哀公十四年获麟结束；年条来源中混排的获麟后记事与后续经文另标，不将哀公十五年至二十七年冒称为原经。255年是项目采用的《左传》年条范围，不是原经的年数。\n\n### 各君年段\n\n| 鲁君 | 年份范围 | 年页 | 本次处理 |\n|---|---|---:|---|\n'
rulers=collections.defaultdict(list)
for y,d in D.items():rulers[d['ruler_index']].append(y)
for ri,ys in sorted(rulers.items()):
 d=D[ys[0]];lo=min(ys);hi=max(ys)
 s+=f'| {d["ruler"]} | 前{hi}—前{lo}年 | {len(ys)} / {len(ys)} | '+('整组31年补齐；旧稿1—28年核读回填，29—31年完成细写' if ri==9 else '保留原正文；本次核对经文短条及传文独有事项')+' |\n'
s+='\n### 襄公完整接回\n\n依据旧审读分支`'+OLD+'`的实际正文与逐段去向，不直接合并旧目录。新正文共411个叙述条目，映射286段经、421段传；时期回叙、未来结局和论赞进入同号说明。最后三年补写季札观乐各组评语、伯有之乱、子产初政、鲁国继位、莒国弑君及使节活动。\n\n[襄公707段的逐项去向](春秋-襄公-经传去向.md)。原来七个年份中的《史记》事件已并入同一事件的正文或注，全部旧锚点保留；诸樊让位的前560／559年差别明确注出，不重复发生。\n\n### 其他年页补核\n\n本次对下列原文与年页进行补写或更正。既有条号不改，不用新生成器整页替换较早正文。\n\n| 年份 | 处理 | 条目 |\n|---|---|---|\n'
for o in AUDIT['patches']:
 p=mdpath(o['year']);s+=f'| [前{o["year"]}年]({link(r,p,"event-"+str(o["event"]))}) | {o["type"]} | {o["heading"]} |\n'
s+='\n另改正文几处过度解释或重复记录：宋攻曹与娄林之战不再重复列战，长狄结局标为跨年回叙／预叙，宋国内族乱保留经传年次差别。齐高子来盟只据本年经文，不把其他传的故事冒充《左传》本段。\n\n### 版本与校验口径\n\n原始TXT、PDF和采集JSON仍用同一Git对象。仅为实际引用的有标点原文展示页增加J/T段落锚点，原文汉字未增删。修改前的正式年页、原有史料锚点及《史记》入口逐一检查；有意更正的句子在本页与对应注中说明。\n\n覆盖核对解决“有无漏年、漏条、独立事项和引用落点”，不声称所有古地名、兵力、祥瑞、礼制、年代异说都已成为学术定论；传文论赞在同号原文或注中保留，不把每句评论复制成另一个事件。字符串相似度仅用来发现候选，不能代替这次逐项文字核读。\n\n### 后续增量\n\n《史记》继续从已完成的卷001、002向后按卷序补入，春秋时段有新材料仍加在现有年页，不恢复废弃的书名目录。本次完成经传不等于二十四史全部汇入。\n\n## 关联入口\n\n[前800—701年](../../years/bce-0800-0701/README.md) · [前700—601年](../../years/bce-0700-0601/README.md) · [前600—501年](../../years/bce-0600-0501/README.md) · [前500—401年](../../years/bce-0500-0401/README.md) · [记录目录](README.md)\n';put(r,s)
p='meta/记录/README.md';s=oldtext(p);at=s.index('|---|---|')+len('|---|---|');s=s[:at]+'\n| [春秋完整覆盖核对](春秋-完整覆盖核对.md) | 前722—前468年连续255年，补齐襄公并复核早期漏条 |\n| [襄公经传逐段去向](春秋-襄公-经传去向.md) | 31年、286段经、421段传的正文与注释位置 |'+s[at:];put(p,s)
FINAL=set(T)|set(OUT)
errors=[];preserved=0
for p in T:
 if re.fullmatch(r'years/.*/(?:bce|ce)-\d{4}\.md',p):
  before=oldtext(p);after=text(p)
  for a in ids(before):
   preserved+=1
   if a not in ids(after):errors.append(['lost-year-anchor',p,a])
for p,s in OUT.items():
 a=ids(s)
 if len(a)!=len(set(a)):errors.append(['duplicate-anchor',p,[x for x,n in collections.Counter(a).items() if n>1]])
 if not s.endswith('\n') or s.endswith('\n\n'):errors.append(['eof',p])
 if p.endswith('.md') and len(re.findall('^# ',s,re.M))!=1:errors.append(['h1',p])
def mdlinks(s):
 out=[];i=0
 while True:
  a=s.find('](',i)
  if a<0:break
  j=a+2;depth=1;escape=False;angle=False
  while j<len(s) and depth:
   c=s[j]
   if escape:escape=False
   elif c=='\\':escape=True
   elif c=='<':angle=True
   elif c=='>':angle=False
   elif c=='(' and not angle:depth+=1
   elif c==')' and not angle:depth-=1
   j+=1
  if not depth:out.append(s[a+2:j-1]);i=j
  else:i=a+2
 return out
def headingids(s):
 a=set(ids(s));counts=collections.Counter()
 for h in re.findall(r'^#{1,6}\s+(.*)',s,re.M):
  h=re.sub(r'<[^>]+>','',h);h=re.sub(r'\[([^]]+)\]\([^)]*\)',r'\1',h);h=h.replace('`','').replace('*','')
  h=re.sub(r'[^\w\s\-]','',h.lower()).replace(' ','-');n=counts[h];counts[h]+=1;a.add(h+('-'+str(n) if n else ''))
 return a
def prosekey(s):
 s=re.sub(r'\]\([^\n]*?\)',']',s)
 return norm(s)
replacements={(p,prosekey(b)) for p,e,b in AUDIT['replaced']}
conserved=0;intentional=0
for p in T:
 if not re.fullmatch(r'years/.*/(?:bce|ce)-\d{4}\.md',p):continue
 if p.startswith('years/bce-0600-0501/') and 542<=int(Path(p).stem[4:])<=572:continue
 before=oldtext(p);after=prosekey(text(p))
 for a,b in PATCH['text_fixes'].get(p,[]):before=before.replace(a,b)
 for paragraph in re.split(r'\n\s*\n',before):
  paragraph=paragraph.strip()
  if paragraph.startswith(('#','<a','<!--','[←','[本世纪')):continue
  key=prosekey(paragraph)
  if len(re.findall(r'[\u3400-\u9fff]',key))<8:continue
  if (p,key) in replacements:intentional+=1;continue
  conserved+=1
  if key not in after:errors.append(['lost-existing-paragraph',p,paragraph[:160]])
assert intentional==9,intentional
assert len(AUDIT['preserved_shiji'])==13
AUDIT['existing_paragraphs_preserved']=conserved
AUDIT['explicit_replacements']=intentional
checked=0
for p in FINAL:
 if not p.endswith('.md'):continue
 if LOCAL and p not in OUT and not (C/p).exists():continue
 s=text(p)
 for u in mdlinks(s):
  u=u.strip();u=u[1:-1] if u.startswith('<') and u.endswith('>') else u
  if re.match(r'^\w+:',u):continue
  u=re.sub(r'\s+[\"\x27].*[\"\x27]$','',u)
  v,_,frag=u.partition('#');v=urllib.parse.unquote(v).replace('\\(','(').replace('\\)',')')
  destp=posixpath.normpath(posixpath.join(posixpath.dirname(p),v)) if v else p
  checked+=1
  if destp not in FINAL and not any(q.startswith(destp.rstrip('/')+'/') for q in FINAL):errors.append(['missing-link',p,u,destp]);continue
  if frag and destp in FINAL and destp.endswith('.md'):
   if LOCAL and destp not in OUT and not (C/destp).exists():continue
   if urllib.parse.unquote(frag) not in headingids(text(destp)):errors.append(['missing-fragment',p,u,destp])
AUDIT.update(annual_before=sum(bool(re.fullmatch(r'years/.*/(?:bce|ce)-\d{4}\.md',p)) for p in T),annual_after=len(ANNUAL),spring_years=255,xiang_events=sum(len(v['entries']) for v in B.values()),xiang_j=sum(len(v['j']) for v in B.values()),xiang_t=sum(len(v['t']) for v in B.values()),old_year_anchors_checked=preserved,links_checked=checked,files_changed=len(OUT),errors=errors)
(W/'validation.json').write_text(json.dumps(AUDIT,ensure_ascii=False,indent=2))
if LOCAL:
 O=W/'result'
 for p,s in OUT.items():
  f=O/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
 print(json.dumps({k:v for k,v in AUDIT.items() if k not in ['events','patches','replaced','preserved_shiji']},ensure_ascii=False,indent=2));sys.exit(bool(errors))
if errors:raise RuntimeError(json.dumps(errors[:25],ensure_ascii=False))
idx=str(Path(os.environ.get('RUNNER_TEMP','/tmp'))/'spring-complete-index');env=os.environ.copy();env['GIT_INDEX_FILE']=idx
try:Path(idx).unlink()
except FileNotFoundError:pass
git('read-tree',BASE,env=env)
rows=[]
for p,s in sorted(OUT.items()):
 sha=git('hash-object','-w','--stdin',input=s.encode()).decode().strip();rows.append('100644 '+sha+'\t'+p+'\0')
git('update-index','-z','--index-info',input=''.join(rows).encode(),env=env)
newtree=git('write-tree','--missing-ok',env=env).decode().strip()
newcommit=git('commit-tree',newtree,'-p',BASE,input='Complete continuous Chunqiu chronology and restore reviewed Duke Xiang narratives without losing source layers\n'.encode()).decode().strip()
git('push','origin',newcommit+':refs/heads/'+REF)
AUDIT.update(result_commit=newcommit,result_tree=newtree)
(W/'validation.json').write_text(json.dumps(AUDIT,ensure_ascii=False,indent=2))
print(json.dumps({k:AUDIT[k] for k in ['result_commit','result_tree','annual_after','spring_years','xiang_events','links_checked','files_changed']},ensure_ascii=False,indent=2))
