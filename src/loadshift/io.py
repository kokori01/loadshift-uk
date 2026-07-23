"""Serialisation helpers for pipeline outputs."""

from __future__ import annotations

import json
from collections.abc import Iterable
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel


def file_sha256(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return a streaming SHA-256 checksum for provenance metadata."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def write_jsonl(records: Iterable[BaseModel], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.model_dump(mode="json"), sort_keys=True))
            handle.write("\n")
