# AI 버그 Taxonomy (최종) — gpt-3.5-turbo × ConDefects [2021-09~2022-11]

> 누수-free(gpt-3.5-turbo 컷오프 Sep 2021) + 인간진정(ChatGPT 이전) 겹치는 구간.
> 프롬프트: system("Output ONLY a Python 3 program …") + user(정규화 problem.txt). temp 1.0.
> 채점: ConDefects **전체 hidden 테스트**(평균 ~32/task). **428 task × 10 생성 = 4,280**.

## 1. 채점 (full hidden tests, 10/task)
| | 수 | |
|---|---|---|
| 생성 | 4,280 | 100% Python |
| pass | 589 | **13.8%** |
| **버그** | **3,691** | |

난이도 pass율: easy **45.8%** → mid 3.7% → hard **0%** → vhard **0%**. (gpt-3.5-turbo는 hidden 기준 쉬운 문제만 절반 정도 통과.)

## 2. 카테고리 분포 (버그 3,691)
| 카테고리 | 수 | 비율 |
|---|---|---|
| **A/B Spec-Misinterpretation·Incomplete (WA)** | **2,808** | **76%** |
| D Inefficiency/Complexity (TLE) | 504 | 14% |
| RE (Index/Input-format/Numeric·Env) | 338 | 9% |
| H Truncated/Malformed (CE) | 41 | 1% |

**WA(Spec-Misinterpretation) 하위분류** — `correct.py` 대조 개방코딩 → 5유형(S1 출력단순화 · S2 핵심조건 단순화 · S3 잘못된 알고리즘/공식 · S4 패러다임 미인식 · S5 엣지/언어의미). 상세·예시: [spec_subtaxonomy.md](spec_subtaxonomy.md).

## 3. ★ 체계성 (Systematicity) — 핵심 정량 결과
한 문제에 대한 10개 생성의 버그가 **같은 실패 유형으로 수렴하는가**:

| 지표 | 값 |
|---|---|
| 평균 modal-share (버그 중 최빈 카테고리 비율) | **0.845** |
| 완전 일치 문제 비율 (모든 버그 동일 카테고리) | **38.8%** |
| 평균 정규화 엔트로피 (0=완전체계) | 0.43 |
| modal-share=1.0 문제 수 | 150 / 387 |

→ **AI 버그는 무작위가 아니라 문제별로 체계적**(coarse 기준 84.5% 수렴; WA 하위유형 기준은 더 강함 — §B 사례). = "명세 한 곳을 바로잡으면 그 문제 다수 오답이 일괄 수리"라는 **Spec-Grounded Repair(Phase 5)의 직접 근거.**

## 4. 핵심 발견
1. **Spec-Misinterpretation 지배(76%)** + **체계적**(modal-share 0.845) → 문법/패턴 APR이 약한, 명세-기반 수리가 필요한 유형. 대규모·엄격채점으로 입증.
2. **Hallucinated-API ≈ 0** — ModuleNotFoundError는 sympy 등 실제 라이브러리(샌드박스 부재), 환각 아님. → 제안서 사전 5종이 보편적이지 않음(데이터-주도 분류 정당).
3. **프롬프트**: "Write a Python 3 solution" 1줄 → 100% Python(없으면 C++ 이탈 46%).
4. **sample 오라클 위험**: pass를 23%로 과대평가(full-test 13.8%) → 전체 테스트 필수.
5. **질적 대조**: AI 코드는 장황·"그럴듯한데 틀림"(문법·실행 정상), 인간 정답은 간결.

## 5. 데이터셋 무결성
- `_h`↔AtCoder"Ex" 매핑 수정(22 task full test 복구), interactive 4 제외 → **428 task** 전부 full hidden 테스트.
- 인간 대조군 `data/<pid>/human/` **1,215 faulty**(correct·faultLocation 포함).

## 6. 한계 / 다음
- 한계: AtCoder special-judge(다중정답) 일부 오판 가능(소수); 샌드박스 라이브러리 부재로 sympy 거짓 RE(설치로 완화).
- 다음: WA 하위유형 **규모 라벨링**(자동신호+LLM보조+사람검증, 2인 κ) → 하위유형별 분포·난이도 교차표; **RQ1** 인간(1,215) vs AI χ²·FL 비교.

> 산출물: `consistency.json`, `fulltest_summary.json`, `spec_subtaxonomy.md`, `wa_opencoding.txt`, `data/<task>/{problem.txt,testcases(full),human,ai/gen_1..10.py}`.
