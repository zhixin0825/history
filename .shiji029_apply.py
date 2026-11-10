#!/usr/bin/env python3
"""Apply data-only, checksum-verified line edits on a review branch; never push main."""
from pathlib import Path
import base64,hashlib,html,json,lzma,re,zipfile
ROOT=Path.cwd()
def sha(b): return hashlib.sha256(b).hexdigest()
def text(p): return (ROOT/p).read_text(encoding='utf-8')
def ids(t): return re.findall(r'<a\s+(?:id|name)=["\']([^"\']+)["\'][^>]*>',t)
def clean(t): return re.sub(r'\s+','',html.unescape(re.sub(r'<[^>]*>','',t))).replace('\ufeff','')
def quotes(t): return '\n'.join(x[2:] if x.startswith('> ') else x[1:] for x in t.splitlines() if x.startswith('>'))
payload=''.join(text(f'.shiji029_part_{i}') for i in range(1,4))
assert sha(payload.encode())=='c1b4c30627db9f864dd96f1eb81b973f05a5a8201f200abeda6d0e2b36985337','Transport checksum'
obj=json.loads(lzma.decompress(base64.b64decode(payload,validate=True)))
assert obj['baseline_commit']=='879b2436769f9c231fd23babd885214357df8574'
assert len(obj['files'])==27
prepared=[]
for f in obj['files']:
    p=Path(f['path']);assert not p.is_absolute() and '..' not in p.parts
    assert str(p)=='README.md' or p.parts[0] in ('years','sources','meta')
    if f['old_sha256'] is None:
        assert not p.exists(),f'Unexpected existing path: {p}'
        old=b''
    else:
        old=p.read_bytes();assert sha(old)==f['old_sha256'],f'Baseline changed: {p}'
    lines=old.decode('utf-8').splitlines(keepends=True)
    last=len(lines)+1
    for op in reversed(f['ops']):
        assert 0<=op['start']<=op['end']<=len(lines) and op['end']<last
        last=op['start'];lines[op['start']:op['end']]=op['lines']
    new=''.join(lines).encode();assert sha(new)==f['sha256'],f'Result changed: {p}'
    if p.suffix=='.md':
        assert set(ids(old.decode('utf-8')))<=set(ids(new.decode('utf-8'))),f'Lost anchors: {p}'
        a=ids(new.decode('utf-8'));assert len(a)==len(set(a)),f'Duplicate anchors: {p}'
    prepared.append((p,new))
for p,new in prepared:
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(new)

units=json.loads(text('meta/记录/史记-卷029-单元数据.json'))
sj=Path('sources/二十四史/txt/01_shiji_full.txt').read_bytes()
hs=Path('sources/二十四史/txt/02_hanshu_full.txt').read_bytes()
assert sha(sj)==units['source_sha256']
assert Path('sources/摘录/原始见证/史记-卷029-CCDH.txt').read_bytes()==b''.join(sj.splitlines(keepends=True)[2874:2892])
assert sha(hs)=='4fd2c97ce5c7e6a94c46741897fca72bb84a7e4748096c6d0ab60c392061fd44'
sjlines=sj.decode('utf-8-sig').splitlines();hslines=hs.decode('utf-8-sig').splitlines()
def unit_section(t,a,prefix):
    m=re.search(r'<a id="'+re.escape(a)+r'"></a>',t);assert m,a
    tail=t[m.end():];n=re.search(r'<a id="'+prefix+r'\d+"></a>',tail)
    return tail[:n.start()] if n else tail
src=text('sources/摘录/史记-卷029-河渠书.md')
for u in units['units']:
    a=u['id'];sec=unit_section(src,a,'[pz]')
    assert quotes(sec)==u['raw']==sjlines[u['line']-1],a
hsrc=text('sources/摘录/史记-卷029-汉书互校.md')
for u in units['han_excerpts']:
    sec=unit_section(hsrc,u['id'],'h')
    assert quotes(sec)=='\n'.join(hslines[u['start_line']-1:u['end_line']]),u['id']
placements=json.loads(text('meta/记录/史记-卷029-新增引句清单.json'))
for p in placements:
    a=p['anchor'];sec=unit_section(text(p['source']),a,'h' if a.startswith('h') else '[pz]')
    assert clean(p['quote']) in clean(quotes(sec)),a

pages=0;groups=0
for p in sorted(Path('years').rglob('*.md')):
    if not(re.match(r'(bce|ce)-\d+\.md$',p.name) or p.parent.name=='上古' and re.match(r'\d\d-',p.name)):continue
    t=p.read_text();assert '本条的直接引文待核。' not in t,str(p)
    body,tail=t.split('<a id="sources-start"></a>',1);notes=tail.split('<a id="appendix-start"></a>',1)[0]
    shown=[]
    for n,entry in re.findall(r'(?m)^(\d+)\. (.*?)(?=\n\d+\. |\Z)',body,re.S):
        m=re.search(r'\[\['+n+r'\]\]\(#([^\)]+)\)',entry)
        if not m:
            assert '**' not in entry,(str(p),n,'no same-number citation')
            continue
        target=m[1];mark=re.search(r'<a\s+(?:id|name)=["\']'+re.escape(target)+r'["\'][^>]*>',notes)
        assert mark,(str(p),target)
        sec=notes[mark.end():];heads=list(re.finditer(r'^###\s+\d+\.',sec,re.M))
        if len(heads)>1:sec=sec[:heads[1].start()]
        title=re.search(r'^###\s+(\d+)\.',sec,re.M);assert title and title[1]==n
        back=re.search(r'\[返回正文第'+n+r'条\]\(#([^\)]+)\)',sec)
        assert back and back[1] in ids(body),(str(p),n,'return link')
        assert re.search(r'^> ',sec,re.M),(str(p),n,'no quote')
        shown.append(int(n))
    assert shown==list(range(1,len(shown)+1)),str(p)
    pages+=1;groups+=len(shown)
assert pages==771 and groups==4944,(pages,groups)
audit=json.loads(text('meta/记录/史记-卷029-整卷核验.json'))
assert audit['summary']['status']=='verified' and not audit['errors']
for f in obj['files']:assert sha(Path(f['path']).read_bytes())==f['sha256']
out=Path('/tmp/shiji029-output');out.mkdir(exist_ok=True)
(out/'hashes.json').write_text(json.dumps({f['path']:f['sha256'] for f in obj['files']},ensure_ascii=False,indent=2))
with zipfile.ZipFile(out/'shiji029-result.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for f in obj['files']:z.write(f['path'],f['path'])
print('SHIJI029_VERIFIED',json.dumps({'files':len(obj['files']),'raw_units':15,'han_excerpt_groups':16,'new_quote_placements':len(placements),'all_reading_pages':pages,'all_numbered_groups':groups,'verified_links_local':audit['summary']['changed_markdown_links_checked'],'new_link_errors':audit['summary']['new_broken_links']},ensure_ascii=False))
