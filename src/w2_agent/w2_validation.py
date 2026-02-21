from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from langchain_community.document_loaders import PyPDFLoader


_AMOUNT_PATTERN = (
    r"("
    r"[0-9][0-9,]*(?:\.[0-9]{2})"        # standard decimal amount
    r"|[0-9]{1,3}\s+[0-9]{3}\s+[0-9]{2}"  # split thousands, e.g. 5 262 70
    r")"
)


@dataclass
class ValidationIssue:
    level: str
    code: str
    message: str


def load_w2_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        docs = PyPDFLoader(str(path)).load()
        return "\n".join(doc.page_content for doc in docs)
    raise ValueError("Unsupported file type. Use .pdf, .txt, or .md")


def _to_float(raw: str) -> float | None:
    token = raw.strip()
    if re.fullmatch(r"[0-9]{1,3}\s+[0-9]{3}\s+[0-9]{2}", token):
        a, b, c = re.split(r"\s+", token)
        token = f"{a}{b}.{c}"
    cleaned = token.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize(text: str) -> str:
    # Normalize whitespace and punctuation noise common in PDF extraction.
    squashed = re.sub(r"[\t\r\f\v]+", " ", text)
    squashed = re.sub(r"\s+", " ", squashed)
    # Convert split-money sequences into decimal format for regex matching.
    squashed = re.sub(r"\b([0-9]{1,3})\s+([0-9]{3})\s+([0-9]{2})\b", r"\1,\2.\3", squashed)
    return squashed.strip()


def _first_amount_match(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        value = _to_float(match.group(1))
        if value is not None:
            return value
    return None


def _extract_by_keywords(text: str, keyword_patterns: list[str]) -> float | None:
    raw_text = text
    normalized = _normalize(text)

    patterns: list[str] = []
    for keyword in keyword_patterns:
        # Same-line/nearby value in raw extracted text.
        patterns.append(rf"(?:{keyword})[^0-9$]{{0,120}}\$?{_AMOUNT_PATTERN}")
        # Value-first cases where amount appears before truncated label in PDFs.
        patterns.append(rf"\$?{_AMOUNT_PATTERN}[^0-9A-Za-z]{{0,120}}(?:{keyword})")
        # Normalized fallback with bigger gap.
        patterns.append(rf"(?:{keyword})[^0-9$]{{0,180}}\$?{_AMOUNT_PATTERN}")

    value = _first_amount_match(raw_text, patterns)
    if value is not None:
        return value
    return _first_amount_match(normalized, patterns)


def _extract_box12_codes(text: str) -> list[tuple[str, float]]:
    candidates: list[tuple[str, float]] = []
    lines = text.splitlines()

    # Strong signal: explicit box slot labels, e.g. "12a D 5000.00".
    slot_pattern = re.compile(r"\b12[abcd]?\s*[:\-]?\s*([A-Za-z]{1,2})\s+\$?" + _AMOUNT_PATTERN)
    inline_box12_pattern = re.compile(
        r"\b([A-Za-z]{1,2})\s*[-:]?\s*box\s*12[^0-9$]{0,50}\$?" + _AMOUNT_PATTERN,
        flags=re.IGNORECASE,
    )

    for line in lines:
        for code, amount in slot_pattern.findall(line):
            value = _to_float(amount)
            if value is not None:
                candidates.append((code.upper(), value))
        for code, amount in inline_box12_pattern.findall(line):
            value = _to_float(amount)
            if value is not None:
                candidates.append((code.upper(), value))

    # Fallback: lines explicitly mentioning Box 12 with code/value pairs.
    for line in lines:
        if "box 12" not in line.lower() and "12" not in line:
            continue
        for code, amount in re.findall(r"\b([A-Za-z]{1,2})\s+\$?" + _AMOUNT_PATTERN, line):
            value = _to_float(amount)
            if value is not None:
                candidates.append((code.upper(), value))

    deduped: list[tuple[str, float]] = []
    seen: set[tuple[str, float]] = set()
    for item in candidates:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def parse_w2_fields(text: str) -> dict[str, float | list[tuple[str, float]] | None]:
    box1 = _extract_by_keywords(
        text,
        [
            r"(?:box\s*1|\b1\b)\s*wages(?:,?\s*tips)?(?:,?\s*other\s*compensation)?",
            r"box\s*1\s*of\s*w-?2",
        ],
    )
    box2 = _extract_by_keywords(
        text,
        [
            r"(?:box\s*2|\b2\b)\s*federal\s*income\s*tax\s*withheld",
            r"box\s*2\s*of\s*w-?2",
        ],
    )
    box3 = _extract_by_keywords(
        text,
        [
            r"(?:box\s*3|\b3\b)\s*social\s*security\s*wages",
            r"box\s*3\s*of\s*w-?2",
        ],
    )
    box5 = _extract_by_keywords(
        text,
        [
            r"(?:box\s*5|\b5\b)\s*medicare\s*wages(?:\s*and\s*tips)?",
            r"box\s*5\s*of\s*w-?2",
        ],
    )

    state_wages = _extract_by_keywords(
        text,
        [
            r"state\s*wages(?:,?\s*tips)?(?:,?\s*etc\.?)*",
            r"(?:box\s*16|\b16\b)\s*state\s*wages",
        ],
    )
    state_withholding = _extract_by_keywords(
        text,
        [
            r"state\s*income\s*tax",
            r"(?:box\s*17|\b17\b)\s*state\s*income\s*tax",
        ],
    )
    local_wages = _extract_by_keywords(
        text,
        [
            r"local\s*wages(?:,?\s*tips)?(?:,?\s*etc\.?)*",
            r"(?:box\s*18|\b18\b)\s*local\s*wages",
        ],
    )
    local_withholding = _extract_by_keywords(
        text,
        [
            r"local\s*income\s*tax",
            r"(?:box\s*19|\b19\b)\s*local\s*income\s*tax",
        ],
    )

    return {
        "box1_wages": box1,
        "box2_fed_withholding": box2,
        "box3_ss_wages": box3,
        "box5_medicare_wages": box5,
        "state_wages": state_wages,
        "state_withholding": state_withholding,
        "local_wages": local_wages,
        "local_withholding": local_withholding,
        "box12_codes": _extract_box12_codes(text),
    }


def validate_w2_fields(parsed: dict[str, float | list[tuple[str, float]] | None]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    required_numeric = [
        "box1_wages",
        "box2_fed_withholding",
        "box3_ss_wages",
        "box5_medicare_wages",
    ]
    for field in required_numeric:
        value = parsed.get(field)
        if value is None:
            issues.append(
                ValidationIssue(
                    level="warn",
                    code="MISSING_FIELD",
                    message=f"{field} was not detected. Verify OCR/parsing and source document quality.",
                )
            )
        elif isinstance(value, float) and value < 0:
            issues.append(
                ValidationIssue(
                    level="warn",
                    code="NEGATIVE_AMOUNT",
                    message=f"{field} is negative ({value:.2f}), which is unusual for W-2 summary fields.",
                )
            )

    box1 = parsed.get("box1_wages")
    box2 = parsed.get("box2_fed_withholding")
    box3 = parsed.get("box3_ss_wages")
    box5 = parsed.get("box5_medicare_wages")

    if isinstance(box1, float) and isinstance(box2, float):
        if box1 > 0 and box2 == 0:
            issues.append(
                ValidationIssue(
                    level="warn",
                    code="ZERO_WITHHOLDING",
                    message="Box 2 is 0 while Box 1 is positive. Confirm withholding setup and payroll records.",
                )
            )
        if box1 > 0 and box2 / box1 > 0.60:
            issues.append(
                ValidationIssue(
                    level="warn",
                    code="HIGH_WITHHOLDING_RATIO",
                    message="Federal withholding appears very high relative to wages. Review for possible data issues.",
                )
            )

    if isinstance(box1, float) and isinstance(box3, float) and box1 > 0 and box3 < box1 * 0.50:
        issues.append(
            ValidationIssue(
                level="warn",
                code="LOW_BOX3_VS_BOX1",
                message="Box 3 is much lower than Box 1. Confirm Social Security wage treatment.",
            )
        )

    if isinstance(box1, float) and isinstance(box5, float) and box1 > 0 and box5 < box1 * 0.50:
        issues.append(
            ValidationIssue(
                level="warn",
                code="LOW_BOX5_VS_BOX1",
                message="Box 5 is much lower than Box 1. Confirm Medicare wage treatment.",
            )
        )

    state_wages = parsed.get("state_wages")
    state_withholding = parsed.get("state_withholding")
    local_wages = parsed.get("local_wages")
    local_withholding = parsed.get("local_withholding")
    if isinstance(state_withholding, float) and state_withholding > 0 and state_wages is None:
        issues.append(
            ValidationIssue(
                level="warn",
                code="STATE_MISSING_WAGES",
                message="State withholding is present but state wages were not detected.",
            )
        )
    if isinstance(local_withholding, float) and local_withholding > 0 and local_wages is None:
        issues.append(
            ValidationIssue(
                level="warn",
                code="LOCAL_MISSING_WAGES",
                message="Local withholding is present but local wages were not detected.",
            )
        )

    box12_codes = parsed.get("box12_codes")
    if isinstance(box12_codes, list) and len(box12_codes) == 0:
        issues.append(
            ValidationIssue(
                level="info",
                code="BOX12_NOT_FOUND",
                message="No Box 12 codes were detected. This may be normal for some employees.",
            )
        )

    return issues
