# Full-Test AI 버그 Taxonomy — gpt-3.5-turbo × ConDefects [2021-09~2022-11]

> 누수-free(gpt-3.5-turbo 컷오프 Sep 2021) + 인간진정(ChatGPT 이전) 겹치는 구간.
> 프롬프트: **system**("Output ONLY a complete Python 3 program …") + **user**(정규화 problem.txt). temp 1.0, n=5.
> 채점 오라클: **ConDefects 전체 hidden 테스트**(평균 ~32개/문제; `_h`↔AtCoder "Ex" 매핑 포함). interactive 4문제 제외.

## 규모
- **428 task / 2,140 생성** (gpt-3.5-turbo). 100% Python(system 프롬프트로 C++ 이탈 제거).
- 인간 대조군: `data/<pid>/human/` **1,215 faulty**(ConDefects, 누수-free·인간진정, faultLocation 포함).

## 1. 채점 결과 (full hidden tests)

| | sample 오라클 | **full hidden (확정)** |
|---|---|---|
| pass | 490 (23%) | **291 (13%)** |
| wrong_answer | 1,315 | 1,430 |
| timeout | 122 | 244 |
| runtime_error | (혼재) | 166 |
| compile_error | 9 | 9 |
| **버그 합** | — | **1,849** |

→ **샘플만 통과하고 hidden에서 떨어진 199개**가 보정됨(과대평가 제거). 큰 입력이 드러내는 TLE도 122→244로 2배.

### 난이도 구배 (full-test pass율)
| 난이도(AtCoder diff) | 생성 | pass | pass율 |
|---|---|---|---|
| easy (<400) | 600 | 270 | **45%** |
| mid (400–1200) | 520 | 21 | 4% |
| hard (1200–2000) | 445 | 0 | **0%** |
| vhard (≥2000) | 575 | 0 | **0%** |

gpt-3.5-turbo는 hidden 테스트 기준 **쉬운 문제만(그것도 <50%)** 통과 — 난이도 오르면 사실상 0%.

## 2. 창발 Taxonomy (버그 1,849)

| 카테고리 | 수 | 비율 |
|---|---|---|
| **A/B Spec-Misinterpretation·Incomplete (WA)** | **1,430** | **77%** |
| D Inefficiency/Complexity (TLE) | 244 | 13% |
| RE (Index/Input-format/Numeric·Env) | 166 | 8% |
| H Truncated/Malformed (CE) | 9 | 0.5% |

> RE 세부(IndexError·입력형식·sympy 등)는 sample-단계 분석 참조(§아래). full-test 재채점 레코드엔 stderr 미보유라 status-level로 집계.

## 3. 핵심 발견

1. **Spec-Misinterpretation이 압도적(버그의 77%)** — full hidden 테스트로 보정하니 *더 선명*. AI 버그의 시그니처는 "문법 정상·실행되나 *다른 문제*를 풂". 문법/패턴 기반 기존 APR이 약한 유형 → **Spec-Grounded Repair(Phase 5) 타당성을 대규모·엄격 채점으로 지지.**
2. **sample 오라클은 위험** — pass를 23%→13%로 과대평가했고, hidden에서만 드러나는 버그(특히 엣지·TLE)를 놓쳤음. **전체 테스트 필수**임을 데이터가 입증.
3. **Hallucinated-API ≈ 0** — `ModuleNotFoundError`는 환각이 아니라 sympy/sortedcontainers(실제 라이브러리, 샌드박스 부재). 제안서 사전 5종이 모든 설정에 보편적이지 않음 → 데이터-주도 분류 정당.
4. **100% Python** — "Write a Python 3 solution" system 1줄이 코퍼스 순도를 54%→100%로.

## 4. 데이터셋 무결성 (이번 정리)
- **`_h`↔"Ex" 매핑 수정**: AtCoder가 ABC 마지막 문제를 "Ex"로 표시 → 22개 `_h` task의 full test를 `Test/<contest>/Ex/`에서 복구(누락 아님). 이제 **428 task 전부 full hidden 테스트**.
- **interactive 4문제 제외**(abc244_c, abc269_e, abc278_g, arc142_c): stdin/stdout 채점 불가.

## 5. 한계
- AtCoder special-judge(다중 정답) 문제는 exact 비교라 일부 오판 가능(소수).
- 샌드박스 라이브러리 부재로 sympy 등 거짓 RE 잔존(소수; sympy/sortedcontainers는 설치함).

## 6. 다음 (RQ1)
인간 대조군 `data/<pid>/human`(1,215 faulty, 동일 428문제, 누수-free·인간진정, `faultLocation.txt`) → **AI vs 인간 버그 분포(χ²)·FL 정확도** 비교 준비 완료.

> 산출물: `results/fulltest_summary.json`, `fulltest_taxonomy.json`, `fulltest_generations.jsonl`(2,140, gitignored), `data/<task>/{problem.txt,testcases(full),human,ai}`.
