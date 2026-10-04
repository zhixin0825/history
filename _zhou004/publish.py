#!/usr/bin/env python3
"""Temporary deterministic text integration; publish only sources/years/meta."""
from pathlib import Path
import re,json,posixpath,collections,sys,subprocess,os,hashlib,urllib.parse
from periods import PERIOD,WESTERN,ANNUAL
import events
from undated import UNDATED
BASE='6e47e48051f613b3531859594c4163fadd930323'
LOCAL='--local' in sys.argv
W=Path('/mnt/data/zhou004') if LOCAL else Path('_zhou004')
R=W/'input' if LOCAL else Path('.')
def git(*a,input=None,env=None):return subprocess.check_output(['git',*a],input=input,env=env)
def gettree(ref):
    d={}
    for x in git('ls-tree','-rz',ref).split(b'\0'):
        if x:
            h,p=x.split(b'\t',1);mode,kind,sha=h.decode().split();d[p.decode()]={'mode':mode,'type':kind,'sha':sha}
    return d
TREE=json.loads((R/'tree.json').read_text()) if LOCAL else gettree(BASE)
OUT={};CACHE={};ROUTES=collections.defaultdict(list);CHANGES=[];NOTECOUNT=collections.Counter()
def original(p):
    if p not in CACHE:
        if LOCAL:CACHE[p]=(R/p).read_text(encoding='utf-8-sig')
        else:CACHE[p]=git('show',BASE+':'+p).decode('utf-8-sig')
    return CACHE[p]
def text(p):return OUT[p] if p in OUT else original(p)
def put(p,s):OUT[p]=s.rstrip()+'\n'
def rel(p,q,a=''):return posixpath.relpath(q,posixpath.dirname(p))+('#'+a if a else '')
def explicit(s):return re.findall(r'\bid=[\"\x27]([^\"\x27]+)',s)
def yearpath(y):
    c=((y-1)//100+1)*100
    return f'years/bce-{c:04}-{c-99:04}/bce-{y:04}.md'
SOURCE='sources/摘录/史记-卷004-周本纪.md'
META='meta/考证/史记-卷004-纪年与异说.md'
RECORD='meta/记录/史记-卷004-引文去向.md'
raw=original('sources/二十四史/txt/01_shiji_full.txt');lines=raw.splitlines()
a=lines.index('*01-004*');b=lines.index('*01-005*')
P=[];LABELS=[]
for n,line in enumerate(lines[a+1:b],a+2):
    if not line.strip():continue
    if len(line.strip())<70 and not any(z in line for z in ['。','：','「']):LABELS.append((n,line));continue
    P.append({'line':n,'text':line.strip(),'id':f'P{len(P)+1:03}'})
assert len(P)==82 and len(LABELS)==30,(len(P),len(LABELS))
source='''# 《史记》卷004｜周本纪阅读原文

[史料目录](../README.md) · [引文去向](../../meta/记录/史记-卷004-引文去向.md) · [时间入口](../../years/README.md)

本页逐字保存仓库完整工作TXT中卷004的实质文字。底本固定在提交 `'''+BASE+'''`，原文件Git blob为 `e3fdd88dc0dad8e918fb99979f759cf4a17ff144`。原有的30行人物标签另列结构记录，不当成司马迁的新增纪事；82个P号是项目阅读单元，不是古籍原有统一段号。

另对读[维基文库固定版本7909147](https://zh.wikisource.org/w/index.php?oldid=7909147&title=史記/卷004)。保留工作TXT字形、括注及可疑字句，不把公开章文本或本页改排冒称为中华书局定本，亦未重新编码原TXT。古籍原文属公有领域，工作文本源流与许可沿用仓库来源说明。核读与编写日期：2026-10-04。

'''
for p in P:
    source+=f'<a id="{p["id"].lower()}"></a>\n## {p["id"]}｜原TXT第{p["line"]}行\n\n{p["text"]}\n\n'
source+='## 工作TXT中的结构标签\n\n以下只记录底本的现代分段标签，不据标签造人物名或历史事件。“叔袭”尤其须回到正文断为“叔／袭杀”。\n\n| 原行 | 标签 |\n|---|---|\n'+''.join(f'| {n} | {s} |\n' for n,s in LABELS)
put(SOURCE,source)
def refs(path,ps):return ' · '.join(f'[卷004 P{int(i):03}]({rel(path,SOURCE,"p"+str(int(i)).zfill(3))})' for i in ps)
def route(ps,path,anchor,kind):
    for i in ps:
        r={'path':path,'anchor':anchor,'kind':kind}
        if r not in ROUTES[int(i)]:ROUTES[int(i)].append(r)
def append_foot(p,anchor,note,ps,title):
    s=text(p);entry=f'<a id="{anchor}"></a>\n### {title}\n\n'+refs(p,ps)+'。'+(' '+note if note else '')+'\n\n'
    # Insert after existing source notes and before final navigation.
    nav=list(re.finditer(r'^\[←[^\n]+|^\[上古目录\][^\n]+',s,re.M))
    pos=nav[-1].start() if nav and nav[-1].start()>len(s)//2 else len(s)
    put(p,s[:pos]+entry+s[pos:])
def insert_after_section(s,anchor,addition):
    tok=f'<a id="{anchor}"></a>';start=s.index(tok)
    # The next explicit anchor starts the next main section (or sources).
    m=re.search(r'\n<a id="[^\"]+"></a>|\n## 原文与出处',s[start+len(tok):])
    end=start+len(tok)+m.start() if m else len(s)
    return s[:end].rstrip()+'\n\n'+addition+'\n\n'+s[end:].lstrip()
for d in PERIOD:
    path='years/上古/'+d['file'];s=text(path);anchor=d['anchor'];foot='sj004-'+anchor
    block=f'<a id="{anchor}"></a>\n'+('## '+d['title']+'\n\n' if d['title'] else '')+d['body']+f' [原文与说明](#{foot})\n'
    if d['before']:
        mark=f'<a id="{d["before"]}"></a>';assert mark in s;put(path,s.replace(mark,block+'\n'+mark,1))
    else:put(path,insert_after_section(s,d['after'],block))
    append_foot(path,foot,d['note'],d['ps'],'卷四补充｜'+(d['title'] or {'release-details':'西伯获释','wen-campaigns':'西伯征行','wu-council':'盟津与武王辅臣','musicians':'商朝乐官出走','muye-orders':'牧野军令与败战','settlement-more':'战后安置与营洛','wugeng-outcome':'武庚之役与归政'}[anchor]))
    route(d['ps'],path,anchor,'时期叙事／同一事件补充')
# Deliberate correction: two classics differ on the death of the consorts.
p='years/上古/06-商末与周初.md';s=text(p)
a='武王斩下他的头悬于大白旗，妲己也被杀。';b='武王斩下他的头悬于大白旗；商王嬖妾的结局，两篇本纪的细节不同，见同号说明。'
assert a in s;s=s.replace(a,b,1);CHANGES.append([p,a,b])
s=s.replace('更完整的周初经过在下一卷核读后补入这些现有位置。','本轮卷四增补了这些现有位置，周初的治理继续见下一时期。')
s=s.replace('具体经过及各人的不同结局尚需后续卷章补充，不能从“诛之”扩写成此处所有参与者同日同样处死。','卷四已补出武庚、管叔被诛、蔡叔被放逐；仍不能从“诛之”扩大为所有参加者同日同样处死。')
s=s.replace('下一卷：《周本纪》（尚未顺序整卷完成）','[继续：西周的治理与危机 →](07-西周的治理与危机.md)')
put(p,s)
west='years/上古/07-西周的治理与危机.md'
s='''# 西周｜从成康治理到厉王危机

[← 商末与周初](06-商末与周初.md) · [上古目录](README.md) · [全部时间](../README.md) · [继续：前841年 →](../bce-0900-0801/bce-0841.md)

> **范围：成王亲政前后至厉王出奔以前。** 这里按事件先后与王序阅读，不按同一精度给所有早周故事配公元年。前1046年的克商采用工程方案；相对年数、制度性长段和史家评论仍分层。从共和元年前841年起，接入按世纪排列的年度页。

'''
for i,(a,h,b,ps,n) in enumerate(WESTERN,1):s+=f'<a id="{a}"></a>\n## {i}. {h}\n\n{b} [原文与说明](#s{i})\n\n';route(ps,west,a,'时期叙事或制度、评论')
s+='## 原文与出处\n\n'
for i,(a,h,b,ps,n) in enumerate(WESTERN,1):s+=f'<a id="s{i}"></a>\n### S{i}｜{h}\n\n'+refs(west,ps)+'。 '+n+'\n\n'
s+='[← 商末与周初](06-商末与周初.md) · [上古目录](README.md) · [继续：前841年 →](../bce-0900-0801/bce-0841.md)\n';put(west,s)
# Match the existing lone Shiji event instead of guessing its old identifier.
p=yearpath(453)
aids=[a for a in explicit(original(p)) if a.startswith('sj-')]
assert len(aids)==1,aids
for d in ANNUAL:
    if d['year']==453:d['event']=aids[0]
    d['ps']=[int(x) for x in d['ps']]
# New pages take the native numbered event/note format; old pages retain all IDs.
def next_event(s):
    a=[int(x) for x in re.findall(r'<a id="event-(\d+)"></a>',s)];return max(a,default=0)+1
new_years=[];annual_deltas=[]
for d in ANNUAL:
    y=d['year'];p=yearpath(y);foot=f'sj004-{y}-{NOTECOUNT[y]+1}';NOTECOUNT[y]+=1
    existed=p in TREE
    if not existed and p not in OUT:
        new_years.append(y)
        put(p,f'# 公元前{y}年｜{d["title"]}\n\n**{d["label"] or "本年已整理纪事"}**\n\n> 本页按古史年条与传统公元对照归档；明确有争议的日期见对应说明。月份、干支未直接换算为公历日期；不以已有一条材料表示本年所有历史都已收齐。\n\n## 本年纪事\n\n## 本年相关史料\n\n')
    s=text(p);ev=d['event']
    if ev is not None:
        ea='event-'+str(ev) if isinstance(ev,int) else ev
        mark=f'<a id="{ea}"></a>';assert mark in s,(y,ea)
        pos=s.index(mark);pattern=r'\n<a id="(?:event-\d+|sj-[^"]+)"|\n## (?:本年相关史料|原文与出处)|\n---'
        m=re.search(pattern,s[pos+len(mark):]);end=pos+len(mark)+m.start() if m else len(s)
        extra=('\n\n'+d['body'] if d['body'] else '\n\n')+f' [卷四互见与归年](#{foot})\n\n'
        s=s[:end].rstrip()+extra+s[end:]
        # Insert note within the existing same-number note when one exists.
        na='note-'+str(ev) if isinstance(ev,int) else None
        note=f'<a id="{foot}"></a>\n'+('#### ' if na and f'id="{na}"' in s else '### ')+d['title']+'｜卷四互见\n\n'+refs(p,d['ps'])+'。 '+d['note']+'\n\n'
        if na and f'<a id="{na}"></a>' in s:
            st=s.index(f'<a id="{na}"></a>');token=f'<a id="{na}"></a>';rest=s[st+len(token):]
            m=re.search(r'\n<a id="(?:note-\d+|cq-source-[^"]+)"|\n## |\n---',rest)
            en=st+len(token)+m.start() if m else len(s)
            s=s[:en].rstrip()+'\n\n'+note+s[en:]
        else:
            m=re.search(r'\n---\s*\n',s[pos:]);en=pos+m.start() if m else len(s)
            s=s[:en].rstrip()+'\n\n'+note+s[en:]
    else:
        no=next_event(s);ea='event-'+str(no);na='note-'+str(no)
        event=f'<a id="{ea}"></a>\n\n{no}. **{d["title"]}。** {d["body"]} [原文与说明](#{na})\n\n'
        marker='## 本年相关史料'
        assert marker in s,(y,'source heading missing')
        s=s.replace(marker,event+marker,1)
        note=f'<a id="{na}"></a>\n<a id="{foot}"></a>\n### {no}. {d["title"]}\n\n'+refs(p,d['ps'])+'。 '+d['note']+'\n\n'
        # before footer navigation, after existing notes
        last=s.rfind('\n---\n');last=last if last>len(s)//2 else len(s)
        s=s[:last].rstrip()+'\n\n'+note+s[last:]
    put(p,s);route(d['ps'],p,ea,'年页正文／同一事件互见')
    annual_deltas.append({'year':y,'event':ea,'source':d['ps'],'existing':existed})
# Full but explicitly undated narrative, attached as a bounded period supplement.
p=yearpath(315);s=text(p);at=s.index('## 本年相关史料')
u='## 两周分治时期的补充阅读｜以下各事未能确年\n\n> 这些材料只按本纪的相对叙述安排，不计为前315年的事件，也不是赧王继位以前的“登场前事”。它们发生在两周分治的背景下，先读清经过，待确年材料再归入相应年页。\n\n'
for a,h,b,ps,n in UNDATED:
    u+=f'<a id="{a}"></a>\n### {h}\n\n{b} [原文与说明](#sj004-undated-{a})\n\n';route(ps,p,a,'明确未确年的时期补充，不计本年')
s=s[:at]+u+s[at:]
for a,h,b,ps,n in UNDATED:s+=f'\n<a id="sj004-undated-{a}"></a>\n### 未确年说明｜{h}\n\n'+refs(p,ps)+'。 '+n+'\n'
put(p,s)
# Correct an already existing duplicate death found during the cross-book check.
p=yearpath(636);s=text(p);a='11. **晋惠公夷吾去世。** 晋国旧君一系彻底退出政治舞台。';b='11. **晋惠公夷吾之死属于前一年。** 本条保留旧有互见入口，实际丧事见[前637年](bce-0637.md#event-4)，不再将同一人死亡计入本年。'
if a in s:put(p,s.replace(a,b,1));CHANGES.append([p,a,b])
# Consistent metadata format, and a compact decision record rather than another timeline.
s='''# 《史记》卷004｜纪年、制度与异说

[考证目录](README.md) · [编写依据](../README.md) · [时间入口](../../years/README.md)

| 字段 | 内容 |
|---|---|
| 类型 | 考证 |
| 范围 | 《周本纪》整卷的归年、人物、制度与版本差别 |
| 状态 | 本轮实际对读的取舍记录；不宣称周史所有年代及细节已定 |

## 内容

### 本轮直接核读的材料

主线为仓库卷004全文82个实质段，另对读[维基文库固定版本7909147](https://zh.wikisource.org/w/index.php?oldid=7909147&title=史記/卷004)。王年对照使用同书[卷014《十二诸侯年表》](https://zh.wikisource.org/wiki/史記三家註/卷014)、[卷015《六国年表》](https://zh.wikisource.org/wiki/史記/卷015)，必要处查卷005、卷033；与春秋时段重叠者核对仓库已经引用的《春秋》《左传》年条。仅为互证读到他卷相关部分，不把卷005或卷014等整卷工作提前计作完成。

前1046年克商仍沿此前注明的断代工程方案，不自行声称重算了天象与碳十四数据。前共和的王年本卷多有困难，采用时期叙事；共和以后以连续年表、经传相互校核，但“有年表”不等于同书所有文字自动一致。新出土文献也不与传世史书机械投票，各争点单独处理。

<a id="republic"></a>
### 共和：主持者的不同记载要保留

《周本纪》以周、召二相行政解释共和。清华《系年》释文则出现“共伯和立”，而关于十四年的句读也存在讨论。本轮核读[孙振兴《清华简〈系年〉标点质疑一则》](https://www.fdgwz.org.cn/Web/Show/1987)，注意其将十四年与执政时段相连，避免误解为宣王出生十四年后直接登位。正文记政权转移和共和阶段，不拼出文献没有的三人共治，更不借古词宣称有现代共和国。

<a id="ping"></a>
### 幽王末年与平王东迁：战争可叙，异年不藏

卷004保存烽火失信故事，也写废后易储、申侯与戎人的战争；正文采用继承冲突与战争作为主要线索，烽火与龙漦等传说在同号说明保留。没有因一本书没有某故事便简单宣布故事已被彻底证伪，也没有把褒姒个人写成所有政治失败的原因。

清华《系年》有关携王、“周亡王九年”、迎平王与随后东徙的句子，与传统前770年东迁的排列不易直接相合。本轮核读[清华读书会研读札记（二）](https://fdgwz.org.cn/Web/Show/1760)和[魏栋关于“周亡王九年”的解释](https://fdgwz.org.cn/Web/Show/1895)，两者对断句、王位状态、绝对年的处理不同。这里只据其证明问题尚在讨论，不从某一篇提出的新年代推成全学界定论。读者主线暂用卷014的传统年坐标，异说附在前771、770两页。

### 本纪与既有年页不合处的处理

| 事项 | 本纪或工作文本 | 本轮安排 |
|---|---|---|
| 鲁武公朝周 | 宣王十二年；卷033又有武公九年 | 暂列前816，注明前817异说，不重复一趟朝觐 |
| 宣王即位 | 共和十四年接立 | 前828记继立；前827是次年元年，不创造两次登位 |
| 许田 | 桓王五年一句带过 | 前715交祊；前711交易盟约收尾 |
| 王子带召戎、奔齐 | 襄王三年压缩数事 | 前649攻周、前648奔齐与调处 |
| 王子带返国 | 襄王十二年 | 依僖公二十二年，前638 |
| 王命滑、借狄与出奔 | 襄王十三、十五、十六年分列 | 以现有前636经传完整链为正文；王使、富辰等补同事 |
| 迎襄王与赐晋礼 | 紧邻写迎王、赐重耳礼器 | 前635迎王与赐田；前632践土册命、冬河阳另分 |
| 襄、顷、匡之死 | 前代积年产生一年偏差 | 依经传前619、613、607，继承者补在同条 |
| 景王之死 | 二十年 | 依卷014与昭公二十二年，前520；不另写前525 |
| 王猛之死 | 本纪子朝杀之 | 保留经传病逝叙述，记异说，不伪造第二次死法 |
| 诸侯城周 | 紧随敬王四年 | 前510请城与分派、前509完工，不误作前516 |
| 敬王避乱地点 | 十六年奔晋 | 依经传前504出居姑莸，前503受晋援回返 |
| 孔子之死与灭陈 | 同在敬王四十一年段 | 前479孔子卒，前478楚灭陈 |
| 敬王之死 | 四十二年 | 依哀公十九年敬王丧事，前476 |
| 元王在位 | 八年 | 依表传衔接，前469卒，次年贞定王元年 |
| 思王名 | 现代标签写“叔袭” | 正文断为弟叔／袭杀，不造“叔袭”之名 |
| 烈王在位 | 十年 | 依六国年表七年，前369卒，前368显王元年 |
| 秦惠王早年称谓 | 本纪追称王 | 前336、334用惠文君；前325记称王 |
| 秦取西周、宝器转移 | 段中连续后叙 | 前256西周献城、赧王死；前255周民东亡及器物转移 |
| 灭东周、周祀 | 本纪“周既不祀”，秦本纪“不绝其祀” | 前249政治兼并；保留后裔奉祀安排及两文差别 |
| 周子南君 | 在太史公论末尾 | 依汉武帝纪、卷020，前113年，绝不放在周亡年 |

这些取舍不是统一宣称《左传》永远优于《史记》：本卷有些是篇内压缩，有些是同书年表异文，有些是实质叙事冲突。具体依据随年度原文脚注同行，未以源书名替代判断。

<a id="two-zhou"></a>
### 两周分治与无确年段落

P064是从考王封弟，经数代传承到巩地另一周国的总括；P069又说赧王时分治、徙居西周。P070太子争立、P072秦借道、P073召周君、P074两周相战、P075雍氏征兵粮都没有足够独立纪年。本轮在[前315年页的时期补充](../../years/bce-0400-0301/bce-0315.md#two-zhou-background)给出完整白话和原文入口，显著标明不是前315年事件，也不冒称是继位以前的前事。

史厌、苏代、马犯等说辞里，计划、威胁、猜测和最后实际结果分别处理。别人说周王病重，不等于已核实病情；建议献地、交鼎，不等于已经兑现。尤其不能只把未标年的段落跟在“八年”后，就说所有情节都发生在前307。

### 原文与实物的证据层次

武王征商可与先前核读的利簋等材料互证，但这不能扩大为每一项兵力、尸体处置、白鱼赤乌都获金文证明。反过来，某种祥瑞不可靠，也不意味着该卷所有征战和承继都不存在。姚、褒姒、密康三女等故事的道德判断留在出处，不用来替王朝覆亡作单因解释。

《甫刑》的三千、五服的五百里、穆王的年龄与在位数，都是不同文本层级的数值。原数保留，未换算成现代税率、法条库、面积或出生年份。

<a id="text"></a>
### 几处工作底本字句

“鲁天子之命”“迁其君薄泵”“王赧谓成君”及周最／周聚的括注，都保留在原文摘录，不从可疑句子补造新史事。“康诰”与今传康王即位文告的篇名差别在时期页说明。原TXT中的30行现代人物标签不冒充本纪正文；正文的82段是工作阅读编号，不是中华书局点校本的自然段编号。本轮未逐页核阅现代扫描本，不声称独立点校完成。

## 关联入口

[卷004原文](../../sources/摘录/史记-卷004-周本纪.md) · [全卷去向](../记录/史记-卷004-引文去向.md) · [西周时期页](../../years/上古/07-西周的治理与危机.md) · [前841年](../../years/bce-0900-0801/bce-0841.md)
'''
put(META,s)
assert set(ROUTES)==set(range(1,83)),sorted(set(range(1,83))-set(ROUTES))
s='''# 《史记》卷004｜周本纪引文去向

[记录目录](README.md) · [编写依据](../README.md) · [时间目录](../../years/README.md)

| 字段 | 内容 |
|---|---|
| 类型 | 记录 |
| 范围 | 卷004全文；后稷至周亡及汉代周子南君后记 |
| 状态 | 82个实质文本段均已归入叙事、同事互见或明确的未确年说明 |

## 内容

### 底本、边界与完成口径

本轮接续提交 `'''+BASE+'''`。工作TXT原样抽取为[卷004阅读原文](../../sources/摘录/史记-卷004-周本纪.md)，以82个P号定位，30行现代人物标签另行登记。按整卷内容读完后，回到已有页合并事件；不复制一套“周本纪年表”。原有卷001—003、春秋255年及其他史书材料保留。

完成指本卷实质段落都有可读位置，不是每句古语都已独立训诂，也不表示本纪与年表、经传、出土文字的全部差别已经定论。无确年的说辞和跨代制度不伪装成某一年的新事件。原文、年页和本表均保留返回链接，便于继续核对。

### 全段去向

| 单元 | 原文段首 | 阅读位置与处理 |
|---|---|---|
'''
for i,p in enumerate(P,1):
    ds='；'.join(f'[{r["path"].split("/")[-1][:-3]} · {r["anchor"]}]({rel(RECORD,r["path"],r["anchor"])})（{r["kind"]}）' for r in ROUTES[i])
    s+=f'| [P{i:03}]({rel(RECORD,SOURCE,"p"+str(i).zfill(3))}) | {p["text"][:22].replace("|","｜")}… | {ds} |\n'
s+='''
### 特别保留的边界

商周交接仍在既有时期页，成王以后加一页西周时期，前841年起进入世纪目录。敬王、景王等与经传不同的年份并未再次生成重复的死亡。周末兼并分前256、255、249年；篇末汉代封嘉回到前113年。

本轮新增33张年度页，年度正文由290增至323张，世纪目录由9增至10个；上古时期正文由6增至7页。所有255张春秋时段年页仍在，未按史书另建时间线。

本轮还发现旧前636年页重复写晋惠公去世，已将其改为前637年丧事的互见说明，保留旧条号与锚点。另将商末页关于妲己死法的无条件表述改为标明两本纪异说，其余旧文不借本轮任意改写。

下一卷为005《秦本纪》。本轮仅为核年查看其中相关段落，未将整卷计作完成。

## 关联入口

[纪年与异说](../考证/史记-卷004-纪年与异说.md) · [原文](../../sources/摘录/史记-卷004-周本纪.md) · [卷003](史记-卷003-引文去向.md) · [记录目录](README.md)
'''
put(RECORD,s)
# Indices: only one current canonical path per year, with century boundaries.
annual=sorted([p for p in set(TREE)|set(OUT) if re.fullmatch(r'years/(?:bce|ce)-\d{4}-\d{4}/(?:bce|ce)-\d{4}\.md',p)],key=lambda p: -int(Path(p).stem[4:]) if Path(p).name.startswith('bce') else int(Path(p).stem[3:]))
def ydisplay(p):
    st=Path(p).stem;return ('公元前'+str(int(st[4:])) if st.startswith('bce') else '公元'+str(int(st[3:])))+'年'
for i,p in enumerate(annual):
    s=text(p);old=s
    nav=('['+'← 上一张已编年页：'+ydisplay(annual[i-1])+']('+rel(p,annual[i-1])+') · ' if i else '')+'[本世纪目录](README.md) · [全部世纪](../README.md)'+(' · [下一张已编年页：'+ydisplay(annual[i+1])+' →]('+rel(p,annual[i+1])+')' if i+1<len(annual) else '')
    s=re.sub(r'^\[(?:← 上一张|本世纪目录)[^\n]*\[全部世纪\][^\n]*\n?','',s,flags=re.M).strip()
    s=re.sub(r'\n---\s*$','',s).strip()
    h,_,rest=s.partition('\n');new=h+'\n\n'+nav+'\n\n'+rest.strip()+'\n\n---\n\n'+nav+'\n'
    if re.sub(r'\s+','',new)!=re.sub(r'\s+','',old) or p in OUT:put(p,new)
groups=collections.defaultdict(list)
for p in annual:groups[posixpath.dirname(p)].append(p)
ordered=list(groups)
def groupname(g):
    _,lo,hi=Path(g).name.split('-');return ('公元前' if Path(g).name.startswith('bce') else '公元')+str(int(lo))+'—'+str(int(hi))+'年'
for i,g in enumerate(ordered):
    p=g+'/README.md';nav=('[← 上一个已有内容的世纪]('+rel(p,ordered[i-1]+'/README.md')+') · ' if i else '[上古时期](../上古/README.md) · ')+'[全部世纪](../README.md) · [项目首页](../../README.md)'+(' · [下一个已有内容的世纪 →]('+rel(p,ordered[i+1]+'/README.md')+')' if i+1<len(ordered) else '')
    ss='# '+groupname(g)+'\n\n'+nav+f'\n\n本目录覆盖100年，现有 **{len(groups[g])}** 张年度正文。只列已有页面，不以空文件表示已经完成。\n\n| 年份 | 本页主线 |\n|---|---|\n'
    for q in groups[g]:ss+='| ['+ydisplay(q)+']('+Path(q).name+') | '+text(q).splitlines()[0].lstrip('# ').replace('|','｜')+' |\n'
    ss+='\n'+nav+'\n'
    if p not in TREE or ss!=original(p):put(p,ss)
century_rows='| 世纪范围 | 已有年份页 | 阅读入口 |\n|---|---:|---|\n'
for g in ordered:century_rows+='| '+groupname(g)+' | '+str(len(groups[g]))+' | [打开本世纪]('+posixpath.relpath(g+'/README.md','years')+') |\n'
p='years/README.md';s=original(p)
s=s.replace('→ [夏代](上古/03-夏代.md)','→ [夏代](上古/03-夏代.md)')
# replace only the century table, retain the established coverage narrative
m=re.search(r'\| 世纪范围 \|[\s\S]*?(?=\n\n)',s);assert m;s=s[:m.start()]+century_rows.rstrip()+s[m.end():]
s=s.replace('→ [商末与周初](上古/06-商末与周初.md)','→ [商末与周初](上古/06-商末与周初.md) → [西周的治理与危机](上古/07-西周的治理与危机.md)')
if '07-西周' not in s:s=s.replace('## 世纪目录','上古叙事现续至[西周的治理与危机](上古/07-西周的治理与危机.md)，再从[前841年](bce-0900-0801/bce-0841.md)进入年度页。\n\n## 世纪目录')
put(p,s)
p='README.md';s=original(p);m=re.search(r'\| 世纪范围 \|[\s\S]*?(?=\n\n)',s);assert m
rootrows=century_rows.replace('](','](years/')
s=s[:m.start()]+rootrows.rstrip()+s[m.end():]
s=s.replace('**290**',f'**{len(annual)}**').replace('**9** 个世纪',f'**{len(groups)}** 个世纪').replace('正文 **6** 页','正文 **7** 页')
s=re.sub(r'本次按顺序完成《史记》卷001[\s\S]*?下一卷为004《周本纪》。','本次按顺序完成《史记》卷001—004的整卷阅读与编写；下一卷为005《秦本纪》。',s)
s=s.replace('下一卷为004《周本纪》','下一卷为005《秦本纪》')
s=s.replace('已按顺序完成《史记》卷001、卷002、卷003的整卷阅读与编年汇入；下一卷为005《秦本纪》。','已按顺序完成《史记》卷001—004的整卷阅读与编年汇入；下一卷为005《秦本纪》。')
line='| 7 | [西周的治理与危机](years/上古/07-西周的治理与危机.md) | 前共和用时期叙事；共和以后接世纪年页 |\n'
m=re.search(r'^\| 6 \|[^\n]*\n',s,re.M);assert m;s=s[:m.end()]+line+s[m.end():]
if '卷001—004' not in s:
    s=s.replace('## 世纪目录','本轮已按卷序完成《史记》001—004；[卷四全段去向](meta/记录/史记-卷004-引文去向.md)与[纪年取舍](meta/考证/史记-卷004-纪年与异说.md)可逐项核对。下一卷005。\n\n## 世纪目录')
put(p,s)
p='years/上古/README.md';s=original(p);m=re.search(r'^\| 6 \|[^\n]*\n',s,re.M);assert m
s=s[:m.end()]+'| 7 | 西周前期至厉王危机 | [西周的治理与危机](07-西周的治理与危机.md) | 前共和不强配王年；前841起接年度页 |\n'+s[m.end():]
s=s.replace('卷003《殷本纪》。','卷003《殷本纪》、卷004《周本纪》。').replace('28、35、33','28、35、33、82')
s=s.replace('[断代工程的使用范围]', '[卷004引文去向](../../meta/记录/史记-卷004-引文去向.md) · [断代工程的使用范围]',1)
a=s.index('## 后续时间线');s=s[:a]+'''## 后续时间线

西周时期接[前841年](../bce-0900-0801/bce-0841.md)，其后已确定的事进入同一套世纪年页；未写出的年份仍不以空页填满。卷004已读到周亡及汉代封嘉的篇末后记。下一卷005《秦本纪》，重叠的周秦往来继续补既有事件，不新建一条秦国专用年表。
''';put(p,s)
for p,row in [
('meta/记录/README.md','| [《史记》卷004引文去向](史记-卷004-引文去向.md) | 后稷至周亡及汉代后记，82个实质段均有去向 |'),
('meta/考证/README.md','| [《史记》卷004纪年与异说](史记-卷004-纪年与异说.md) | 共和、东迁、经传异年、两周分治与无确年说辞 |')]:
    s=original(p);at=s.index('|---|---|')+len('|---|---|');s=s[:at]+'\n'+row+s[at:]
    s=re.sub(r'卷001[与、]002[与、]003已完成去向整理，下一卷004尚未计作完成','卷001—004已完成去向整理，下一卷005尚未计作完成',s)
    s=s.replace('卷001、002、003已完成去向整理，下一卷004尚未计作完成','卷001—004已完成去向整理，下一卷005尚未计作完成')
    put(p,s)
# Validate text, anchors, citations, structure and corpus preservation.
FINAL=set(TREE)|set(OUT)
errors=[]
assert {p.split('/')[0] for p in FINAL if '/' in p}=={'sources','years','meta'}
assert all(yearpath(y) in FINAL for y in range(468,723))
assert len(annual)==290+len(new_years)
assert len(set(Path(p).name for p in annual))==len(annual)
assert not any(re.search(r'/(?:bce|ce)-0000\.md$',p) for p in FINAL)
assert not any(p.endswith(('.py','.yml','.yaml','.pyc')) for p in FINAL)
# Source body strictly matches all 82 source paragraphs, and only labels are separated.
for q in P:assert q['text'] in text(SOURCE)
for i,ds in ROUTES.items():
    for d in ds:
        if d['path'] not in FINAL or d['anchor'] not in explicit(text(d['path'])):errors.append(['route',i,d])
def mdlinks(s):
    out=[];i=0
    while True:
        a=s.find('](',i)
        if a<0:break
        j=a+2;depth=1;esc=False;angle=False
        while j<len(s) and depth:
            c=s[j]
            if esc:esc=False
            elif c=='\\':esc=True
            elif c=='<':angle=True
            elif c=='>':angle=False
            elif c=='(' and not angle:depth+=1
            elif c==')' and not angle:depth-=1
            j+=1
        if depth:i=a+2
        else:out.append((a+2,j-1,s[a+2:j-1]));i=j
    return out
def allanchors(s):
    a=set(explicit(s));cnt=collections.Counter()
    for h in re.findall(r'^#{1,6}\s+(.+)',s,re.M):
        h=re.sub(r'<[^>]+>','',h);h=re.sub(r'\[([^]]+)\]\([^)]*\)',r'\1',h);h=h.replace('`','').replace('*','')
        h=re.sub(r'[^\w\s-]','',h.lower()).replace(' ','-');n=cnt[h];cnt[h]+=1;a.add(h+('-'+str(n) if n else ''))
    return a
checked=0;oldanchors=0
for p in FINAL:
    if not p.endswith('.md'):continue
    if LOCAL and p not in OUT and not (R/p).exists():continue
    s=text(p);a=explicit(s)
    if len(a)!=len(set(a)):errors.append(['duplicate-ids',p])
    if p in OUT and len(re.findall(r'^# ',s,re.M))!=1:errors.append(['h1',p])
    if p in TREE and (p.startswith('years/') or p.startswith('meta/')):
        for a in explicit(original(p)):
            oldanchors+=1
            if a not in explicit(s):errors.append(['lost-anchor',p,a])
    for _,_,u in mdlinks(s):
        u=u.strip();u=u[1:-1] if u.startswith('<') and u.endswith('>') else u
        if re.match(r'^\w+:',u):continue
        v,_,f=u.partition('#');v=urllib.parse.unquote(v).replace('\\(','(').replace('\\)',')')
        q=posixpath.normpath(posixpath.join(posixpath.dirname(p),v)) if v else p;checked+=1
        if q not in FINAL and not any(z.startswith(q.rstrip('/')+'/') for z in FINAL):errors.append(['link',p,u,q]);continue
        if f and q in FINAL and q.endswith('.md'):
            if LOCAL and q not in OUT and not (R/q).exists():continue
            if urllib.parse.unquote(f) not in allanchors(text(q)):errors.append(['fragment',p,u,q])
def norm(s):
    for a,b,u in reversed(mdlinks(s)):s=s[:a]+s[b:]
    s=re.sub(r'<[^>]+>','',s);return ''.join(re.findall(r'[\u3400-\u9fffA-Za-z0-9]',s))
conserved=0
for p in TREE:
    if not re.fullmatch(r'years/.+/(?:bce|ce)-\d{4}\.md',p) and not (p.startswith('years/上古/') and not p.endswith('README.md')):continue
    before=original(p);after=norm(text(p))
    for q,a,b in CHANGES:
        if p==q:before=before.replace(a,b)
    before=before.replace('更完整的周初经过在下一卷核读后补入这些现有位置。','本轮卷四增补了这些现有位置，周初的治理继续见下一时期。').replace('具体经过及各人的不同结局尚需后续卷章补充，不能从“诛之”扩写成此处所有参与者同日同样处死。','卷四已补出武庚、管叔被诛、蔡叔被放逐；仍不能从“诛之”扩大为所有参加者同日同样处死。')
    for par in re.split(r'\n\s*\n',before):
        if par.strip().startswith(('#','<a','<!--','[←','[本世纪','[上古')):continue
        n=norm(par)
        if len(re.findall('[\u3400-\u9fff]',n))<10:continue
        conserved+=1
        if n not in after:errors.append(['lost-prose',p,par[:110]])
report=dict(base=BASE,source_paragraphs=len(P),source_labels=len(LABELS),new_years=sorted(new_years,reverse=True),annual_total=len(annual),centuries=len(groups),ancient_pages=7,source_body_characters=sum(len(d['text']) for d in P),old_explicit_anchors_checked=oldanchors,old_paragraphs_checked=conserved,relative_links_checked=checked,changed_files=len(OUT),intended_corrections=CHANGES,errors=errors)
W.mkdir(exist_ok=True)
(W/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
if LOCAL:
    target=W/'result';target.mkdir(exist_ok=True)
    for p,s in OUT.items():
        f=target/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s,encoding='utf-8')
    (W/'out.json').write_text(json.dumps(OUT,ensure_ascii=False))
    print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(bool(errors))
if errors:raise RuntimeError(json.dumps(errors[:25],ensure_ascii=False))
idx=str(Path(os.environ.get('RUNNER_TEMP','/tmp'))/'zhou004-index');env=os.environ.copy();env['GIT_INDEX_FILE']=idx
try:Path(idx).unlink()
except FileNotFoundError:pass
git('read-tree',BASE,env=env)
rows=[]
for p,s in sorted(OUT.items()):
    sha=git('hash-object','-w','--stdin',input=s.encode()).decode().strip();rows.append('100644 '+sha+'\t'+p+'\0')
git('update-index','-z','--index-info',input=''.join(rows).encode(),env=env)
treesha=git('write-tree','--missing-ok',env=env).decode().strip()
expected=(W/'expected-tree.txt').read_text().strip()
assert treesha==expected,(treesha,expected)
commit=git('commit-tree',treesha,'-p',BASE,input='Integrate complete Shiji volume 004 into the canonical chronology; preserve existing events and date variants\n'.encode()).decode().strip()
git('push','origin',commit+':refs/heads/work/zhou004-result-20261004')
report.update(result_commit=commit,result_tree=treesha)
(W/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
