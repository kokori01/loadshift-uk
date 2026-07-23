"""Serialisation helpers for pipeline outputs."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel


def write_jsonl(records: Iterable[BaseModel], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(
                json.dumps(record.model_dump(mode="json"), sort_keys=True)
            )
            handle.write("\n")
