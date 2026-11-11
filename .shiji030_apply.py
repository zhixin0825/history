#!/usr/bin/env python3
"""Replay the locally reviewed chapter against identical inputs; never push main."""
from pathlib import Path
import base64,hashlib,json,lzma,os,subprocess,sys,zipfile
ROOT=Path.cwd()
def sha(b): return hashlib.sha256(b).hexdigest()
payload=''.join(Path(f'.shiji030_part_{i}').read_text(encoding='utf-8').strip() for i in range(1,5))
assert sha(payload.encode())=='e990c89efe93bc5670426721e42ebe38b25bfb6ac17803e5d5b7ec4ecb8e8ddf','Transport checksum'
bundle=json.loads(lzma.decompress(base64.b64decode(payload,validate=True)))
assert set(bundle)=={'make30.py','units.tsv','input_hashes.json','output_hashes.json'}
package=Path('/tmp/shiji030-package'); package.mkdir(exist_ok=True)
for name,content in bundle.items():
    (package/name).write_text(content,encoding='utf-8')
inputs=json.loads(bundle['input_hashes.json']); expected=json.loads(bundle['output_hashes.json'])
assert len(expected)==42 and set(inputs)==set(expected)
for name,wanted in inputs.items():
    p=Path(name)
    assert not p.is_absolute() and '..' not in p.parts
    assert name=='README.md' or p.parts[0] in ('years','meta','sources')
    if wanted is None: assert not p.exists(),f'Unexpected existing file: {name}'
    else: assert p.is_file() and sha(p.read_bytes())==wanted,f'Changed baseline file: {name}'
manifest=subprocess.run(['git','-c','core.quotepath=false','ls-tree','-rz','--name-only','HEAD'],check=True,stdout=subprocess.PIPE).stdout
(package/'repo-manifest.bin').write_bytes(manifest)
subprocess.run([sys.executable,str(package/'make30.py')],check=True,env={**os.environ,'HISTORY_ROOT':str(ROOT)})
for name,wanted in expected.items():
    assert sha(Path(name).read_bytes())==wanted,f'Replayed output differs: {name}'
summary=json.loads((package/'summary.json').read_text())
assert summary['status']=='verified' and summary['errors']==0
out=Path('/tmp/shiji030-output');out.mkdir(exist_ok=True)
(out/'hashes.json').write_text(json.dumps(expected,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(out/'shiji030-result.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
    for name in expected:z.write(name,name)
print('SHIJI030_REPLAY_VERIFIED',json.dumps(summary,ensure_ascii=False))
