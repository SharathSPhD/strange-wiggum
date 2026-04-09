# C05 — Markdown Parser

## Task

Implement a `parse_markdown(text: str) -> str` function that converts a subset of
Markdown to HTML. Support exactly these elements:

| Markdown | HTML output |
|----------|-------------|
| `# Heading` | `<h1>Heading</h1>` |
| `## Heading` | `<h2>Heading</h2>` |
| `### Heading` | `<h3>Heading</h3>` |
| `**bold**` | `<strong>bold</strong>` |
| `*italic*` | `<em>italic</em>` |
| `[text](url)` | `<a href="url">text</a>` |
| blank line | paragraph break (`</p><p>`) |
| plain text | wrapped in `<p>...</p>` |

Rules:
- Headings take the entire line (no inline elements needed inside headings)
- Bold/italic/links can be nested in paragraph text
- `*italic*` vs `**bold**`: greedy — `**bold**` must be matched before `*italic*`
- Consecutive non-blank lines form one paragraph
- Do not wrap heading lines in `<p>` tags
- Output should be a single string (no trailing newline required)

Output your COMPLETE solution as a single ```python code block in your TEXT RESPONSE (do not use any file tools). When complete: <promise>TASK COMPLETE</promise>

## Test Suite (pytest)

```python
# test_C05.py
from solution import parse_markdown

def test_headings():
    assert parse_markdown("# Hello") == "<h1>Hello</h1>"
    assert parse_markdown("## World") == "<h2>World</h2>"
    assert parse_markdown("### Sub") == "<h3>Sub</h3>"

def test_bold_italic():
    result = parse_markdown("This is **bold** and *italic*.")
    assert "<strong>bold</strong>" in result
    assert "<em>italic</em>" in result

def test_link():
    result = parse_markdown("[Click here](https://example.com)")
    assert '<a href="https://example.com">Click here</a>' in result

def test_paragraph_wrapping():
    result = parse_markdown("Hello world")
    assert result.startswith("<p>") and result.endswith("</p>")

def test_paragraph_break():
    result = parse_markdown("First paragraph\n\nSecond paragraph")
    assert "<p>First paragraph</p>" in result
    assert "<p>Second paragraph</p>" in result

def test_heading_not_wrapped_in_p():
    result = parse_markdown("# Title")
    assert "<p>" not in result

def test_combined():
    md = "# Title\n\nThis has **bold** and a [link](http://x.com)."
    result = parse_markdown(md)
    assert "<h1>Title</h1>" in result
    assert "<strong>bold</strong>" in result
    assert '<a href="http://x.com">link</a>' in result
```
