#!/usr/bin/env python3
"""Convert README.md to a styled PDF using weasyprint."""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

@page {
    size: A4;
    margin: 2.2cm 2.5cm 2.2cm 2.5cm;
    @bottom-right {
        content: counter(page) " / " counter(pages);
        font-family: Inter, sans-serif;
        font-size: 9pt;
        color: #94a3b8;
    }
    @top-right {
        content: "Harness Engineering for Claude Code";
        font-family: Inter, sans-serif;
        font-size: 9pt;
        color: #94a3b8;
    }
}

* { box-sizing: border-box; }

body {
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.65;
    color: #1e293b;
    background: #ffffff;
}

h1 {
    font-size: 26pt;
    font-weight: 700;
    color: #0f172a;
    border-bottom: 3px solid #6366f1;
    padding-bottom: 10px;
    margin-top: 0;
    margin-bottom: 6px;
    page-break-after: avoid;
}

h2 {
    font-size: 15pt;
    font-weight: 700;
    color: #1e293b;
    border-bottom: 1.5px solid #e2e8f0;
    padding-bottom: 5px;
    margin-top: 28px;
    margin-bottom: 10px;
    page-break-after: avoid;
}

h3 {
    font-size: 11.5pt;
    font-weight: 600;
    color: #334155;
    margin-top: 20px;
    margin-bottom: 6px;
    page-break-after: avoid;
}

h4 {
    font-size: 10.5pt;
    font-weight: 600;
    color: #475569;
    margin-top: 14px;
    margin-bottom: 4px;
}

p { margin: 0 0 10px 0; }

blockquote {
    margin: 14px 0;
    padding: 10px 16px;
    border-left: 4px solid #6366f1;
    background: #f1f5f9;
    border-radius: 0 6px 6px 0;
    font-style: italic;
    color: #334155;
}

blockquote p { margin: 0; }

code {
    font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
    font-size: 9pt;
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 3px;
    padding: 1px 5px;
    color: #7c3aed;
}

pre {
    background: #0f172a;
    border-radius: 8px;
    padding: 14px 16px;
    margin: 12px 0;
    overflow-x: auto;
    page-break-inside: avoid;
}

pre code {
    background: none;
    border: none;
    padding: 0;
    color: #e2e8f0;
    font-size: 8.5pt;
    line-height: 1.55;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}

th {
    background: #1e293b;
    color: #f1f5f9;
    padding: 8px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 9pt;
}

td {
    padding: 7px 12px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
}

tr:nth-child(even) td { background: #f8fafc; }
tr:last-child td { border-bottom: none; }

ul, ol {
    margin: 8px 0 10px 0;
    padding-left: 22px;
}

li { margin-bottom: 3px; }
li > ul, li > ol { margin-top: 3px; }

strong { font-weight: 600; color: #0f172a; }
em { font-style: italic; }

hr {
    border: none;
    border-top: 2px solid #e2e8f0;
    margin: 24px 0;
}

a { color: #6366f1; text-decoration: none; }

.cover {
    text-align: center;
    padding: 60px 0 40px;
    page-break-after: always;
}

.cover h1 {
    font-size: 32pt;
    border: none;
    padding: 0;
    margin-bottom: 16px;
    color: #0f172a;
}

.cover .subtitle {
    font-size: 14pt;
    color: #6366f1;
    font-weight: 600;
    margin-bottom: 12px;
}

.cover .tagline {
    font-size: 11pt;
    color: #64748b;
    max-width: 420px;
    margin: 0 auto 36px;
    line-height: 1.7;
}

.score-badge {
    display: inline-block;
    background: #6366f1;
    color: white;
    font-weight: 700;
    font-size: 28pt;
    padding: 16px 32px;
    border-radius: 12px;
    margin-bottom: 8px;
}

.score-label {
    font-size: 10pt;
    color: #64748b;
}

.toc {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 20px 24px;
    margin: 0 0 20px;
    page-break-after: always;
}

.toc h2 {
    border: none;
    margin-top: 0;
    font-size: 13pt;
    color: #0f172a;
}

.toc ol {
    margin: 0;
    padding-left: 20px;
    column-count: 2;
    column-gap: 30px;
}

.toc li {
    font-size: 10pt;
    margin-bottom: 5px;
    color: #334155;
    break-inside: avoid;
}
"""


def md_to_html(md: str) -> str:
    """Convert markdown to HTML using Python's built-in or markdown lib."""
    try:
        import markdown
        extensions = ['tables', 'fenced_code', 'nl2br', 'sane_lists']
        return markdown.markdown(md, extensions=extensions)
    except ImportError:
        # Fallback: basic conversion
        html = md
        # Headers
        for i in range(6, 0, -1):
            html = re.sub(rf'^{"#" * i} (.+)$', rf'<h{i}>\1</h{i}>', html, flags=re.M)
        # Bold + italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        # Code blocks
        html = re.sub(r'```[\w]*\n(.*?)```', r'<pre><code>\1</code></pre>', html, flags=re.S)
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        # Tables (basic)
        # Horizontal rules
        html = re.sub(r'^---+$', '<hr/>', html, flags=re.M)
        # Blockquotes
        html = re.sub(r'^> (.+)$', r'<blockquote><p>\1</p></blockquote>', html, flags=re.M)
        # Paragraphs
        html = re.sub(r'\n\n', '</p><p>', html)
        html = f'<p>{html}</p>'
        return html


def build_html(md_content: str) -> str:
    pip_install = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', 'markdown', '-q'],
        capture_output=True
    )

    # Split off the first blockquote as tagline
    body_html = md_to_html(md_content)

    cover = """
<div class="cover">
  <h1>Harness Engineering<br/>for Claude Code</h1>
  <div class="subtitle">A systematic guide to the infrastructure that makes AI sessions work</div>
  <p class="tagline">
    The model is 1.6% of what makes Claude Code effective.<br/>
    The harness is 98.4%. This repo teaches you to build it deliberately.
  </p>
  <div class="score-badge">22/25</div><br/>
  <div class="score-label">This repo's own harness audit score</div>
</div>
"""

    toc = """
<div class="toc">
<h2>Contents</h2>
<ol>
  <li>The Big Idea — why harness beats model</li>
  <li>What a Harness Is — the four levers</li>
  <li>Repo Structure — what is where</li>
  <li>Where to Start — three entry points</li>
  <li>The Karpathy Baseline — 65 lines, 94% accuracy</li>
  <li>The Research Guides — seven in-depth references</li>
  <li>The Templates — ready to copy and use</li>
  <li>The Examples — real-world CLAUDE.md files</li>
  <li>The Audit Tool — score any project 0–25</li>
  <li>The Research Agent — interactive stretch-loop</li>
  <li>The Slash Commands — /ultraplan /goal /agents /ultrareview</li>
  <li>The Audit-Fix-Verify Loop — how to improve iteratively</li>
  <li>Key Findings from the Literature</li>
  <li>Contributing</li>
</ol>
</div>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Harness Engineering for Claude Code</title>
<style>
{CSS}
</style>
</head>
<body>
{cover}
{toc}
{body_html}
</body>
</html>"""


def main():
    readme = (HERE / "README.md").read_text(encoding="utf-8")
    html = build_html(readme)

    html_path = HERE / "GUIDE.html"
    pdf_path = HERE / "GUIDE.pdf"

    html_path.write_text(html, encoding="utf-8")
    print(f"HTML written: {html_path}")

    try:
        from weasyprint import HTML
        HTML(filename=str(html_path)).write_pdf(str(pdf_path))
        print(f"PDF written:  {pdf_path}  ({pdf_path.stat().st_size // 1024} KB)")
    except Exception as e:
        print(f"PDF generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
