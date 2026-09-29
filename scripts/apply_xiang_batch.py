#!/usr/bin/env python3
"""Apply authored annual prose and its manually assigned source-paragraph routes."""
from __future__ import annotations
import json
import re
from review_xiang_gong import BASE, REVIEW, MAP, cn, put


def main():
    routes = {}
    patch_path = REVIEW/'corrections.json'
    corrections = json.loads(patch_path.read_text(encoding='utf-8')) if patch_path.exists() else {}
    for p in sorted((REVIEW/'batches').glob('*.json')):
        data = json.loads(p.read_text(encoding='utf-8'))
        for key, route in data.items():
            if key in routes:
                raise ValueError(f'Duplicate regnal year {key}')
            y = int(key)
            if not 1 <= y <= 31:
                raise ValueError(f'Outside Xiang scope: {y}')
            correction = corrections.get(key,{})
            route['entries'].extend(correction.get('append_entries',[]))
            for n, entry in correction.get('replace_entries',{}).items():
                route['entries'][int(n)-1] = entry
            for field in ('j','t','m'):
                if field in correction:
                    route[field] = correction[field]
            route.setdefault('notes',{}).update(correction.get('notes',{}))
            entries = route['entries']
            bce = 573-y
            nav = f'[上一年：前{bce+1}](bce-{bce+1:04}.md) · [目录](../README.md)'
            if y < 31:
                nav += f' · [下一年：前{bce-1}](bce-{bce-1:04}.md)'
            lines = [f'# 公元前{bce}年（鲁襄公{cn(y)}年）','',nav,'']
            for n, entry in enumerate(entries,1):
                if len(entry) != 2:
                    raise ValueError(f'{y}/{n}: expected headline and narrative')
                head, prose = entry
                if not head or re.search(r'《(?:春秋|左传|史记)》',head+prose):
                    raise ValueError(f'{y}/{n}: keep source discussion in notes')
                lines += [f'{n}. **{head}**'+(' '+prose if prose else '')+f'[{n}]','']
            lines += ['## 本年相关史料','', '原文引用由逐段去向表生成；必须先运行 review_xiang_gong.py 后发布。','']
            put(BASE/'years'/f'bce-{bce:04}.md','\n'.join(lines))
            routes[key] = {k:v for k,v in route.items() if k != 'entries'}
    put(MAP,json.dumps(routes,ensure_ascii=False,indent=2)+'\n')
    if set(routes)=={str(n) for n in range(1,32)}:
        p = BASE/'README.md'
        text = p.read_text(encoding='utf-8')
        block = '\n### 鲁襄公（前572—前542）\n\n'
        block += '\n'.join(f'{y}. [襄公{cn(y)}年｜前{573-y}](years/bce-{573-y:04}.md)' for y in range(1,32))
        block += '\n\n[本组三十一年复核记录与逐段原文](review/xiang-gong/README.md)\n\n'
        if '### 鲁襄公（' not in text:
            pos = text.rfind('\n> ')
            text = text[:pos]+block+text[pos:] if pos>=0 else text+block
        text = text.replace('、成公已经完成','、成公、襄公已经完成')
        text = text.replace('下一组骨架从鲁襄公开始','下一组骨架从鲁昭公开始')
        put(p,text)
        prev = BASE/'years/bce-0573.md'
        s = prev.read_text()
        old = '[上一年：前574](bce-0574.md) · [目录](../README.md)'
        if '[下一年：前572]' not in s:
            s = s.replace(old,old+' · [下一年：前572](bce-0572.md)',1)
            put(prev,s)
    print(f'Applied {len(routes)}/31 reviewed annual narratives')

if __name__=='__main__':
    main()
