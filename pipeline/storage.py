"""Archive the raw source files of every run (an immutable 'raw zone').

LocalArchive works out of the box. S3Archive does the same against an AWS S3
bucket and is only used when CASHFLOW_S3_BUCKET is set (credentials come from the
standard AWS environment / IAM role, never from the source code).
"""
from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path


class ArchiveStore(ABC):
    @abstractmethod
    def save(self, run_id: str, files: list[Path]) -> list[str]:
        """Copy the files for a run and return their archive locations."""


class LocalArchive(ArchiveStore):
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)

    def save(self, run_id: str, files: list[Path]) -> list[str]:
        target = self.base_dir / run_id
        target.mkdir(parents=True, exist_ok=True)
        locations = []
        for f in files:
            shutil.copy2(f, target / Path(f).name)
            locations.append(str(target / Path(f).name))
        return locations


class S3Archive(ArchiveStore):
    def __init__(self, bucket: str, prefix: str = "raw", client=None):
        self.bucket, self.prefix = bucket, prefix.strip("/")
        if client is None:
            import boto3  # imported lazily so boto3 stays optional
            client = boto3.client("s3")
        self.client = client

    def save(self, run_id: str, files: list[Path]) -> list[str]:
        locations = []
        for f in files:
            key = f"{self.prefix}/{run_id}/{Path(f).name}"
            self.client.upload_file(str(f), self.bucket, key)
            locations.append(f"s3://{self.bucket}/{key}")
        return locations


def archive_from_env(local_dir: Path) -> ArchiveStore:
    bucket = os.getenv("CASHFLOW_S3_BUCKET")
    return S3Archive(bucket, os.getenv("CASHFLOW_S3_PREFIX", "raw")) if bucket else LocalArchive(local_dir)
