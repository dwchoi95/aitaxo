# aitaxo — Phase 0–4 실행 로그 (결과 마스터)

> 실행: PLANS.md(ConDefects 기반) 대로 Phase 0–4. 데이터 누수 회피용 `gpt-3.5-turbo`(컷오프 Sep 2021) + ConDefects(AtCoder Oct 2021–Sep 2023).
> **파일럿 규모**: 난이도 층화 **40 task / 200 생성**. 채점 오라클 = AtCoder **sample I/O**(전체 hidden 테스트 `Test.zip` 미확보 — 한계).

## 전제 확인
- ✅ `gpt-3.5-turbo` 2026년에도 API 사용 가능(현행=`-0125`, 컷오프 Sep 2021). 누수-free 성립.
- ✅ ConDefects clone(`aria/data/ConDefects`, 985 Python tasks).
- ⚠ **공백①(명세)**: CodeNet 기각(2016–2020 only, ConDefects는 2021+ → 0 매칭) → **AtCoder 스크레이핑**으로 해결.
- ⚠ **공백②(테스트)**: `Test.zip` OneDrive 자동 다운로드 401 → **sample I/O로 대체**(수동 다운로드 필요).

## Phase별 결과

| Phase | 상태 | 핵심 산출물 |
|---|---|---|
| 0 하네스 | ✅ | `src/aitaxo/execution/runner.py`로 채점(subprocess, 5s) |
| 1 substrate | ✅ | `data/raw/<task>/` 40개: problem.txt(AtCoder), meta.json, testcases/(sample), human/(faulty+correct+faultLocation). `data/raw/manifest.json` |
| 2 생성 | ✅ | `gpt-3.5-turbo` temp 1.0 ×5 = 200. `results/phase2_*.jsonl/json` |
| 3 Taxonomy | ✅ | 데이터-주도 개방코딩 → `results/phase3_taxonomy.md` (+json, bugs) |
| 4 APR baseline | ◐ 부분 | Refactory 작동 검증 + 26q 입력 어댑터 구축; ConDefects 실행은 crash(하드닝 필요). PaR repo 미확정. `results/phase4_status.md` |

## Phase 2 채점 분포 (200 생성)
- 언어: **Python 108 / C++ 47 / 기타 45** → **비-Python 46%**(프롬프트 "problem.txt만"의 부작용; 언어 미지정 → C++ 이탈).
- Python 111 판정: pass 30, **실패(AI 버그) 81**.

## Phase 3 — 창발 Taxonomy (Python 버그 81)
| 카테고리 | 수 |
|---|---|
| A Spec-Misinterpretation (명세 오해) — *지배적* | 45(WA) 중 대다수 |
| B Incomplete-Logic | 45(WA) 중 일부 |
| C Input-Format Misreading | 4 |
| D Inefficiency/TLE | 14 |
| E Index/Boundary | 5 |
| F Numeric/Env Limit | 4 |
| H Truncated output(CE) | 9 |
| (G Wrong-Language, 생성 아티팩트) | 47+ |

**핵심 발견**: ① AI 버그의 시그니처는 **Spec-Misinterpretation**(문법 정상·실행되나 *다른 문제*를 풂) → 기존 APR이 약한 유형 = Spec-Grounded Repair(Phase 5) 타당성. ② **Hallucinated-API ≈ 0**(제안서 5종이 보편적이지 않음 → 데이터-주도 분류 정당). ③ 언어 이탈(C++) 46% — 프롬프트 결정 포인트.

## 산출물 위치
- 데이터: `data/raw/` (40 task), `data/raw/manifest.json`
- 생성/채점: `results/phase2_generations.jsonl`(200), `phase2_failures.jsonl`, `phase2_summary.json`, `phase2_log.txt`
- Taxonomy: `results/phase3_taxonomy.md`, `phase3_taxonomy.json`, `phase3_python_bugs.jsonl`(81), `phase3_bugs_readable.txt`(정독 덤프)
- APR: `results/phase4_status.md`, `tools/refactory/`(패치·어댑터), `tools/refactory/data_condefects/`(26q)
- 코드: `scripts/phase1_build_raw.py`, `phase2_generate.py`, `phase4_refactory_adapter.py`

## 미해결(사용자/리소스 필요)
1. **ConDefects `Test.zip`** 수동 다운로드(OneDrive/Baidu) → sample I/O를 hidden 테스트로 교체(과학적 완전판). 현 모든 수치는 sample 기준 하한.
2. **프롬프트 정책**: "problem.txt만" 유지(언어 이탈 46% 수용) vs "Write a Python 3 solution" 1줄 추가(Python 버그에 집중).
3. **PaR repo 확정**(저자·URL·언어).
4. **Refactory 정량화**: 공식 Docker(Python3.7) 또는 reference 정규화 어댑터로 crash 해결 후 pass@1.
5. **전체 985 task 확장**(현재 40 파일럿).
