# Phase 3 — AI 생성 코드 버그 Taxonomy (데이터-주도 개방 코딩)

> 분석 대상: `gpt-3.5-turbo`(temp 1.0)가 ConDefects(AtCoder, 누수-free) **40 task에 5개씩 = 200 생성**한 코드.
> 채점 오라클: AtCoder **sample I/O**(전체 hidden 테스트는 `Test.zip` 필요 — 아래 한계 참조).
> 방법: 사전 카테고리 없이 실패 코드를 정독하여 근본 원인을 개방 코딩(open coding)으로 군집화. 카테고리 개수는 데이터에서 창발.

---

## 0. 먼저 — 생성물의 절반이 Python이 아니다 (프로세스 발견)

| 생성물(200) | 수 | 비율 |
|---|---|---|
| **Python** | 108 | 54% |
| **C++** (`#include`, `int main`, `cout`) | 47 | 24% |
| 기타/산문(설명·의사코드·markdown) | 45 | 22% |
| → **비-Python** | **92** | **46%** |

**원인**: 프롬프트가 "`problem.txt` 내용만"(언어 미지정)이고 AtCoder 문제는 관습적으로 C++ 중심 → `gpt-3.5-turbo`가 자주 **C++로 답한다**. 이는 코드의 *추론 버그*가 아니라 **프롬프트·디코딩 아티팩트**이므로 코드-버그 taxonomy와 **분리**해야 한다.

> **결정 포인트(사용자 합의 필요)**: "problem.txt만" 원칙을 유지하면 비-Python 46%가 노이즈로 남는다. Python 버그를 연구 대상으로 좁히려면 최소 지시("Write a Python 3 solution") 한 줄이 필요. 현재는 사용자 지시대로 **무지시 유지** + 이 현상을 별도 카테고리(G)로 보고.

---

## 1. Python 생성물 채점 결과

| | 수 |
|---|---|
| Python 생성물 | 108 (+ 'other' 중 일부 Python 유사 3) = 111 판정 |
| **pass** (sample I/O 통과) | 30 |
| **실패 = AI 버그 코퍼스** | **81** |

난이도 분포(81): easy(<400) 12 · mid(400–1200) 38 · hard(≥1200) 31.

---

## 2. 창발 카테고리 (데이터-주도)

실제 코드를 읽어 도출한 **코드-버그 6종(A–F)** + **생성-프로세스 아티팩트 2종(G–H)**.

| 코드 | 카테고리 | 수 | 정의 |
|---|---|---|---|
| **A** | **Spec-Misinterpretation (명세 오해)** | 45 중 대다수 | 실행은 되나 **다른/단순화된 문제**를 풂. 명세가 요구한 바를 잘못 읽음. |
| **B** | **Incomplete-Logic (불완전 로직)** | 45 중 일부 | 과제의 핵심 연산/경우를 **통째로 누락**. |
| **C** | **Input-Format Misreading (입력 형식 오독)** | 4 | stdin 레이아웃을 잘못 가정 → unpack/parse 예외. |
| **D** | **Inefficiency / Complexity Blowup (비효율)** | 14 | 로직은 그럴듯하나 brute force로 제약 초과 → TLE. |
| **E** | **Index / Boundary Error (인덱스·경계)** | 5 | off-by-one·범위 초과 → IndexError. |
| **F** | **Numeric / Env Limit (수치·환경 한계)** | 4 | 오버플로 유사·Python int-str 4300자리 한계 등. |
| **G** | **Wrong-Language Output (언어 이탈)** | 47(+산문) | Python 대신 C++ 등 출력 (§0, 프로세스 아티팩트). |
| **H** | **Truncated / Malformed Output (출력 잘림)** | 9 | `max_tokens`로 코드가 잘림 → unterminated string/SyntaxError. |

> A·B는 같은 WA 버킷(45)에서 나오며, 정독 결과 **A(명세 오해)가 지배적**이고 B(누락)는 소수. 둘 다 "깔끔하게 실행되는, 그러나 틀린 코드"라는 점이 AI 버그의 핵심 특징.

---

## 3. 카테고리별 실제 예시 (정독)

### A. Spec-Misinterpretation — *가장 빈번, AI 버그의 시그니처*
- **abc225_a** "길이 3 문자열의 **서로 다른** 순열 수": 모델은 `3*2*1=6`(총 순열) 또는 `factorial(3)//factorial(3-uniq)`를 출력 → `aba`에 6 (정답 3). **"different(중복 제외)"를 무시**하고 총 순열로 오해.
- **abc234_c** "10진수로 **0과 2로만** 이루어진 K번째 수": 모델은 `if '2' in str(current)`(2를 *포함*) → K=3에 20 (정답 22). **"only 0/2"를 "contains 2"로 오독**. (게다가 brute force → D도 동반.)
- **abc238_b** 피자 절단 후 최대 중심각: 누적 회전으로 절단 위치를 정렬해 최대 간격을 구해야 하나, `max(A)+N`·`(360-누적)%360` 등으로 **기하를 오모델링** → 전부 오답.

### B. Incomplete-Logic
- **abc237_c** "`S` 앞에 **a를 몇 개 붙여** 회문이 되는가": 모델은 `if S==S[::-1]`(단순 회문 검사)만 하고 **"a를 붙이는 연산 자체를 구현 안 함**" → `kasaka`에 No (정답 Yes).

### C. Input-Format Misreading
- **abc229_d**: `S, K = input().split()` — S와 K가 **다른 줄**에 있는데 한 줄로 가정 → `ValueError: not enough values to unpack`.
- **abc230_c**: `N,A,B,P,Q,R,S = map(int, input().split())` — 7값을 한 줄로 가정(실제 2줄) → 동일 예외.

### D. Inefficiency (TLE)
- **abc234_c**: K ≤ 10^18인데 1씩 증가하는 brute force → 타임아웃.

### E. Index/Boundary
- **abc230_c**: 그리드 크기·인덱스 계산이 음수/범위 밖 → `IndexError: list index out of range`.

### F. Numeric/Env Limit
- **abc235_d**: `int(str(N)+str(a))`가 4300자리 초과 → `ValueError: Exceeds the limit (4300 digits)`. 게다가 `current_value`를 갱신 안 해 루프 의미 상실.

### H. Truncated
- **abc226_c/d, abc224_d** 등: `unterminated string literal`·`invalid syntax` — `max_tokens=1024`에 코드가 중간에서 끊김.

---

## 4. 제안서 사전 5종과의 대조

| 제안서 사전 카테고리 | 본 데이터에서 | 비고 |
|---|---|---|
| **Spec-Mismatch** | **A로 확인 — 지배적** | 제안서 가설("가장 빈번") 일치. |
| **Incomplete-Logic** | **B로 확인** | 엣지/연산 누락. |
| Hallucinated-API | **미관측(0)** | gpt-3.5-turbo·경쟁프로그래밍에선 표준 라이브러리만 사용 → 환각 API 거의 없음. 다른 모델/도메인에선 재확인 필요. |
| Test-Gaming | **미관측** | sample I/O만으로는 하드코딩 탐지 불가(hidden 테스트 필요). |
| Style-Overfitting | **미관측(비효율은 D로 분리)** | TLE는 효율 문제로 별도 잡힘. |

**데이터-주도 신규**: C(입력 형식 오독), E/F(인덱스·수치·환경 한계), 그리고 프로세스 축의 **G(언어 이탈)·H(출력 잘림)** — 제안서엔 없던 축이며, 특히 **G는 무지시 프롬프트에서 가장 큰 실패원**.

---

## 5. 핵심 발견 (요약)

1. **AI 버그의 시그니처 = Spec-Misinterpretation(A)**: 문법은 멀쩡하고 실행도 되는데 *다른 문제*를 푼다. 기존 APR(문법/패턴 기반)이 못 잡는 유형 → **Spec-Grounded Repair(Phase 5)의 핵심 타겟**임을 데이터가 지지.
2. **언어 이탈(G)**: 언어 미지정 프롬프트에서 46%가 비-Python(주로 C++). 프롬프트 설계 결정 필요.
3. **Hallucinated-API는 이 설정에서 사실상 0** — 제안서 5종이 모든 맥락에 보편적이지 않음을 시사(데이터-주도 분류의 정당성).

---

## 6. 한계 (전체 연구판으로 가기 위한 조건)

- **오라클이 약함**: AtCoder **sample I/O만** 사용 → hidden 테스트로만 드러나는 버그(엣지케이스, Test-Gaming)는 "pass"로 새어나감. **ConDefects `Test.zip`(수동 다운로드)** 적용 시 A/B/엣지 비중이 늘 것.
- **표본**: 40 task / 81 버그 파일럿. 985 task 전체로 확장 시 분포 안정화.
- **언어 이탈(G)** 때문에 Python 유효 표본이 절반으로 줄어듦 → 프롬프트 결정에 따라 코퍼스 크기 달라짐.
- 인간 대조군(ConDefects faultyVersion) 비교(RQ1: 분포·FL 정확도)는 다음 단계.

> 산출물: `results/phase3_taxonomy.json`(카운트), `results/phase3_python_bugs.jsonl`(81 버그), `results/phase3_bugs_readable.txt`(전체 정독 덤프).
