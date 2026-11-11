#!/usr/bin/env python3
"""Replay the recovered, locally revalidated volume032 revision on the review branch."""
from pathlib import Path
import base64,hashlib,json,lzma,os,subprocess,sys
payload=''.join(Path(f'.recover-next/part{i}').read_text(encoding='utf-8').strip() for i in range(1,5))
assert hashlib.sha256(payload.encode()).hexdigest()=='cf0059d0fe4c9b0965c6d1cd18fac53589e2548d152bff0ab96415ec844f2e83'
obj=json.loads(lzma.decompress(base64.b64decode(payload,validate=True)))
expected={'readings.tsv','build.py','config.py','bindings.py','init.py','source_helpers.py','finish.py','summary.json','validate.py','run.py','finalize.py'}
assert set(obj)==expected
out=Path('/tmp/shiji032-package');out.mkdir(exist_ok=True)
for name,content in obj.items():
    assert Path(name).name==name
    (out/name).write_text(content,encoding='utf-8')
subprocess.run([sys.executable,str(out/'run.py')],check=True,env=os.environ)
