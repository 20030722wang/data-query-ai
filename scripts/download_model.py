"""
Download the embedding model from HuggingFace Hub before first run.

The model file (~1.3GB) is gitignored because GitHub rejects files >100MB.
Run this script once to download it locally:

    python scripts/download_model.py
"""
import sys
from pathlib import Path

MODEL_ID = "BAAI/bge-large-zh-v1.5"
TARGET_DIR = Path(__file__).resolve().parents[1] / "docker" / "embedding" / "bge-large-zh-v1.5"


def main():
    target = TARGET_DIR / "pytorch_model.bin"
    if target.exists():
        print(f"模型已存在: {target} ({target.stat().st_size / 1e9:.1f} GB)")
        return

    print(f"正在从 HuggingFace 下载 {MODEL_ID} ...")
    print(f"目标路径: {TARGET_DIR}")
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id=MODEL_ID,
            local_dir=str(TARGET_DIR),
            local_dir_use_symlinks=False,
            resume_download=True,
        )
    except ImportError:
        print("请先安装 huggingface_hub: pip install huggingface_hub")
        sys.exit(1)

    print("下载完成。")


if __name__ == "__main__":
    main()
