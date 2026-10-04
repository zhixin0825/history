#!/usr/bin/env python3
"""One-shot layout change; publishes only a review branch, never main."""
from pathlib import Path
import collections, hashlib, html, json, os, posixpath, re, subprocess, sys, unicodedata
from urllib.parse import quote, unquote, urlsplit, urlunsplit

BASE = 'ab0b698f5908bafa621ac6a54078c1115eed3580'
RESULT = 'work/century-layout-result-20261004'
LOCAL = '--local' in sys.argv
ROOT = Path('/mnt/data/century-work/old') if LOCAL else Path('.')
OUT = Path('/mnt/data/century-work/new') if LOCAL else Path('_work/output/result')
REPORTDIR = OUT.parent

def git(*args, input=None, env=None):
    return subprocess.check_output(['git', *args], input=input, env=env)

def gitsha(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

if LOCAL:
    TREE = json.loads((ROOT/'tree.json').read_text())
else:
    TREE = {}
    for row in git('ls-tree','-rz',BASE).split(b'\0'):
        if row:
            m,p=row.split(b'\t',1); mode,typ,sha=m.decode().split()
            TREE[p.decode()]={'mode':mode,'type':typ,'sha':sha}
CACHE = {}
def raw(p):
    if p not in CACHE:
        if LOCAL:
            CACHE[p]=(ROOT/p).read_bytes()
        else:
            CACHE[p]=git('show', BASE+':'+p)
        assert gitsha(CACHE[p])==TREE[p]['sha'], ('Input hash mismatch',p)
    return CACHE[p]
def read(p):return raw(p).decode('utf-8-sig')

# Every range contains exactly 100 historical year numbers, with no year zero.
def year(p):
    m=re.search(r'(bce|ce)-(\d{4})\.md$',p)
    if not m:return None
    n=int(m[2]);assert n>0
    return -n if m[1]=='bce' else n

def century(n):
    a=((abs(n)-1)//100)*100+1; b=a+99
    return f'bce-{b:04d}-{a:04d}' if n<0 else f'ce-{a:04d}-{b:04d}'

def ylabel(n):return ('公元前' if n<0 else '公元')+str(abs(n))+'年'
def cname(c):
    era,a,b=c.split('-');return ('公元前' if era=='bce' else '公元')+str(int(a))+'—'+str(int(b))+'年'

def ypath(n):return f'years/{century(n)}/'+('bce-' if n<0 else 'ce-')+f'{abs(n):04d}.md'

# meta has four functions, not separate histories by book.
META = {
 '编辑规则.md':('规范/编写规则.md','编写规则','规范','全项目','已确认规则；目录口径按本次要求更新'),
 '人物登场说明.md':('记录/人物登场索引.md','人物登场索引','索引','已审材料中的人物前事','暂定阅读位置；不改变原事发生时间'),
 '来源说明.md':('来源/史料目录与许可.md','史料目录与许可','来源','已入库史料的版本、来源、许可和校验','沿用既有来源记录；未作新的版本鉴定'),
 '来源材料/版本核查.md':('来源/2026-09-28-底本核查.md','底本核查（2026-09-28）','来源','2026-09-28 所核《春秋》《资治通鉴》文本','历史核查记录；其中“当前”指原核查日期'),
 '伍子胥-异说与未定年.md':('考证/史记-卷066-伍子胥列传-异说.md','《伍子胥列传》异说与未定年材料','考证','《史记》卷066及所列互见材料','异说、未定年和作者评论分层保留'),
 '前468年后衔接说明.md':('考证/前0468年后-编年衔接.md','前468年后的编年衔接','考证','《左传》年条之后的编年底本衔接','衔接依据；不代表后续年份已经编成'),
 '史记66-引文去向.md':('记录/史记-卷066-引文去向.md','《史记》卷066引文去向','引文索引','《伍子胥列传》24个正文段及结构标记','已记录去向；不等于24个独立事件'),
 '后汉书1-异说说明.md':('考证/后汉书-卷001-光武帝纪-异说.md','《光武帝纪》异说与叙事边界','考证','公元22—25年首批材料','保留既有取舍；未新增史实考证'),
 '后汉书1-引文去向.md':('记录/后汉书-卷001-引文去向.md','《后汉书》卷001引文去向','引文索引','《光武帝纪》原TXT第3—47行','首批材料已经进入公元22—25年页'),
 '哀公段-考证.md':('考证/鲁哀公-考证.md','鲁哀公时期考证','考证','哀公组实际阅读的古籍、古注及研究线索','阅读范围与未核事项分别保留'),
 '定公段-考证.md':('考证/鲁定公-考证.md','鲁定公时期考证','考证','定公组实际阅读的古籍、古注及研究线索','阅读范围与未核事项分别保留'),
 '宣帝纪-归年说明.md':('考证/晋书-卷001-宣帝纪-归年.md','《宣帝纪》归年依据','考证','《晋书》卷001首批司马懿材料','按实际年份安放；不按本纪叙次硬排'),
 '宣帝纪-未定年材料.md':('考证/晋书-卷001-宣帝纪-未定年.md','《宣帝纪》未定年材料','考证','《晋书》卷001首批无法精确归年的材料','未确年，不据目录位置补造日期'),
 '文献与评论.md':('考证/史记-文献与评论.md','《史记》文献与评论','考证','旧试编保留的文献、论赞、后补与异说','不把作者评论或后补材料当作当年事件'),
 '未定年材料.md':('考证/史记-未定年与跨年材料.md','《史记》未定年与跨年材料','考证','旧试编保留的未确年、跨年与人物背景','逐条保留原时间判断，仍待进一步归年'),
 '汉书1-引文去向.md':('记录/汉书-卷001-引文去向.md','《汉书》卷001引文去向','引文索引','《高帝纪》工作文本P001—P115','P001—P033首批已入年页；其余状态见表'),
 '迁移说明.md':('记录/2026-10-03-三目录迁移.md','三目录迁移记录（2026-10-03）','迁移记录','提交ab0b698f的三目录迁移及旧条目对应关系','历史结构记录；现行目录规则见规范'),
 '鲁世家-哀公段核对.md':('考证/史记-卷033-鲁周公世家-哀公核对.md','《鲁周公世家》哀公时期核对','考证','《史记》卷033哀公段','保留逐项归年、互见与异文'),
 '鲁世家-定公段核对.md':('考证/史记-卷033-鲁周公世家-定公核对.md','《鲁周公世家》定公时期核对','考证','《史记》卷033定公段','保留逐项归年、互见与异文'),
 '鲁世家-昭公段核对.md':('考证/史记-卷033-鲁周公世家-昭公核对.md','《鲁周公世家》昭公时期核对','考证','《史记》卷033昭公段','保留逐项归年、互见与异文'),
}
RAW_META = {
 'SHA256SUMS.txt':'来源/原始记录/SHA256SUMS.txt',
 '来源材料/CCDH_README.txt':'来源/原始记录/CCDH_README.txt',
 '来源材料/KANRIPO_SOURCE.txt':'来源/原始记录/KANRIPO_SOURCE.txt',
 '来源材料/ccdh_13_classics_manifest.json':'来源/原始记录/ccdh_13_classics_manifest.json',
 '来源材料/osf_manifest.json':'来源/原始记录/osf_manifest.json',
}
MAP={p:p for p in TREE}
for p in TREE:
    if re.fullmatch(r'years/(bce|ce)-\d{4}\.md',p):MAP[p]=ypath(year(p))
    if p.startswith('meta/') and p!='meta/README.md':
        k=p[5:];assert k in META or k in RAW_META, ('Unclassified meta',p)
        MAP[p]='meta/'+(META[k][0] if k in META else RAW_META[k])
assert len(set(MAP.values()))==len(MAP)

# Balanced inline targets plus reference definitions and HTML href/src.
def link_spans(s):
    spans=[]; i=0
    while (a:=s.find('](',i))>=0:
        j=a+2; dep=1; esc=False; angle=False
        while j<len(s) and dep:
            c=s[j]
            if esc:esc=False
            elif c=='\\':esc=True
            elif c=='<' and j==a+2:angle=True
            elif c=='>' and angle:angle=False
            elif not angle and c=='(':dep+=1
            elif not angle and c==')':dep-=1
            j+=1
        if not dep:spans.append((a+2,j-1,s[a+2:j-1]));i=j
        else:i=a+2
    for m in re.finditer(r'(?m)^\s{0,3}\[(?!\^)[^\]\n]+\]:\s*(<[^>]+>|\S+)',s):
        spans.append((m.start(1),m.end(1),m[1]))
    for m in re.finditer(r'\b(?:href|src)=["\x27]([^"\x27]+)["\x27]',s):
        spans.append((m.start(1),m.end(1),m[1]))
    return sorted(set(spans))

def split_target(v):
    if v.startswith('<') and '>' in v:
        i=v.index('>');return v[1:i], v[i+1:]
    m=re.match(r'^(.*?)\s+(["\x27].*["\x27])$',v)
    return (m[1], ' '+m[2]) if m else (v,'')

def rewrite_target(u,old,new):
    if re.match(r'^[a-zA-Z][\w+.-]*:',u) or u.startswith('//'):
        return u
    u=u.replace('\\(','(').replace('\\)',')')
    sp=urlsplit(u); p=unquote(sp.path)
    resolved=posixpath.normpath(posixpath.join(posixpath.dirname(old),p)) if p else old
    if resolved not in MAP:
        if resolved=='meta/来源材料':dest='meta/来源/原始记录'
        else:dest=resolved
    else:dest=MAP[resolved]
    if dest==new and not p:out=''
    else:out=posixpath.relpath(dest,posixpath.dirname(new) or '.')
    return urlunsplit(('', '', out, sp.query, sp.fragment))

def rewire(s,old,new):
    for a,b,v in reversed(link_spans(s)):
        u,tail=split_target(v.strip());nu=rewrite_target(u,old,new)
        if ' ' in nu and not s[max(0,a-6):a].endswith(('href="','src="')):nu='<'+nu+'>'
        s=s[:a]+nu+tail+s[b:]
    return s

def slug(s):
    s=re.sub(r'<[^>]*>','',s)
    s=re.sub(r'\[([^]]*)\]\([^)]*\)',r'\1',s).replace('`','').replace('*','')
    return ''.join(c for c in s.lower() if c in '-_ ' or unicodedata.category(c)[0] in 'LN').replace(' ','-')

def heading_ids(s):
    ids=[];counts=collections.Counter();fence=False
    for l in s.splitlines():
        if l.startswith('```'):fence=not fence
        if fence:continue
        m=re.match(r'^(#{1,6})\s+(.+?)\s*#*$',l)
        if m:
            x=slug(m[2]);n=counts[x];counts[x]+=1;ids.append((l,x if not n else x+'-'+str(n)))
    return ids

def explicit(s):return re.findall(r'\bid=["\x27]([^"\x27]+)',s)

def tidy(s):
    s=s.replace('\r\n','\n').replace('\r','\n')
    ls=[l.rstrip() + ('  ' if l.endswith('  ') and l.strip() else '') for l in s.splitlines()]
    out=[]
    for i,l in enumerate(ls):
        if not l.strip():
            prev=next((x for x in reversed(out) if x.strip()),'')
            nxt=next((x for x in ls[i+1:] if x.strip()),'')
            if prev.startswith('|') and nxt.startswith('|'):continue
        out.append(l)
    s='\n'.join(out)
    return re.sub(r'\n{3,}','\n\n',s).strip()+'\n'

NEW={MAP[p]:{'sha':m['sha'],'mode':m['mode']} for p,m in TREE.items()}
ORIGINAL_TEXT={}
FORMAT_STATS=collections.Counter()
def put(p,s):NEW[p]={'content':s.encode('utf-8'),'mode':'100644'}
def content(p):
    n=NEW[p]
    return n['content'].decode('utf-8') if 'content' in n else read(next(k for k,v in MAP.items() if v==p))

for p in TREE:
    if not p.endswith('.md'):continue
    if LOCAL and not (ROOT/p).exists():continue
    s=read(p);ORIGINAL_TEXT[p]=s
    ns=rewire(s,p,MAP[p])
    if ns!=s:put(MAP[p],ns)

NAV=lambda l: ('上一张已编年页' in l or '下一张已编年页' in l or '[总目录](' in l) and l.lstrip().startswith('[')
def no_nav(s):return '\n'.join(l for l in s.splitlines() if not NAV(l)).strip()
def sans_urls(s):
    for a,b,_ in reversed(link_spans(s)):s=s[:a]+'__TARGET__'+s[b:]
    return s

YEARS=sorted([year(p) for p in TREE if re.fullmatch(r'years/(bce|ce)-\d{4}\.md',p)])
GROUPS=collections.OrderedDict()
for n in YEARS:GROUPS.setdefault(century(n),[]).append(n)
for i,n in enumerate(YEARS):
    p=ypath(n);old='years/'+Path(p).name;s=no_nav(content(p));head,_,rest=s.partition('\n')
    def rel(t):return posixpath.relpath(t,posixpath.dirname(p))
    nav=('[← 上一张已编年页：'+ylabel(YEARS[i-1])+']('+rel(ypath(YEARS[i-1]))+') · ' if i else '')
    nav+='[本世纪目录](README.md) · [全部世纪](../README.md)'
    if i+1<len(YEARS):nav+=' · [下一张已编年页：'+ylabel(YEARS[i+1])+' →]('+rel(ypath(YEARS[i+1]))+')'
    put(p,head+'\n\n'+nav+'\n\n'+rest.strip()+'\n\n'+nav+'\n')
    assert sans_urls(no_nav(read(old)))==sans_urls(no_nav(content(p))), ('Year narrative changed',old)

ENUMS={
 'already_integrated_keep_corrected_date':'已汇入；沿用纠正后的归年',
 'same_event_add_source_note':'同一事件；补入史料说明',
 'retain_chronology_dispute_in_notes_not_duplicate_event':'保留年次争议；不重复造事件',
 'same_event_source_note_han':'同一事件；补充互见',
 'retain_distinct_event':'独有事件；保留在年度正文',
}
for key,info in META.items():
    dst='meta/'+info[0];s=content(dst);orig=ORIGINAL_TEXT['meta/'+key]
    oldids=heading_ids(s);explicit_ids=set(explicit(s))
    ls=s.splitlines();body=[];first=True
    for l in ls:
        if re.match(r'^# ',l) and first:first=False;continue
        if l.startswith('[返回') or l.startswith('[试编入口]'):continue
        body.append(l)
    s='\n'.join(body).strip()
    if key=='编辑规则.md':
        s=s.replace('只写入根目录 `years/`','只写入 `years/对应世纪/`')
        s=s.replace('# 逐年读史｜已确认的编写规则','## 已确认的编写规则')
        s=s.replace('## 本轮实现范围','## 2026-09-28首轮实施记录')
    if key=='迁移说明.md':
        for a,b in ENUMS.items():s=s.replace(a,b)
        marker='## 旧试编条目去向'
        if marker in s:
            pre,table=s.split(marker,1)
            s=pre+marker+'\n\n<details>\n<summary>展开旧条目与当前落点对照表</summary>\n\n'+table.strip()+'\n\n</details>'
    s=s.replace('[memorial](', '[身后立祠](').replace('[bo_pi](', '[伯嚭结局异说](').replace('[author](', '[司马迁评论](')
    s=s.replace('[`provenance/CCDH_README.txt`]','[CCDH原始说明]').replace('[`provenance/KANRIPO_SOURCE.txt`]','[Kanripo原始说明]')
    s=s.replace('[`provenance/osf_manifest.json`]','[二十四史下载清单]').replace('[`provenance/ccdh_13_classics_manifest.json`]','[先秦典籍下载清单]')
    if key=='汉书1-引文去向.md':
        s=s.replace('`chronicle/years/`','`years/bce-0300-0201/`')
    if key=='后汉书1-引文去向.md':
        for n in range(22,26):
            dest=posixpath.relpath(ypath(n),posixpath.dirname(dst))
            s=s.replace('| 公元'+str(n)+'年 |','| [公元'+str(n)+'年]('+dest+') |')
    levels=[len(m[1]) for m in re.finditer(r'(?m)^(#{1,6})\s+',s)]
    low=min(levels) if levels else 3
    shift=3-low
    s=re.sub(r'(?m)^(#{1,6})(?=\s+)',lambda m:'#'*min(6,len(m[1])+shift),s)
    newids={a for _,a in heading_ids(s)} | set(explicit(s))
    alias=[a for _,a in oldids if a not in newids and a not in explicit_ids]
    alias=list(dict.fromkeys(alias))
    nav='[分类目录](README.md) · [编写依据总目录](../README.md) · [世纪目录](../../years/README.md)'
    h='# '+info[1]+'\n\n'+nav+'\n\n| 字段 | 内容 |\n|---|---|\n| 类型 | '+info[2]+' |\n| 范围 | '+info[3]+' |\n| 状态 | '+info[4]+' |\n\n'
    h+=''.join('<a id="'+html.escape(a,quote=True)+'"></a>\n' for a in alias)
    ns=tidy(h+'\n## 内容\n\n'+s+'\n\n## 关联入口\n\n'+nav+'\n')
    put(dst,ns)
    FORMAT_STATS['documents_standardized']+=1
    FORMAT_STATS['table_blank_lines_removed']+=len(re.findall(r'\|\s*\n\s*\n\s*\|',orig))

def grouptable(prefix=''):
    s='| 世纪范围 | 已有年份页 | 阅读入口 |\n|---|---:|---|\n'
    for c,ns in GROUPS.items():s+='| '+cname(c)+' | '+str(len(ns))+' | [打开本世纪]('+prefix+c+'/README.md) |\n'
    return s
root='# 逐年读史\n\n**按时间读历史；同一年只有一张正文页，不按史书另建年表。**\n\n'
root+='[按世纪阅读](years/README.md) · [史料](sources/README.md) · [编写依据](meta/README.md)\n\n'
root+='```text\nhistory/\n├── sources/       史书、版本和引用原文\n├── years/         每个世纪一个文件夹，每年一页\n├── meta/          规范、来源、考证、记录\n└── README.md      世纪入口\n```\n\n'
root+='<a id="year-list"></a>\n## 世纪目录\n\n'+grouptable('years/')
root+='\n现有 **'+str(len(YEARS))+'** 张年度正文，分布在 **'+str(len(GROUPS))+'** 个世纪目录。进入某一世纪后才显示该世纪的年份列表；只建立已有内容的目录和年页，不填空页。\n\n'
root+='<a id="unwritten"></a>\n## 阅读范围\n\n前800—前701年为一组，前700—前601年为下一组；公元1—100年为一组，101—200年为下一组。每组正好100个年号，不设0年。已写页数不等于某世纪已经完整覆盖，更不等于所有史书都已汇入。原有缺年、归年争议和待复核材料不因本次目录整理而消失。\n'
put('README.md',root)
put('years/README.md','# 按世纪读史\n\n[项目首页](../README.md) · [史料](../sources/README.md) · [编写依据](../meta/README.md)\n\n'+grouptable()+'\n## 分组规则\n\n一个目录覆盖连续100年，但只放已经写好的年份页。公元前按数字递减阅读，公元后按数字递增阅读；前1年后接公元1年，没有0年。目录名保留四位年份以便检索，例如 `bce-0800-0701`、`ce-0001-0100`。\n\n年页的前后导航连接相邻的**已编年页**，可以跨世纪；目录中没有的年份表示尚无已编页面。\n')
centuries=list(GROUPS)
for i,(c,ns) in enumerate(GROUPS.items()):
    nav='[全部世纪](../README.md) · [项目首页](../../README.md)'
    if i:nav='[← 上一个已有内容的世纪](../'+centuries[i-1]+'/README.md) · '+nav
    if i+1<len(centuries):nav+=' · [下一个已有内容的世纪 →](../'+centuries[i+1]+'/README.md)'
    s='# '+cname(c)+'\n\n'+nav+'\n\n本目录覆盖100年，现有 **'+str(len(ns))+'** 张年度正文。只列已有页面，不以空文件表示已经完成。\n\n| 年份 | 本页主线 |\n|---|---|\n'
    for n in ns:
        p=ypath(n);h=content(p).splitlines()[0].lstrip('# ').replace('|','｜')
        s+='| ['+ylabel(n)+']('+Path(p).name+') | '+h+' |\n'
    put('years/'+c+'/README.md',s+'\n'+nav+'\n')

format_doc='''# 目录与文档格式

[分类目录](README.md) · [编写依据总目录](../README.md) · [世纪目录](../../years/README.md)

| 字段 | 内容 |
|---|---|
| 类型 | 规范 |
| 范围 | 目录、命名、Markdown及引用链接 |
| 状态 | 本次确认的统一格式 |

## 内容

### 三个内容目录

`sources/` 只放史料；`years/` 只按世纪和年份组织正文；`meta/` 只放编写依据。世纪不是另一套编年史，只是同一条时间线的阅读分组。

### 年页与世纪

文件路径统一为 `years/世纪范围/bce-年份.md` 或 `years/世纪范围/ce-年份.md`。世纪范围的端点均包含在内：前800—前701年、前700—前601年；公元1—100年、101—200年。不得产生0年，不得把100年与101年分到同一世纪。每个世纪允许一个 `README.md` 作为目录，不创建未编年的空页。

根目录和 `years/README.md` 只列世纪；世纪的 `README.md` 才列具体年份。年页保留上一张、下一张已编年页导航，并提供本世纪和全部世纪入口。跨世纪继续读，不要求读者返回总目录找下一页。

### meta分类与文件名

| 分类 | 保存内容 | 不应放入 |
|---|---|---|
| 规范 | 长期有效的编写规则、目录和格式 | 批次成果清单 |
| 来源 | 版本、许可、来源、原始采集和校验说明 | 年度历史叙事 |
| 考证 | 具体归年、异说、未定年、文本核对 | 第二套年页 |
| 记录 | 引文去向、人物入口、已经完成的迁移记录 | 生成程序、工作流、缓存 |

普通文件用中文主题名；涉及卷次用三位阿拉伯数字，如 `史记-卷066-引文去向.md`；按日期保存的记录用 `YYYY-MM-DD-主题.md`。上游原始文件名放在 `来源/原始记录/` 原样保留，不改许可文本、原始哈希和下载清单。

### 说明文档模板

每篇说明只有一个一级标题。开头依次为导航、字段表（类型／范围／状态）；主体使用二级标题“内容”，原有分项用三级标题，必要的子项用四级；结尾为二级标题“关联入口”。各级目录的 `README.md` 是导航页，不强套说明文模板。

表格各行必须连续，表头与分隔行列数一致。表格单元格内的竖线应转义；不要在表格行间插空行。UTF-8编码，Markdown使用LF换行，文件末尾保留一个换行。保留有意义的双空格换行、脚注、引文与旧锚点，不用排版改动悄悄改写史实。

### 链接与历史记录

仓库内当前页面使用相对链接，移动文件时同步更新正文、来源页、索引及跨世纪导航。带完整提交SHA的旧链接是历史证据，不改成浮动的main链接；旧记录中作为证据列出的旧路径可以保留，但应明确它是旧位置。

重新排版后检查：年页数不变、每年只有一页、世纪边界正确、原正文和史料不丢失、旧锚点仍可定位、引用与导航无失效路径。排版通过不等于史实考证全部通过。

## 关联入口

[编写规则](编写规则.md) · [世纪目录](../../years/README.md) · [编写依据总目录](../README.md)
'''
put('meta/规范/目录与格式.md',format_doc)
reorg='''# 世纪目录与文档格式整理（2026-10-04）

[分类目录](README.md) · [编写依据总目录](../README.md) · [世纪目录](../../years/README.md)

| 字段 | 内容 |
|---|---|
| 类型 | 迁移记录 |
| 范围 | 原main提交 `ab0b698f5908bafa621ac6a54078c1115eed3580` |
| 状态 | 目录与格式调整；不增加、不删除年度正文 |

## 内容

### 年份目录

原来的266张年页按每100年一组归入9个已有内容的世纪目录。根目录不再展示全部年份；每世纪单独列年页，并保留跨世纪连续阅读导航。世纪划分不设0年，不用空页填满100年。

### 编写依据

原meta文件全部按规范、来源、考证、记录四类归位。统一文件名、单一一级标题、类型／范围／状态字段、内容与关联入口层级；修复表格空行、标题层级和可见的内部英文标签。原始TXT、JSON、校验清单保留字节不变。

### 保全范围

年度正文的文字、引文及锚点保留；只调整链接目标与导航。史料TXT、PDF、JSON不重新编码。既有来源页的当前相对链接随路径更新；固定提交链接和历史记录中的旧路径保持其证据性质。本次不新增史实、不重新判定年代、不把待核事项改标为完成。

## 关联入口

[目录与格式规范](../规范/目录与格式.md) · [此前三目录迁移](2026-10-03-三目录迁移.md) · [世纪目录](../../years/README.md)
'''
put('meta/记录/2026-10-04-世纪目录与格式.md',reorg)
CATDESC={'规范':'长期规则、目录及文档模板','来源':'史料版本、来源许可、原始清单与校验','考证':'归年、异说、未定年材料与文本核对','记录':'引文去向、人物阅读入口与已完成的迁移记录'}
for cat,desc in CATDESC.items():
    fs=sorted(p for p in NEW if p.startswith('meta/'+cat+'/') and p.endswith('.md') and not p.endswith('/README.md'))
    s='# '+cat+'\n\n'+desc+'。\n\n[编写依据总目录](../README.md) · [世纪目录](../../years/README.md)\n\n| 文档 | 内容 |\n|---|---|\n'
    for p in fs:
        title=content(p).splitlines()[0][2:]
        m=re.search(r'(?m)^\| 范围 \| (.*?) \|$',content(p));description=m[1] if m else title
        s+='| ['+title+']('+posixpath.relpath(p,'meta/'+cat)+') | '+description+' |\n'
    if cat=='来源':s+='\n[上游说明、下载清单与校验记录](原始记录/)保留原文件名与原字节，不按说明文模板改写。\n'
    put('meta/'+cat+'/README.md',s)
put('meta/README.md','# 编写依据\n\n只保存支撑编年正文的必要依据；这里没有独立年表，也不保留旧生成程序和流水线。\n\n[按世纪读史](../years/README.md) · [史料](../sources/README.md) · [项目首页](../README.md)\n\n| 分类 | 内容 |\n|---|---|\n'+''.join('| ['+k+']('+k+'/README.md) | '+v+' |\n' for k,v in CATDESC.items())+'\n新资料按用途进入以上分类；卷次统一三位数字，日期统一YYYY-MM-DD。文档格式与检查口径见[目录与格式](规范/目录与格式.md)。\n')
put('.gitattributes','sources/** -text\nmeta/** text eol=lf\nmeta/来源/原始记录/** -text\nyears/** text eol=lf\nREADME.md text eol=lf\n')

ERRORS=[];STATS={'year_pages_before':len(YEARS),'year_pages_after':0,'century_directories':len(GROUPS),'century_counts':{k:len(v) for k,v in GROUPS.items()},**FORMAT_STATS}
MD={p:content(p) for p in NEW if p.endswith('.md') and ('content' in NEW[p] or not LOCAL or (ROOT/next((k for k,v in MAP.items() if v==p),p)).exists())}
IDS={p:set(explicit(s))|{x for _,x in heading_ids(s)} for p,s in MD.items()}
for p,s in MD.items():
    ex=explicit(s)
    if len(ex)!=len(set(ex)):ERRORS.append(['duplicate_explicit_anchor',p,[x for x,n in collections.Counter(ex).items() if n>1]])
    if p.startswith('meta/') and not p.endswith('/README.md'):
        hs=re.findall(r'(?m)^# ',s)
        if len(hs)!=1:ERRORS.append(['multiple_H1',p,len(hs)])
        for required in ['| 类型 |','| 范围 |','| 状态 |','## 内容','## 关联入口']:
            if required not in s:ERRORS.append(['missing_template_field',p,required])
        if re.search(r'\|\s*\n\s*\n\s*\|',s):ERRORS.append(['broken_table_spacing',p])
    for a,b,v in link_spans(s):
        u,_=split_target(v.strip());u=html.unescape(u)
        if re.match(r'^\w+:',u) or u.startswith('//'):continue
        sp=urlsplit(u);dp=unquote(sp.path).replace('\\(','(').replace('\\)',')')
        dest=posixpath.normpath(posixpath.join(posixpath.dirname(p),dp)) if dp else p
        STATS['internal_links_checked']=STATS.get('internal_links_checked',0)+1
        if dest not in NEW and not any(q.startswith(dest.rstrip('/')+'/') for q in NEW):ERRORS.append(['broken_path',p,u,dest]);continue
        if sp.fragment and dest in MD and unquote(sp.fragment) not in IDS[dest]:ERRORS.append(['broken_anchor',p,u,dest])
for old,s in ORIGINAL_TEXT.items():
    new=MAP[old]
    for a in explicit(s):
        if a not in IDS.get(new,set()):ERRORS.append(['lost_original_anchor',old,a])
    if old.startswith('years/'):
        STATS['year_pages_after']+=1
        assert year(new)==year(old) and '/'+century(year(old))+'/' in new
        if sans_urls(no_nav(s))!=sans_urls(no_nav(MD[new])):ERRORS.append(['year_text_changed',old])
for n in [-800,-701,-700,-601,-100,-1,1,100,101,200,201,300]:
    c=century(n);_,a,b=c.split('-');assert min(int(a),int(b))<=abs(n)<=max(int(a),int(b)) and abs(int(a)-int(b))==99
assert STATS['year_pages_after']==len(YEARS)==266
assert set(p.split('/')[0] for p in NEW if '/' in p)=={'meta','sources','years'}
assert set(p for p in NEW if p.startswith('meta/') and p.count('/')==1)=={'meta/README.md'}
assert set(p for p in NEW if p.startswith('years/') and p.count('/')==1)=={'years/README.md'}
assert all(n<=100 for n in STATS['century_counts'].values())
assert not any(p.endswith(('.py','.pyc','.yml','.yaml')) for p in NEW)
STATS['unchanged_source_files']=sum(1 for p in TREE if p.startswith('sources/') and NEW[p].get('sha')==TREE[p]['sha'])
STATS['source_navigation_files_updated']=sum(1 for p in TREE if p.startswith('sources/') and 'content' in NEW[p])
STATS['raw_source_blobs_preserved']=sum(1 for p in TREE if p.startswith('sources/') and not p.endswith('.md'))
for p in TREE:
    if p.startswith('sources/') and not p.endswith('.md'):assert NEW[p].get('sha')==TREE[p]['sha']
for p in RAW_META:assert NEW[MAP['meta/'+p]]['sha']==TREE['meta/'+p]['sha']
STATS['old_explicit_anchors_checked']=sum(len(explicit(s)) for s in ORIGINAL_TEXT.values())
STATS['validation_errors']=len(ERRORS)
STATS['output_files']=len(NEW)
OUT.mkdir(parents=True,exist_ok=True)
for p,n in NEW.items():
    if 'content' in n:
        f=OUT/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(n['content'])
(REPORTDIR/'validation-errors.json').write_text(json.dumps(ERRORS,ensure_ascii=False,indent=2))
(REPORTDIR/'result-summary.json').write_text(json.dumps(STATS,ensure_ascii=False,indent=2))
(REPORTDIR/'output-tree.json').write_text(json.dumps({p:{'sha':gitsha(n['content']) if 'content' in n else n['sha'],'mode':n['mode']} for p,n in NEW.items()},ensure_ascii=False))
print(json.dumps(STATS,ensure_ascii=False,indent=2))
if ERRORS:print(json.dumps(ERRORS[:30],ensure_ascii=False,indent=2));raise SystemExit(1)
if LOCAL:raise SystemExit(0)

# Publish a branch for inspection; default branch is updated separately via the connector.
idx=str(Path(os.environ.get('RUNNER_TEMP','/tmp'))/'century-layout-index');env=os.environ.copy();env['GIT_INDEX_FILE']=idx
if Path(idx).exists():Path(idx).unlink()
git('read-tree','--empty',env=env)
rows=[]
for p,n in sorted(NEW.items()):
    sha=n.get('sha') or git('hash-object','-w','--stdin',input=n['content']).decode().strip()
    rows.append(n['mode']+' '+sha+'\t'+p+'\0')
git('update-index','-z','--index-info',input=''.join(rows).encode(),env=env)
newtree=git('write-tree','--missing-ok',env=env).decode().strip()
current=git('ls-remote','origin','refs/heads/'+RESULT).decode().split()
parent=current[0] if current else BASE
if current:git('fetch','--depth=1','origin',parent)
commit=git('commit-tree',newtree,'-p',parent,input='Group canonical years by century and standardize metadata format\n'.encode()).decode().strip()
git('push','origin',commit+':refs/heads/'+RESULT)
STATS.update(result_commit=commit,result_tree=newtree)
(REPORTDIR/'result-summary.json').write_text(json.dumps(STATS,ensure_ascii=False,indent=2))
print('RESULT',commit,newtree)
