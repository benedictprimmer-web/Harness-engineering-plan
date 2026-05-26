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

.overview {
    page-break-after: always;
    padding: 20px 0 0;
}

.overview-header {
    margin-bottom: 24px;
}

.overview-header h2 {
    font-size: 20pt;
    border: none;
    margin: 0 0 6px 0;
    color: #0f172a;
}

.overview-header p {
    font-size: 10.5pt;
    color: #64748b;
    margin: 0;
}

.stats-row {
    display: flex;
    gap: 16px;
    margin: 20px 0;
}

.stat-box {
    flex: 1;
    background: #0f172a;
    border-radius: 10px;
    padding: 20px 16px;
    text-align: center;
    color: white;
}

.stat-number {
    font-size: 28pt;
    font-weight: 700;
    color: #a5b4fc;
    line-height: 1.1;
    display: block;
}

.stat-label {
    font-size: 8.5pt;
    color: #94a3b8;
    margin-top: 6px;
    line-height: 1.4;
    display: block;
}

.overview-para {
    font-size: 10.5pt;
    color: #334155;
    line-height: 1.7;
    margin: 16px 0;
}

.overview-para strong {
    color: #0f172a;
}

.overview table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 9.5pt;
}

.overview th {
    background: #1e293b;
    color: #f1f5f9;
    padding: 7px 12px;
    text-align: left;
    font-weight: 600;
    font-size: 9pt;
}

.overview td {
    padding: 6px 12px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
}

.overview tr:nth-child(even) td { background: #f8fafc; }
.overview tr:last-child td { border-bottom: none; }

.start-here {
    background: #f0fdf4;
    border: 1.5px solid #86efac;
    border-radius: 8px;
    padding: 14px 18px;
    margin-top: 20px;
}

.start-here p {
    margin: 0;
    font-size: 10pt;
    color: #166534;
    line-height: 1.6;
}

.start-here strong {
    color: #14532d;
}

.start-here code {
    background: #dcfce7;
    border-color: #86efac;
    color: #166534;
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

    overview = """
<div class="overview">
  <div class="overview-header">
    <h2>At a Glance</h2>
    <p>Everything you need to know about this repo in one page.</p>
  </div>

  <div class="stats-row">
    <div class="stat-box">
      <span class="stat-number">98.4%</span>
      <span class="stat-label">of Claude Code is harness infrastructure — not AI logic</span>
    </div>
    <div class="stat-box">
      <span class="stat-number">65→94%</span>
      <span class="stat-label">accuracy gain from a 65-line CLAUDE.md (Karpathy result)</span>
    </div>
    <div class="stat-box">
      <span class="stat-number">22/25</span>
      <span class="stat-label">this repo's own harness audit score</span>
    </div>
  </div>

  <p class="overview-para">
    <strong>The problem.</strong> Claude Code sessions go wrong — Claude edits the wrong file, repeats the same mistake,
    asks for approval every five seconds, drifts off-task. The instinct is to blame the model.
    When researchers analysed Claude Code's source code, they found that <strong>1.6% is AI decision logic</strong>.
    The other 98.4% is the harness — the permission pipeline, context management, tool routing, and safety guards
    wrapped around the model. Four independent teams building coding agents from scratch converged on the same architecture.
  </p>

  <p class="overview-para">
    <strong>The discipline.</strong> Harness engineering is the practice of building that wrapper deliberately —
    so Claude knows your project, respects its boundaries, and behaves consistently across sessions.
    This repo is a reference library: research guides, copy-paste templates, real-world examples,
    and Python tools for auditing and improving any project's harness.
  </p>

  <table>
    <tr><th>What you get</th><th>Where it is</th></tr>
    <tr><td>Seven in-depth research guides</td><td><code>research/00-overview.md</code> → <code>06-codebase-analysis.md</code></td></tr>
    <tr><td>Fill-in-the-blank templates (CLAUDE.md, settings.json, four hooks)</td><td><code>templates/</code></td></tr>
    <tr><td>Real-world examples: web app, API service, data pipeline, Karpathy minimal</td><td><code>examples/</code></td></tr>
    <tr><td>Audit tool — scores any project 0–25, outputs a prioritised fix list</td><td><code>python agent/audit.py /your/project</code></td></tr>
    <tr><td>Interactive research agent with two-pass stretch loop</td><td><code>python agent/main.py</code></td></tr>
    <tr><td>Parallel research runner — multiple topics simultaneously</td><td><code>python agent/parallel.py</code></td></tr>
    <tr><td>Four slash commands: /ultraplan /goal /agents /ultrareview</td><td><code>.claude/commands/</code></td></tr>
  </table>

  <div class="start-here">
    <p>
      <strong>Start here.</strong> If you have five minutes, run
      <code>python agent/audit.py /path/to/your/project</code> — it will tell you exactly what your
      harness is missing and in what order to fix it. If you have fifteen, copy
      <code>examples/karpathy-minimal/CLAUDE.md</code> into your project root — that alone is the
      biggest single improvement most codebases can make.
    </p>
  </div>
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
{overview}
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
