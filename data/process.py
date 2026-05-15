import os
import json
import yaml
from dotenv import load_dotenv

load_dotenv()

CURATED_PATH = "data/curated/trinodb_trino.jsonl"
OUT_PATH = "data/processed/trinodb_trino.jsonl"
CONFIG_PATH = "data/curation_config.yaml"

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

guidelines_path = config.get("guidelines_path", "")
try:
    with open(guidelines_path) as f:
        guidelines = f.read().strip()
except (OSError, TypeError):
    guidelines = ""

os.makedirs("data/processed", exist_ok=True)

system_prompt = f"You are a senior engineer reviewing code at Trino. {guidelines}".strip()

count = 0
with open(CURATED_PATH) as inp, open(OUT_PATH, "w") as out:
    for line in inp:
        row = json.loads(line)
        record = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Review this diff:\n\n{row['file']}: {row['diff_hunk']}"},
                {"role": "assistant", "content": row["comment_body"]},
            ]
        }
        out.write(json.dumps(record) + "\n")
        count += 1

print(f"Processed {count} rows -> {OUT_PATH}")
