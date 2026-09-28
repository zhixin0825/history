"""Source-supported within-year precedence; unknown months are not automatically last.
The edges are editorial reading constraints, not newly inferred day/month dates.
"""
from __future__ import annotations
import json
from pathlib import Path

EDGES = [
 ('sj-066-L4663-01','sj-066-L4664-01','sj:4663;sj:4664','伍奢先被囚，随后召二子。'),
 ('sj-066-L4664-01','sj-031-L2971-01','sj:4664;sj:4665;sj:2971','伍员先出亡，再到吴；不因世家先录入而倒置。'),
 ('sj-086-L5387-01','sj-086-L5388-01','sj:5387;sj:5388','先谋划，再于四月行刺。'),
 ('sj-086-L5388-01','sj-031-L2975-01','sj:2974;sj:2975','季札回国哭祭及公子投楚在刺僚之后。'),
 ('sj-031-L2979-01','sj-031-L2979-02','sj:2979;sj:4670','先出兵、交战，后入郢。'),
 ('sj-031-L2979-02','sj-031-L2979-03','sj:4672','鞭尸是入郢后的叙述。'),
 ('sj-031-L2980-01','sj-031-L2980-02','sj:2980;sj:4672','秦援、吴退等前事在楚王九月返郢以前。'),
 ('sj-066-L4677-01','sj-031-L2986-01','sj:4677','献礼及谏言是出使托子的前因。'),
 ('sj-031-L2986-01','sj-031-L2986-02','sj:2986;sj:4678','先出使托子、后被赐死。'),
 ('sj-031-L2986-02','sj-031-L2985-04','zz:12.11','按《左传》本次伐齐前的伍员之死编排；《史记》各段北伐排列差异仍见条注。'),
]

def order_units(units, month_key):
    """Stable topological order, with explicit months used only among unconstrained nodes."""
    if not units:return []
    alias={rid:i for i,u in enumerate(units) for rid in u['aliases']}
    successors={i:set() for i in range(len(units))};incoming={i:0 for i in range(len(units))}
    for a,b,_,_ in EDGES:
        if a not in alias or b not in alias:continue
        i,j=alias[a],alias[b]
        if i==j:continue
        if j not in successors[i]:successors[i].add(j);incoming[j]+=1
    ready=[i for i,v in incoming.items() if v==0];result=[]
    while ready:
        i=min(ready,key=lambda k:(month_key(units[k]),k));ready.remove(i);result.append(units[i])
        for j in sorted(successors[i]):
            incoming[j]-=1
            if incoming[j]==0:ready.append(j)
    if len(result)!=len(units):raise ValueError('Conflicting within-year order; retain for review rather than force sorting')
    return result

def check_pages(root=Path('.')):
    folder=root/'chronicle/shiji-trial'
    records=[json.loads(s) for s in (folder/'data/records.jsonl').read_text().splitlines()]
    by_id={r['id']:r for r in records}
    for a,b,source,reason in EDGES:
        if a not in by_id or b not in by_id:raise AssertionError(('Stale sequence edge',a,b))
        y=by_id[a]['year_bce']
        if y!=by_id[b]['year_bce']:continue
        page=(folder/f'years/bce-{y:04d}.md').read_text()
        assert page.index(f'<a id="{a}"></a>')<page.index(f'<a id="{b}"></a>'),reason
    data=[{'before':a,'after':b,'basis_source_keys':s.split(';'),'basis':r,'meaning':'同年阅读先后；不是新增月日'} for a,b,s,r in EDGES]
    (folder/'data/sequence-constraints.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':check_pages()
