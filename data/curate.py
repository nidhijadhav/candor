import os
import json
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = "data/raw/trinodb_trino"
OUT_PATH = "data/curated/trinodb_trino.jsonl"

os.makedirs("data/curated", exist_ok=True)

files = sorted(f for f in os.listdir(RAW_DIR) if f.endswith(".json"))
print(f"Found {len(files)} files in {RAW_DIR}")

comments = []
skipped = 0

for i, filename in enumerate(files, 1):
    try:
        with open(os.path.join(RAW_DIR, filename)) as f:
            pr = json.load(f)
    except (json.JSONDecodeError, OSError):
        skipped += 1
        continue

    for c in pr.get("comments", []):
        comments.append({
            "pr_number": pr["pr_number"],
            "merged_at": pr["merged_at"],
            "file": c.get("path"),
            "diff_hunk": c.get("diff_hunk"),
            "comment_body": c.get("body"),
            "reviewer_association": c.get("author_association"),
        })

    if i % 1000 == 0:
        print(f"  Processed {i}/{len(files)} files ({len(comments)} comments so far)...")

if skipped:
    print(f"Skipped {skipped} unreadable files.")

total = len(comments)
print(f"\nTotal comments before filtering: {total}")

# Filter 1: drop comments under 20 words
before = len(comments)
comments = [c for c in comments if len((c["comment_body"] or "").split()) >= 20]
dropped_short = before - len(comments)
print(f"Dropped (under 20 words):         {dropped_short}")

# Filter 2: drop comments where reviewer association is NONE
before = len(comments)
comments = [c for c in comments if c["reviewer_association"] != "NONE"]
dropped_none = before - len(comments)
print(f"Dropped (association = NONE):      {dropped_none}")

# Filter 3: drop comments from PRs where merged_at is null
before = len(comments)
comments = [c for c in comments if c["merged_at"] is not None]
dropped_unmerged = before - len(comments)
print(f"Dropped (PR not merged):           {dropped_unmerged}")

print(f"Final comment count:               {len(comments)}")

with open(OUT_PATH, "w") as f:
    for c in comments:
        f.write(json.dumps(c) + "\n")

print(f"\nSaved to {OUT_PATH}")
