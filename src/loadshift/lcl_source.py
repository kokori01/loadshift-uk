"""Official Low Carbon London source discovery and sample extraction."""

from __future__ import annotations

import csv
import io
import json
import os
import re
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from loadshift.clients.http import JsonHttpClient
from loadshift.io import file_sha256

LCL_DATASET_ID = "vqm0d"
LCL_DATASET_PAGE = (
    "https://data.london.gov.uk/dataset/"
    "smartmeter-energy-consumption-data-in-london-households-vqm0d"
)
LCL_METADATA_URL = f"https://data.london.gov.uk/api/v3/dataset/{LCL_DATASET_ID}"
LCL_PARTITIONED_RESOURCE_TITLE = "low-carbon-london-data-168-files"
LCL_RAW_COLUMNS = (
    "LCLid",
    "stdorToU",
    "DateTime",
    "KWH/hh (per half hour)",
)
LCL_SCHEMA_VERSION = "lcl-raw-v1"
DEFAULT_USER_AGENT = "loadshift-uk/0.2 (+https://github.com/kokori01/loadshift-uk)"
_MEMBER_PATTERN = re.compile(r"LCL-June2015v2_(\d+)\.csv$")


@dataclass(frozen=True)
class LCLArchiveResource:
    """Metadata needed to retrieve the official partitioned archive."""

    resource_id: str
    title: str
    url: str
    size_bytes: int
    source_hash: str
    licence_title: str
    licence_url: str


@dataclass(frozen=True)
class LCLSampleResult:
    """Provenance and transfer statistics for a downloaded sample."""

    output: Path
    metadata_output: Path
    member_name: str
    rows: int
    sha256: str
    range_requests: int
    transferred_bytes: int


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return value


def discover_lcl_archive(
    http: JsonHttpClient | None = None,
) -> LCLArchiveResource:
    """Resolve the current official archive URL through the catalogue API."""

    payload = (http or JsonHttpClient(user_agent=DEFAULT_USER_AGENT)).get_json(
        LCL_METADATA_URL
    )
    resources = _require_mapping(payload.get("resources"), "resources")
    licence = _require_mapping(payload.get("licence"), "licence")

    for resource_id, raw_resource in resources.items():
        resource = _require_mapping(raw_resource, "resource")
        if resource.get("title") != LCL_PARTITIONED_RESOURCE_TITLE:
            continue

        url = str(resource.get("url", ""))
        if not url.startswith("https://data.london.gov.uk/download/"):
            raise ValueError("official LCL resource URL is not an HTTPS download")

        size_bytes = int(resource.get("size", 0))
        if size_bytes <= 0:
            raise ValueError("official LCL resource has an invalid size")

        return LCLArchiveResource(
            resource_id=str(resource_id),
            title=str(resource["title"]),
            url=url,
            size_bytes=size_bytes,
            source_hash=str(resource.get("hash", "")),
            licence_title=str(licence.get("title", "")),
            licence_url=str(licence.get("url", "")),
        )

    raise ValueError(f"catalogue does not contain {LCL_PARTITIONED_RESOURCE_TITLE!r}")


class HTTPRangeReader(io.RawIOBase):
    """Seekable HTTP reader that refuses full-file fallback responses."""

    def __init__(
        self,
        url: str,
        *,
        size_bytes: int,
        timeout_seconds: float = 60,
        block_size: int = 1024 * 1024,
        user_agent: str = DEFAULT_USER_AGENT,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        super().__init__()
        if not url.startswith("https://"):
            raise ValueError("range reader requires an HTTPS URL")
        if size_bytes <= 0:
            raise ValueError("size_bytes must be positive")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if block_size <= 0:
            raise ValueError("block_size must be positive")

        self.url = url
        self.size_bytes = size_bytes
        self.timeout_seconds = timeout_seconds
        self.block_size = block_size
        self.user_agent = user_agent
        self._opener = opener
        self._position = 0
        self._cache_start = 0
        self._cache = b""
        self.range_requests = 0
        self.transferred_bytes = 0
        self.etag: str | None = None
        self.last_modified: str | None = None

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            position = offset
        elif whence == io.SEEK_CUR:
            position = self._position + offset
        elif whence == io.SEEK_END:
            position = self.size_bytes + offset
        else:
            raise ValueError(f"unsupported seek mode: {whence}")

        if position < 0:
            raise ValueError("cannot seek before the beginning of the file")
        self._position = min(position, self.size_bytes)
        return self._position

    def _cached_slice(self, start: int, end: int) -> bytes | None:
        cache_end = self._cache_start + len(self._cache)
        if self._cache_start <= start and end <= cache_end:
            begin = start - self._cache_start
            return self._cache[begin : begin + (end - start)]
        return None

    def _fetch(self, start: int, requested_end: int) -> None:
        fetch_end = min(
            max(requested_end, start + self.block_size),
            self.size_bytes,
        )
        request = Request(
            self.url,
            headers={
                "Range": f"bytes={start}-{fetch_end - 1}",
                "User-Agent": self.user_agent,
            },
        )
        with self._opener(request, timeout=self.timeout_seconds) as response:
            status = getattr(response, "status", None)
            if status != 206:
                raise OSError(
                    "server ignored the byte-range request; "
                    "refusing to download the full archive"
                )
            payload = response.read()
            headers = response.headers

        expected = fetch_end - start
        expected_content_range = f"bytes {start}-{fetch_end - 1}/{self.size_bytes}"
        if headers.get("Content-Range") != expected_content_range:
            raise OSError("server returned an unexpected Content-Range header")
        if len(payload) != expected:
            raise OSError(
                f"incomplete byte range: expected {expected}, got {len(payload)}"
            )

        self._cache_start = start
        self._cache = payload
        self.range_requests += 1
        self.transferred_bytes += len(payload)
        self.etag = headers.get("ETag", self.etag)
        self.last_modified = headers.get("Last-Modified", self.last_modified)

    def read(self, size: int = -1) -> bytes:
        if self._position >= self.size_bytes:
            return b""

        if (
            size is None or size < 0
        ) and self.size_bytes - self._position > self.block_size:
            raise OSError(
                "refusing an unbounded read that could download the full archive"
            )
        end = (
            self.size_bytes
            if size is None or size < 0
            else min(self._position + size, self.size_bytes)
        )
        cached = self._cached_slice(self._position, end)
        if cached is None:
            self._fetch(self._position, end)
            cached = self._cached_slice(self._position, end)
        if cached is None:
            raise OSError("requested range was not cached after download")

        self._position += len(cached)
        return cached


def select_lcl_member(names: Sequence[str], member_name: str | None) -> str:
    """Select a partition deterministically, preferring numeric partition 0."""

    csv_members: list[tuple[int, str]] = []
    for name in names:
        match = _MEMBER_PATTERN.search(name)
        if match:
            csv_members.append((int(match.group(1)), name))

    if not csv_members:
        raise ValueError("archive does not contain an LCL partition CSV")

    if member_name is None:
        return min(csv_members)[1]

    exact = [name for _, name in csv_members if name == member_name]
    if not exact:
        available = ", ".join(name for _, name in sorted(csv_members)[:3])
        raise ValueError(
            f"archive member {member_name!r} not found; examples: {available}"
        )
    return exact[0]


def extract_lcl_rows(
    archive: zipfile.ZipFile,
    output: Path,
    *,
    rows: int,
    member_name: str | None = None,
) -> tuple[str, int]:
    """Extract the header and first N records from one official partition."""

    if rows <= 0:
        raise ValueError("rows must be positive")

    selected = select_lcl_member(archive.namelist(), member_name)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    temporary.unlink(missing_ok=True)

    extracted = 0
    try:
        with (
            archive.open(selected) as raw_input,
            io.TextIOWrapper(
                raw_input,
                encoding="utf-8-sig",
                newline="",
            ) as text_input,
            temporary.open("w", encoding="utf-8", newline="") as handle,
        ):
            reader = csv.reader(text_input)
            header = next(reader, None)
            normalised_header = tuple(column.strip() for column in (header or ()))
            if normalised_header != LCL_RAW_COLUMNS:
                raise ValueError(
                    "unexpected LCL columns: "
                    f"expected {LCL_RAW_COLUMNS!r}, got {header!r}"
                )

            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(LCL_RAW_COLUMNS)
            for row in reader:
                if len(row) != len(LCL_RAW_COLUMNS):
                    raise ValueError(
                        f"row has {len(row)} fields, expected {len(LCL_RAW_COLUMNS)}"
                    )
                writer.writerow(row)
                extracted += 1
                if extracted >= rows:
                    break

        if extracted == 0:
            raise ValueError("selected LCL partition contains no data rows")
        os.replace(temporary, output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise

    return selected, extracted


def _write_metadata(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.unlink(missing_ok=True)
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def fetch_lcl_sample(
    output: Path,
    *,
    rows: int,
    metadata_output: Path | None = None,
    member_name: str | None = None,
    http: JsonHttpClient | None = None,
) -> LCLSampleResult:
    """Download only the byte ranges required for one reproducible sample."""

    resource = discover_lcl_archive(http)
    reader = HTTPRangeReader(
        resource.url,
        size_bytes=resource.size_bytes,
    )
    with zipfile.ZipFile(reader) as archive:
        selected, extracted = extract_lcl_rows(
            archive,
            output,
            rows=rows,
            member_name=member_name,
        )

    checksum = file_sha256(output)
    metadata_path = metadata_output or output.with_suffix(
        output.suffix + ".metadata.json"
    )
    retrieved_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    _write_metadata(
        metadata_path,
        {
            "schema_version": LCL_SCHEMA_VERSION,
            "dataset_id": LCL_DATASET_ID,
            "dataset_page": LCL_DATASET_PAGE,
            "resource_id": resource.resource_id,
            "resource_title": resource.title,
            "resource_url": resource.url,
            "resource_size_bytes": resource.size_bytes,
            "resource_hash": resource.source_hash,
            "resource_etag": reader.etag,
            "resource_last_modified": reader.last_modified,
            "licence": {
                "title": resource.licence_title,
                "url": resource.licence_url,
            },
            "archive_member": selected,
            "requested_rows": rows,
            "extracted_rows": extracted,
            "sample_sha256": checksum,
            "retrieved_at_utc": retrieved_at,
            "transfer": {
                "range_requests": reader.range_requests,
                "bytes": reader.transferred_bytes,
                "fraction_of_archive": (reader.transferred_bytes / resource.size_bytes),
            },
        },
    )
    return LCLSampleResult(
        output=output,
        metadata_output=metadata_path,
        member_name=selected,
        rows=extracted,
        sha256=checksum,
        range_requests=reader.range_requests,
        transferred_bytes=reader.transferred_bytes,
    )
