"""HTML → plain text for scheme pages (Phase 1). Preserve headings; drop chrome."""

from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

_DROP_TAGS = (
    "script",
    "style",
    "noscript",
    "svg",
    "iframe",
    "canvas",
    "form",
    "button",
    "input",
    "nav",
    "footer",
    "header",
    "aside",
)

_HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")

# Groww CSS-module prefixes that are scheme facts (not site chrome).
_KEEP_CLASS_PREFIXES = (
    "fundDetails",
    "investmentObjective",
    "exitLoadStampDutyTax",
    "holdings",
    "fundHouse",
    "fundManagement",
    "returnsAndRankings",
    "understandTerms",
    "faq",
)

_DROP_CLASS_PREFIXES = (
    "footer",
    "footerTopSection",
    "dropdownUI",
    "letterLinks",
    "loggedOut",
    "compareSimilarFunds",
    "returnCalculator",
    "companyLogo",
    "lazyload-wrapper",
)

# Keep fact-related JSON keys if Groww embeds Next.js data.
_FACT_KEY_HINTS = (
    "expense",
    "exit",
    "load",
    "sip",
    "lock",
    "risk",
    "benchmark",
    "nav",
    "aum",
    "min",
    "tenure",
    "elss",
    "tax",
    "statement",
    "ratio",
    "category",
    "fund",
    "scheme",
    "return",
    "holding",
    "objective",
)


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    embedded = _extract_embedded_json_text(soup)
    visible = _extract_visible_text(soup)
    parts = [p for p in (visible, embedded) if p]
    merged = "\n\n".join(parts)
    return _normalize_whitespace(merged)


def _extract_visible_text(soup: BeautifulSoup) -> str:
    root = soup.find("main") or soup.find("article") or soup.body or soup
    working = BeautifulSoup(str(root), "lxml")

    for tag in working.find_all(_DROP_TAGS):
        tag.decompose()
    drop_class_nodes = [
        tag
        for tag in working.find_all(True)
        if isinstance(tag, Tag)
        and tag.attrs is not None
        and _class_matches(tag, _DROP_CLASS_PREFIXES)
    ]
    for tag in _top_level_keep_nodes(drop_class_nodes):
        tag.decompose()

    keep_nodes = [
        tag
        for tag in working.find_all(True)
        if _class_matches(tag, _KEEP_CLASS_PREFIXES)
    ]
    h1 = working.find("h1")
    pieces: list[Tag | BeautifulSoup] = []
    if h1:
        pieces.append(h1)
    if keep_nodes:
        pieces.extend(_top_level_keep_nodes(keep_nodes))
        lines: list[str] = []
        for piece in pieces:
            lines.extend(_lines_from_tree(piece))
        return "\n".join(_dedupe_consecutive(lines))

    return "\n".join(_dedupe_consecutive(_lines_from_tree(working)))


def _class_matches(tag: Tag, prefixes: tuple[str, ...]) -> bool:
    if not isinstance(tag, Tag) or tag.attrs is None:
        return False
    classes = tag.get("class") or []
    for cls in classes:
        name = cls.split("_")[0]
        if name in prefixes:
            return True
    return False


def _top_level_keep_nodes(nodes: list[Tag]) -> list[Tag]:
    selected: list[Tag] = []
    for node in nodes:
        if any(other is not node and other in node.parents for other in nodes):
            continue
        selected.append(node)
    return selected


def _lines_from_tree(root: Tag | BeautifulSoup) -> list[str]:
    lines: list[str] = []
    for element in root.descendants:
        if isinstance(element, Tag) and element.name in _HEADING_TAGS:
            heading = element.get_text(" ", strip=True)
            if heading:
                lines.append(heading)
        elif isinstance(element, NavigableString):
            parent = element.parent
            if parent is None or parent.name in _HEADING_TAGS:
                continue
            if parent.name in ("script", "style"):
                continue
            text = str(element).strip()
            if text:
                lines.append(text)
    return lines


def _extract_embedded_json_text(soup: BeautifulSoup) -> str:
    blobs: list[str] = []

    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        blobs.append(_json_to_fact_lines(next_data.string))

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if script.string:
            blobs.append(_json_to_fact_lines(script.string))

    return "\n".join(line for blob in blobs for line in blob.splitlines() if line)


def _json_to_fact_lines(raw: str) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    pairs: list[str] = []
    _walk_json(data, pairs)
    return "\n".join(_dedupe_consecutive(pairs))


def _walk_json(node: Any, out: list[str], prefix: str = "") -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            key_str = str(key)
            path = f"{prefix}.{key_str}" if prefix else key_str
            if _looks_like_fact_key(key_str) or _looks_like_fact_key(path):
                if isinstance(value, (str, int, float, bool)) and str(value).strip():
                    label = _humanize_key(key_str)
                    out.append(f"{label}: {value}")
                elif isinstance(value, list) and value and all(
                    isinstance(x, (str, int, float)) for x in value[:8]
                ):
                    label = _humanize_key(key_str)
                    joined = ", ".join(str(x) for x in value[:12])
                    out.append(f"{label}: {joined}")
            _walk_json(value, out, path)
    elif isinstance(node, list):
        for item in node[:40]:
            _walk_json(item, out, prefix)


def _looks_like_fact_key(key: str) -> bool:
    lowered = key.lower()
    return any(hint in lowered for hint in _FACT_KEY_HINTS)


def _humanize_key(key: str) -> str:
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", key)
    return spaced.replace("_", " ").strip()


def _dedupe_consecutive(lines: list[str]) -> list[str]:
    out: list[str] = []
    prev = None
    for line in lines:
        compact = re.sub(r"\s+", " ", line).strip()
        if not compact or compact == prev:
            continue
        out.append(compact)
        prev = compact
    return out


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
