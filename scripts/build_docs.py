"""Gera docs/index.html a partir de README.md e specs/*.md."""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT / "README.md", *sorted((ROOT / "specs").glob("*.md"))]
OUT = ROOT / "docs" / "index.html"


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "secao"


def inline(text: str) -> str:
    codes: list[str] = []

    def hold_code(match: re.Match[str]) -> str:
        codes.append(match.group(1))
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", hold_code, text)
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    for index, code in enumerate(codes):
        text = text.replace(
            f"\x00{index}\x00",
            f"<code>{html.escape(code)}</code>",
        )
    return text


def markdown_to_html(source: str) -> tuple[str, list[tuple[int, str, str]]]:
    lines = source.splitlines()
    out: list[str] = []
    toc: list[tuple[int, str, str]] = []
    paragraph: list[str] = []
    stack: list[int] = []
    item_open = False
    section = "doc"
    used: set[str] = set()

    def flush_paragraph() -> None:
        if paragraph:
            out.append(f"<p>{inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_item() -> None:
        nonlocal item_open
        if item_open:
            out.append("</li>")
            item_open = False

    def close_nested() -> None:
        nonlocal item_open
        out.append("</ul>")
        stack.pop()
        if stack:
            item_open = True
            close_item()

    def close_lists() -> None:
        close_item()
        while stack:
            close_nested()

    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            flush_paragraph()
            close_lists()
            block: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                block.append(lines[index])
                index += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(block))}</code></pre>")
            index += 1
            continue

        if not line.strip():
            flush_paragraph()
            close_lists()
            index += 1
            continue

        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading:
            flush_paragraph()
            close_lists()
            level = len(heading.group(1))
            title = heading.group(2).strip()
            anchor = slugify(title if level == 1 else f"{section}-{title}")
            if level == 1:
                section = slugify(title)
                anchor = section
            base = anchor
            suffix = 2
            while anchor in used:
                anchor = f"{base}-{suffix}"
                suffix += 1
            used.add(anchor)
            out.append(f"<h{level} id=\"{anchor}\">{inline(title)}</h{level}>")
            toc.append((level, title, anchor))
            index += 1
            continue

        item = re.match(r"^(\s*)-\s+(.*)$", line)
        if item:
            flush_paragraph()
            indent = len(item.group(1))
            if stack and indent > stack[-1]:
                out.append("<ul>")
                stack.append(indent)
            else:
                close_item()
                while stack and stack[-1] > indent:
                    close_nested()
                if not stack:
                    out.append("<ul>")
                    stack.append(indent)
            out.append(f"<li>{inline(item.group(2))}")
            item_open = True
            index += 1
            continue

        close_lists()
        paragraph.append(line.strip())
        index += 1

    flush_paragraph()
    close_lists()
    return "\n".join(out), toc


def page(sections: list[tuple[str, str, list[tuple[int, str, str]]]]) -> str:
    nav: list[str] = []
    body: list[str] = []
    for html_body, _label, toc in sections:
        for level, title, anchor in toc:
            cls = "nav-h1" if level == 1 else "nav-h2"
            nav.append(
                f'<a class="{cls}" href="#{anchor}">{html.escape(title)}</a>'
            )
        body.append(f"<article>\n{html_body}\n</article>")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Trading bot — specs</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1c1917;
      --muted: #57534e;
      --line: #e7e5e4;
      --paper: #fafaf9;
      --side: #1c1917;
      --side-ink: #f5f5f4;
      --code: #f5f5f4;
      --accent: #b45309;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font: 16px/1.6 "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--paper);
    }}
    .layout {{
      display: grid;
      grid-template-columns: 240px 1fr;
      min-height: 100vh;
    }}
    nav {{
      position: sticky;
      top: 0;
      height: 100vh;
      overflow: auto;
      padding: 28px 18px;
      background: var(--side);
      color: var(--side-ink);
    }}
    nav p {{
      margin: 0 0 18px;
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #a8a29e;
    }}
    nav a {{
      display: block;
      color: inherit;
      text-decoration: none;
      border-radius: 6px;
    }}
    nav a:hover {{ background: #292524; }}
    .nav-h1 {{
      margin-top: 14px;
      padding: 6px 8px;
      font-weight: 650;
    }}
    .nav-h2 {{
      padding: 3px 8px 3px 18px;
      font-size: 14px;
      color: #d6d3d1;
    }}
    main {{
      max-width: 760px;
      padding: 40px 48px 80px;
    }}
    article + article {{
      margin-top: 48px;
      padding-top: 8px;
      border-top: 1px solid var(--line);
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 32px;
      line-height: 1.2;
    }}
    h2 {{
      margin: 28px 0 8px;
      font-size: 18px;
    }}
    p, li {{ color: var(--ink); }}
    ul {{ margin: 8px 0 12px; padding-left: 22px; }}
    li {{ margin: 4px 0; }}
    code {{
      font-family: Consolas, "Cascadia Mono", monospace;
      font-size: 0.92em;
      background: var(--code);
      border-radius: 4px;
      padding: 0 4px;
    }}
    pre {{
      overflow: auto;
      padding: 14px 16px;
      background: #292524;
      color: #f5f5f4;
      border-radius: 8px;
    }}
    pre code {{
      background: transparent;
      padding: 0;
      color: inherit;
    }}
    strong {{ color: var(--accent); }}
    @media (max-width: 800px) {{
      .layout {{ grid-template-columns: 1fr; }}
      nav {{
        position: static;
        height: auto;
      }}
      main {{ padding: 24px 18px 48px; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <nav>
      <p>Specs</p>
      {chr(10).join(nav)}
    </nav>
    <main>
      {chr(10).join(body)}
    </main>
  </div>
</body>
</html>
"""


def main() -> None:
    sections = []
    for path in SOURCES:
        body, toc = markdown_to_html(path.read_text(encoding="utf-8"))
        sections.append((body, path.stem, toc))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page(sections), encoding="utf-8")
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
