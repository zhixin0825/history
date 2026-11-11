#!/usr/bin/env python3
"""Replay the checksum-verified local volume033 review on a review branch only."""
import base64,hashlib,json,lzma,os,subprocess,sys
from pathlib import Path
payload=''.join(Path(f'.shiji033-package/part{i}').read_text(encoding='utf-8').strip() for i in range(1,6))
assert hashlib.sha256(payload.encode()).hexdigest()=='9ac8bacd4e304425c3cbe83066f196353584f4b64c3ebd4a48006f1372bf8192','Transport checksum mismatch'
obj=json.loads(lzma.decompress(base64.b64decode(payload,validate=True)))
expected={'run.py','build.py','validate.py','config.py','compare.py','readings.tsv','chronology.md','numbers.md'}
assert set(obj)==expected
out=Path('/tmp/shiji033-package');out.mkdir(exist_ok=True)
for name,content in obj.items():
    assert Path(name).name==name
    (out/name).write_text(content,encoding='utf-8')
subprocess.run([sys.executable,str(out/'run.py')],check=True,env=os.environ)
