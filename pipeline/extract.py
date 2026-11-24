"""Extract step: read source CSV files exactly as delivered (all values as text)."""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import DATASETS


@dataclass
class ExtractedDataset:
    name: str
    path: Path
    frame: pd.DataFrame  # raw values, every column as text
    sha256: str  # fingerprint of the exact file that was read

    @property
    def row_count(self) -> int:
        return len(self.frame)


class Extractor:
    def __init__(self, source_dir: Path):
        self.source_dir = Path(source_dir)

    def extract(self) -> dict[str, ExtractedDataset]:
        out: dict[str, ExtractedDataset] = {}
        for name, filename in DATASETS.items():
            path = self.source_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"Source file missing for '{name}': {path}")
            payload = path.read_bytes()
            frame = pd.read_csv(io.BytesIO(payload), dtype=str, keep_default_na=False)
            frame.columns = [c.strip() for c in frame.columns]
            out[name] = ExtractedDataset(name, path, frame, hashlib.sha256(payload).hexdigest())
        return out
