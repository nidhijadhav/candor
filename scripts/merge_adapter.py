import argparse
import os

parser = argparse.ArgumentParser(description="Merge a LoRA adapter into the base model")
parser.add_argument("--adapter", required=True, help="Path to the LoRA adapter directory")
parser.add_argument("--base-model", required=True, help="Path to the base model directory")
parser.add_argument("--output", required=True, help="Output path for the merged model")
args = parser.parse_args()

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

print(f"Loading base model from {args.base_model}...")
model = AutoModelForCausalLM.from_pretrained(
    args.base_model,
    torch_dtype=torch.float16,
    device_map="auto",
)
tokenizer = AutoTokenizer.from_pretrained(args.base_model)

print(f"Loading adapter from {args.adapter}...")
model = PeftModel.from_pretrained(model, args.adapter)

print("Merging adapter weights...")
model = model.merge_and_unload()

os.makedirs(args.output, exist_ok=True)
print(f"Saving merged model to {args.output}...")
model.save_pretrained(args.output)
tokenizer.save_pretrained(args.output)

print("Done.")
print()
print("Next steps:")
print(f"  1. Convert to GGUF:  python convert_hf_to_gguf.py {args.output} --outtype f16 --outfile models/trino-merged-f16.gguf")
print(f"  2. Quantize:         llama-quantize models/trino-merged-f16.gguf models/trino-merged.gguf Q4_K_M")
