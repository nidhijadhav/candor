import argparse
import subprocess
import sys

parser = argparse.ArgumentParser(description="Start the llama-server inference server")
parser.add_argument("--model", required=True, help="Path to GGUF model file")
parser.add_argument("--port", type=int, default=8080)
parser.add_argument("--ctx-size", type=int, default=4096)
args = parser.parse_args()

cmd = [
    "llama-server",
    "--model", args.model,
    "--host", "127.0.0.1",
    "--port", str(args.port),
    "--ctx-size", str(args.ctx_size),
]

print(f"Starting llama-server...")
print(f"  Model:  {args.model}")
print(f"  URL:    http://127.0.0.1:{args.port}")
print(f"  Health: http://127.0.0.1:{args.port}/health")
print(f"  Chat:   http://127.0.0.1:{args.port}/v1/chat/completions")
print()

try:
    proc = subprocess.run(cmd)
    sys.exit(proc.returncode)
except KeyboardInterrupt:
    print("\nServer stopped.")
