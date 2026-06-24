# aitaxo — 진행 상태 (마스터 로그)

연구: AI 생성 코드 버그 Taxonomy (누수-free + 인간진정 설계). 상세 계획은 [PLANS.md](../PLANS.md).

## 데이터셋 (확정)
- **소스**: ConDefects(AtCoder), 시기 윈도우 **[2021-09 ~ 2022-11-30]** = gpt-3.5-turbo 컷오프 ↔ ChatGPT 출시 사이 → 문제는 모델 미학습(누수 X) + 인간 제출은 ChatGPT 이전(진정).
- **규모**: **428 task** (interactive 4 제외). 각 task: `data/<pid>/{problem.txt, testcases(full hidden), human, ai, meta.json}`.
- **인간 대조군**: `human/` 1,215 faulty (correct·faultLocation 포함, RQ1·FL용).
- **테스트**: ConDefects 전체 hidden 테스트(평균 ~32/task). `_h`↔AtCoder"Ex" 매핑 수정 완료.

## 생성 (gpt-3.5-turbo)
- 프롬프트: **system**("Output ONLY a Python 3 program …") + **user**(정규화 problem.txt). temp 1.0.
- 현재 **task당 10개**로 확장 중 (gen_1~5 완료, gen_6~10 생성·채점 진행 중 → taxonomy 표본 강화).

## Taxonomy (full hidden 테스트, 현재 5/task 기준)
- 채점: pass 291/2140 (**13%**) — sample 오라클(23%) 대비 보정(샘플만 통과·hidden 실패 199개 제거).
- 분포(버그 1,849): **Spec-Misinterpretation(WA) 1,430 = 77%** 지배 · TLE 244 · RE 166 · CE 9.
- 난이도: easy 45% → mid 4% → hard/vhard 0% pass.
- **Hallucinated-API ≈ 0** (ModuleNotFoundError는 sympy 등 실제 라이브러리, 환각 아님).
- → AI 버그의 시그니처 = "문법 정상·실행되나 다른 문제를 풂" → **Spec-Grounded Repair(Phase 5) 타당성**.

## Phase 상태
| Phase | 상태 |
|---|---|
| 1 substrate (data/<pid>) | ✅ 428 task |
| 2 생성 (gpt-3.5-turbo) | ✅ 5/task → ⏳ 10/task 확장 중 |
| 3 Taxonomy (open coding) | ✅ full-test 5/task → 10/task로 갱신 예정 |
| 4 APR baseline (Refactory/PaR) | ◐ Refactory 작동·어댑터 구축; ConDefects 통합 crash(하드닝 필요). PaR repo 미정 |
| 5 Spec-Grounded Repair | 미착수 |
| 6 교육 피드백 | 미착수 |

## 산출물
- 보고서: [window_taxonomy.md](window_taxonomy.md)(현재 full-test), [phase3_taxonomy.md](phase3_taxonomy.md)(카테고리 정의·예시), [phase4_status.md](phase4_status.md)
- 데이터(요약): `fulltest_summary.json`, `fulltest_taxonomy.json`
- 코드: `scripts/`(extract_window, window_generate, materialize_fulltests, rejudge_fulltest, fix_ex_and_rejudge, generate_more, phase4_refactory_adapter)
- 대용량 코퍼스(`*.jsonl`)·`data/`(15GB 테스트)·`tools/`는 gitignore (재생성 가능)

## git
- 연결: https://github.com/dwchoi95/aitaxo — 의미 있는 마일스톤마다 커밋.

## 다음
- gen2(10/task) 완료 → taxonomy 재집계.
- RQ1: 인간(1,215) vs AI 분포·FL 비교.
- Phase 4: PaR repo 확정 + Refactory Docker 하드닝.
