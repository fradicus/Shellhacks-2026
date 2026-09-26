#!/usr/bin/env python3
"""Retrieve public URLs cited by Plan E; never fetch secrets or runtime endpoints."""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
# Authoring documents only; reports are generated evidence, not new source inputs.
paths=[ROOT/'PLAN.md']+list((ROOT/'paperclip').rglob('*.md'))+list((ROOT/'specs').rglob('*.md'))
refs={}
for p in paths:
    for url in set(re.findall(r'https://[^\s<>`\)]+',p.read_text())):
        refs.setdefault(url,[]).append(str(p.relative_to(ROOT)))

def probe(item):
    url,documents=item
    result={'url':url,'cited_in':documents,'checked_at_utc':datetime.now(timezone.utc).isoformat()}
    for attempt in range(2):
        try:
            with urlopen(Request(url,headers={'User-Agent':'GridBridge-Plan-E-source-check/1.0'}),timeout=35) as response:
                body=response.read()
                result.update(ok=200<=response.status<300,status=response.status,final_url=response.url,
                              content_type=response.headers.get('Content-Type'),bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),attempts=attempt+1)
                return result
        except (HTTPError,URLError,TimeoutError,OSError) as error:
            result.update(ok=False,error=str(error),status=getattr(error,'code',None),attempts=attempt+1)
    return result
with ThreadPoolExecutor(max_workers=4) as pool:
    results=list(pool.map(probe,sorted(refs.items())))
report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'method':'HTTP GET via Python urllib; redirects followed; maximum two attempts','results':results}
(HERE/'source-checks.json').write_text(json.dumps(report,indent=2)+'\n')
for result in results:
    print(('PASS' if result['ok'] else 'FAIL'),result.get('status'),result['url'],result.get('error',''))
print(f"{sum(r['ok'] for r in results)}/{len(results)} URLs retrieved")
raise SystemExit(0 if all(r['ok'] for r in results) else 1)
