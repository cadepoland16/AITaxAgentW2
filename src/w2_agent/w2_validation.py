from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from langchain_community.document_loaders import PyPDFLoader


_AMOUNT_PATTERN = r"([0-9][0-9,]*(?:\.[0-9]{2})?)"


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


def _first_amount_match(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        raw = match.group(1).replace(",", "")
        try:
            return float(raw)
        except ValueError:
            continue
    return None


def _extract_box12_codes(text: str) -> list[tuple[str, float]]:
    # Capture common "D 12000.00" style pairs near box-12 references.
    candidates: list[tuple[str, float]] = []
    lines = text.splitlines()
    for line in lines:
        if "12" not in line and "box 12" not in line.lower():
            continue
        for code, amount in re.findall(r"\b([A-Za-z]{1,2})\s+\$?" + _AMOUNT_PATTERN, line):
            try:
                candidates.append((code.upper(), float(amount.replace(",", ""))))
            except ValueError:
                continue
    # Deduplicate while preserving order.
    deduped: list[tuple[str, float]] = []
    seen: set[tuple[str, float]] = set()
    for item in candidates:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def parse_w2_fields(text: str) -> dict[str, float | list[tuple[str, float]] | None]:
    return {
        "box1_wages": _first_amount_match(
            text,
            [
                rf"(?:Box\s*1|1\s+Wages.*?compensation)\s*[:\-]?\s*\$?{_AMOUNT_PATTERN}",
            ],
        ),
        "box2_fed_withholding": _first_amount_match(
            text,
            [
                rf"(?:Box\s*2|2\s+Federal income tax withheld)\s*[:\-]?\s*\$?{_AMOUNT_PATTERN}",
            ],
        ),
        "box3_ss_wages": _first_amount_match(
            text,
            [
                rf"(?:Box\s*3|3\s+Social security wages)\s*[:\-]?\s*\$?{_AMOUNT_PATTERN}",
            ],
        ),
        "box5_medicare_wages": _first_amount_match(
            text,
            [
                rf"(?:Box\s*5|5\s+Medicare wages(?: and tips)?)\s*[:\-]?\s*\$?{_AMOUNT_PATTERN}",
            ],
        ),
        "state_wages": _first_amount_match(
            text,
            [
                rf"(?:State wages.*?etc\.?)\s*[:\-]?\s*\$?{_AMOUNT_PATTERN}",
            ],
        ),
        "state_withholding": _first_amount_match(
            text,
            [
                rf"(?:State income tax)\s*[:\-]?\s*\$?{_AMOUNT_PATTERN}",
            ],
        ),
        "local_wages": _first_amount_match(
            text,
            [
                rf"(?:Local wages.*?etc\.?)\s*[:\-]?\s*\$?{_AMOUNT_PATTERN}",
            ],
        ),
        "local_withholding": _first_amount_match(
            text,
            [
                rf"(?:Local income tax)\s*[:\-]?\s*\$?{_AMOUNT_PATTERN}",
            ],
        ),
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
