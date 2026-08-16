"""Structure-aware extraction of official 3GPP PDF specifications."""

from dataclasses import dataclass
from pathlib import Path
import re

import fitz


STANDALONE_SECTION_PATTERN = re.compile(r"^(?P<number>\d{1,2}(?:\.\d{1,3}){0,5}[A-Za-z]?)$")
COMBINED_SECTION_PATTERN = re.compile(
    r"^(?P<number>\d{1,2}(?:\.\d{1,3}){1,5}[A-Za-z]?)\s+(?P<title>[A-Za-z][A-Za-z0-9 ,;()/'&+\-]{2,120})$"
)
SPEC_PATTERN = re.compile(r"\bTS\s*(\d{2}\.\d{3})\b", re.IGNORECASE)
RELEASE_PATTERN = re.compile(r"\bRelease\s+(\d+)\b", re.IGNORECASE)
CONTENTS_LEADER_PATTERN = re.compile(r"\.{8,}\s*\d+\s*$")


@dataclass(frozen=True)
class ExtractedChunk:
    text: str
    specification: str
    release: str | None
    section: str | None
    section_title: str | None
    page: int
    source: str
    source_url: str | None = None


def _normalise(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\u00ad", "")).strip()


def _metadata(document_text: str, filename: str) -> tuple[str, str | None]:
    spec = SPEC_PATTERN.search(document_text) or SPEC_PATTERN.search(filename)
    release = RELEASE_PATTERN.search(document_text)
    specification = f"TS {spec.group(1)}" if spec else "Unknown 3GPP specification"
    return specification, f"Release {release.group(1)}" if release else None


def _is_running_header_or_footer(line: str) -> bool:
    """Remove repeating ETSI/3GPP page furniture without removing clause numbers."""
    lowered = line.lower()
    return (
        line == "ETSI"
        or lowered.startswith("etsi ts ")
        or lowered.startswith("3gpp ts ")
        or (line.isdigit() and len(line) >= 3)
    )


def _is_contents_page(lines: list[str]) -> bool:
    """The contents is useful for people, but must never become retrieval evidence."""
    leaders = sum(bool(CONTENTS_LEADER_PATTERN.search(line)) for line in lines)
    return leaders >= 4


def _heading_at(lines: list[str], index: int) -> tuple[str, str, int] | None:
    """Return (clause number, title, consumed line count) for a conservative heading."""
    line = lines[index]
    combined = COMBINED_SECTION_PATTERN.match(line)
    if combined:
        return combined.group("number"), combined.group("title"), 1

    standalone = STANDALONE_SECTION_PATTERN.match(line)
    if not standalone or index + 1 >= len(lines):
        return None
    title = lines[index + 1]
    if (
        len(title) < 3
        or len(title) > 120
        or not re.match(r"^[A-Za-z]", title)
        or title.endswith((".", ";", ":"))
        or CONTENTS_LEADER_PATTERN.search(title)
    ):
        return None
    return standalone.group("number"), title, 2


def _split_clause_text(text: str, max_chars: int) -> list[str]:
    """Split only at sentence boundaries, retaining the current clause metadata."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    chunks: list[str] = []
    running = ""
    for sentence in sentences:
        candidate = f"{running} {sentence}".strip()
        if running and len(candidate) > max_chars:
            chunks.append(running)
            running = sentence
        else:
            running = candidate
    if running:
        chunks.append(running)
    return chunks


def extract_pdf(pdf_path: Path, source_url: str | None = None, max_chars: int = 1800) -> list[ExtractedChunk]:
    """Extract page-local evidence blocks while preserving verified clause context."""
    document = fitz.open(pdf_path)
    first_page = document[0].get_text("text") if document.page_count else ""
    specification, release = _metadata(first_page, pdf_path.name)
    current_section: str | None = None
    current_title: str | None = None
    chunks: list[ExtractedChunk] = []

    for page_number, page in enumerate(document, start=1):
        raw_lines = [_normalise(line) for line in page.get_text("text").splitlines()]
        lines = [line for line in raw_lines if line and not _is_running_header_or_footer(line)]
        if _is_contents_page(lines):
            continue

        buffer: list[str] = []

        def flush() -> None:
            text = "\n".join(buffer).strip()
            buffer.clear()
            if len(text) < 80:
                return
            for part in _split_clause_text(text, max_chars):
                if len(part) >= 80:
                    chunks.append(
                        ExtractedChunk(
                            part,
                            specification,
                            release,
                            current_section,
                            current_title,
                            page_number,
                            pdf_path.name,
                            source_url,
                        )
                    )

        index = 0
        while index < len(lines):
            heading = _heading_at(lines, index)
            if heading:
                flush()
                current_section, current_title, consumed = heading
                index += consumed
                continue
            buffer.append(lines[index])
            index += 1
        flush()

    document.close()
    return chunks
