# PLANS.md — aitaxo 개발 계획

`T3_AI-Generated-Code-Aware_APR.md`(ICSE 2027) 목표를 코드로 실현하기 위한 단계별 개발 계획.
연구 논리(가설 → Taxonomy → baseline gap → 새 수리법)와 코드 구현을 1:1로 매핑한다.

> **읽는 법**: 각 Phase는 `목표 / 매핑(RQ·기여) / 산출물 / 신규 모듈 / 데이터 / CLI / 완료 기준 / 리스크` 순서.
> 프롬프트·라벨링 루브릭·피드백 템플릿은 **한국어 원문 보존**(working-language 규약).

---

## 데이터 소스 결정 (확정: ConDefects)

**데이터 누수(leakage)가 핵심 제약이다.** 생성 모델을 **`gpt-3.5-turbo`(지식 컷오프 2021-09-01)**로 고정하므로, 평가용 문제는 **그 컷오프 이후**에 출제되어 모델이 학습하지 못한 것이어야 한다. CodeNet·Codeforces는 이 구간 데이터가 사실상 없으므로 폐기하고, **[ConDefects](https://github.com/appmlk/ConDefects)** 를 substrate로 쓴다.

ConDefects는 바로 이 누수 문제를 위해 설계된 데이터셋:

- **AtCoder Oct 2021 – Jun 2024** 문제(전체 985 Python tasks / 2,864 faulty). 컷오프 이후 → `gpt-3.5-turbo`에 누수 없음.
- 각 프로그램이 **수정본(correct) + 버그본(faulty) + fault location** 쌍으로 제공 → 인간 버그 대조군·APR ground truth·FL 정답을 공짜로 얻음(`--language python`, Java 제외).

### ⏱ 시기 윈도우 결정 (확정: 2021-09 ~ 2022-11-30, "ChatGPT 이전")

**두 제약이 서로 다른 데이터에 걸린다.** ① *데이터 누수*는 "AI가 생성할 문제"에 걸리고(문제가 모델 컷오프 *이후*여야 함), ② *인간 진정성*은 "인간 대조군"에 걸린다(인간 제출이 LLM 대중화 *이전*이어야 함). 두 컷오프가 다르므로 그 사이에 **둘 다 만족하는 겹치는 구간**이 존재한다:

- gpt-3.5-turbo 지식 컷오프 = **2021-09**
- ChatGPT 출시(학생 AI 제출 급증 분기점) = **2022-11-30**

→ **ConDefects를 contest date ∈ [2021-09, 2022-11-30] 로 제한** → 문제는 모델이 못 봤고(누수 X) + 인간 제출은 진짜 인간(ChatGPT 이전) + **같은 문제셋**이라 RQ1 paired 비교 유효.

**실측 가용량(`date.txt` 기준)**:

| 구간 | Python tasks | human faulty |
|---|---|---|
| **[2021-09 ~ 2022-11-30] (확정)** | **432** | **1,215** |
| (참고) 더 보수적 [~2022-06, Copilot GA 이전] | 236 | 657 |
| (참고) 전체 | 985 | 2,864 |

> **잔여 한계(명시)**: ConDefects는 *문제 출제일*은 주지만 *개별 제출 시각*은 없음 → 인간 진정성은 "컨테스트가 ChatGPT 이전" 프록시에 의존(옛 문제에 2023+ AI 재제출 소수는 잔존 가능). contest-date 프록시는 통상 수용됨. airtight하게는 AtCoder 제출시각 교차확인 필요(향후).
>
> **하이브리드 옵션**: taxonomy 자체는 인간 대조군이 불필요 → AI 생성·taxonomy는 전체 985(전부 누수-free)로 키우고, **AI vs 인간 paired 비교(RQ1)만 432-구간**으로 제한할 수도 있음. 기본은 단순히 전 파이프라인을 432-구간으로 통일.

### ConDefects 구조 (실측)

```
ConDefects/                       (git clone)
├── Code/<task>/Python/<subId>/   # 예: Code/abc221_f/Python/40898300/
│     ├── correctVersion.py       # 인간 정답(수정본)  — 레퍼런스/oracle
│     ├── faultyVersion.py        # 인간 버그본        — 인간 대조군
│     └── faultLocation.txt       # 버그 위치(라인)    — FL 정답(RQ1)
├── ConDefects.py                 # checkout / run / coverage / info 도구
├── Tool/RunTest.py
├── date.txt                      # task별 출제일
├── difficulty.txt                # task별 난이도
└── (Test.zip)                    # ⚠ repo에 없음 — OneDrive/Baidu 별도 다운로드
```

task 이름 = AtCoder id (`abc221_f` = ABC221 problem F). 985개가 Python 보유.

### ⚠ 두 가지 공백 (반드시 메울 것)

1. **문제 설명(problem.txt)이 repo에 없음** — ConDefects는 코드·테스트만 제공, 자연어 명세는 없음.
   → task id로 **AtCoder에서 영어 명세를 스크레이핑** (`https://atcoder.jp/contests/<contest>/tasks/<task>`). 생성·Spec-Grounded·피드백의 입력이 되므로 필수.
   > **CodeNet으로 대체 시도 → 기각**: `aria/data/Project_CodeNet`에 AtCoder 문제 1,519개가 있으나 **2016–2020(ABC042·AGC001까지)** 뿐. ConDefects는 **Oct 2021 이후**(abc221+)라 `abc221/arc128/agc055` 검색 시 **0 hits**. 두 코퍼스는 시기상 배타적(그게 ConDefects의 누수-free 설계의 본질) → CodeNet은 명세 소스가 될 수 없음. CodeNet의 `atcoder_test_cases.zip`도 같은 이유로 공백②의 대체 불가.
2. **테스트가 repo에 없음** — `Test.zip`(대용량)을 **OneDrive/Baidu에서 직접 다운로드**해 구축.
   → 해제 후 `data/raw/<task>/testcases/`로 물질화해 우리 runner가 직접 채점(AI·인간·수리 일관 채점). 필요 시 `ConDefects.py run`으로 교차검증.

> **AtCoder 특수 판정(special judge)·부동소수 허용오차 문제**: 일부 task는 exact 비교가 틀림 → meta에 표시·채점 분기 또는 제외(Codeforces의 checker 이슈와 동일 성격).

---

## 생성 모델 결정 (확정)

| 항목 | 값 |
|---|---|
| 모델 | **`gpt-3.5-turbo`** (컷오프 2021-09-01 → ConDefects에 누수 없음) |
| temperature | **1.0** |
| task당 생성 수 | **5개** |
| 프롬프트 | **`problem.txt` 내용만** (추가 지시·few-shot·시스템 프롬프트 장식 없음) |

> **가용성 확인됨(2026-06)**: `gpt-3.5-turbo` 패밀리는 API에서 여전히 사용 가능(현행 alias = `-0125`, 지식 컷오프 Sep 2021). 구형 스냅샷 `-0613`만 은퇴. 재현성 위해 응답의 실제 snapshot(`response.model`)을 레코드에 기록.

---

## 설계 원칙 (전 Phase 공통)

1. **Schema-first** — 레코드가 백본. Phase마다 *덮어쓰지 않고 필드를 덧붙임*(`generation` → `label` → `constraints` → `repairs` → `feedback`). 단일 정의 `src/aitaxo/dataset/schema.py`.
2. **Leakage-free 불변식** — 평가 문제는 항상 모델 컷오프 이후. 모델 변경 시 이 불변식 재검증.
3. **Reproducibility** — 모든 LLM 호출은 `model·snapshot·temperature·prompt·raw_response·tokens` 기록. 스크레이핑·다운로드는 멱등·재개 가능.
4. **2-oracle 분리** — "테스트 통과" ≠ "명세 준수"(Phase 5). 스키마에서 `execution`과 `constraint_check` 분리.
5. **외부 도구는 adapter로** — Refactory/PaR는 우리 코드가 아니다. thin adapter로 감싸고 버전·커밋 고정.

---

## 통합 데이터 스키마

`dataset/schema.py`의 `Sample` — Phase마다 필드 추가. **append-only**.

```python
Sample
  task_id                       # AtCoder id, 예 "abc221_f"
  source = "condefects"
  origin: "ai" | "human"        # human = ConDefects faultyVersion (누수-free 대조군)
  statement                     # problem.txt (AtCoder 스크레이핑)
  code                          # 생성/제출 코드 (버그본)
  tests: [TestCase]             # ConDefects Test.zip
  execution: ExecutionReport    # test-oracle 결과
  fault_location: [int]|None    # human=faultLocation.txt; ai=테스트/명세로 추정(선택)
  reference_fix: str|None       # human=correctVersion.py (APR ground truth)
  generation: Generation|None   # ai: {model:"gpt-3.5-turbo", snapshot, temperature:1.0, sample_idx∈1..5, tokens, raw}
  label: Label|None             # Phase 3: 데이터-주도 카테고리(아래)
  constraints: ConstraintSpec|None         # Phase 5a
  constraint_check: ConstraintReport|None  # Phase 5b
  repairs: [RepairAttempt]      # Phase 4·5: {tool, code, execution, constraint_check}
  feedback: str|None            # Phase 6
  meta: {contest, difficulty, date, atcoder_url, has_special_judge}
```

---

## Phase 0 — 실행 하네스 & 하드닝 (스케일 전 선결)

**목표**: 생성·인간·수리 코드를 동일 기준으로 채점하는 신뢰성 있는 샌드박스.

**작업**
- **샌드박스**: `execution/runner.py`(기존 subprocess) 위에 per-task 자원 한도 + 네트워크 차단. 대량 실행 시 `docker_runner.py`(컨테이너·FS read-only). 무한루프·악성 생성 방지.
- **ConDefects 테스트 채점**: `data/raw/<task>/testcases/`를 우리 runner로 채점(AI·human·repair 일관). 또는 `ConDefects.py run` 위임 — **runner 직접 채점을 기본**으로(스키마 일관). special judge task는 meta 표시·분기.
- **재개·멱등**: 생성·실행 중단 후 이어서.
- **비용 가드**: `--dry-run`, `--max-cost-usd`(gpt-3.5-turbo는 저렴하나 가드 유지).
- **스키마 승격**: `dataset/schema.py` dataclass화 + `dataset_version`.

**완료 기준**: 한 task의 인간 faulty/correct를 ConDefects 테스트로 채점한 결과가 ConDefects 도구 결과와 일치(채점기 검증). 무한루프 코드가 호스트에 영향 0.

**리스크**: special judge·부동소수 task → exact 비교 오판. meta로 격리.

---

## Phase 1 — ConDefects substrate 추출 (`data/raw/` 구축)

**목표**: ConDefects Python **432 task**(시기 윈도우 [2021-09~2022-11])를 task별 디렉터리로 물질화(명세·테스트·인간 버그·FL 정답).

**매핑**: 기여 ⑤(데이터셋), RQ1·RQ2 substrate.

### 산출 디렉터리 레이아웃
```
data/raw/<task>/                   # 예: abc221_f
├── problem.txt        # AtCoder 영어 명세 (스크레이핑)  [공백①]
├── meta.json          # contest, atcoder_url, date(date.txt), difficulty(difficulty.txt),
│                      #   n_human_faulty, n_tests, has_special_judge
├── testcases/         # Test.zip → 물질화  [공백②]
│   ├── <name>/in.txt   <name>/out.txt
│   └── ...
├── human/             # ConDefects 인간 프로그램 (누수-free 대조군)
│   └── <subId>/faulty.py  correct.py  faultLocation.txt
└── generated/         # Phase 2 AI 버그
    └── gpt-3.5-turbo/<1..5>.py
data/raw/manifest.json  # task 목록 + 출처(commit), 다운로드·스크레이핑 파라미터
```

### 추출 파이프라인 (`dataset/build_raw.py`)
1. **ConDefects clone** + `Test.zip` 다운로드(OneDrive/Baidu) 해제.
2. **Python task 선별 + 시기 윈도우**: `Code/<task>/Python/` 존재 **AND** `date.txt`의 contest date ∈ **[2021-09-01, 2022-11-30]** → **432 task**(누수-free + 인간진정 겹치는 구간, 위 결정).
3. **인간 프로그램 복사**: `correctVersion.py`/`faultyVersion.py`/`faultLocation.txt` → `human/<subId>/`.
4. **테스트 물질화**: `ConDefects.py info --test-cases` / 압축 해제 → `testcases/<name>/{in,out}.txt`.
5. **명세 스크레이핑**(`problems/atcoder.py`): task→contest 매핑으로 AtCoder 문제 페이지 fetch → 영어 statement 추출 → `problem.txt`. (rate-limit 준수·캐시·재시도; ToS는 ConDefects와 동일한 연구목적 fair-use 범위.)
6. **meta**: date.txt·difficulty.txt 병합, special judge 여부 추정.
7. **manifest**: 재현용 기록.

### 신규 모듈
- `dataset/build_raw.py` — 위 파이프라인.
- `problems/condefects.py` — ConDefects repo/Test.zip 로더.
- `problems/atcoder.py` — 명세 스크레이퍼(BeautifulSoup; en 우선).
- `problems/local.py` — `data/raw/<task>/` → `Problem`(statement=problem.txt, tests=testcases/) 로더. **생성·실행은 이 로컬 디렉터리만 읽음**.

### CLI
`build-raw` (clone·다운로드·스크레이핑·물질화) · `inspect-raw --limit 3`(API 불필요)

**완료 기준**: `data/raw/`에 **432개** task(전부 contest date ∈ 윈도우), 각각 `problem.txt` + ≥1 testcase + ≥1 `human/*/faulty.py`. 인간 faulty가 ConDefects 테스트에서 실제로 실패함을 검증(데이터 정합성).

**리스크**: ① AtCoder 스크레이핑 rate-limit·페이지 구조 변동 → 캐시·재시도·간격. ② Test.zip 대용량·미러 만료 → 로컬 보관·체크섬. ③ 일부 task 명세 누락 → manifest에 누락 기록(silent drop 금지).

---

## Phase 2 — `gpt-3.5-turbo` 생성 (연구 step ①, 기여 ⑤)

**목표**: 누수-free task에 `gpt-3.5-turbo`로 코드 생성 → 실패 코드 = AI 버그 코퍼스. 인간 대조군은 이미 `human/`.

**생성 설정(확정)**: model `gpt-3.5-turbo`(snapshot pin) · temperature **1.0** · task당 **5개** · 프롬프트 = **`problem.txt` 내용만**.

**신규/수정 모듈**
- `generation/openai_client.py`(기존) — `gpt-3.5-turbo` + temp 1.0 + n=5. 프롬프트는 problem.txt 그대로(시스템 프롬프트 장식 없음). 5개 각각 record.
- `generation/base.py` — provider 인터페이스(차후 멀티-프로바이더 확장 여지, 현재는 OpenAI만).
- `pipeline.py` — `problems/local.py`로 432 task 순회 → 5× 생성 → Phase 0 샌드박스로 `testcases/` 채점 → 실패 record 적재.

**CLI**: `generate --model gpt-3.5-turbo --n 5 --temperature 1.0` (입력 data/raw, 기본 실패만 저장).

**완료 기준**: 432×5 생성 record + task별 pass/fail 분포. 실패 코드가 AI 버그 코퍼스로 적재되고, 동일 task 인간 faulty(누수-free·인간진정)와 짝지어짐.

**리스크**: ① `gpt-3.5-turbo` 폐기 시 전체 설계 흔들림(Open decisions #1). ② problem.txt만 주면 코드블록 외 잡담을 줄 수 있음 → `_extract_code`가 처리(그래도 추출 실패율 모니터; 지시 추가는 사용자 합의 후).

---

## Phase 3 — Taxonomy (데이터-주도, RQ1 / 기여 ①②)

**목표**: AI 생성 버그를 **사전 카테고리 없이** 분석해 **창발적(open-coding) 분류 체계**를 도출. **카테고리 개수 미고정** — 데이터를 보고 적절히 군집화.

**접근 (grounded / open coding)**
1. Phase 2의 실패 코드 + 명세 + 테스트 diff + (인간 correctVersion과의 차이)를 증거로 수집.
2. **분석자가 직접** 각 버그의 근본 원인을 개방 코딩 → 반복적으로 유사 코드를 병합 → 카테고리 창발.
3. 제안서의 5종(Spec-Mismatch 등)은 **사전(prior)으로만** 참조·대조하되, 최종 분류는 데이터에서 나온 것을 따른다(개수·이름 모두).
4. 신뢰도: 2인 독립 라벨 + Cohen's κ, 불일치 중재(RQ1 신뢰성). κ는 *확정된* 카테고리 위에서 측정.

> **이 Phase의 산출물(실제 카테고리)은 Phase 2의 생성 데이터가 있어야 만든다.** 데이터가 모이면 분석자가 분류 결과를 직접 보고한다(현 시점에 카테고리를 지어내지 않음).

**신규 모듈**
- `taxonomy/code.py` — 개방 코딩 세션 저장(증거·잠정 코드·병합 이력).
- `taxonomy/kappa.py` — Cohen's κ·혼동행렬.
- `taxonomy/compare.py` — AI vs 인간(ConDefects faulty) 분포 χ², **FL 정확도**(faultLocation.txt 활용), 수리 용이성 비교(RQ1).

**완료 기준**: 데이터에서 창발한 카테고리 집합 + 정의·대표 예시 3~5개/카테고리 + κ 리포트 + AI/인간 비교표.

**리스크**: 카테고리 불안정 → 라운드 반복·정의 문서화. 제안서 5종과 어긋나면 *데이터 우선*으로 보고(논문에서 차이를 논의).

---

## Phase 4 — APR baseline (RQ2, 기여 ②) — 공개 코드 도구만

**목표**: **공개 소스**가 있는 APR 도구로 AI 버그 수리율을 측정해 gap을 정량화. 사용 도구는 **Refactory · PaR** (FastFixer/PyDex/CREF는 이번 범위 제외).

> **Refactory·PaR는 데이터셋이 아니라 실행 도구(수리 방법론)다.** GitHub에서 *도구 자체*를 clone해 우리 AI 버그에 돌린다. (로컬 `aria/data/Refactory/question_{1..5}/`는 Refactory **논문의 벤치마크 데이터셋**일 뿐 — 도구가 아님. 도구 동작 sanity-check 용도로만 참고 가능.)

**도구**
- **Refactory** ([github.com/githubhuyang/refactory](https://github.com/githubhuyang/refactory)) — Python 입문 프로그래밍 APR(블록 기반 합성). 교육 맥락·Python·공개 코드로 최적. 입력: (buggy program, 테스트, 정답 풀이 풀). → ConDefects task(버그본 + `testcases/` + `correctVersion.py`)를 Refactory가 기대하는 입력으로 변환하는 어댑터 필요.
- **PaR** — 공개 repo 확정 후 어댑터(언어·입력 포맷·실행법 파악). 착수 전 repo·라이선스·Python 지원 확인.

**신규 모듈**
- `repair/base.py` — `Repairer` 프로토콜: `repair(sample) -> RepairAttempt`.
- `repair/baselines/refactory.py` — Refactory 도구 clone·설치 + ConDefects→Refactory 입력 변환 + 실행 + 결과 회수. 커밋 고정·격리(Docker).
- `repair/baselines/par.py` — PaR 도구 clone·실행 어댑터.
- `eval/harness.py` — (데이터셋 × 도구) 실행, 수리 코드는 Phase 0 샌드박스로 재채점.
- `eval/metrics.py` — pass@1(카테고리·도구별), status 전이.

**CLI**: `baseline run --tools refactory,par --split ai|human`, `eval report`.

**완료 기준**: (카테고리 × {Refactory, PaR}) pass@1 표. 특히 명세 오해형 버그에서 낮은 수리율이 드러나면 Phase 5 동기 성립. 인간(ConDefects) 대조군 대비 gap도 산출.

**리스크**: Refactory는 자체 question 포맷·자체 테스트 구조 → ConDefects 변환이 비자명. PaR 환경(언어/의존성) 격리 필요. 통합 불가 시 *문서화하고 제외*(silent drop 금지).

---

## Phase 5 — Spec-Grounded Repair (RQ3, 기여 ③) — 핵심 신규 기여

**목표**: 명세에서 의미 제약을 구조화 추출 → 수리 oracle로 추가 → 명세 오해형 버그 수리율을 vanilla LLM APR 대비 향상.

**신규 모듈**
- `spec/constraints.py` — `ConstraintSpec{input_ranges, output_format, algorithm_constraints, edge_cases}`.
- `spec/extractor.py`(5a) — LLM이 `problem.txt`(AtCoder) → `ConstraintSpec`. 추출 F1용 golden 제약 수동 라벨.
- `spec/verifier.py`(5b) — constraint-compliance **제2 oracle** → `ConstraintReport`.
- `repair/spec_grounded.py`(5c) — 제약 주입 수리 루프(`Repairer` 구현, Phase 4 harness 재사용). vanilla LLM APR(제약 없음) 대조군 동반.

**완료 기준/메트릭**: 추출 F1; 명세 오해형 한정 repair-rate 향상폭(spec_grounded − vanilla > 0, 유의); 테스트는 통과하나 제약 위반 케이스 포착.

**리스크**: 제약 추출이 정답 누출이 되지 않게 *형식·범위·엣지*로 제한, 알고리즘 자체 미추출.

---

## Phase 6 — AI 인식 교육 피드백 (RQ4, 기여 ④)

**목표**: `[명세 + 버그코드 + 카테고리 + 수리코드]` → "AI가 명세의 X를 Y로 오해해 Z 오류" 설명 생성·평가.

**신규 모듈**
- `feedback/generator.py` — 프롬프트 템플릿(한국어). AI 오해 *메커니즘* 명시.
- `eval/` 확장 — 전문가 3인 5점(Helpfulness·Accuracy·AI-Awareness) 폼, 학생 설문 n≈20 사전-사후 집계.

**완료 기준**: 전문가 평점 + 일반 LLM 설명/오류 메시지 대비 우위, 학생 인식 변화.

**리스크**: 인간 평가는 코드 밖 — 폼·집계만 코드로, 일정은 로드맵 Q4.

---

## 공통 인프라

- `eval/metrics.py` — pass@1·Cohen's κ·χ²·F1·FL accuracy 한 곳(`scipy`).
- `dataset/build.py` — sidecar(라벨·수리·피드백) 머지 → 버전된 최종 데이터셋. `dataset build`, `dataset stats`.
- `cli.py` 서브커맨드: `build-raw · inspect-raw · generate · code(open-coding) · kappa · baseline · spec · repair · feedback · eval · dataset`.
- `requirements.txt`: `openai`(기존), `beautifulsoup4/lxml`(AtCoder 스크레이핑·기존), `scipy`(통계). pandas/pyarrow는 ConDefects엔 불필요.

---

## 의존 그래프 / 순서

```
Phase 0 (하네스)
   └─► Phase 1 (ConDefects→data/raw: 명세 스크레이핑 + 테스트 + 인간 버그) ─► Phase 2 (gpt-3.5-turbo 생성)
            ├─► Phase 3 (Taxonomy: 데이터-주도 개방코딩)
            └─► Phase 4 (APR baseline: Refactory, PaR)
                     │
        Phase 5 (Spec-Grounded) ◄── (Phase 3 명세오해형 라벨로 타겟 확정)
                     │
                     └─► Phase 6 (피드백)
```

## 로드맵 매핑 (제안서 §8, 2026)

| 분기 | 제안서 | 코드 Phase |
|---|---|---|
| Q1 | AI 코드 대량 생성·분류 | Phase 0 + 1 + 2 + 3 착수 |
| Q2 | Taxonomy 확정 + 실증 분석 | Phase 3 완료 + 4 |
| Q3 | Spec-Grounded Repair 구현 | Phase 5 |
| Q4 | 피드백 평가 + 논문 준비 | Phase 6 + 통합 |

> 현재(2026-06): Phase 0·1 즉시 착수.

---

## Open decisions

- ✅ ~~gpt-3.5-turbo 가용성~~ → 확인됨(사용 가능, alias=`-0125`, 컷오프 Sep 2021).
- ✅ ~~명세 소스~~ → AtCoder 스크레이핑 확정(CodeNet 기각, 파일럿 검증 완료).
- ✅ ~~시기 윈도우~~ → **[2021-09 ~ 2022-11-30] 432 task 확정**(누수 X + 인간진정).
1. **⚠ Test.zip 취득** — OneDrive 자동다운 401 확인됨 → **수동 다운로드 필요**. 현재 파일럿은 AtCoder *sample I/O*만 오라클(약함). 전체 hidden 테스트로 교체 시 채점 타당성↑.
2. **⚠ 프롬프트 정책** — "problem.txt만"이면 생성물 46%가 비-Python(C++ 이탈, 파일럿 실측). 유지(수용) vs "Write a Python 3 solution" 1줄 추가(Python 집중). **데이터 절반을 좌우.**
3. **PaR repo 확정** — 공개 소스 위치·언어·입력 포맷 미상 → 식별 필요. (Refactory는 작동 검증됨.)
4. **special judge task 처리** — 격리 vs 제외.
5. **CLAUDE.md 갱신** — "External data location"을 ConDefects로 갱신(구현 본격화 시).

---

## 현재 진행 상태 (파일럿 실행됨)

`/goal`로 Phase 0–4를 **40-task 파일럿**(sample I/O 오라클)으로 1회 관통. 산출물 `results/`(PROGRESS.md, phase2/3/4*). **윈도우 확정에 따라 재선택 필요**: 파일럿 40개는 전 시기에서 층화됨 → 432-구간으로 재구성해야 함.

핵심 파일럿 결과: 비-Python 46%(프롬프트 이슈) · Python 버그 81 · **Spec-Misinterpretation 지배적, Hallucinated-API≈0** · Refactory 작동하나 ConDefects 통합 crash.

## 다음 액션

1. **Phase 1 재구성** — `build-raw`에 **윈도우 필터([2021-09~2022-11])** 적용해 432 task로 `data/raw/` 재구축.
2. **결정 #1·#2** — Test.zip 수동 다운로드 + 프롬프트 정책 확정(둘이 채점 타당성·코퍼스 크기를 좌우).
3. **Phase 2–3 재실행** — 432-윈도우 + (가능시) hidden 테스트로 생성·taxonomy 정밀화, 인간 대조군(RQ1) 비교 추가.
4. **Phase 4** — PaR repo 확정 + Refactory Docker(Py3.7)/정규화로 pass@1 산출.

각 Phase 완료 시 CLAUDE.md "Currently implemented"를 갱신한다.
