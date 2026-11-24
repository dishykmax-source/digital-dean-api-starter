import json
from pathlib import Path
import matplotlib.pyplot as plt

ROOT=Path('results/practice-03')
data=json.loads((ROOT/'report.json').read_text(encoding='utf-8'))
for op in ('encrypt','decrypt'):
    rows=[r for r in data['results'] if r['operation']==op]
    labels=[f"{r['profile']}\n{r['payload_bytes']} B" for r in rows]
    values=[r['median_ns']/1e6 for r in rows]
    plt.figure(figsize=(12,6)); plt.bar(range(len(rows)),values); plt.xticks(range(len(rows)),labels,rotation=35,ha='right')
    plt.ylabel('Median time (ms)'); plt.title(f'Practice 03 — {op}'); plt.tight_layout(); plt.savefig(ROOT/f'{op}_median_ms.png',dpi=160); plt.close()
rows=data['key_generation']; plt.figure(figsize=(9,5)); plt.bar([r['profile'] for r in rows],[r['median_ns']/1e6 for r in rows]); plt.ylabel('Median key generation time (ms)'); plt.title('Practice 03 — key generation'); plt.xticks(rotation=25,ha='right'); plt.tight_layout(); plt.savefig(ROOT/'key_generation_ms.png',dpi=160); plt.close()
