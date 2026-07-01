# Wei et al. (2026) error taxonomy for LLM-generated competitive programs.
# "Evaluating and improving LLM-based competitive program generation", Information and Software
# Technology 191 (2026) 107977 (https://doi.org/10.1016/j.infsof.2025.107977). Family names, leaf
# codes/names, family descriptions, and leaf definitions are quoted verbatim from the paper's
# Section 4.2 (only the trailing "An example ... can be found in Fig. N" figure cross-references are
# omitted, as those figures are not reproduced here). 6 General-Error (GE) families / 14 leaves +
# 6 Algorithm-specific-Error (AE) families / 18 leaves = 32 leaves.

FAMILIES = {
    "GE1": "Design-related Errors",
    "GE2": "Boundary-related Errors",
    "GE3": "Condition-related Errors",
    "GE4": "Data Type Errors",
    "GE5": "Syntax Errors",
    "GE6": "Input/Output Errors",
    "AE1": "Mathematical Problem-related Errors",
    "AE2": "Greedy Algorithm-related Errors",
    "AE3": "Graph Theory-related Errors",
    "AE4": "Recursion & Divide-and-Conquer-related Errors",
    "AE5": "Dynamic Programming-related Errors",
    "AE6": "Search-related Errors",
}

ALGORITHM_SPECIFIC_NOTE = ("Algorithm-specific errors refer to logic-specific mistakes tied to "
                           "particular algorithm types (e.g., dynamic programming, graph algorithms, "
                           "greedy algorithms).")

FAMILY_DEFINITIONS = {
    "GE1": "These errors stem from flaws in the overall solution strategy or algorithm design, often caused by a misunderstanding of the problem requirements or the selection of an inappropriate algorithm. Fixing such errors typically requires substantial revisions to the algorithm design, rather than simple code-level modifications. This category consists of four subcategories.",
    "GE2": "Improper handling of edge values can compromise the program's logical correctness at the boundaries of the input domain. These errors often remain undetected until exposed by adversarial or hidden test cases.",
    "GE3": "Faulty boolean expressions (such as incorrect operators, misinterpreted precedence, or misplaced negations) can misdirect control flow or prematurely terminate loops. These errors typically result in partially correct outputs or missed corner cases.",
    "GE4": "This error occurs when an inappropriate numeric range or precision is used, or when implicit type conversions alter the intended semantics. Such issues can lead to overflow, underflow, or subtle rounding errors. Selecting an appropriate data type or applying explicit casts can effectively resolve the problem.",
    "GE5": "Purely lexical or grammatical mistakes that prevent compilation or produce immediate runtime faults, such as missing tokens, mismatched delimiters, or language-specific misuse of keywords. They reflect lapses in basic code authoring rather than conceptual misunderstanding.",
    "GE6": "The program mishandles the prescribed I/O contract: it misparses input, formats output incorrectly, or neglects special cases like empty streams, leading to WA status despite correct internal logic.",
    "AE1": "Errors related to mathematical problems.",
    "AE2": "Errors related to the greedy algorithm.",
    "AE3": "Errors related to graph-theory algorithms.",
    "AE4": "Errors related to recursion and divide-and-conquer.",
    "AE5": "Errors related to the dynamic programming.",
    "AE6": "Errors related to the search algorithm.",
}

# leaf -> (name, definition [verbatim from the paper], language_dependent)
TAXONOMY = {
    "GE1.1": ("Incorrect Algorithm",
              "This type of error arises when the model selects an inappropriate algorithm for the given problem, leading to a fundamental flaw in the overall solution strategy. A common example is the use of a greedy algorithm for problems that inherently require dynamic programming or exhaustive search. While a greedy approach might pass simple test cases, it often fails on edge cases due to its inability to account for all of the problem's constraints.", False),
    "GE1.2": ("Misunderstanding Problem Requirements",
              "This type of error stems from the model's incorrect semantic understanding of the problem description. Such misunderstandings typically occur during the initial problem analysis phase, which leads to the subsequent algorithm design in the wrong direction. As a result, even if the implementation is logically consistent, the final program fails to fulfill the actual requirements of the task.", False),
    "GE1.3": ("Overly Complex or Inefficient Design",
              "This type of error refers to situations where the solver constructs a solution that, while logically correct, incorporates unnecessary layers of computation, overly complex control flow, or inefficient algorithms. Such designs tend to increase time or space complexity, making the solution susceptible to time-limit or memory-limit violations, especially when handling large-scale inputs.", False),
    "GE1.4": ("Inappropriate Data Structure Selection",
              "This type of error arises when the selected data structure does not align with the operational requirements or constraints of the problem. Such a mismatch can lead to low time or space efficiency and may even prevent the correct implementation of the intended algorithm, particularly in problems with strict performance constraints.", False),
    "GE2.1": ("Incorrect Handling of Edge Cases or Input Boundaries",
              "This type of error occurs when the program fails to properly handle edge cases or input boundaries, leading to incorrect behavior under extreme or uncommon conditions.", False),
    "GE2.2": ("Off-by-one Errors in Loops or Indexing",
              "This type of error arises when loop boundaries or array indices are set incorrectly, typically due to using < instead of <=, or starting from an off-position such as 1 instead of 0. These errors often lead to out-of-bounds access, skipped elements, or incomplete processing of edge cases, especially in problems involving arrays, strings, or intervals.", False),
    "GE3.1": ("Faulty Condition Expressions in Control Statements",
              "This type of error occurs when the conditions within control structures are incorrectly formulated, causing essential execution paths to be skipped or irrelevant code blocks to be executed unintentionally.", False),
    "GE3.2": ("Incorrect Logical Operators or Precedence",
              "This type of error arises when logical expressions use incorrect operators or depend on operator precedence without proper use of parentheses. As a result, control flow may follow unintended branches, leading to missed conditions or incorrect outputs in test cases.", False),
    "GE4.1": ("Overflow or Precision Loss Due To Improper Data Type Selection",
              "This error arises when a variable is declared with a data type that lacks sufficient range or precision to represent the required values. For instance, using int where long long is necessary can cause integer overflow and lead to incorrect results.", True),
    "GE4.2": ("Implicit Type Conversions Causing Unexpected Behavior",
              "This error occurs when operations involve mixed data types, causing implicit conversions that alter the program's intended semantics. Such conversions can lead to loss of precision, sign mismatches, or unintended value truncation, particularly in arithmetic or conditional expressions.", True),
    "GE5.1": ("Compilation Errors",
              "Syntax errors occur when the program fails to compile due to missing semicolons, mismatched brackets, undeclared variables, or other programming language syntax rule violations.", True),
    "GE5.2": ("Language-specific Syntax Misuse",
              "This refers to the incorrect use of programming language features that behave differently depending on the language environment. For example, in C++, mixing cin/cout with scanf/printf without disabling synchronization can lead to unexpected I/O behavior or significant performance degradation. Such misuse does not cause compilation errors but can result in inefficient execution.", True),
    "GE6.1": ("Incorrect Input Format Handling",
              "This error occurs when the program does not adhere to the input format specified in the problem statement. As a result, it may read input incorrectly or prematurely, leading to incorrect values being processed by the subsequent logic.", False),
    "GE6.2": ("Output Format Mismatches",
              "This type of error occurs when the program's output format does not strictly conform to the problem's specifications. Even if the underlying logic and computed values are correct, such formatting issues can still lead to a WA judgment.", False),
    "AE1.1": ("Misuse or Derivation Error of Mathematical Formulas or Conclusions",
              "These errors occur when the solver applies mathematical formulas incorrectly, derives flawed expressions, or ignores the necessary preconditions for applying known results. Common issues include misusing modular arithmetic identities, applying combinatorial formulas without handling edge conditions, or invoking theorems under invalid assumptions.", False),
    "AE1.2": ("Special Mathematical Structure Handle Errors",
              "When dealing with data with special mathematical properties (such as prime sieve, factorization, GCD, modular inverses), the model often makes mistakes in implementation, has logical structure defects, or fails to cover all special cases.", False),
    "AE2.1": ("Incorrect Local Decision-making Leading to Suboptimal Solutions",
              "Greedy algorithms make choices based on local optimality with the hope that this leads to a global optimum. When the local decision rule is flawed, such as picking the largest item without considering constraints, it may yield a feasible but non-optimal solution.", False),
    "AE2.2": ("Lack of Proof/Validation for Greedy Choice Correctness",
              "Greedy algorithms require a correctness guarantee (e.g., the property of greedy choice or the optimal substructure). Failing to validate that the greedy strategy works for all inputs formally can lead to solutions that pass sample cases but fail on edge cases, especially where greedy behavior breaks down.", False),
    "AE3.1": ("Not Marking Visited Nodes",
              "Failing to mark nodes as visited during traversal may lead to infinite loops or repeated visits, particularly in graphs with cycles. This often breaks DFS or BFS logic and affects termination.", False),
    "AE3.2": ("Incorrect Visitation Order",
              "Marking nodes too late or processing them in the wrong sequence can cause incorrect behavior in traversal-based algorithms (i.e., topological sort, cycle detection). Ensuring proper visitation timing is key to correctness.", False),
    "AE3.3": ("Ignoring Disconnected Components",
              "Only exploring from a single start node and neglecting other unvisited nodes can cause entire components to be missed. This results in incomplete outputs for problems involving connectivity or component counting.", False),
    "AE4.1": ("Incorrect Base Cases",
              "In divide-and-conquer algorithms, recursion must terminate at well-defined base cases. Errors in base case logic, such as incorrect stopping conditions or failure to handle minimal input sizes, can result in infinite recursion or wrong answers on trivial subproblems.", False),
    "AE4.2": ("Faulty Merging of Subproblems",
              "After dividing the problem and solving each part recursively, the merge step is responsible for combining the sub-results into a complete solution. If the merging logic is incorrect, the final output may fail to reflect the correct solution to the original problem accurately.", False),
    "AE4.3": ("Missing Recursive Calls or Incorrect Recursion Depth",
              "Divide-and-conquer relies on recursive decomposition of the input. Omitting necessary recursive calls or failing to reach sufficient depth can cause parts of the problem to remain unsolved, leading to incomplete or incorrect results.", False),
    "AE5.1": ("Incorrect State Definition",
              "Dynamic programming relies on defining problem states that capture sufficient information for recurrence. If the state is too coarse (i.e., loses key distinctions) or too fine (i.e., leads to over-complexity), the DP formulation will fail to represent the full problem correctly, resulting in incorrect or incomplete solutions.", False),
    "AE5.2": ("Errors in State Transition Logic",
              "State transitions describe how a larger problem is built from smaller subproblems. Mistakes in this recurrence, such as using the wrong indices, conditions, or transition direction, cause the DP table to be filled incorrectly, producing wrong final answers even when the states are defined properly.", False),
    "AE5.3": ("Improper Initialization of Base States",
              "Dynamic programming solutions depend on correctly initializing base cases (e.g., dp[0], dp[1]) from which all other values are derived. If base values are missing or set incorrectly, subsequent transitions accumulate errors, propagating incorrect values throughout the DP table.", False),
    "AE5.4": ("Overlapping Subproblems not Identified Properly",
              "A key idea of Dynamic programming is recognizing and reusing solutions to overlapping subproblems. If the problem is solved repeatedly for the same input (e.g., in a naive recursive form), it indicates that the overlapping substructure has not been exploited. This often leads to redundant computation and inefficiency.", False),
    "AE6.1": ("Incomplete State Space Traversal",
              "This error occurs when the search algorithm fails to explore all reachable states due to early termination or limited expansion logic. It leads to missing valid solutions, especially in problems requiring full coverage or global optimality.", False),
    "AE6.2": ("Over-pruning or Missing Transitions",
              "Search algorithms often include pruning to improve efficiency, but overly aggressive or incorrect pruning can remove valid paths. Similarly, neglecting certain transitions in the state graph results in an incomplete or incorrect traversal.", False),
    "AE6.3": ("Incorrect Use of BFS, DFS, or Heuristic Pruning",
              "Each search strategy has a specific application scenario. For example, BFS guarantees the shortest path in unweighted graphs, while DFS does not. Applying the wrong strategy or misusing heuristics (e.g., in A*) can produce logically incorrect or suboptimal results.", False),
    "AE6.4": ("Infinite Loops or Cycles in Graph Traversal",
              "Failing to track visited states or cycles can cause the algorithm to revisit the same nodes indefinitely. This often results in non-terminating execution or redundant computation, especially in graphs with cycles or bidirectional edges.", False),
}
