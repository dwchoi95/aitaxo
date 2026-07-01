# Root-Cause Audit Item e9c9ebb4e6

## Metadata
- problem_id: 1600E
- model: human
- idx: 66
- rating: 1900
- tags: games,greedy,two pointers
- sandbox_verdict: WA
- first_fail_kind: private
- original_labels: AE2.1
- original_rationale: Uses a local greedy choice that does not guarantee the global optimum.

## Problem Statement
Alice and Bob are playing a game. They are given an array A of length N. The array consists of integers. They are building a sequence together. In the beginning, the sequence is empty. In one turn a player can remove a number from the left or right side of the array and append it to the sequence. The rule is that the sequence they are building must be strictly increasing. The winner is the player that makes the last move. Alice is playing first. Given the starting array, under the assumption that they both play optimally, who wins the game?

Input

The first line contains one integer N (1 ≤ N ≤ 2*10^5) - the length of the array A.

The second line contains N integers A_1, A_2,...,A_N (0 ≤ A_i ≤ 10^9)

Output

The first and only line of output consists of one string, the name of the winner. If Alice won, print "Alice", otherwise, print "Bob".

Examples

Input


1
5


Output


Alice


Input


3
5 4 5


Output


Alice


Input


6
5 8 2 1 10 9


Output


Bob

## Submitted Rejected C++ Code
```cpp
#include <bits/stdc++.h>
using namespace std;
mt19937 mr(time(0));
struct LL {
  static long long int m;
  long long int val;
  LL(long long int v) { val = reduce(v); };
  LL(int v) { val = reduce((long long int)v); };
  LL() { val = 0; };
  ~LL(){};
  LL(const LL& l) { val = l.val; };
  LL& operator=(int l) {
    val = l;
    return *this;
  }
  LL& operator=(long long int l) {
    val = l;
    return *this;
  }
  LL& operator=(LL l) {
    val = l.val;
    return *this;
  }
  static void setMod(long long int m) {
    assert(m);
    LL::m = m;
  }
  static long long int reduce(long long int x, long long int md = m) {
    x %= md;
    while (x >= md) x -= md;
    while (x < 0) x += md;
    return x;
  }
  bool operator<(const LL& b) { return val < b.val; }
  bool operator<=(const LL& b) { return val <= b.val; }
  bool operator!=(const LL& b) { return val != b.val; }
  bool operator==(const LL& b) { return val == b.val; }
  bool operator>=(const LL& b) { return val >= b.val; }
  bool operator>(const LL& b) { return val > b.val; }
  LL operator+(const LL& b) { return LL(val + b.val); }
  LL operator+(const long long int& b) { return (*this + LL(b)); }
  LL& operator+=(const LL& b) { return (*this = *this + b); }
  LL& operator+=(const long long int& b) { return (*this = *this + b); }
  LL operator-(const LL& b) { return LL(val - b.val); }
  LL operator-(const long long int& b) { return (*this - LL(b)); }
  LL& operator-=(const LL& b) { return (*this = *this - b); }
  LL& operator-=(const long long int& b) { return (*this = *this - b); }
  LL operator*(const LL& b) { return LL(val * b.val); }
  LL operator*(const long long int& b) { return (*this * LL(b)); }
  LL& operator*=(const LL& b) { return (*this = *this * b); }
  LL& operator*=(const long long int& b) { return (*this = *this * b); }
  static LL exp(const LL& x, const long long int& y) {
    long long int z = y;
    z = reduce(z, m - 1);
    LL ret = 1;
    LL w = x;
    while (z) {
      if (z & 1) ret *= w;
      z >>= 1;
      w *= w;
    }
    return ret;
  }
  LL& operator^=(long long int y) { return (*this = LL(val ^ y)); }
  LL operator/(const LL& b) { return ((*this) * exp(b, -1)); }
  LL operator/(const long long int& b) { return (*this / LL(b)); }
  LL operator/=(const LL& b) { return ((*this) *= exp(b, -1)); }
  LL& operator/=(const long long int& b) { return (*this = *this / LL(b)); }
};
ostream& operator<<(ostream& os, const LL& obj) { return os << obj.val; }
long long int LL::m = 1000000007;
using namespace std;
long long int cases, N, M, Q, K, X, Y;
long long int rd() {
  long long int x;
  cin >> x;
  return x;
}
double rdd() {
  double x;
  cin >> x;
  return x;
}
string rds() {
  string x;
  cin >> x;
  return x;
}
template <class T>
void rds(char* S, T* sz) {
  *sz = strlen(strcpy(S, rds().c_str()));
}
template <class T>
void rG(int sz, vector<vector<T>>& adj, int E = -18852946) {
  if (E == -18852946) E = sz - 1;
  adj.clear();
  for (long long int i = 0; i < sz + 1; ++i) adj.push_back(vector<T>());
  for (long long int i = 0; i < E; ++i) {
    T a = rd();
    T b = rd();
    adj[a].push_back(b);
    adj[b].push_back(a);
  }
}
void fl() { cout.flush(); }
template <class T>
void ds(vector<T> v) {
  for (auto x : v) cout << x << " ";
  cout << endl;
}
template <class T>
void panic(T out) {
  cout << out << endl;
  exit(0);
}
template <class S, class T>
bool updmin(S& a, T b) {
  S B = (S)b;
  if (B < a) {
    a = B;
    return 1;
  }
  return 0;
}
template <class S, class T>
bool updmax(S& a, T b) {
  S B = (S)b;
  if (B > a) {
    a = B;
    return 1;
  }
  return 0;
}
template <class S, class T>
S min(S a, T b) {
  S c = a;
  updmin(c, b);
  return c;
}
template <class S, class T>
S max(S a, T b) {
  S c = a;
  updmax(c, b);
  return c;
}
long long int gcd(long long int a, long long int b) {
  return b ? gcd(b, a % b) : a;
}
void precalc() {}
void reset() {}
bool cmp(pair<int, int> a, pair<int, int> b) {}
int L, A, B, R;
int S[3 * 100010];
void read() {
  N = rd();
  for (long long int i = 1; i <= N; ++i) S[i] = rd();
  S[0] = S[N + 1] = -99999;
  L = 1;
  R = N;
  for (A = 1; S[A + 1] > S[A]; A++) {
  }
  for (B = N; S[B - 1] > S[B]; B--) {
  }
  bool turn = 1;
  while (L <= A || B <= R) {
    if (S[L] == S[R]) {
      if (((A - L) & 1) && ((R - B) & 1)) turn = !turn;
      break;
    }
    if (L > A) {
      if ((R - B) & 1) turn = !turn;
      break;
    }
    if (R < B) {
      if ((L - A) & 1) turn = !turn;
      break;
    }
    if (S[L] > S[R])
      if ((A - L) & 1 == 0)
        break;
      else
        R--;
    if (S[R] > S[L])
      if ((R - B) & 1 == 0)
        break;
      else
        L++;
    turn = !turn;
  }
  cout << (turn ? "Alice" : "Bob") << endl;
}
int main() {
  precalc();
  bool trials = 0;
  bool interactive = 0;
  if (!interactive) {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
  }
  if (trials)
    cases = rd();
  else
    cases = 1;
  while (cases--) {
    read();
  }
}

```

## Accepted Reference C++ Implementation
```cpp
#include <bits/stdc++.h>
using namespace std;
int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr), cout.tie(nullptr);
  int n;
  cin >> n;
  vector<int> a(n + 1);
  for (int i = 1; i <= n; i++) cin >> a[i];
  int l = 1, r = n;
  while (l < n && a[l] < a[l + 1]) l++;
  while (r > 1 && a[r] < a[r - 1]) r--;
  r = n - r + 1;
  if (l & 1 || r & 1)
    cout << "Alice" << endl;
  else
    cout << "Bob" << endl;
  return 0;
}

```

## First Failing Test
Input:
```text
2
5 12

```

Expected output:
```text
Alice

```

Actual output:
```text
Bob

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
