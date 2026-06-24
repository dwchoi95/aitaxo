# aitaxo — T3 AI-Generated-Code-Aware APR

논문 [`T3_AI-Generated-Code-Aware_APR.md`](./T3_AI-Generated-Code-Aware_APR.md) 의
실험 구현. 현재는 **MVP 데이터 생성 파이프라인**만 구현됨.

## MVP 범위 (현재)

`CodeNet 문제 명세 → GPT-4o가 Python 코드 생성 → 샌드박스에서 sample I/O 실행 → 실패 케이스 JSONL 저장`

| 단계 | 모듈 |
|---|---|
| 문제 로딩 | `src/aitaxo/problems/codenet.py` |
| GPT-4o 생성 | `src/aitaxo/generation/openai_client.py` |
| 실행·채점 | `src/aitaxo/execution/runner.py` |
| 파이프라인 | `src/aitaxo/pipeline.py` |
| CLI | `src/aitaxo/cli.py` |

## 셋업

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # OPENAI_API_KEY 채우기
```

## 사용

```bash
# API 호출 없이 로더만 검증
python -m aitaxo.cli inspect --limit 3

# 5개 문제 end-to-end (API 키 필요)
python -m aitaxo.cli generate --limit 5
```

출력: `data/generated/codenet_<model>_<timestamp>.jsonl` (실패 케이스만; `--save-all` 이면 전부)

각 레코드는 `problem_id`, `statement`, `tests`, `generation`(코드·토큰·모델), `execution`(테스트별 결과·status) 를 포함.

## 테스트 (API 키 불필요)

```bash
python tests/test_runner.py
```

## 다음 단계 (논문 기준)

- [ ] Taxonomy 라벨링 도구 — 5개 카테고리 수동 분류 + Cohen's κ
- [ ] Claude / Gemini 생성기 추가
- [ ] Spec-Grounded constraint extractor
- [ ] APR 베이스라인 (FastFixer, PaR, PyDex, CREF) 어댑터
- [ ] 교육 피드백 생성기
