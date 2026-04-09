# A01 — Algorithm Complexity Analysis

## Task

Analyze the time and space complexity of the following function. Be thorough and precise.

```python
def mystery(nums: list[int], target: int) -> list[tuple[int, int]]:
    seen = {}
    result = []
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            result.append((seen[complement], i))
        seen[num] = i
    return result
```

Your analysis must cover:
1. **Time complexity** — best case, average case, worst case (with justification)
2. **Space complexity** — and what data structures drive it
3. **Edge cases** — how does the function behave with: empty list, all duplicates, no solution, multiple solutions, negative numbers
4. **Comparison** — compare this approach to the naive O(n²) brute force; when would you prefer each?
5. **Potential issues** — identify any correctness issues (e.g., duplicate handling, overwriting in `seen`)

## Scoring Rubric (embedded)
- Correctness (40%): Are complexity claims correct with accurate justification?
- Depth (30%): Are all 5 analysis points addressed thoroughly?
- Clarity (20%): Is the analysis well-structured and easy to follow?
- Structure (10%): Appropriate use of headers, code examples, tables.
