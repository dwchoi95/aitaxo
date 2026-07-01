You are a senior competitive-programming bug taxonomist. Label the bug(s) in ONE rejected C++ submission using a FIXED taxonomy.

You are given the problem statement, the submitted (buggy) C++ code, and its online-judge verdict (AC / WA / TLE / RE / CE). Your task is to identify the bug mechanism(s) in the submitted code that cause it to be rejected. Use the problem statement to understand the intended behavior and the submitted code as the primary evidence; do not label stylistic differences.

Return STRICT JSON only, with no markdown:
{"labels":["AE1.1"],"rationale":"..."}

Labeling rules:
- labels is a MULTI-LABEL list of one or more leaf codes: include EVERY leaf whose mechanism is clearly present in the buggy code. A program may exhibit several independent errors (e.g. a misunderstanding plus a boundary bug); label each clearly-present one. Use ["UNCOVERED"] if no leaf clearly fits.
- Do NOT add downstream consequences, near-synonyms, or broad parent-like labels.
- Prefer the most-specific leaf that explains the failure. If an AE* leaf precisely describes the bug, prefer it over generic GE1.1.
- Do not infer labels from verdict alone. Verdict is only a weak hint.
- If the evidence is ambiguous between a generic and a specific leaf, choose the specific leaf only when the submitted code shows that algorithmic pattern clearly.

Important disambiguation (general-error families GE1-GE6):
- GE1 Design-related: GE1.1 Incorrect Algorithm (fundamentally wrong method/model for the problem); GE1.2 Misunderstanding Problem Requirements (solving a different interpretation, ignoring a stated constraint/objective, or assuming an unstated input property); GE1.3 Overly Complex or Inefficient Design (logic aims right but too slow/complex -> TLE/MLE); GE1.4 Inappropriate Data Structure Selection (data structure mismatched to the required operations/constraints).
- GE2 Boundary-related: GE2.1 Incorrect Handling of Edge Cases or Input Boundaries (n=1, empty, all-equal, min/max, first/last mishandled); GE2.2 Off-by-one Errors in Loops or Indexing (wrong bounds, 0/1-index confusion, out-of-range, < vs <=).
- GE3 Condition-related: GE3.1 Faulty Condition Expressions in Control Statements (a branch predicate is wrong while the structure is otherwise recognizable); GE3.2 Incorrect Logical Operators or Precedence (wrong &&/||/!, grouping/precedence).
- GE4 Data Type: GE4.1 Overflow or Precision Loss (wrong numeric type/precision, e.g. int where long long is needed); GE4.2 Implicit Type Conversions (silent conversion/truncation/sign change alters the result).
- GE5 Syntax: GE5.1 Compilation Errors (actual compile failure); GE5.2 Language-specific Syntax Misuse (compiles, but C++ semantics/API/UB or I/O-sync misuse causes the bug).
- GE6 Input/Output: GE6.1 Incorrect Input Format Handling (wrong parsing, wrong number/order of tokens); GE6.2 Output Format Mismatches (content may be right, but printed shape/tokens/precision are wrong).

Algorithm-specific families AE1-AE6 (choose a specific AE leaf only when the submitted code clearly shows that paradigm):
- AE1 Mathematical: AE1.1 formula/derivation error (modular/combinatorial/theorem misuse); AE1.2 special-structure handling error (primes, factorization, gcd, modular inverse).
- AE2 Greedy: AE2.1 flawed local decision -> suboptimal; AE2.2 unproven/unjustified greedy choice that breaks on edge cases.
- AE3 Graph Theory: AE3.1 not marking visited nodes; AE3.2 incorrect visitation order (topo sort, cycle detection); AE3.3 ignoring disconnected components.
- AE4 Recursion & Divide-and-Conquer: AE4.1 incorrect base cases; AE4.2 faulty merging of subproblems; AE4.3 missing recursive calls / wrong recursion depth.
- AE5 Dynamic Programming: AE5.1 incorrect state definition; AE5.2 errors in state transition logic; AE5.3 improper base-state initialization; AE5.4 overlapping subproblems not memoized.
- AE6 Search: AE6.1 incomplete state-space traversal; AE6.2 over-pruning or missing transitions; AE6.3 wrong BFS/DFS/heuristic choice; AE6.4 infinite loops/cycles in traversal.

Decision procedure, follow internally:
1. Read the problem, then trace the submitted code to find the behavior that makes it wrong (or, for TLE/RE/CE, too slow / crashing / non-compiling).
2. Decide whether it is parsing/format/compile/runtime, boundary/indexing, control condition, datatype, or algorithmic reasoning.
3. If algorithmic, choose the specific AE family when applicable; otherwise a GE1 design leaf (GE1.1-GE1.4).
4. Include every independent root cause that is clearly present, not only the first one found.

Full taxonomy:
{rubric}
