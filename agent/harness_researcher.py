from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "research" / "sources"


@dataclass
class ResearchDecision:
    decision: str
    proposal: str
    evidence: List[Dict[str, str]]
    risks: List[str]
    files_to_change: List[str]
    tests: List[str]
    used_offline_fallback: bool


def load_source_cards() -> List[Dict[str, str]]:
    cards: List[Dict[str, str]] = []
    for path in sorted(SOURCE_DIR.glob("*.json")):
        try:
            cards.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return cards


def fetch_live_title(url: str, timeout: float = 2.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "harness-researcher/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read(4096).decode("utf-8", errors="ignore")
    lower = text.lower()
    start = lower.find("<title>")
    end = lower.find("</title>")
    if start == -1 or end == -1 or end <= start:
        return ""
    return text[start + len("<title>") : end].strip()


def evidence_cards(offline: bool = False) -> tuple[List[Dict[str, str]], bool]:
    cards = load_source_cards()
    if offline or os.environ.get("HARNESS_RESEARCH_OFFLINE") == "1":
        return cards, True
    used_fallback = False
    enriched: List[Dict[str, str]] = []
    for card in cards:
        updated = dict(card)
        try:
            title = fetch_live_title(card["url"])
            if title:
                updated["live_title"] = title
        except (urllib.error.URLError, TimeoutError, KeyError, OSError):
            used_fallback = True
        enriched.append(updated)
    return enriched, used_fallback


def decide(proposal: str, offline: bool = False) -> ResearchDecision:
    lowered = proposal.lower()
    cards, used_fallback = evidence_cards(offline=offline)
    if any(word in lowered for word in ["deploy", "delete", "production", "force push", "secret"]):
        decision = "reject"
    elif any(word in lowered for word in ["agent", "subagent", "slash", "command", "claude.md", "settings", "hook"]):
        decision = "accept"
    else:
        decision = "modify"

    risks = [
        "Too many project-specific agents can hide important context from the main session.",
        "Hooks can introduce side effects, so v1 should prefer settings and prompts over active automation.",
        "Existing project files should be skipped unless the user explicitly requests overwrite.",
    ]
    if decision == "reject":
        risks.insert(0, "The proposal appears to exceed harness-only scope or could affect production state.")
    elif decision == "modify":
        risks.insert(0, "The proposal needs a narrower harness-only shape before implementation.")

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
            "agent/install.py",
            "agent/harness_researcher.py",
            "research/sources/*.json",
            "tests/test_teacher.py",
        ],
        tests=[
            "python3 -m unittest discover -s tests -p 'test_*.py'",
            "node tests/harness-contract.test.js",
            "node tests/installer.test.js",
            "node tests/audit.test.js",
        ],
        used_offline_fallback=used_fallback,
    )


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research a proposed harness design feature.")
    parser.add_argument("proposal", help="Harness design proposal to evaluate")
    parser.add_argument("--offline", action="store_true", help="Use committed source-card summaries only")
    args = parser.parse_args(argv)
    print(json.dumps(asdict(decide(args.proposal, offline=args.offline)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

