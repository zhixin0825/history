#!/usr/bin/env python3
"""Temporary read-only inventory; never modifies main."""
import json, os, re, subprocess, tarfile
from pathlib import Path
BASE='32ef7a8731e048333941ef65498a4adbef776f6b'
REFS={'main':BASE,'han':'a485252f253a5063a4f5f63175418a55f8716f76','laterhan':'1367dbae8672cc480589f11a5748b483c4f4345a','jin':'2b9716ab9562c352b9ae4a0d8d463455c4d3dae9'}
def git(*a): return subprocess.check_output(['git',*a])
def tree(ref):
    out={}
    for row in git('ls-tree','-rz','--full-tree',ref).split(b'\0'):
        if row:
            meta,p=row.split(b'\t',1); mode,typ,sha=meta.decode().split(); out[p.decode()]={'sha':sha,'mode':mode,'type':typ}
    return out
out=Path('_migration/export'); out.mkdir(parents=True,exist_ok=True)
catalog={'refs':REFS,'roots':{},'years':{},'overlaps':[],'extra_branch_files':{}}
main_tree=tree(BASE)
for label,ref in REFS.items():
    tr=tree(ref)
    catalog['roots'][label]=sorted(set(p.split('/')[0] for p in tr))
    years=[p for p in tr if re.search(r'/years/(bce|ce)-\d{4}\.md$',p) and p.startswith('chronicle/')]
    catalog['years'][label]=years
    if label!='main':
        catalog['extra_branch_files'][label]=[p for p in tr if p.startswith('chronicle/') and (p not in main_tree or main_tree[p]['sha']!=tr[p]['sha'])]
    selected=[p for p in tr if p.startswith(('chronicle/','provenance/')) or p in ['README.md','SHA256SUMS.txt','.gitattributes']]
    if label!='main': selected=[p for p in selected if p not in main_tree or main_tree[p]['sha']!=tr[p]['sha']]
    for p in selected:
        target=out/label/p; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(git('show',f'{ref}:{p}'))
    (out/f'{label}-tree.json').write_text(json.dumps(tr,ensure_ascii=False),encoding='utf-8')
for p in catalog['years']['main']:
    if not p.startswith('chronicle/shiji-trial/years/'): continue
    name=Path(p).name; primary=f'chronicle/chunqiu/years/{name}'
    if primary not in main_tree: continue
    a=git('show',f'{BASE}:{p}').decode(); b=git('show',f'{BASE}:{primary}').decode()
    ev=[]
    for m in re.finditer(r'<a id="([^"]+)"[^>]*></a>(.*?)(?=<a id=|\n---\n|\Z)',a,re.S):
        ev.append({'id':m[1],'text':m[2][:1600]})
    catalog['overlaps'].append({'year':name,'trial_events':ev,'primary_headings':re.findall(r'^#{1,4} .+$',b,re.M),'has_066_overlay':'shiji066' in b})
# Produce compact, reviewable records without downloading the raw PDF archive.
Path('_migration/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
with tarfile.open('_migration/review-inputs.tar.gz','w:gz') as t: t.add(out,arcname='inputs')
print(json.dumps({'main_year_pages':len(catalog['years']['main']),'overlap_years':len(catalog['overlaps']),'branch_additions':catalog['extra_branch_files'],'refs':REFS},ensure_ascii=False,indent=2))
