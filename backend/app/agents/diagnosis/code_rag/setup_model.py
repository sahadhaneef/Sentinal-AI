"""Explicit operator-only pinned model download; runtime retrieval never downloads."""

import argparse
import logging
import urllib.request
from pathlib import Path

from .config import RagSettings
from .embeddings import MODEL_FILES, MODEL_REPOSITORY, MODEL_REVISION, verify_model
from .ingestion import reject_redirects

LOGGER = logging.getLogger(__name__)


def download_model(root: Path) -> None:
    """Download fixed public model files over TLS and validate their pinned checksums."""
    reject_redirects(root)
    root.mkdir(parents=True, exist_ok=True)
    for name in MODEL_FILES:
        target = root / name
        reject_redirects(target)
        if target.exists():
            continue
        url = f"https://huggingface.co/{MODEL_REPOSITORY}/resolve/{MODEL_REVISION}/{name}"
        temporary = root / f"{name}.download"
        reject_redirects(temporary)
        with urllib.request.urlopen(url, timeout=120) as response, temporary.open("xb") as output:
            total = 0
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > 80 * 1024 * 1024:
                    raise ValueError("Model file exceeded download limit")
                output.write(block)
        temporary.rename(target)
    verify_model(root)
    LOGGER.info("Pinned local semantic model verified", extra={"revision": MODEL_REVISION})


def main() -> None:
    """Run only when the operator explicitly requests model installation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=RagSettings().model_root)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    download_model(args.root)


if __name__ == "__main__":
    main()
