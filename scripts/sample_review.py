import json
import random

JSONL_PATH = "data/curated/trinodb_trino.jsonl"
SAMPLE_SIZE = 20

with open(JSONL_PATH) as f:
    records = [json.loads(line) for line in f]

samples = random.sample(records, min(SAMPLE_SIZE, len(records)))

for i, r in enumerate(samples, 1):
    print(f"{'='*80}")
    print(f"[{i}/{SAMPLE_SIZE}] PR #{r['pr_number']}  |  {r['file']}")
    print(f"{'='*80}")
    print("DIFF HUNK:")
    print(r["diff_hunk"])
    print()
    print("COMMENT:")
    print(r["comment_body"])
    print()
