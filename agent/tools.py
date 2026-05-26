from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": (
            "Read the full contents of a file in the repository. "
            "Use this to inspect research guides, templates, and examples."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to repo root (e.g. 'research/01-claude-md-guide.md')",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and sub-directories at a path in the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to repo root (e.g. 'templates/hooks/')",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "search_repo",
        "description": (
            "Search for text patterns across repository files using grep. "
            "Useful for finding a topic, config key, or keyword across all guides and templates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Search pattern (grep-compatible, basic regex OK)",
                },
                "path": {
                    "type": "string",
                    "description": "Directory or file to search in (default: entire repo)",
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Whether the search is case-sensitive (default: false)",
                },
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "save_note",
        "description": "Save a research note as markdown to research/notes/. Use to persist key findings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Filename without path (e.g. 'hook-patterns.md'). Saved under research/notes/",
                },
                "content": {
                    "type": "string",
                    "description": "Markdown content to save",
                },
            },
            "required": ["filename", "content"],
        },
    },
]


def read_file(path: str) -> str:
    full = REPO_ROOT / path
    if not full.exists():
        return f"Error: not found: {path}"
    if not full.is_file():
        return f"Error: not a file: {path}"
    try:
        text = full.read_text(encoding="utf-8")
        if len(text) > 24_000:
            return text[:24_000] + "\n\n[... truncated at 24 000 chars ...]"
        return text
    except Exception as e:
        return f"Error reading {path}: {e}"


def list_directory(path: str) -> str:
    full = REPO_ROOT / path
    if not full.exists():
        return f"Error: not found: {path}"
    if not full.is_dir():
        return f"Error: not a directory: {path}"
    try:
        items = sorted(full.iterdir())
        lines = []
        for item in items:
            rel = item.relative_to(REPO_ROOT)
            suffix = "/" if item.is_dir() else f"  ({item.stat().st_size:,} bytes)"
            lines.append(f"{rel}{suffix}")
        return "\n".join(lines) or "(empty)"
    except Exception as e:
        return f"Error: {e}"


def search_repo(pattern: str, path: str = ".", case_sensitive: bool = False) -> str:
    search_path = REPO_ROOT / path
    if not search_path.exists():
        return f"Error: not found: {path}"

    flags = [
        "-r", "-n",
        "--include=*.md", "--include=*.json", "--include=*.sh",
        "--include=*.py", "--include=*.yml", "--include=*.yaml",
    ]
    if not case_sensitive:
        flags.append("-i")

    try:
        result = subprocess.run(
            ["grep"] + flags + [pattern, str(search_path)],
            capture_output=True, text=True, timeout=10,
        )
        output = result.stdout.strip()
        if not output:
            return f"No matches for: {pattern}"
        lines = output.split("\n")
        truncated = len(lines) > 60
        display = lines[:60]
        # Strip absolute repo prefix for readability
        prefix = str(REPO_ROOT) + "/"
        display = [ln.replace(prefix, "") for ln in display]
        out = "\n".join(display)
        if truncated:
            out += f"\n... ({len(lines) - 60} more matches)"
        return out
    except subprocess.TimeoutExpired:
        return "Error: search timed out"
    except Exception as e:
        return f"Error: {e}"


def save_note(filename: str, content: str) -> str:
    notes_dir = REPO_ROOT / "research" / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in filename if c.isalnum() or c in "-_.")
    if not safe.endswith(".md"):
        safe += ".md"
    (notes_dir / safe).write_text(content, encoding="utf-8")
    return f"Saved → research/notes/{safe}"


def execute_tool(name: str, tool_input: dict) -> str:
    if name == "read_file":
        return read_file(tool_input["path"])
    if name == "list_directory":
        return list_directory(tool_input["path"])
    if name == "search_repo":
        return search_repo(
            tool_input["pattern"],
            tool_input.get("path", "."),
            tool_input.get("case_sensitive", False),
        )
    if name == "save_note":
        return save_note(tool_input["filename"], tool_input["content"])
    return f"Unknown tool: {name}"
