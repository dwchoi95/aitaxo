# Phase 4 — APR Baseline (Refactory, PaR) 상태

## Refactory
- **도구 확보**: `tools/refactory/` (github.com/githubhuyang/refactory, ASE'19). 데이터셋 아님 — 실행 도구.
- **환경**: 순수 Python 의존성 설치 성공(zss, psutil, autopep8, astunparse, prettytable, python-Levenshtein, numpy, pandas). macOS 비호환 1건 패치: `basic_framework/exec.py`의 `RLIMIT_AS setrlimit`를 try/except 가드(우리 runner와 동일 이슈).
- **self-test**: 번들 예제 `question_1`에서 **수리 성공 확인**(`wrong_1_132.py` → success, csv 생성). → 도구 자체는 이 환경에서 동작.
- **입력 어댑터**: `scripts/phase4_refactory_adapter.py` → ConDefects/AI버그를 Refactory 포맷으로 변환 (`tools/refactory/data_condefects/`, **26 questions**: correct=ConDefects correctVersion, wrong=AI Python 버그, ans=AtCoder sample I/O).
- **ConDefects 실행**: ⚠ **crash**. Refactory가 reference 정답을 refactoring하는 과정(`template.get_temp_cons_lists` → `ast.parse`)에서 `IndentationError: unexpected indent`.
  - 원인: Refactory는 **입문 프로그래밍(함수형 제출)** 가정으로 설계 — AtCoder의 **stdin/stdout 경쟁 스크립트** 스타일을 refactoring 엔진이 처리 못함.
  - 이것 자체가 **RQ2의 정성적 신호**(기존 APR이 이 분포에 안 맞음)지만, 정량 pass@1을 내려면 추가 하드닝 필요: (a) 公式 Docker(Python 3.7) 환경, (b) un-refactorable 정답 필터링/정규화, (c) 더 큰 정답 풀.

## PaR
- **미확정**: 공개 repo 자동 탐색 실패. 제안서가 가리키는 정확한 "PaR" 도구(저자·repo·언어) 확인 필요 → **사용자 입력 요망**.

## 공통 한계
- 채점 오라클이 **AtCoder sample I/O**뿐(ConDefects `Test.zip` 미확보) → 수리 검증도 sample 기준. 완전판은 hidden 테스트 필요.

## 다음 단계
1. Refactory를 공식 Docker(Python 3.7)로 실행하거나 reference 정규화 어댑터 추가 → 26 questions pass@1 산출.
2. PaR repo 확정 후 어댑터.
3. `Test.zip` 확보 시 오라클 교체 → Phase 2/3/4 전부 재실행으로 수치 정밀화.
