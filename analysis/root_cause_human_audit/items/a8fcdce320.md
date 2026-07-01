# Root-Cause Audit Item a8fcdce320

## Metadata
- problem_id: 1599F
- model: gpt-5.4-nano
- idx: 10
- rating: 2700
- tags: hashing
- sandbox_verdict: WA
- first_fail_kind: public
- original_labels: GE2.1
- original_rationale: The logic misses boundary or special cases in the problem constraints.

## Problem Statement
In the year 2420 humans have finally built a colony on Mars thanks to the work of Elon Tusk. There are 10^9+7 cities arranged in a circle in this colony and none of them are connected yet. Elon Tusk wants to connect some of those cities using only roads of the same size in order to lower the production cost of those roads. Because of that he gave a list on N cites where some cites can appear more than once and Q queries that you need to answer. For the query you need to determine if it is possible to connect all the cities from L_{i} to R_{i} on that list using only roads of length D_{i}. 

Input

The first line contains two integers N and Q (1 ≤ N, Q ≤ 2⋅10^5 ) — the length of the array of cities and the number of queries you need to answer. 

The second lines contains N integers representing the array of cites. Next Q lines contain three integers L, R and D (1 ≤ L_{i}, R_{i} ≤ N, 0 ≤ D_{i} ≤ 10^9+6) — the range of cities that needs to be connected and the length of the road that you can use. 

Output

The output contains Q lines. If it is possible to connect all the cities from the i-th query can be connected with roads of length D_{i} the i-th line should contain the word "Yes", otherwise it should contain the word "No". 

Examples

Input


9 8
17 0 12 6 10 8 2 4 5
2 3 12
2 3 6
2 4 6
4 6 2
2 8 2
1 2 17
1 8 2
9 9 14


Output


Yes
No
Yes
Yes
Yes
Yes
No
Yes


Input


4 1
7 21 14 0
1 4 1000000000


Output


Yes

Note

In the 5^{th} query of the first test case we can connect cities in this order 0-2-4-6-8-10-12 this way distance between any two connected cities is 2. In the second test case we can connect cities in this order 21-14-7-0 this way distance between any two connected cities is 10^9 module 10^9+7. 

## Submitted Rejected C++ Code
```cpp
#include <bits/stdc++.h>
using namespace std;

static const int MOD = 1000000007;

struct DSU {
    vector<int> p, r;
    DSU(int n=0){ init(n); }
    void init(int n){
        p.resize(n);
        r.assign(n,0);
        iota(p.begin(), p.end(), 0);
    }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    void unite(int a,int b){
        a=find(a); b=find(b);
        if(a==b) return;
        if(r[a]<r[b]) swap(a,b);
        p[b]=a;
        if(r[a]==r[b]) r[a]++;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, Q;
    cin >> N >> Q;
    vector<int> a(N+1);
    for(int i=1;i<=N;i++) cin >> a[i];

    // Precompute log2
    int LG = 1;
    while((1<<LG) <= N) LG++;
    vector<vector<int>> st(LG, vector<int>(N+1));
    for(int i=1;i<=N;i++) st[0][i] = a[i];

    for(int k=1;k<LG;k++){
        int len = 1<<k;
        for(int i=1;i+len-1<=N;i++){
            // We'll store AND of pairwise gcd differences indirectly? Not needed.
            // Actually we will build segment tree over gcd of differences between consecutive values in array modulo MOD.
        }
    }

    // Use sparse table for gcd over range of "g_i = gcd(|a[i]-a[i+1]|, MOD)"? Let's derive properly.
    // Condition: from values in subarray, need graph on those distinct vertices on circle with step D.
    // Let S be set of residues (a[i] mod MOD). You can connect all vertices iff
    // for all vertices, they lie in same coset of gcd(D,MOD) subgroup: i.e., all pairwise differences are divisible by g = gcd(D, MOD).
    // Equivalent: there exists x such that for all i: (a[i]-x) % g == 0.
    // So compute g = gcd(D,MOD) then check if all a in [L,R] are congruent mod g.
    //
    // We answer many queries: check whether max-min? no.
    // Need fast congruence check for variable modulus g (depends on D).
    //
    // Approach: factor MOD and use CRT-like congruence checking by divisibility of differences.
    // Since MOD is prime (1e9+7), gcd(D,MOD) is either 1 (if D not multiple of MOD) or MOD (if D==0 mod MOD).
    // But D is constrained 0..MOD-1, hence gcd(D,MOD) is:
    // - if D==0 => gcd(0,MOD)=MOD
    // - else => gcd(D,MOD)=1
    // Therefore:
    // If D != 0: g=1 => all differences divisible by 1 always => answer always "Yes".
    // If D == 0: g=MOD => need all values congruent mod MOD => values must be equal (since residues in [0,MOD-1]).
    //
    // Wait: input says cities arranged in circle of size 1e9+7 and cities can be labeled 0..MOD-1.
    // Roads of length D: can connect between cities whose clockwise distance equals D or counter? It says "roads of length D"
    // and note indicates with D=2 on list 0,2,4,... they connected with distance 2 between any two connected cities.
    // That implies edges between cities whose circular distance (absolute modular difference) equals D (not both directions?).
    // For prime modulus, gcd reasoning holds with undirected edges of step D: reachable vertices are those in same coset modulo gcd(D,MOD).
    //
    // For D=0, only self-loops; thus need all cities in range to be same city.
    // For D!=0, gcd(D,MOD)=1 so graph is connected across all MOD cities => can connect all distinct cities.
    //
    // However, subarray may have duplicates; still all vertices can be connected if the induced set is contained in the connected component,
    // which is entire circle when D!=0. So "Yes".
    //
    // Thus solution reduces to:
    // If D != 0 => Yes
    // Else D==0 => check if all a[L..R] are equal.
    //
    // Let's implement range equality check with sparse table for min/max or just equality via hashing.
    // We'll use sparse table for min and max; all equal iff min==max.
    vector<int> mn(N+1), mx(N+1);
    // sparse table for min and max
    vector<vector<int>> stMin(LG, vector<int>(N+1, INT_MAX));
    vector<vector<int>> stMax(LG, vector<int>(N+1, INT_MIN));
    for(int i=1;i<=N;i++){
        stMin[0][i]=a[i];
        stMax[0][i]=a[i];
    }
    for(int k=1;k<LG;k++){
        int len = 1<<k;
        for(int i=1;i+len-1<=N;i++){
            stMin[k][i]=min(stMin[k-1][i], stMin[k-1][i+(len>>1)]);
            stMax[k][i]=max(stMax[k-1][i], stMax[k-1][i+(len>>1)]);
        }
    }
    auto queryMin = [&](int l,int r)->int{
        int len=r-l+1;
        int k=31-__builtin_clz(len);
        return min(stMin[k][l], stMin[k][r-(1<<k)+1]);
    };
    auto queryMax = [&](int l,int r)->int{
        int len=r-l+1;
        int k=31-__builtin_clz(len);
        return max(stMax[k][l], stMax[k][r-(1<<k)+1]);
    };

    while(Q--){
        int L,R;
        long long D;
        cin >> L >> R >> D;
        if(D%MOD != 0){
            cout << "Yes\n";
        }else{
            int mnv = queryMin(L,R);
            int mxv = queryMax(L,R);
            cout << (mnv==mxv ? "Yes\n" : "No\n");
        }
    }
    return 0;
}
```

## Accepted Reference C++ Implementation
```cpp
#include <bits/stdc++.h>
using namespace std;
const int N = 200010, mo = 1e9 + 7;
int n, q;
long long a[N], s1[N], s2[N], c[N];
long long qmi(long long a, long long k) {
  long long res = 1;
  while (k) {
    if (k & 1) res = res * a % mo;
    a = a * a % mo;
    k >>= 1;
  }
  return res;
}
long long mod(long long x) { return (x % mo + mo) % mo; }
int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  cout.tie(0);
  cin >> n >> q;
  for (long long i = 1; i <= n; i++) {
    cin >> a[i];
    s1[i] = (s1[i - 1] + a[i]) % mo;
    s2[i] = (s2[i - 1] + a[i] * a[i] % mo) % mo;
    c[i] = (c[i - 1] + i * i % mo) % mo;
  }
  long long l, r, d, len;
  while (q--) {
    cin >> l >> r >> d;
    len = r - l + 1;
    long long f1 = (s1[r] - s1[l - 1]), f2 = (s2[r] - s2[l - 1]);
    f1 = mod(f1), f2 = mod(f2);
    long long f = (f1 * 2 * qmi(len, mo - 2) % mo - (len - 1) * d % mo) % mo *
                  qmi(2, mo - 2) % mo;
    f = mod(f);
    long long ans = f * f % mo * len % mo +
                    f * (len - 1) % mo * len % mo * d % mo +
                    c[len - 1] * d % mo * d % mo;
    ans = mod(ans);
    if (ans == f2)
      puts("Yes");
    else
      puts("No");
  }
  return 0;
}

```

## First Failing Test
Input:
```text
9 8
17 0 12 6 10 8 2 4 5
2 3 12
2 3 6
2 4 6
4 6 2
2 8 2
1 2 17
1 8 2
9 9 14

```

Expected output:
```text
Yes
No
Yes
Yes
Yes
Yes
No
Yes

```

Actual output:
```text
Yes
Yes
Yes
Yes
Yes
Yes
Yes
Yes

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
