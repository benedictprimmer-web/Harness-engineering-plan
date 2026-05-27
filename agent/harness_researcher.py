#!/usr/bin/env python3
"""
Research proposed harness-design changes with live docs when available and
committed source-card fallback when offline.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "research" / "sources"


@dataclass
class ResearchDecision:
    decision: str
    proposal: str
    evidence: list[dict[str, str]]
    risks: list[str]
    files_to_change: list[str]
    tests: list[str]
    used_offline_fallback: bool


def load_source_cards() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for path in sorted(SOURCE_DIR.glob("*.json")):
        try:
            cards.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return cards


def _fetch_title(url: str, timeout: float = 2.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "harness-researcher/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read(4096).decode("utf-8", errors="ignore")
    lower = text.lower()
    start = lower.find("<title>")
    end = lower.find("</title>")
    if start == -1 or end == -1 or end <= start:
        return ""
    return text[start + len("<title>") : end].strip()


def source_cards(offline: bool = False) -> tuple[list[dict[str, Any]], bool]:
    cards = load_source_cards()
    if offline or os.environ.get("HARNESS_RESEARCH_OFFLINE") == "1":
        return cards, True

    used_fallback = False
    enriched = []
    for card in cards:
        updated = dict(card)
        try:
            title = _fetch_title(card["url"])
            if title:
                updated["live_title"] = title
        except (KeyError, OSError, TimeoutError, urllib.error.URLError):
            used_fallback = True
        enriched.append(updated)
    return enriched, used_fallback


def decide(proposal: str, offline: bool = False) -> ResearchDecision:
    lowered = proposal.lower()
    cards, used_fallback = source_cards(offline=offline)
    if any(term in lowered for term in ["deploy", "production", "delete", "force push", "secret"]):
        decision = "reject"
    elif any(term in lowered for term in ["agent", "subagent", "slash", "command", "claude.md", "settings", "hook"]):
        decision = "accept"
    else:
        decision = "modify"

    risks = [
        "Too many project-specific agents can fragment context.",
        "Hooks can create side effects, so prefer prompts and settings first.",
        "Teacher mode should skip existing files unless --force is explicit.",
    ]
    if decision == "reject":
        risks.insert(0, "The proposal appears to exceed harness-only scope or production safety limits.")
    elif decision == "modify":
        risks.insert(0, "The proposal needs a narrower harness-only implementation shape.")

    evidence = [
        {
            "title": card.get("title", "Untitled source"),
            "url": card.get("url", ""),
            "summary": card.get("summary", ""),
        }
        for card in cards[:5]
    ]
    return ResearchDecision(
        decision=decision,
        proposal=proposal,
        evidence=evidence,
        risks=risks,
        files_to_change=[
            "agent/teacher.py",
            "agent/harness_researcher.py",
            "research/sources/*.json",
            "tests/test_teacher.py",
        ],
        tests=[
            "python3 -m unittest discover -s tests -p 'test_*.py'",
            "python3 agent/teacher.py . --task 'make this repo easy for agents to build features' --json",
            "python3 agent/harness_researcher.py 'Add task-specific project subagents' --offline",
        ],
        used_offline_fallback=used_fallback,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research a proposed harness design feature.")
    parser.add_argument("proposal", help="Harness proposal to evaluate")
    parser.add_argument("--offline", action="store_true", help="Use committed source cards only")
    args = parser.parse_args(argv)
    print(json.dumps(asdict(decide(args.proposal, offline=args.offline)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

