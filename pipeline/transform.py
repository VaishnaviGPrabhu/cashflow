"""Transform step: clean, type-cast and validate each dataset.

Rows that fail validation are *rejected with a reason* (never silently fixed),
matching the project's rule that no silent correction is applied to finance data.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

import pandas as pd

from core.validators import SCHEMAS

from .extract import ExtractedDataset

ENUMS = {
    "transactions": {"type": {"inflow", "outflow"}},
    "accounts_receivable": {"status": {"open", "paid", "overdue"}},
    "accounts_payable": {"status": {"open", "paid", "overdue"}},
}
LOWERCASE = {"transactions": ["type"], "accounts_receivable": ["status"], "accounts_payable": ["status"]}


class SchemaError(Exception):
    """A source file is missing a required column; the run must stop."""


@dataclass
class Reject:
    dataset: str
    reason: str
    raw_record: str


@dataclass
class TransformResult:
    clean: dict[str, pd.DataFrame] = field(default_factory=dict)
    rejects: list[Reject] = field(default_factory=list)

    def rejects_for(self, dataset: str) -> list[Reject]:
        return [r for r in self.rejects if r.dataset == dataset]


class Transformer:
    def transform(self, extracted: dict[str, ExtractedDataset]) -> TransformResult:
        result = TransformResult()
        for name, ds in extracted.items():
            clean, rejects = self._clean(name, ds.frame)
            result.clean[name] = clean
            result.rejects.extend(rejects)
        return result

    def _clean(self, name: str, raw: pd.DataFrame) -> tuple[pd.DataFrame, list[Reject]]:
        schema = SCHEMAS[name]
        missing = [c for c in schema["required"] if c not in raw.columns]
        if missing:
            raise SchemaError(f"{name}: missing required column(s) {missing}")

        df = raw[schema["required"]].copy()
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        for col in LOWERCASE.get(name, []):
            df[col] = df[col].str.lower()

        reasons: list[list[str]] = [[] for _ in range(len(df))]

        def flag(mask: pd.Series, message: str) -> None:
            for pos in [i for i, bad in enumerate(mask.tolist()) if bad]:
                reasons[pos].append(message)

        for col in schema["required"]:
            flag(df[col] == "", f"missing value in {col}")
        for col in schema.get("numeric", []):
            parsed = pd.to_numeric(df[col], errors="coerce")
            flag((df[col] != "") & parsed.isna(), f"invalid number in {col}")
            df[col] = parsed
            if col in schema.get("nonnegative", []):
                flag(parsed < 0, f"negative value in {col}")
        for col in schema.get("date", []):
            parsed = pd.to_datetime(df[col], errors="coerce")
            flag((df[col] != "") & parsed.isna(), f"invalid date in {col}")
            df[col] = parsed.dt.strftime("%Y-%m-%d")
        for col, allowed in ENUMS.get(name, {}).items():
            flag((df[col] != "") & ~df[col].isin(allowed), f"unexpected value in {col}")

        bad = [bool(r) for r in reasons]
        rejects = [
            Reject(name, "; ".join(reasons[i]), json.dumps(raw.iloc[i].to_dict(), default=str))
            for i in range(len(df)) if bad[i]
        ]
        clean = df[[not b for b in bad]].reset_index(drop=True)
        if name == "transactions":
            clean = self._add_row_hash(clean)
        return clean, rejects

    @staticmethod
    def _add_row_hash(df: pd.DataFrame) -> pd.DataFrame:
        """Stable id per transaction so re-running a load never duplicates rows.

        Identical rows (same day/vendor/amount) are legitimate, so each one also
        gets its occurrence number: hash(content) + '#' + n.
        """
        df = df.copy()
        if df.empty:
            df["row_hash"], df["is_repeat"] = pd.Series(dtype=str), pd.Series(dtype=int)
            return df
        keys = ["date", "type", "category", "vendor", "amount"]
        occurrence = df.groupby(keys).cumcount()
        content = df[keys].astype(str).agg("|".join, axis=1)
        df["row_hash"] = [
            hashlib.sha1(f"{c}#{n}".encode()).hexdigest() for c, n in zip(content, occurrence)
        ]
        df["is_repeat"] = (occurrence > 0).astype(int)
        return df
