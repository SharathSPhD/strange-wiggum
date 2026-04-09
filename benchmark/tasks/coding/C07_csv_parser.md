# C07 — CSV Parser

## Task

Implement `parse_csv(text: str, delimiter: str = ",") -> list[list[str]]` that correctly
handles RFC 4180 CSV including:
- Quoted fields: `"hello, world"` → single field `hello, world`
- Escaped quotes within quoted fields: `"say ""hi"""` → `say "hi"`
- Embedded newlines within quoted fields
- Trailing newline (optional — should not produce an extra empty row)
- Empty fields: `a,,b` → `["a", "", "b"]`
- Custom delimiter support

Do NOT use Python's `csv` module.

Output your COMPLETE solution as a single ```python code block in your TEXT RESPONSE (do not use any file tools). When complete: <promise>TASK COMPLETE</promise>

## Test Suite (pytest)

```python
# test_C07.py
from solution import parse_csv

def test_simple():
    assert parse_csv("a,b,c") == [["a", "b", "c"]]

def test_quoted_field_with_comma():
    assert parse_csv('"hello, world",b') == [["hello, world", "b"]]

def test_escaped_quote():
    assert parse_csv('"say ""hi"""') == [['say "hi"']]

def test_embedded_newline():
    text = '"line1\nline2",b'
    result = parse_csv(text)
    assert result == [["line1\nline2", "b"]]

def test_empty_field():
    assert parse_csv("a,,b") == [["a", "", "b"]]

def test_trailing_newline():
    assert parse_csv("a,b\n") == [["a", "b"]]

def test_multiple_rows():
    text = "a,b\nc,d\ne,f"
    assert parse_csv(text) == [["a","b"], ["c","d"], ["e","f"]]

def test_custom_delimiter():
    assert parse_csv("a;b;c", delimiter=";") == [["a", "b", "c"]]

def test_empty_input():
    assert parse_csv("") == []
```
