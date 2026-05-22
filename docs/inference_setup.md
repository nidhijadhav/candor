# Inference Setup

How to run the Candor inference server locally using a fine-tuned GGUF model.

---

## Prerequisites

Install llama.cpp via Homebrew:

```bash
brew install llama.cpp
```

This provides `llama-server` and `llama-cli` on your PATH.

---

## Downloading the Base Model

The base model is Code Llama 13B Instruct. Download a pre-quantized GGUF from Hugging Face:

```bash
mkdir -p models/base-model
curl -L -o models/base-model/codellama-13b-instruct.Q4_K_M.gguf \
  "https://huggingface.co/TheBloke/CodeLlama-13B-Instruct-GGUF/resolve/main/codellama-13b-instruct.Q4_K_M.gguf"
```

For fine-tuning you also need the full fp16 HuggingFace weights (not GGUF). Download them separately:

```bash
huggingface-cli download codellama/CodeLlama-13b-Instruct-hf \
  --local-dir models/base-model-hf
```

---

## Merging and Converting the Adapter

After training, the LoRA adapter lives in `models/trino_adapter/`. Three steps convert it to a runnable GGUF.

### Step 1 — Merge adapter into base model

```bash
python scripts/merge_adapter.py \
  --base-model models/base-model-hf \
  --adapter models/trino_adapter \
  --output models/trino-merged
```

This loads the base model, applies `PeftModel.merge_and_unload()`, and saves a standard HuggingFace model to `models/trino-merged/`.

### Step 2 — Convert to GGUF (fp16)

```bash
python $(brew --prefix llama.cpp)/convert_hf_to_gguf.py \
  models/trino-merged \
  --outtype f16 \
  --outfile models/trino-merged-f16.gguf
```

### Step 3 — Quantize to Q4_K_M

```bash
llama-quantize \
  models/trino-merged-f16.gguf \
  models/trino-merged.gguf \
  Q4_K_M
```

The final model is at `models/trino-merged.gguf` (~7GB for a 13B model at Q4_K_M).

---

## Starting the Inference Server

```bash
python inference/server/start.py \
  --model models/trino-merged.gguf \
  --port 8080 \
  --ctx-size 4096
```

The server exposes:
- `GET  /health` — returns `{"status":"ok"}` when ready
- `POST /v1/chat/completions` — OpenAI-compatible chat endpoint

---

## Testing with curl

Wait for the health check to return OK, then send a request:

```bash
curl -s http://127.0.0.1:8080/health

curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "system",
        "content": "You are a senior engineer reviewing code at Trino."
      },
      {
        "role": "user",
        "content": "Review this diff:\n\nFoo.java: @@ -1,5 +1,6 @@\n+    public void process() throws Exception {"
      }
    ],
    "temperature": 0.2,
    "max_tokens": 512
  }' | python -m json.tool
```
