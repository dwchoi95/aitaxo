# Codebook — Wei et al. competitive-programming bug taxonomy

Pinned from github.com/minnanWei/LLMs-Competitive-Program-Generation (Tables 1-2).
Assign **one or more** leaf codes per item. Codes marked **[lang]** are
language-dependent (relevant to C++ here). If no leaf fits, set `uncovered=yes`
and describe the pattern in `notes`.

## GE1 — Algorithm Understanding

- **GE1.1 Incorrect Algorithm**: The chosen approach is fundamentally wrong for the problem. _Example:_ Uses a greedy scan where the problem provably needs DP, wrong on non-trivial cases.
- **GE1.2 Misunderstanding Problem Requirements**: Misreads what the problem asks for. _Example:_ Outputs the maximum when the minimum is requested.
- **GE1.3 Overly Complex or Inefficient Design**: Approach is logically correct but too slow/complex for the constraints. _Example:_ O(n^2) loop with n=1e6 where O(n log n) is required, causing TLE.

## GE2 — Syntax / Language-Specific

- **GE2.1 Compilation Errors** **[lang]**: The code fails to compile. _Example:_ Undeclared identifier, missing semicolon, or a type the compiler rejects.
- **GE2.2 Language-specific Syntax Misuse** **[lang]**: Misuse of a language construct that compiles but violates its rules or intent. _Example:_ Misusing an STL container API, or relying on unspecified evaluation order.

## GE3 — Input/Output Handling

- **GE3.1 Incorrect Input Format Handling**: Parses the input incorrectly. _Example:_ Reads one integer per line when the input is space-separated on one line.
- **GE3.2 Output Format Mismatches**: Output shape/format does not match the expected one. _Example:_ Missing newline/space, wrong float precision, or extra/missing tokens.

## GE4 — Edge Cases & Indexing

- **GE4.1 Incorrect Edge Case/Boundary Handling**: Fails on extreme, empty, or boundary inputs. _Example:_ Does not handle n=0 or a single-element array.
- **GE4.2 Off-by-one Errors in Loops/Indexing**: Loop bounds or indices are off by one. _Example:_ `for(i=0;i<=n;i++)` indexing an n-length array out of bounds.

## GE5 — Control Logic

- **GE5.1 Faulty Condition Expressions**: A branch condition is wrong. _Example:_ `if(a<b)` where `a<=b` was intended.
- **GE5.2 Incorrect Logical Operators/Precedence**: Wrong boolean operator or operator precedence. _Example:_ `a && b || c` grouped differently than intended.

## GE6 — Data Type Selection

- **GE6.1 Overflow or Precision Loss Due to Improper Data Type Selection** **[lang]**: Numeric overflow or floating precision loss from the wrong type. _Example:_ Summing 1e5 values up to 1e9 in 32-bit int overflows (C++-specific; Python3 has bigints).
- **GE6.2 Implicit Type Conversions Causing Unexpected Behavior** **[lang]**: A silent type conversion changes the result. _Example:_ int/int truncates before assignment to a double.

## AE1 — Mathematical Reasoning

- **AE1.1 Misuse/Derivation Error of Mathematical Formulas**: A formula or its derivation is wrong. _Example:_ Incorrect combinatorial identity or wrong modular inverse.
- **AE1.2 Special Mathematical Structures Handling Errors**: Mishandles a special mathematical structure. _Example:_ Wrong handling of gcd/primes or matrix exponentiation boundary.

## AE2 — Greedy Algorithms

- **AE2.1 Incorrect Local Decision-making**: The greedy choice itself is wrong. _Example:_ Picks the largest item when smallest-first is optimal.
- **AE2.2 Lack of Proof for Greedy Choice Correctness**: A greedy that is not globally optimal. _Example:_ Passes samples but fails where an exchange argument breaks.

## AE3 — Dynamic Programming

- **AE3.1 Incorrect State Definition**: The DP state does not capture the information needed. _Example:_ Omits a dimension required to distinguish subproblems.
- **AE3.2 Errors in State Transition Logic**: The recurrence/transition is wrong. _Example:_ Transition misses a case or double-counts.
- **AE3.3 Improper Base State Initialization**: DP base values are wrong. _Example:_ dp[0]=0 where -infinity is required.

## AE4 — Divide & Conquer

- **AE4.1 Incorrect Base Cases (D&C)**: The divide-and-conquer base case is wrong. _Example:_ Returns the wrong value for a size-1 segment.
- **AE4.2 Faulty Subproblem Merging (D&C)**: The combine step is wrong. _Example:_ Merge step in merge-sort/segment combine drops elements.
- **AE4.3 Missing/Incorrect Recursive Calls (D&C)**: Wrong split or missing recursive call. _Example:_ Recurses on incorrect half boundaries.

## AE5 — Recursion / Memoization

- **AE5.1 Incorrect Base Cases (Recursion)**: The recursion base case is wrong. _Example:_ Missing or wrong terminating value.
- **AE5.2 Faulty Subproblem Merging (Recursion)**: Recursive results are combined incorrectly. _Example:_ Adds instead of taking the max over recursive results.
- **AE5.3 Missing Recursive Calls/Incorrect Depth**: Under/over-recursion or wrong recursion depth. _Example:_ Forgets one branch, or unbounded recursion overflowing the stack.
- **AE5.4 Overlapping Subproblems Not Identified**: No memoization where overlapping subproblems recur. _Example:_ Naive recursion recomputes and times out for lack of caching.

## AE6 — Graph Traversal / Search

- **AE6.1 Incomplete State Space Traversal**: Misses reachable states/nodes. _Example:_ Forgets to enqueue some neighbors in BFS.
- **AE6.2 Over-pruning or Missing Transitions**: Prunes valid paths or omits edges/transitions. _Example:_ Marks nodes visited too early and skips valid paths.
- **AE6.3 Incorrect BFS/DFS/Heuristic Use**: Uses the wrong traversal/heuristic. _Example:_ Plain BFS for a weighted shortest path instead of Dijkstra.
- **AE6.4 Infinite Loops or Cycles in Graph Traversal**: Does not handle cycles, looping forever. _Example:_ No visited set on a cyclic graph causes an infinite loop.

## Verdict → likely candidate leaves (guidance, not a restriction)

- **CE**: GE2.1, GE2.2
- **RE**: GE4.1, GE4.2, GE6.1, GE6.2, AE5.3, AE6.4, GE2.2
- **TLE**: GE1.3, AE5.4, AE6.4, AE6.1
- **WA**: GE1.1, GE1.2, GE1.3, GE2.2, GE3.1, GE3.2, GE4.1, GE4.2, …
