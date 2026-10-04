"""One-time, loss-aware volume 005 integration. Not included in final tree."""
from pathlib import Path
import re,json,sys,os,subprocess,posixpath,hashlib,collections,urllib.parse
BASE='dfcbe7a0a5c124a51490c145068d09f263922ed2'
LOCAL='--local' in sys.argv
W=Path('/mnt/data/qin005') if LOCAL else Path('_qin005')
C=W/'current' if LOCAL else Path('.')
def git(*args,input=None,env=None):return subprocess.check_output(['git',*args],input=input,env=env)
def tree(ref):
 d={}
 for r in git('ls-tree','-rz',ref).split(b'\0'):
  if r:
   m,p=r.split(b'\t',1);mode,kind,sha=m.decode().split();d[p.decode()]={'mode':mode,'type':kind,'sha':sha}
 return d
T=json.loads((C/'tree.json').read_text()) if LOCAL else tree(BASE)
cache={}
def old(p):
 if p not in cache:cache[p]=(C/p).read_text(encoding='utf-8-sig') if LOCAL else git('show',BASE+':'+p).decode('utf-8-sig')
 return cache[p]
OUT={}
def text(p):return OUT[p] if p in OUT else old(p)
def put(p,s):OUT[p]=s.rstrip()+'\n'
def ids(s):return set(re.findall(r'\bid=[\"\x27]([^\"\x27]+)',s))
def yp(y):
 hi=((y-1)//100+1)*100;return f'years/bce-{hi:04d}-{hi-99:04d}/bce-{y:04d}.md'
def rel(a,b,f=''):return posixpath.relpath(b,posixpath.dirname(a))+('#'+f if f else '')
SRC='sources/摘录/史记-卷005-秦本纪.md'
REC='meta/记录/史记-卷005-引文去向.md'
RES='meta/考证/史记-卷005-纪年与异说.md'
FULL='sources/二十四史/txt/01_shiji_full.txt'
raw=old(FULL).split('*01-005*')[1].split('*01-006*')[0]
lines=[s.strip() for s in raw.splitlines() if s.strip()]
labels=[s for s in lines if len(s)<20 and not any(c in s for c in '。，；：')]
P=[s for s in lines if s not in labels]
assert len(P)==72 and len(labels)==34,(len(P),len(labels))
REG=[]
def params(p):return [p] if isinstance(p,int) else p
def E(y,p,h,d,note=''):REG.append(dict(kind='new',year=y,path=yp(y),ps=params(p),h=h,d=d,note=note))
def R(y,p,anchor,note,d=''):REG.append(dict(kind='merge',year=y,path=yp(y),ps=params(p),anchor=anchor,h='',d=d,note=note))
def U(name,anchor,aid,h,p,d,note):REG.append(dict(kind='period',path='years/上古/'+name,ps=params(p),anchor=anchor,aid=aid,h=h,d=d,note=note))
import early,middle,late
for module in [early,middle,late]:module.populate(E,R,U)
# Normalize the pre-royal title in the newly authored 329 BCE sentence.
for r in REG:
 if r.get("year")==329 and r["kind"]=="new":r["d"]=r["d"].replace("秦王与魏王", "秦君与魏王")
# The source-note reference may be to a plain heading, a stable legacy id or an event number.
def resolve_anchor(s,a):
 if isinstance(a,int):
  key='event-'+str(a)
  assert key in ids(s),('event missing',a)
  return key
 if a in ids(s):return a
 m=re.search(r'^#{2,4} '+re.escape(a)+r'\s*$',s,re.M)
 if m:
  key='sj005-existing-'+hashlib.sha1(a.encode()).hexdigest()[:10]
  return key
 raise ValueError(('anchor missing',a))
def anchor_start(s,key):
 m=re.search(r'<a id=[\"\x27]'+re.escape(key)+r'[\"\x27][^>]*>\s*</a>',s)
 assert m,('id missing',key)
 return m.start(),m.end()
def block_end(s,frompos,period=False):
 if period:
  m=re.search(r'\n(?:<a id="[^"]+"></a>\n)?## ',s[frompos:])
  return frompos+m.start() if m else len(s)
 ms=list(re.finditer(r'\n<a id="(?:event-\d+|sj-\d{3}-[^"]+)"|\n## (?!#)',s[frompos:]))
 return frompos+ms[0].start() if ms else len(s)
def without_tail(s):
 lines=s.splitlines()
 # Only remove the former end navigation, not any historical paragraph or footnote.
 while lines and not lines[-1].strip():lines.pop()
 if lines and lines[-1].startswith('[') and any(w in lines[-1] for w in ['全部世纪','上古目录','继续：','上一张已编年页']):
  tail=lines.pop()
  while lines and not lines[-1].strip():lines.pop()
  if lines and lines[-1].strip()=='---':lines.pop()
  return '\n'.join(lines).rstrip(),tail
 return s.rstrip(),''
NOTES=collections.defaultdict(list);ROUTES=collections.defaultdict(list);MATCHES=[];CREATED=[]
for idx,r in enumerate(REG,1):
 path=r['path'];ps=r['ps'];key=f'sj005-{idx:03}'
 if path not in T and path not in OUT:
  y=r['year'];put(path,f'# 公元前{y}年｜年度记事\n\n> 当前页面整理已有史料，不表示这一年全部国家和全部史书均已覆盖。\n\n## 本年纪事\n\n## 本年相关史料\n');CREATED.append(path)
 s=text(path);nk=key+'-note'
 reflinks=' · '.join(f'[卷005 P{p:03}]({rel(path,SRC,f"p{p:03}")})' for p in ps)
 if r['kind']=='new':
  nums=[int(x) for x in re.findall(r'\bid="(?:event|note)-(\d+)"',s)];n=max(nums,default=0)+1
  # Unnumbered old trial entries are not silently renumbered.
  aid=f'event-{n}';r['resolved']=aid
  block=f'<a id="{aid}"></a>\n\n{n}. **{r["h"]}** {r["d"]} [原文与说明](#{nk})\n\n'
  pos=re.search(r'^## (?:本年相关史料|原文与出处|史料核对说明|补充史料与异说)',s,re.M)
  if pos:s=s[:pos.start()]+block+s[pos.start():]
  else:
   pre,tail=without_tail(s);s=pre+'\n\n## 本年补充纪事\n\n'+block+'\n\n'+tail
  r['caption']=r['h']
 elif r['kind']=='merge':
  aid=resolve_anchor(s,r['anchor']);r['resolved']=aid
  if aid not in ids(s):
   m=re.search(r'^#{2,4} '+re.escape(r['anchor'])+r'\s*$',s,re.M)
   s=s[:m.start()]+f'<a id="{aid}"></a>\n'+s[m.start():]
  st,en=anchor_start(s,aid)
  scan=en
  own=re.match(r'\s*#{2,4} [^\n]+\n',s[en:])
  if own:scan=en+own.end()
  end=block_end(s,scan)
  if isinstance(r['anchor'],str) and r['anchor'].startswith('s') and r['anchor'][1:].isdigit():
   nextid=re.search(r'\n<a id=|\n## ',s[scan:])
   if nextid:end=scan+nextid.start()
  oldblock=s[en:end]
  caption=next((l.strip('# ') for l in oldblock.splitlines() if re.match(r'\d+\. |#{2,4} ',l)),aid)
  r['caption']=(r['anchor'] if caption==aid and isinstance(r['anchor'],str) and len(r['anchor'])>25 else caption)[:150]
  MATCHES.append({'year':r['year'],'ps':ps,'target':aid,'target_text':oldblock[:300],'note':r['note']})
  addition=('\n\n'+r['d'] if r['d'] else '')+f'\n\n[补充史料与年次说明](#{nk})\n\n'
  s=s[:end].rstrip()+addition+s[end:]
 else:
  st,en=anchor_start(s,r['anchor']);aid=r['aid'];r['resolved']=aid;r['caption']=r['h']
  block=f'<a id="{aid}"></a>\n## {r["h"]}\n\n{r["d"]} [原文与说明](#{nk})\n\n'
  # Feizi precedes King Li. Other short additions follow the related episode.
  if aid=='feizi':pos=st
  else:
   hm=re.search(r'\n## ',s[en:]);start=en+hm.end() if hm else en
   pos=block_end(s,start,period=True)
  s=s[:pos].rstrip()+'\n\n'+block+s[pos:]
 note=f'<a id="{nk}"></a>\n### {key}｜{r["h"] or "同一事件的补充与取舍"}\n\n'+reflinks+'。\n\n'
 if r['note']:note+='**说明：**'+r['note']+'\n\n'
 if r['kind']=='new':note+='**归年：**'+('按本条注明的本纪／年表取舍；' if r['note'] else '')+'秦君元年、在位数与《十二诸侯年表》《六国年表》对照，规则及冲突见[本卷纪年说明]('+rel(path,RES)+')。古月与干支未作历算时，不当作同号公历月日。\n\n'
 NOTES[path].append(note)
 for p in ps:ROUTES[p].append((path,aid,nk,r['caption'],r['kind']))
 put(path,s)
for path in CREATED:
 s=text(path);heading=next(r['h'] for r in REG if r['path']==path and r['kind']=='new').rstrip('。')
 put(path,s.replace(s.splitlines()[0],f'# 公元前{next(r["year"] for r in REG if r["path"]==path)}年｜{heading}',1))
for path,ns in NOTES.items():
 s,tail=without_tail(text(path))
 # New pages already have an empty source section; old pages retain their source sections.
 if path in CREATED and s.endswith('## 本年相关史料'):s+='\n\n'+''.join(ns)
 else:s+='\n\n## 补充史料与异说\n\n'+''.join(ns)
 put(path,s+'\n\n'+tail)
assert set(ROUTES)==set(range(1,73)),sorted(set(range(1,73))-set(ROUTES))
# Full source text is frozen unchanged between its chapter markers.
source='# 《史记》卷005｜秦本纪阅读原文\n\n[史料目录](../README.md) · [本卷去向](../../meta/记录/史记-卷005-引文去向.md) · [时间入口](../../years/README.md)\n\n本页从仓库原始《史记》TXT的`*01-005*`至`*01-006*`之间提取实质文字，原TXT Git blob：`'+T[FULL]['sha']+'`。P001—P072是本项目的阅读定位号，不是中华书局点校本自然段号。核读日期：2026-10-04。\n\n[原始TXT](../二十四史/txt/01_shiji_full.txt)及既有来源说明保留；另对读[维基文库固定版本8744286](https://zh.wikisource.org/w/index.php?oldid=8744286&title=史記/卷005)。两个文本源流相关，不能当成两份独立历史证明。本轮未逐页核现代扫描本，不称独立点校完成。原字、括注及难字保留，现代人物标签在末尾登记，不混成本纪正文。\n\n'
for i,p in enumerate(P,1):
 source+=f'<a id="p{i:03}"></a>\n## P{i:03}\n\n'+p+'\n\n'
 dests=[]
 for a,f,_,_,_ in ROUTES[i]:
  u=rel(SRC,a,f)
  if u not in [z[1] for z in dests]:dests.append((Path(a).stem,u))
 source+='[逐项去向]('+rel(SRC,REC,f'p{i:03}')+') · '+' · '.join(f'[{a}]({u})' for a,u in dests)+'\n\n'
source+='## 原工作文本的现代标签\n\n这些标签不作为历史事件，未假称出自司马迁。原顺序：\n\n'+'、'.join(labels)+'。\n'
put(SRC,source)
# Research document deliberately records uncertainties instead of silently flattening dates.
research='''# 《史记》卷005｜纪年、世系与异说

[考证目录](README.md) · [记录](../记录/史记-卷005-引文去向.md) · [时间入口](../../years/README.md)

| 字段 | 内容 |
|---|---|
| 类型 | 考证 |
| 范围 | 《秦本纪》全卷的时间精度、同事合并、文本与年表差别 |
| 状态 | 本轮实际核读与采用的编辑判断；没有把所有争论写成定论 |

## 内容

### 本轮所用材料

主线是仓库完整TXT卷005的72个实质段，原字保留在[阅读原文](../../sources/摘录/史记-卷005-秦本纪.md)。公开对读用[卷005固定版本8744286](https://zh.wikisource.org/w/index.php?oldid=8744286&title=史記/卷005)。既有《春秋》《左传》年页及其已保存原文，作为重叠事件的直接核对材料。

纪年互见使用同一TXT的卷014、015及公开[《十二诸侯年表》](https://zh.wikisource.org/wiki/史記/卷014)、[《六国年表》](https://zh.wikisource.org/wiki/史記/卷015)。必要处读[卷043《赵世家》](https://zh.wikisource.org/wiki/史記/卷043)、[卷068《商君列传》](https://zh.wikisource.org/wiki/史記/卷068)、[卷073《白起王翦列传》](https://zh.wikisource.org/wiki/史記/卷073)、[卷081《廉颇蔺相如列传》](https://zh.wikisource.org/wiki/史記/卷081)的有关段落；仅作互证，不把这些整卷提前计为完成。百里奚异说核到[《孟子·万章上》第九章](https://zh.wikisource.org/zh/孟子/萬章上)。未以没有读到的现代论文声称已有“学界一致结论”。

### 时间精度与年表算法

先祖神异、谱系与孝王非子受邑只用时期页，不硬配绝对年；使用[此前断代工程精度规则](上古纪年与断代工程.md)，而不是为所有秦先公套一个传说始年。秦仲以后有年表坐标时才建年页。某君元年为公元前Y，则第n年为前Y−n＋1；但前提是本纪王年与年表相合，不能先机械累计再掩盖冲突。

主要核对节点：襄公元年前777，文公765，宁公715，武公697，德公677，宣公675，成公663，穆公659，康公620，共公608，桓公603，景公576，哀公536，厉共公476，躁公442，怀公428；战国灵公424，简公414，惠公399，出子386，献公384，孝公361，惠文君337，更元324，武王310，昭襄王306，孝文王250，庄襄王249。用于本轮核算的元年不等于绝对不存在其他王年解释。

同年继立与次年改元分开；因父死而继立不另创造一次次年“再次即位”。惠文王更元必须分两套年数。孝文王除丧即位三日不把全部元年事务压成三日。秦岁首与同段重复十月、正月，仍用古史年条而不擅换公历日。

### 影响正文的主要取舍

| 事项 | 文献差别 | 本轮安放 |
|---|---|---|
| 蜚廉之死 | 殷本纪与秦本纪不同 | 商末原页同号异说，不让同人死后再返北方 |
| 秦襄公受封 | 本纪随东迁，年表七年；八年西畤 | 前771救周，770护送与政治安排，说明封爵年差 |
| 齐襄死、无知死、晋灭三国 | 夹在武公十三年同段 | 分前686、685、661，不按段落位置合年 |
| 曲沃受命 | 本纪武公十九年 | 仍用经传前678正式册命，保留前679异年 |
| 管仲、隰朋卒 | 本纪穆公十二年；经传同年仍出使 | 不在前648造已证实死亡，在现有出使注记年差 |
| 韩原、秦晋质子 | 本纪九月，经十一月；质子连在战后 | 前645韩原、前643圉为质及婚，不压同年 |
| 梁芮之亡 | 本纪同列穆公二十年 | 梁依经传前641，芮暂前640 |
| 河曲与士会归 | 康公六年压缩；战果不同 | 前615河曲、614归士会，保留秦胜／夜退差别 |
| 秦桓公十年附楚败晋 | 对应不上邲之战 | 沿经传前597，不新造前594邲战 |
| 秦女入楚与太子建 | 哀公十一年与昭公十九年不同 | 依既有前523婚事、522争端，不倒回526 |
| 春秋惠公卒 | 本纪与年表491，经传492 | 保留492卒、491葬，不重复卒条 |
| 灵公、简公、献公在位长度 | 本纪13／16／24，年表10／15／23 | 依415／400／362衔接，原数在注保留 |
| 惠公太子、南郑 | 出生差一年，秦蜀胜负反写 | 暂前389生；前387只确定争夺，结果并列 |
| 雨金 | 献公十八年、年表十七年 | 暂前368，不把两条当两次降金 |
| 变法 | 孝公三年议法与“居三年”后效 | 前359写开始及后续，未把所有措施强塞一日 |
| 县数 | 秦本纪41，年表与商君传31 | 前350主叙合县，注中列数，不私改原文 |
| 秦称王 | 原TXT作魏君，秦栏年表作君 | 前325秦称王，韩王号另注；秦旧字不删 |
| 修鱼、义渠、封蜀、燕让国 | 本纪段内有不同年事混列 | 分前317、314、313、316，并回对应年份 |
| 唐昧与怀王、田文 | 昭王八至十一年连续压缩 | 唐昧301；怀王299入秦、297逃、296卒；田文299入298出 |
| 中山 | 本纪只称破，年表295，赵世家三年 | 先用296灭、年表后续异说在注，不把君死齐硬定同年 |
| 齐灭宋 | 附在称帝年段 | 东西帝288，灭宋286 |
| 华阳 | 秦本纪33，年表与白起传34 | 前273，与原有周国游说条合并 |
| 阏与 | 本纪269、六国年表270 | 暂269并列年差，不重复两场阏与 |
| 上党与长平 | 秦本纪四十七年合叙 | 上党262、相距261、决战260 |
| 太原与三十七城 | 庄襄二三年异置 | 248攻城、247置郡，保留日食年差 |
| 统一与秦亡 | 篇末把多年压成一段 | 221统一、210始皇卒、209起事、207二世死、206子婴死，沿既有古史年条 |

这些选择不等于年表永远压过本纪，也不等于经传永远更真。有的只是压缩的复叙，有的是同书不同王年体系，有的是胜负、姓名、地理的实质差别，须分别说明。未经充分核对者用较窄表述，不凭一条便画出新疆域图。

### 人物、长段与数值

百里奚被虞亡波及以后入秦，是本纪的读法；穆公前年已娶晋女，故媵臣、逃宛、赎回、任政不全算前655一年的动作。《孟子》否认自卖五羊皮求见说，并不逐字等于秦本纪的赎回说。年七十、三日问政、二老所传经历都是文献信息，不扩写为精确生日。

由余的完整出使、制度辩论、内史廖的离间、女乐、滞留与返国、再归秦，附在前623征戎的“此前过程”，不称全部发生在623。战功十二国、千里、各役首级数、殉死66／177人分别引用，不作独立计量。穆公子四十人是本纪家族总数，不替四十人新造名字与官职。

战国后期以P066一个很长的原文段跨越昭王十三年至五十年，已经按各年各类事件拆开，并保留攻城、和会、赦迁、封爵、相位、郡县、丧事与天象等不同内容。不能一段只抽“白起大胜”而略去未攻下和退军，也不能把所有见于战争段的外交事情都改叫战役。

### 文本边界

陈宝、大梓大特、作伏御蛊、鸟身人言、神授石棺，按文献性质列入说明，不改成现代动物学、医学或考古发现。薄弱字句如“为纣石北方”“相韩”“到满”“以垣为蒲阪皮氏”“南阳免臣迁居”等不拿来补确定路线与制度细节。胡（伤）［阳］、南（郡）［阳］、篇末（四年）等校改痕迹保持原样。

原TXT中的34行现代标签单独登记。宁公、出子、穆／缪、子舆／子车、太子未立而追谥等分别标识，不因现代惯用字或同名把两人拼成一人。本轮原书TXT与PDF均未改，亦未宣称完成中华书局逐字校勘。

## 关联入口

[全卷去向](../记录/史记-卷005-引文去向.md) · [原文](../../sources/摘录/史记-卷005-秦本纪.md) · [时间目录](../../years/README.md)
'''
put(RES,research)
# Derive indexes from the actual final annual page set, not a promised completion count.
FINAL=set(T)|set(OUT)
annual=sorted([p for p in FINAL if re.fullmatch(r'years/(bce|ce)-\d{4}-\d{4}/(?:bce|ce)-\d{4}\.md',p)],key=lambda p:-int(Path(p).stem[4:]) if Path(p).stem.startswith('bce-') else int(Path(p).stem[3:]))
def display(p):
 st=Path(p).stem;return ('公元前'+str(int(st[4:])) if st.startswith('bce-') else '公元'+str(int(st[3:])))+'年'
for i,p in enumerate(annual):
 prev=annual[i-1] if i else None;nxt=annual[i+1] if i+1<len(annual) else None
 nav=(f'[← 上一张已编年页：{display(prev)}]({rel(p,prev)}) · ' if prev else '')+'[本世纪目录](README.md) · [全部世纪](../README.md)'+(f' · [下一张已编年页：{display(nxt)} →]({rel(p,nxt)})' if nxt else '')
 s=text(p)
 ls=[l for l in s.splitlines() if not (l.startswith('[') and '全部世纪' in l and any(w in l for w in ['上一张已编年页','下一张已编年页']))]
 cleaned='\n'.join(ls).strip();cleaned=re.sub(r'\n---\s*$','',cleaned)
 h,_,tail=cleaned.partition('\n');out=h+'\n\n'+nav+'\n\n'+tail.strip()+'\n\n---\n\n'+nav+'\n'
 if out!=s:put(p,out)
centuries=collections.OrderedDict()
for p in annual:centuries.setdefault(posixpath.dirname(p),[]).append(p)
def centname(c):
 _,era,a,b=re.split(r'[/\-]',c)
 return ('公元前' if era=='bce' else '公元')+str(int(a))+'—'+str(int(b))+'年'
cl=list(centuries)
for i,c in enumerate(cl):
 p=c+'/README.md';nav=(f'[← 上一个已有内容的世纪]({rel(p,cl[i-1]+"/README.md")}) · ' if i else '')+'[全部世纪](../README.md) · [项目首页](../../README.md)'+(f' · [下一个已有内容的世纪 →]({rel(p,cl[i+1]+"/README.md")})' if i+1<len(cl) else '')
 rows='| 年份 | 本页主线 |\n|---|---|\n'
 for f in centuries[c]:rows+=f'| [{display(f)}]({Path(f).name}) | '+text(f).splitlines()[0].lstrip('# ').replace('|','｜')+' |\n'
 put(p,'# '+centname(c)+'\n\n'+nav+f'\n\n本目录覆盖100年，现有 **{len(centuries[c])}** 张年度正文。只列已有页面，不以空文件表示已经完成。\n\n'+rows+'\n'+nav)
for p in ['README.md','years/README.md']:
 s=old(p)
 mt=re.search(r'\| 世纪范围 \|[^\n]*\n\|[-| :]+\n(?:\|[^\n]*\n)+',s)
 assert mt,p
 table='| 世纪范围 | 已有年份页 | 阅读入口 |\n|---|---:|---|\n'
 for c in cl:table+=f'| {centname(c)} | {len(centuries[c])} | [打开本世纪]({rel(p,c+"/README.md")}) |\n'
 s=s[:mt.start()]+table+s[mt.end():]
 s=re.sub(r'\*\*323\*\*',f'**{len(annual)}**',s)
 s=s.replace('下一卷005《秦本纪》','下一卷006《秦始皇本纪》').replace('下一卷为005《秦本纪》','下一卷为006《秦始皇本纪》').replace('下一卷为卷005《秦本纪》','下一卷为卷006《秦始皇本纪》')
 # Earlier completion sentence, if present, is replaced once, not old audit records.
 s=s.replace('卷001—004','卷001—005').replace('卷一至卷四','卷一至卷五')
 pos=s.find('<a id="year-list">') if p=='README.md' else s.find('## 世纪目录')
 notice=f'本轮完成《史记》卷005《秦本纪》的72个实质段落汇入，新增{len(CREATED)}张年度页；既有同一事件只补细节及异说。先世仍在原上古时期页，未另建秦史年表。[全卷去向]({rel(p,REC)}) · [纪年取舍]({rel(p,RES)})。下一卷为006《秦始皇本纪》。\n\n'
 s=s[:pos]+notice+s[pos:]
 put(p,s)
# Other live indexes keep their existing material and add the new entry.
for p,title,target,desc in [('meta/记录/README.md','《史记》卷005引文去向',REC,'72个实质段，秦先世至秦亡；同年事件不重复'),('meta/考证/README.md','《秦本纪》纪年、世系与异说',RES,'秦君王年与经传、年表对照；有争议的数字和称谓')]:
 s=old(p);at=s.find('|---|---|')+len('|---|---|');assert at>=len('|---|---|')
 s=s[:at]+f'\n| [{title}]({rel(p,target)}) | {desc} |'+s[at:]
 s=s.replace('卷001—004','卷001—005')
 s=s.replace('下一卷为005','下一卷为006').replace('下一卷005','下一卷006').replace('《秦本纪》尚未计作完成','《秦始皇本纪》尚未计作完成')
 put(p,s)
p='years/上古/README.md';s=old(p).replace('卷004《周本纪》。本项目阅读单元数依次为28、35、33、82','卷004《周本纪》、卷005《秦本纪》。本项目阅读单元数依次为28、35、33、82、72')
s+='\n\n## 秦先世材料的接入\n\n卷005并未另建“秦本纪时期页”。大费附在[尧舜任官](02-尧舜至禹.md#ying-origin)，费昌接入[夏末战争](03-夏代.md#feichang)，中衍支系补入[商前期](04-商代前期.md#ying-shang)，蜚廉恶来的不同结局留在[商周交接](06-商末与周初.md#feilian-ancestry)，造父与非子接到[西周](07-西周的治理与危机.md#feizi)。有年表坐标后转入原世纪目录。\n\n[卷005全部去向](../../meta/记录/史记-卷005-引文去向.md) · 下一卷：006《秦始皇本纪》。\n'
s=s.replace('下一卷为005《秦本纪》','下一卷为006《秦始皇本纪》').replace('下一卷005《秦本纪》','下一卷006《秦始皇本纪》')
put(p,s)
rec='# 《史记》卷005｜秦本纪引文去向\n\n[记录目录](README.md) · [纪年与异说](../考证/史记-卷005-纪年与异说.md) · [时间入口](../../years/README.md)\n\n| 字段 | 内容 |\n|---|---|\n| 类型 | 记录 |\n| 范围 | 秦先世、历代秦君、统一与秦亡概括及太史公论 |\n| 状态 | 72个实质文本段都有叙事或明确的同号说明去向 |\n\n## 内容\n\n### 底本与完成范围\n\n接续主分支`'+BASE+'`，原TXT全文72段逐项整理，34行现代标签单列。[阅读原文](../../sources/摘录/史记-卷005-秦本纪.md)保留全部字句，本表以事件而不是原文出现次数组织。回叙、年差、政策后效与史家评论不全部充作所在年新事件。\n\n本轮新增 **'+str(len(CREATED))+'** 张年度页，年度正文由323增至 **'+str(len(annual))+'** 张；上古仍为7张时期正文；春秋前722—前468年255张年页保留。既有同事补充'+str(sum(r['kind']=='merge' for r in REG))+'处，先世材料补在'+str(len(set(r['path'] for r in REG if r['kind']=='period')))+'张已有时期页，不新增书名时间线。\n\n### 全段去向\n\n下列折叠项按段首定位，长段进一步列到具体事件。72是工作文本段数，不是独立事件数或已证实史实数。\n\n'
for i,p in enumerate(P,1):
 rec+=f'<a id="p{i:03}"></a>\n<details>\n<summary>P{i:03}｜{p[:24]}</summary>\n\n[完整原文]({rel(REC,SRC,f"p{i:03}")})\n\n| 阅读位置 | 处理 | 说明 |\n|---|---|---|\n'
 for a,aid,nk,caption,kind in ROUTES[i]:
  label=display(a) if re.fullmatch(r'bce-\d{4}',Path(a).stem) else Path(a).stem
  cap=re.sub(r'\[.*?\]\(.*?\)','',caption).replace('|','｜').replace('**','')
  rec+=f'| [{label}]({rel(REC,a,aid)}) | '+{'new':'新增纪事','merge':'同一事件合并','period':'已有时期页补充'}[kind]+f' | {cap}；[同号说明]({rel(REC,a,nk)}) |\n'
 rec+='\n</details>\n\n'
rec+='### 尚待后续卷补充的边界\n\n本卷整卷完成不表示全部相关列传、年表都已整卷读完。卷006将补秦王政在位全程、制度与秦末细节；百里奚、卫鞅、张仪、白起、魏冉等有新来源时仍补原事件。原文本纪只短记者不凭印象抄成长传，有争议年数不以大量空文件制造精度。\n\n## 关联入口\n\n[卷004](史记-卷004-引文去向.md) · [原文](../../sources/摘录/史记-卷005-秦本纪.md) · [纪年取舍](../考证/史记-卷005-纪年与异说.md) · [时间目录](../../years/README.md)\n'
put(REC,rec)
# Assertions: sources unchanged, no missing years, no accidental deletion, reliable local hash.
FINAL=set(T)|set(OUT)
errors=[]
for y in range(468,723):assert yp(y) in FINAL
assert len(annual)==323+len(CREATED)
assert len(set(annual))==len(annual)
assert all(i not in OUT for i in T if i.startswith('sources/') and i!=SRC),'old source changed'
assert set(p.split('/')[0] for p in FINAL if '/' in p)=={'sources','years','meta'}
for p in range(1,73):assert P[p-1] in OUT[SRC]
source_original=T[FULL]['sha']
def mdlinks(s):
 arr=[];i=0
 while True:
  a=s.find('](',i)
  if a<0:break
  j=a+2;depth=1;esc=False;angle=False
  while j<len(s) and depth:
   ch=s[j]
   if esc:esc=False
   elif ch=='\\':esc=True
   elif ch=='<':angle=True
   elif ch=='>':angle=False
   elif ch=='(' and not angle:depth+=1
   elif ch==')' and not angle:depth-=1
   j+=1
  if depth:break
  arr.append((a+2,j-1,s[a+2:j-1]));i=j
 return arr
def heading_ids(s):
 out=ids(s);counter=collections.Counter()
 for line in re.findall(r'^#{1,6} (.+)',s,re.M):
  h=re.sub(r'<[^>]+>','',line);h=h.replace('`','').replace('*','');h=re.sub(r'[^\w\s-]','',h.lower()).replace(' ','-')
  n=counter[h];counter[h]+=1;out.add(h+('-'+str(n) if n else ''))
 return out
def normalized(s):
 for a,b,u in reversed(mdlinks(s)):s=s[:a]+s[b:]
 s=re.sub(r'<[^>]*>','',s)
 return ''.join(re.findall(r'[\u3400-\u9fffA-Za-z0-9]',s))
oldanchors=0;keptparas=0
for p in T:
 if not p.startswith('years/') or p.endswith('/README.md') or not p.endswith('.md'):continue
 before=old(p);after=text(p);dest=normalized(after)
 for a in ids(before):
  oldanchors+=1
  if a not in ids(after):errors.append(['lost-anchor',p,a])
 for b in re.split(r'\n\s*\n',before):
  if b.lstrip().startswith(('#','<a','<!--')) or (b.startswith('[') and any(q in b for q in ['上一张已编年页','下一张已编年页','上古目录'])):continue
  n=normalized(b)
  if len(re.findall('[\u3400-\u9fff]',n))<10:continue
  keptparas+=1
  if n not in dest:errors.append(['lost-paragraph',p,b[:160]])
checked=0;targets={}
for p in sorted(FINAL):
 if not p.endswith('.md'):continue
 if LOCAL and p not in OUT and not (C/p).exists():continue
 s=text(p)
 if p in OUT:
  if len(re.findall(r'^# ',s,re.M))!=1:errors.append(['heading-level1',p])
  arr=re.findall(r'\bid=[\"\x27]([^\"\x27]+)',s)
  if len(arr)!=len(set(arr)):errors.append(['duplicate-id',p])
 for _,_,u in mdlinks(s):
  u=u.strip();u=u[1:-1] if u.startswith('<') and u.endswith('>') else u
  if re.match(r'^\w+:',u):continue
  u=re.sub(r'\s+[\"\x27].*[\"\x27]$','',u)
  url,_,frag=u.partition('#');url=urllib.parse.unquote(url).replace('\\(','(').replace('\\)',')')
  d=posixpath.normpath(posixpath.join(posixpath.dirname(p),url)) if url else p
  checked+=1
  if d not in FINAL and not any(q.startswith(d.rstrip('/')+'/') for q in FINAL):errors.append(['missing-path',p,u,d]);continue
  if frag and d in FINAL and d.endswith('.md'):
   if LOCAL and d not in OUT and not (C/d).exists():continue
   if d not in targets:targets[d]=heading_ids(text(d))
   if urllib.parse.unquote(frag) not in targets[d]:errors.append(['missing-fragment',p,u])
# Hash complete result tree without downloading unchanged PDFs.
def blobhash(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
nt={p:{'mode':x['mode'],'sha':x['sha']} for p,x in T.items()}
for p,s in OUT.items():nt[p]={'mode':'100644','sha':blobhash(s.encode())}
def treehash(entries):
 root={}
 for p,x in entries.items():
  d=root;parts=p.split('/')
  for q in parts[:-1]:d=d.setdefault(q,{})
  d[parts[-1]]=(x['mode'],x['sha'])
 def rec(d):
  chunks=[]
  for name,item in sorted(d.items(),key=lambda t:(t[0]+('/' if isinstance(t[1],dict) else '')).encode()):
   mode,sha=('40000',rec(item)) if isinstance(item,dict) else item
   chunks.append(mode.encode()+b' '+name.encode()+b'\0'+bytes.fromhex(sha))
  b=b''.join(chunks);return hashlib.sha1(b'tree '+str(len(b)).encode()+b'\0'+b).hexdigest()
 return rec(root)
expected=treehash(nt)
report={'base':BASE,'original_txt_blob':source_original,'paragraphs':72,'modern_labels':len(labels),'registered_items':len(REG),'new_events':sum(r['kind']=='new' for r in REG),'same_event_merges':sum(r['kind']=='merge' for r in REG),'period_additions':sum(r['kind']=='period' for r in REG),'new_year_pages':len(CREATED),'year_pages':len(annual),'centuries':len(cl),'old_year_anchors':oldanchors,'old_paragraphs_checked':keptparas,'relative_links_checked':checked,'changed_files':len(OUT),'tree':expected,'errors':errors}
W.mkdir(exist_ok=True)
(W/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(W/'matches.json').write_text(json.dumps(MATCHES,ensure_ascii=False,indent=2))
(W/'registry.json').write_text(json.dumps(REG,ensure_ascii=False,indent=2))
if LOCAL:
 for p,s in OUT.items():
  f=W/'result'/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
 print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(bool(errors))
if errors:raise RuntimeError(json.dumps(errors[:30],ensure_ascii=False))
idx=str(Path(os.environ.get('RUNNER_TEMP','/tmp'))/'qin005-index');env=os.environ.copy();env['GIT_INDEX_FILE']=idx
try:Path(idx).unlink()
except FileNotFoundError:pass
git('read-tree',BASE,env=env)
rows=[]
for p,s in sorted(OUT.items()):
 sh=git('hash-object','-w','--stdin',input=s.encode()).decode().strip();rows.append('100644 '+sh+'\t'+p+'\0')
git('update-index','-z','--index-info',input=''.join(rows).encode(),env=env)
ts=git('write-tree','--missing-ok',env=env).decode().strip();assert ts==expected,(ts,expected)
cs=git('commit-tree',ts,'-p',BASE,input='Complete Shiji volume 005 within the shared chronology; preserve source text and merge overlapping events\n'.encode()).decode().strip()
git('push','origin',cs+':refs/heads/work/qin005-result-20261004')
report.update(result_commit=cs,result_tree=ts)
(W/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
