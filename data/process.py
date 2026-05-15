import os
import json
import yaml
import random
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

CURATED_PATH = "data/curated/trinodb_trino.jsonl"
OUT_DIR = "data/processed"
CONFIG_PATH = "data/curation_config.yaml"

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

guidelines_path = config.get("guidelines_path", "")
try:
    with open(guidelines_path) as f:
        guidelines = f.read().strip()
except (OSError, TypeError):
    guidelines = ""

os.makedirs(OUT_DIR, exist_ok=True)

system_prompt = f"You are a senior engineer reviewing code at Trino. {guidelines}".strip()

# Group formatted records by PR number
by_pr = defaultdict(list)
with open(CURATED_PATH) as f:
    for line in f:
        row = json.loads(line)
        record = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Review this diff:\n\n{row['file']}: {row['diff_hunk']}"},
                {"role": "assistant", "content": row["comment_body"]},
            ]
        }
        by_pr[row["pr_number"]].append(record)

# Shuffle PR numbers then split 80/10/10
pr_numbers = sorted(by_pr.keys())
random.seed(42)
random.shuffle(pr_numbers)

n = len(pr_numbers)
n_train = int(n * 0.80)
n_val = int(n * 0.10)

train_prs = set(pr_numbers[:n_train])
val_prs = set(pr_numbers[n_train:n_train + n_val])
test_prs = set(pr_numbers[n_train + n_val:])

assert train_prs.isdisjoint(val_prs), "Train/val overlap"
assert train_prs.isdisjoint(test_prs), "Train/test overlap"
assert val_prs.isdisjoint(test_prs), "Val/test overlap"

def write_split(path, pr_set):
    rows = [r for pr in pr_set for r in by_pr[pr]]
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return len(rows)

train_count = write_split(f"{OUT_DIR}/train.jsonl", train_prs)
val_count = write_split(f"{OUT_DIR}/val.jsonl", val_prs)
test_count = write_split(f"{OUT_DIR}/test.jsonl", test_prs)

print(f"PRs:  train={len(train_prs)}  val={len(val_prs)}  test={len(test_prs)}  total={n}")
print(f"Rows: train={train_count}  val={val_count}  test={test_count}  total={train_count + val_count + test_count}")
