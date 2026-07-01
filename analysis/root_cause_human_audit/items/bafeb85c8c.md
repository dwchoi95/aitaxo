# Root-Cause Audit Item bafeb85c8c

## Metadata
- problem_id: 1598C
- model: human
- idx: 11
- rating: 1200
- tags: data structures,dp,implementation,math,two pointers
- sandbox_verdict: WA
- first_fail_kind: public
- original_labels: GE6.2
- original_rationale: Prints debug frequency information before the answer, so the output format is wrong.

## Problem Statement
Monocarp has got an array a consisting of n integers. Let's denote k as the mathematic mean of these elements (note that it's possible that k is not an integer). 

The mathematic mean of an array of n elements is the sum of elements divided by the number of these elements (i. e. sum divided by n).

Monocarp wants to delete exactly two elements from a so that the mathematic mean of the remaining (n - 2) elements is still equal to k.

Your task is to calculate the number of pairs of positions [i, j] (i < j) such that if the elements on these positions are deleted, the mathematic mean of (n - 2) remaining elements is equal to k (that is, it is equal to the mathematic mean of n elements of the original array a).

Input

The first line contains a single integer t (1 ≤ t ≤ 10^4) — the number of testcases.

The first line of each testcase contains one integer n (3 ≤ n ≤ 2 ⋅ 10^5) — the number of elements in the array.

The second line contains a sequence of integers a_1, a_2, ..., a_n (0 ≤ a_i ≤ 10^{9}), where a_i is the i-th element of the array.

The sum of n over all testcases doesn't exceed 2 ⋅ 10^5.

Output

Print one integer — the number of pairs of positions [i, j] (i < j) such that if the elements on these positions are deleted, the mathematic mean of (n - 2) remaining elements is equal to k (that is, it is equal to the mathematic mean of n elements of the original array a).

Example

Input


4
4
8 8 8 8
3
50 20 10
5
1 4 7 3 5
7
1 2 3 4 5 6 7


Output


6
0
2
3

Note

In the first example, any pair of elements can be removed since all of them are equal.

In the second example, there is no way to delete two elements so the mathematic mean doesn't change.

In the third example, it is possible to delete the elements on positions 1 and 3, or the elements on positions 4 and 5.

## Submitted Rejected C++ Code
```cpp
#include <bits/stdc++.h>
using namespace std;
long long gcd(long long a, long long b) {
  if (b > a) {
    return gcd(b, a);
  }
  if (b == 0) {
    return a;
  }
  return gcd(b, a % b);
}
void extendedEuclid(long long a, long long b, long long *x, long long *y) {
  if (b == 0) {
    *x = 1;
    *y = 0;
    return;
  }
  extendedEuclid(b, a % b, x, y);
  long long cx = *y;
  *y = *x - (a / b) * (*y);
  *x = cx;
}
long long expo(long long a, long long b, long long mod) {
  long long res = 1;
  while (b > 0) {
    if (b & 1) res = (res * a) % mod;
    a = (a * a) % mod;
    b = b >> 1;
  }
  return res;
}
vector<bool> sieve(long long n) {
  vector<bool> arr(n + 1, true);
  for (long long i = 2; i * i <= n; i++) {
    if (arr[i] == true) {
      for (long long j = i * i; j <= n; j += i) {
        arr[j] = false;
      }
    }
  }
  return arr;
}
long long mod_add(long long a, long long b, long long m) {
  a = a % m;
  b = b % m;
  return (((a + b) % m) + m) % m;
}
long long mod_sub(long long a, long long b, long long m) {
  a = a % m;
  b = b % m;
  return (((a - b) % m) + m) % m;
}
long long mod_mul(long long a, long long b, long long m) {
  a = a % m;
  b = b % m;
  return (((a * b) % m) + m) % m;
}
long long modInverse(long long a, long long m) {
  long long x, y;
  extendedEuclid(a, m, &x, &y);
  return (x + m) % m;
}
void solve() {
  int n;
  cin >> n;
  int ar[n];
  for (int(i) = 0; (i) < n; i++) cin >> ar[i];
  long long sum = accumulate(ar, ar + n, 0LL);
  if ((2 * sum) % n) {
    cout << "0\n";
    return;
  }
  int sumOfTwo = 2 * sum / n;
  map<int, int> freq;
  for (int(i) = 0; (i) < n; i++) freq[ar[i]]++;
  long long ans = 0;
  for (auto i : freq) {
    cout << i.first << " " << i.second << " " << sumOfTwo - i.first << " "
         << freq[sumOfTwo - i.first] << "\n";
    if (sumOfTwo / 2 != i.first)
      ans += i.second * freq[sumOfTwo - i.first];
    else if (sumOfTwo / 2 == i.first)
      ans += i.second * (i.second - 1);
  }
  cout << ans / 2 << "\n";
}
int main() {
  ios_base::sync_with_stdio(false);
  cin.tie(NULL);
  cout.tie(NULL);
  ;
  int t;
  cin >> t;
  while (t--) solve();
  return 0;
}

```

## Accepted Reference C++ Implementation
```cpp
#include <bits/stdc++.h>
using namespace std;
long long int min(long long int a, long long int b) {
  if (a < b) return a;
  return b;
}
long long int max(long long int a, long long int b) {
  if (a > b) return a;
  return b;
}
void solve() {
  long long int n, i, j;
  cin >> n;
  vector<long long int> v(n);
  long long int sum = 0;
  for (long long int i = 0; i < n; i++) {
    cin >> v[i];
    sum += v[i];
  }
  if ((2 * sum) % n != 0) {
    cout << 0 << endl;
    return;
  }
  sort(v.begin(), v.end());
  long long int val = (2 * sum) / n, ans = 0;
  for (long long int i = 0; i < n; i++) {
    long long int diff = val - v[i];
    auto low = lower_bound(v.begin() + i + 1, v.end(), diff);
    auto upp = upper_bound(v.begin() + i + 1, v.end(), diff);
    ans += upp - low;
  }
  cout << ans << endl;
}
int main() {
  ios_base::sync_with_stdio(false);
  cin.tie(NULL);
  cout.tie(NULL);
  long long int t;
  cin >> t;
  while (t--) solve();
  return 0;
}

```

## First Failing Test
Input:
```text
4
4
8 8 8 8
3
50 20 10
5
1 4 7 3 5
7
1 2 3 4 5 6 7

```

Expected output:
```text
6
0
2
3

```

Actual output:
```text
8 4 8 4
6
0
1 1 7 1
3 1 5 1
4 1 4 1
5 1 3 1
7 1 1 1
2
1 1 7 1
2 1 6 1
3 1 5 1
4 1 4 1
5 1 3 1
6 1 2 1
7 1 1 1
3

```

## Labeling Task
Fill `root_labels` and `root_rationale` in `label.csv`.
Use one or more leaf labels from the taxonomy. Prefer the most specific label supported by the
submitted code plus the failing test/reference evidence.

## Taxonomy
- GE1.1 Incorrect Algorithm: This type of error arises when the model selects an inappropriate algorithm for the given problem, leading to a fundamental flaw in the overall solution strategy. A common example is the use of a greedy algorithm for problems that inherently require dynamic programming or exhaustive search. While a greedy approach might pass simple test cases, it often fails on edge cases due to its inability to account for all of the problem's constraints.
- GE1.2 Misunderstanding Problem Requirements: This type of error stems from the model's incorrect semantic understanding of the problem description. Such misunderstandings typically occur during the initial problem analysis phase, which leads to the subsequent algorithm design in the wrong direction. As a result, even if the implementation is logically consistent, the final program fails to fulfill the actual requirements of the task.
- GE1.3 Overly Complex or Inefficient Design: This type of error refers to situations where the solver constructs a solution that, while logically correct, incorporates unnecessary layers of computation, overly complex control flow, or inefficient algorithms. Such designs tend to increase time or space complexity, making the solution susceptible to time-limit or memory-limit violations, especially when handling large-scale inputs.
- GE1.4 Inappropriate Data Structure Selection: This type of error arises when the selected data structure does not align with the operational requirements or constraints of the problem. Such a mismatch can lead to low time or space efficiency and may even prevent the correct implementation of the intended algorithm, particularly in problems with strict performance constraints.
- GE2.1 Incorrect Handling of Edge Cases or Input Boundaries: This type of error occurs when the program fails to properly handle edge cases or input boundaries, leading to incorrect behavior under extreme or uncommon conditions.
- GE2.2 Off-by-one Errors in Loops or Indexing: This type of error arises when loop boundaries or array indices are set incorrectly, typically due to using < instead of <=, or starting from an off-position such as 1 instead of 0. These errors often lead to out-of-bounds access, skipped elements, or incomplete processing of edge cases, especially in problems involving arrays, strings, or intervals.
- GE3.1 Faulty Condition Expressions in Control Statements: This type of error occurs when the conditions within control structures are incorrectly formulated, causing essential execution paths to be skipped or irrelevant code blocks to be executed unintentionally.
- GE3.2 Incorrect Logical Operators or Precedence: This type of error arises when logical expressions use incorrect operators or depend on operator precedence without proper use of parentheses. As a result, control flow may follow unintended branches, leading to missed conditions or incorrect outputs in test cases.
- GE4.1 Overflow or Precision Loss Due To Improper Data Type Selection: This error arises when a variable is declared with a data type that lacks sufficient range or precision to represent the required values. For instance, using int where long long is necessary can cause integer overflow and lead to incorrect results.
- GE4.2 Implicit Type Conversions Causing Unexpected Behavior: This error occurs when operations involve mixed data types, causing implicit conversions that alter the program's intended semantics. Such conversions can lead to loss of precision, sign mismatches, or unintended value truncation, particularly in arithmetic or conditional expressions.
- GE5.1 Compilation Errors: Syntax errors occur when the program fails to compile due to missing semicolons, mismatched brackets, undeclared variables, or other programming language syntax rule violations.
- GE5.2 Language-specific Syntax Misuse: This refers to the incorrect use of programming language features that behave differently depending on the language environment. For example, in C++, mixing cin/cout with scanf/printf without disabling synchronization can lead to unexpected I/O behavior or significant performance degradation. Such misuse does not cause compilation errors but can result in inefficient execution.
- GE6.1 Incorrect Input Format Handling: This error occurs when the program does not adhere to the input format specified in the problem statement. As a result, it may read input incorrectly or prematurely, leading to incorrect values being processed by the subsequent logic.
- GE6.2 Output Format Mismatches: This type of error occurs when the program's output format does not strictly conform to the problem's specifications. Even if the underlying logic and computed values are correct, such formatting issues can still lead to a WA judgment.
- AE1.1 Misuse or Derivation Error of Mathematical Formulas or Conclusions: These errors occur when the solver applies mathematical formulas incorrectly, derives flawed expressions, or ignores the necessary preconditions for applying known results. Common issues include misusing modular arithmetic identities, applying combinatorial formulas without handling edge conditions, or invoking theorems under invalid assumptions.
- AE1.2 Special Mathematical Structure Handle Errors: When dealing with data with special mathematical properties (such as prime sieve, factorization, GCD, modular inverses), the model often makes mistakes in implementation, has logical structure defects, or fails to cover all special cases.
- AE2.1 Incorrect Local Decision-making Leading to Suboptimal Solutions: Greedy algorithms make choices based on local optimality with the hope that this leads to a global optimum. When the local decision rule is flawed, such as picking the largest item without considering constraints, it may yield a feasible but non-optimal solution.
- AE2.2 Lack of Proof/Validation for Greedy Choice Correctness: Greedy algorithms require a correctness guarantee (e.g., the property of greedy choice or the optimal substructure). Failing to validate that the greedy strategy works for all inputs formally can lead to solutions that pass sample cases but fail on edge cases, especially where greedy behavior breaks down.
- AE3.1 Not Marking Visited Nodes: Failing to mark nodes as visited during traversal may lead to infinite loops or repeated visits, particularly in graphs with cycles. This often breaks DFS or BFS logic and affects termination.
- AE3.2 Incorrect Visitation Order: Marking nodes too late or processing them in the wrong sequence can cause incorrect behavior in traversal-based algorithms (i.e., topological sort, cycle detection). Ensuring proper visitation timing is key to correctness.
- AE3.3 Ignoring Disconnected Components: Only exploring from a single start node and neglecting other unvisited nodes can cause entire components to be missed. This results in incomplete outputs for problems involving connectivity or component counting.
- AE4.1 Incorrect Base Cases: In divide-and-conquer algorithms, recursion must terminate at well-defined base cases. Errors in base case logic, such as incorrect stopping conditions or failure to handle minimal input sizes, can result in infinite recursion or wrong answers on trivial subproblems.
- AE4.2 Faulty Merging of Subproblems: After dividing the problem and solving each part recursively, the merge step is responsible for combining the sub-results into a complete solution. If the merging logic is incorrect, the final output may fail to reflect the correct solution to the original problem accurately.
- AE4.3 Missing Recursive Calls or Incorrect Recursion Depth: Divide-and-conquer relies on recursive decomposition of the input. Omitting necessary recursive calls or failing to reach sufficient depth can cause parts of the problem to remain unsolved, leading to incomplete or incorrect results.
- AE5.1 Incorrect State Definition: Dynamic programming relies on defining problem states that capture sufficient information for recurrence. If the state is too coarse (i.e., loses key distinctions) or too fine (i.e., leads to over-complexity), the DP formulation will fail to represent the full problem correctly, resulting in incorrect or incomplete solutions.
- AE5.2 Errors in State Transition Logic: State transitions describe how a larger problem is built from smaller subproblems. Mistakes in this recurrence, such as using the wrong indices, conditions, or transition direction, cause the DP table to be filled incorrectly, producing wrong final answers even when the states are defined properly.
- AE5.3 Improper Initialization of Base States: Dynamic programming solutions depend on correctly initializing base cases (e.g., dp[0], dp[1]) from which all other values are derived. If base values are missing or set incorrectly, subsequent transitions accumulate errors, propagating incorrect values throughout the DP table.
- AE5.4 Overlapping Subproblems not Identified Properly: A key idea of Dynamic programming is recognizing and reusing solutions to overlapping subproblems. If the problem is solved repeatedly for the same input (e.g., in a naive recursive form), it indicates that the overlapping substructure has not been exploited. This often leads to redundant computation and inefficiency.
- AE6.1 Incomplete State Space Traversal: This error occurs when the search algorithm fails to explore all reachable states due to early termination or limited expansion logic. It leads to missing valid solutions, especially in problems requiring full coverage or global optimality.
- AE6.2 Over-pruning or Missing Transitions: Search algorithms often include pruning to improve efficiency, but overly aggressive or incorrect pruning can remove valid paths. Similarly, neglecting certain transitions in the state graph results in an incomplete or incorrect traversal.
- AE6.3 Incorrect Use of BFS, DFS, or Heuristic Pruning: Each search strategy has a specific application scenario. For example, BFS guarantees the shortest path in unweighted graphs, while DFS does not. Applying the wrong strategy or misusing heuristics (e.g., in A*) can produce logically incorrect or suboptimal results.
- AE6.4 Infinite Loops or Cycles in Graph Traversal: Failing to track visited states or cycles can cause the algorithm to revisit the same nodes indefinitely. This often results in non-terminating execution or redundant computation, especially in graphs with cycles or bidirectional edges.
