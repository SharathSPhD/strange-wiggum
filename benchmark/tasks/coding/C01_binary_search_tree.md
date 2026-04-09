# C01 — Binary Search Tree

## Task

Implement a `BinarySearchTree` class in Python with the following methods:
- `insert(value)` — insert a value
- `search(value) -> bool` — return True if value exists
- `delete(value)` — delete a value (handle cases: no children, one child, two children)
- `inorder() -> list` — return sorted list of all values
- `height() -> int` — return tree height (empty tree = 0)

Requirements:
- Handle duplicate values (ignore them — do not insert duplicates)
- Handle deletion from empty tree gracefully (no exception)
- Implement iteratively OR recursively — your choice, but be consistent

Output your COMPLETE solution as a single ```python code block in your TEXT RESPONSE (do not use any file tools) with the class and a brief
docstring explaining your approach.

When the solution is complete and correct, output:
<promise>TASK COMPLETE</promise>

## Test Suite (pytest)

```python
# test_C01.py
import pytest
from solution import BinarySearchTree

def test_insert_and_search():
    bst = BinarySearchTree()
    bst.insert(5); bst.insert(3); bst.insert(7)
    assert bst.search(5) and bst.search(3) and bst.search(7)
    assert not bst.search(99)

def test_inorder_sorted():
    bst = BinarySearchTree()
    for v in [5, 3, 7, 1, 4, 6, 8]:
        bst.insert(v)
    assert bst.inorder() == [1, 3, 4, 5, 6, 7, 8]

def test_no_duplicates():
    bst = BinarySearchTree()
    bst.insert(5); bst.insert(5)
    assert bst.inorder() == [5]

def test_delete_leaf():
    bst = BinarySearchTree()
    for v in [5, 3, 7]: bst.insert(v)
    bst.delete(3)
    assert not bst.search(3)
    assert bst.inorder() == [5, 7]

def test_delete_one_child():
    bst = BinarySearchTree()
    for v in [5, 3, 7, 6]: bst.insert(v)
    bst.delete(7)
    assert bst.inorder() == [3, 5, 6]

def test_delete_two_children():
    bst = BinarySearchTree()
    for v in [5, 3, 7, 6, 8]: bst.insert(v)
    bst.delete(7)
    assert bst.search(6) and bst.search(8)
    assert bst.inorder() == [3, 5, 6, 8]

def test_delete_from_empty():
    bst = BinarySearchTree()
    bst.delete(5)   # must not raise

def test_height():
    bst = BinarySearchTree()
    assert bst.height() == 0
    bst.insert(5)
    assert bst.height() == 1
    bst.insert(3); bst.insert(7)
    assert bst.height() == 2
    bst.insert(1)
    assert bst.height() == 3
```
