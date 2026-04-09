# H02 — Pratt Parser / Expression Evaluator

## Task

Implement a **Pratt parser** (top-down operator precedence parser) that evaluates arithmetic expressions. Pratt parsers are elegant, production-grade parsers used in real compilers (Rust's `rustc`, V8's parser design). They handle operator precedence and associativity without a grammar table.

## Requirements

Implement a function `evaluate` in `solution.py`:

```python
def evaluate(expression: str) -> float:
    ...
```

### Supported syntax

| Token | Meaning | Notes |
|-------|---------|-------|
| integers | `42`, `0`, `7` | parsed as float internally |
| floats | `3.14`, `.5`, `1.` | standard decimal notation |
| `+` `-` | addition, subtraction | left-associative, lowest precedence |
| `*` `/` | multiplication, division | left-associative, higher than +- |
| `**` | exponentiation | **right-associative**, highest binary precedence |
| `-` (unary) | negation | higher precedence than `**` when prefix |
| `(` `)` | grouping | arbitrary nesting |
| whitespace | ignored | spaces/tabs between tokens |

### Operator precedence (low to high)

1. `+` `-` (binary)
2. `*` `/`
3. `**` (right-associative: `2**3**2` = `2**(3**2)` = 512)
4. unary `-`
5. `(` `)` — highest (grouping)

### Error handling

Raise `ValueError` with a descriptive message for:
- Empty expression
- Unknown character
- Mismatched parentheses
- Division by zero
- Incomplete expression (e.g. `"2 +"`)

### Constraints

- No use of `eval()`, `exec()`, `ast.literal_eval()`, or any expression-evaluation library.
- Pure Python, stdlib only.
- The function signature must be exactly `def evaluate(expression: str) -> float`.

## Test Suite

```python
# test_solution
import pytest
from solution import evaluate


# ── Basic arithmetic ────────────────────────────────────────────────────────

def test_integer_literal():
    assert evaluate("42") == 42.0

def test_float_literal():
    assert abs(evaluate("3.14") - 3.14) < 1e-9

def test_addition():
    assert evaluate("2 + 3") == 5.0

def test_subtraction():
    assert evaluate("10 - 4") == 6.0

def test_multiplication():
    assert evaluate("3 * 4") == 12.0

def test_division():
    assert abs(evaluate("7 / 2") - 3.5) < 1e-9


# ── Precedence ───────────────────────────────────────────────────────────────

def test_precedence_mul_over_add():
    assert evaluate("2 + 3 * 4") == 14.0   # not 20

def test_precedence_parens_override():
    assert evaluate("(2 + 3) * 4") == 20.0

def test_precedence_power_over_mul():
    assert evaluate("2 * 3 ** 2") == 18.0  # 2 * 9, not 6**2


# ── Associativity ───────────────────────────────────────────────────────────

def test_left_assoc_subtraction():
    assert evaluate("10 - 3 - 2") == 5.0   # (10-3)-2, not 10-(3-2)

def test_right_assoc_power():
    assert evaluate("2 ** 3 ** 2") == 512.0  # 2**(3**2)=2**9


# ── Unary minus ─────────────────────────────────────────────────────────────

def test_unary_minus_simple():
    assert evaluate("-5") == -5.0

def test_unary_minus_with_power():
    # unary minus has lower precedence than **: -2**2 = -(2**2) = -4
    assert evaluate("-2 ** 2") == -4.0

def test_unary_minus_in_parens():
    assert evaluate("(-2) ** 2") == 4.0


# ── Complex expressions ──────────────────────────────────────────────────────

def test_nested_parens():
    assert evaluate("((2 + 3) * (4 - 1)) / 5") == 3.0

def test_chained_operations():
    assert abs(evaluate("1 + 2 * 3 - 4 / 2 + 5 ** 2") - 30.0) < 1e-9
    # 1 + 6 - 2 + 25 = 30

def test_whitespace_ignored():
    assert evaluate("  2  +  3  ") == 5.0


# ── Error cases ──────────────────────────────────────────────────────────────

def test_empty_raises():
    with pytest.raises(ValueError):
        evaluate("")

def test_division_by_zero_raises():
    with pytest.raises((ValueError, ZeroDivisionError)):
        evaluate("1 / 0")

def test_mismatched_paren_raises():
    with pytest.raises(ValueError):
        evaluate("(2 + 3")

def test_unknown_char_raises():
    with pytest.raises(ValueError):
        evaluate("2 @ 3")
```

## Notes

- A Pratt parser uses two types of parse functions: **nud** (null denotation — prefix position, e.g. literals, unary) and **led** (left denotation — infix position). Each operator has a binding power.
- Alternatively, a recursive-descent parser with explicit precedence levels is also acceptable.
- Do not use `eval()` — that will be detected and penalised.
- Do not use any file tools; output only valid Python.
