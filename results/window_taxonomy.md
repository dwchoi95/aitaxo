# Full-Window AI 버그 Taxonomy — gpt-3.5-turbo × ConDefects [2021-09~2022-11]

> **확정 설정으로 전체 윈도우 실행.** 누수-free(gpt-3.5-turbo 컷오프 Sep 2021) + 인간진정(ChatGPT 이전) 겹치는 구간.
> 프롬프트: **system**("Output ONLY a complete Python 3 program …") + **user**(정규화된 problem.txt). temp 1.0, n=5.
> 채점 오라클: AtCoder **sample I/O**(정규화 스크레이핑). 전체 hidden 테스트는 `Test.zip` 필요(한계).

## 규모
- **428 / 432 task** 생성 완료(4개 sample 0 — interactive류 제외), **2,140 생성**(428×5).
- 인간 대조군 준비됨: `data/<pid>/human/` **1,215 faulty**(ConDefects, 누수-free·인간진정).

## 0. 프롬프트 정책 효과 — 언어 이탈 완전 해소

| | 현행("problem.txt만", 파일럿) | **확정(system+user, 전체)** |
|---|---|---|
| Python 비율 | 54% (C++ 24%·기타 22%) | **100% (2140/2140)** ✅ |
| compile_error | 95(대부분 C++ 오판) | **9**(실제 잘림만) |

→ system 1줄로 C++ 이탈이 **0**이 되어, 버그 코퍼스가 전부 **진짜 Python 버그**로 정제됨.

## 1. 채점 결과 + 난이도 구배

| 난이도(AtCoder diff) | 생성 | pass | pass율 | 버그 |
|---|---|---|---|---|
| easy (<400) | 600 | 310 | **51%** | 290 |
| mid (400–1200) | 520 | 95 | 18% | 425 |
| hard (1200–2000) | 445 | 33 | 7% | 412 |
| vhard (≥2000) | 575 | 52 | 9% | 523 |
| **합계** | **2,140** | **490 (23%)** | — | **1,650** |

난이도 오를수록 pass↓ — 정상 구배. 버그 1,650개가 전 난이도에 고루 분포.

## 2. 창발 Taxonomy 분포 (Python 버그 1,650)

| 카테고리 | 수 | 비율 |
|---|---|---|
| **A/B Spec-Misinterpretation·Incomplete (WA)** | **1,315** | **80%** |
| F Numeric/Env Limit (RE) | 151 | 9% |
| D Inefficiency/Complexity (TLE) | 122 | 7% |
| E Index/Boundary (RE) | 45 | 3% |
| H Truncated/Malformed (CE) | 9 | 0.5% |
| C Input-Format Misreading (RE) | 8 | 0.5% |

RE 예외 세부: IndexError 45 · ValueError 20 · TypeError 13 · ModuleNotFoundError 5 · MemoryError 4 · NameError 4.

## 3. 핵심 발견

1. **Spec-Misinterpretation이 압도적(80%)** — 파일럿(40 task)에서 본 패턴이 **428 task / 1,650 버그 규모에서 강하게 재확인**. AI 버그의 시그니처는 "문법 정상·실행되나 *다른 문제*를 풂". 기존 문법/패턴 기반 APR이 약한 유형 → **Spec-Grounded Repair(Phase 5)의 타당성을 대규모로 지지**.
2. **Hallucinated-API ≈ 0 (진짜 환각은 없음)** — `ModuleNotFoundError`는 **`sympy`(8)·`sortedcontainers`(1)** 로, *환각이 아니라 AtCoder엔 설치돼 있고 우리 샌드박스엔 없는 실제 라이브러리*. → **채점 환경 아티팩트**(아래 한계). 제안서 사전 5종 중 Hallucinated-API는 이 설정에서 사실상 부재.
3. **프롬프트 정책 검증** — "Python 3로 작성" 1줄이 코퍼스 순도를 54%→100%로. 확정 채택.

## 4. 제안서 사전 5종 대조

| 사전 | 데이터 | 비고 |
|---|---|---|
| Spec-Mismatch | **A — 80% 지배** | 가설 강하게 일치 |
| Incomplete-Logic | B(WA 일부) | |
| Hallucinated-API | **≈0** | 이 모델·도메인엔 부재 |
| Test-Gaming | 미관측 | sample만으론 탐지 불가(hidden 필요) |
| Style-Overfitting | D로 분리(비효율) | |
| (신규) Input-Format/Index/Numeric-Env | C·E·F | 데이터-주도 추가 축 |

## 5. 한계 (수치의 성격)
- **오라클이 sample I/O뿐**(Test.zip 미확보) → 엣지케이스·Test-Gaming은 새어나감. 실제 버그율은 *하한*. hidden 테스트 적용 시 WA(A/B) 비중 더 증가 예상.
- **샌드박스 라이브러리 부재** → sympy/sortedcontainers 사용 코드가 거짓 RE(13건+). 샌드박스에 sympy·sortedcontainers·numpy 설치 시 RE 일부가 pass/WA로 재분류됨(소수).
- 4개 task 제외(sample 0, interactive류).

## 6. 다음 (RQ1)
인간 대조군 `data/<pid>/human`(1,215 faulty, 동일 428 문제, 누수-free·인간진정) 준비 완료 → **AI vs 인간 버그 분포 비교(χ²)·FL 정확도**(`faultLocation.txt`) 분석 가능.

> 산출물: `results/window_generations.jsonl`(2,140), `window_failures.jsonl`(1,650), `window_python_bugs.jsonl`, `window_taxonomy.json`, `window_summary.json`. 코드/생성물: `data/<task>/{problem.txt,testcases,ai/gen_*.py,ai/results.json}`.
