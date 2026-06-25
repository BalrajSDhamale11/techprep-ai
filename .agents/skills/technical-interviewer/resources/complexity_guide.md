# Algorithm Complexity Quick Reference
# Used by the technical-interviewer skill for scoring complexity analysis

## What to expect by difficulty

### Easy questions
- Students should know: O(n) vs O(n²) distinction
- Acceptable: brute force with awareness that better exists
- Ideal: optimal solution with correct Big-O stated

### Medium questions
- Students should know: the optimal algorithm by name if it has one
- Acceptable: correct complexity stated even if implementation has minor bugs
- Ideal: optimal solution + correct space complexity + edge cases mentioned

### Hard questions
- Students should know: space-time tradeoffs, why the approach works
- Acceptable: optimal solution without being able to prove why
- Ideal: full explanation of the approach's correctness

## Common Patterns and Their Complexities

| Pattern | Time | Space | When to use |
|---|---|---|---|
| Two Pointers | O(n) | O(1) | Sorted arrays, palindromes |
| Sliding Window | O(n) | O(k) | Subarray/substring problems |
| Hash Map | O(n) | O(n) | Fast lookups, frequency counts |
| BFS/DFS | O(V+E) | O(V) | Trees, graphs, shortest path |
| Dynamic Programming | O(n²) typical | O(n) to O(n²) | Optimization problems |
| Merge Sort | O(n log n) | O(n) | Stable sort needed |
| Binary Search | O(log n) | O(1) | Sorted data, search |

## Deduct points if:
- Student claims O(n) when solution is clearly O(n²)
- Student says "it doesn't matter" about space complexity for hard questions
- Student does not mention edge cases (empty array, single element, negative numbers)

## Do NOT deduct points if:
- Student uses a slightly different but equally valid approach
- Student solves it correctly but cannot name the algorithm
- Student's syntax has minor errors but logic is correct