# T3 · AI-Generated-Code-Aware APR

**AI 생성 코드 버그 Taxonomy + Spec-Grounded Repair + 교육 피드백**

> "ChatGPT가 만든 버그는 다르다, 다르게 고쳐야 한다." API로 즉시 데이터 구성 가능 — 시의성 가장 높음.

**Novelty ★★★★★ · Rigor ★★★★ · Verifiability ★★★★**

---

## 1. 문제 정의

학생의 ChatGPT 코드 제출이 급증하는 시대에, **AI 생성 코드 고유의 버그 패턴(Spec-Mismatch 등)은 기존 APR 도구로 효과적으로 수리되지 않는다.**

---

## 2. AI 생성 코드 버그 Taxonomy (5 카테고리)

| 카테고리 | 설명 |
|---|---|
| **Spec-Mismatch** ← 핵심 타겟 | 문제 명세 오해 (가장 빈번) |
| **Hallucinated-API** | 미존재 함수 호출 |
| **Incomplete-Logic** | 엣지 케이스 누락 |
| **Test-Gaming** | 공개 테스트 하드코딩 |
| **Style-Overfitting** | 비효율 구조 |

---

## 3. 주요 기여 (5 Contributions)

### ① AI 버그 Taxonomy 최초 구축
교육 과제 맥락 특화 5개 카테고리. 두 저자 독립 분류 후 합의(κ ≥ 0.7).

### ② AI vs Human 실증 비교 연구
동일 문제 세트에서 카테고리별 분포, 수리 용이성, FL 정확도 정량 비교.

### ③ Spec-Grounded Repair
자연어 명세에서 의미적 제약 자동 추출 → APR oracle로 활용. 명세 준수 검증.

### ④ AI 인식 교육 피드백 생성
"AI가 명세의 X를 Y로 오해해 Z 오류" 형태로 **AI 한계를 명시하는 설명적 피드백**.

### ⑤ AI-Bugs-in-Education 데이터셋 공개
문제 명세 + AI 생성 버그 코드 + 수동 레이블 + 인간 대조군 최초 공개.

---

## 4. 핵심 방법론

### 처리 파이프라인 (6 Steps)
```
AI 코드 대량 생성 → 버그 수동 분류·합의 → Taxonomy 확정
→ 기존 APR 성능 분석 → Spec-Grounded Repair 설계 → 교육 피드백 생성·평가
```

### AI 생성 코드 데이터 파이프라인
1. CodeNet / open-r1/codeforces 문제 명세 입력
2. GPT-4o · Claude · Gemini 각각에 코드 생성
3. 테스트 불통과 코드만 필터링
4. 수동 버그 분류 레이블 부착
5. 동일 문제 인간 코드(CodeNet)를 대조군으로 병렬 구성

### 버그 분류 프로토콜 (2-Author Agreement)
- 두 저자 독립 분류 → Cohen's Kappa 계산 (목표 κ ≥ 0.7)
- 불일치 시 제3자 중재 → 확정 레이블
- 카테고리별 대표 예시 3~5개를 논문 appendix 수록

### Spec-Grounded Repair Oracle
1. 자연어 명세를 LLM으로 파싱
2. 입력 범위·출력 형식·알고리즘 제약·엣지 케이스를 **구조화된 제약 명세**로 추출
3. 수리 프롬프트에 추가 제공
4. '테스트 통과' 외 '제약 명세 준수' 별도 검증기로 확인

### 교육 피드백 생성 프롬프트 설계
- **입력**: `[문제 명세] + [버그 코드] + [버그 카테고리] + [수리된 코드]`
- **출력**: "AI가 명세의 X를 Y로 잘못 이해했으며, 따라서 Z 부분에서 오류가 발생했습니다."

→ 단순 오류 설명이 아닌 **AI 오해 메커니즘**을 명시

---

## 5. Research Questions

| RQ | 질문 | 평가 방법 |
|---|---|---|
| **RQ1** | AI 생성 코드의 버그 패턴은 인간 코드와 어떻게 다른가? | 동일 문제 세트 카테고리별 분포 비교(χ²). 버그 복잡도·수리 용이성 정량 비교. |
| **RQ2** | 기존 APR 도구들은 AI 버그를 효과적으로 수리하는가? | FastFixer·PaR·PyDex·CREF를 AI 버그 데이터에 적용, 카테고리별 성능 gap 정량화. |
| **RQ3** | Spec-Grounded Repair가 Spec-Mismatch 수리 성능을 향상시키는가? | 일반 LLM APR vs Spec-Grounded Repair 수리 성공률 비교. 제약 추출 F1 측정. |
| **RQ4** | AI 인식 교육 피드백은 전문가 기준 교육적으로 적절한가? | 전문가 3인 5점 척도. 학생 설문 n≈20으로 AI 활용 인식 변화 사전-사후 비교. |

---

## 6. 데이터셋

| 데이터셋 | 역할 | 활용 방안 |
|---|---|---|
| **AI 생성 코드 (직접 구성)** | 핵심 | GPT-4o·Claude·Gemini API로 대량 생성. 수동 분류 레이블 부착. 핵심 기여 데이터셋. |
| **IBM CodeNet** | 인간 대조군 | 동일 문제 인간 버그 코드(WA·RE). 문제 명세 90%+로 제약 추출에 활용. |
| **open-r1/codeforces-cots** | AI 보조 | DeepSeek-R1 생성 ~100k. CoT 포함으로 AI 오해 메커니즘 분석 가능. |
| **open-r1/cf-submissions** | 인간 대규모 | selected_incorrect: 최소 1 테스트 통과 인간 오답 12M+. 통계적 유의성 확보. |
/home/cdw/VSCode/aria/data/ 에 이미 구비되어 있음. 필요한 데이터만 정제해서 ./data/에 만들어 두고 사용할것.

---

## 7. 평가 메트릭

| 메트릭 | 정의 | 비교 대상 |
|---|---|---|
| **Taxonomy Cohen's Kappa** | 두 저자 분류 일치도 (κ ≥ 0.7) | 단일 저자 분류 |
| **APR Tool Repair Rate** | AI 버그 카테고리별 기존 APR pass@1 | FastFixer, PaR, PyDex, CREF |
| **Spec-Constraint Extraction F1** | 자연어 명세 제약 추출 precision·recall | LLM 직접 명세 해석 (추출 없음) |
| **Spec-Grounded Repair Rate** | Spec-Mismatch 한정 수리 성공률 향상폭 | 일반 GPT-4o APR |
| **Feedback Quality (Expert)** | 전문가 3인 Helpfulness·Accuracy·AI-Awareness | 일반 LLM 설명, 일반 오류 메시지 |

---

## 8. 연구 로드맵 (2026)

- **2025 Q3**: T3 데이터셋 구축 시작 (API 생성 즉시 가능)
- **Q1**: AI 코드 대량 생성·분류
- **Q2**: Taxonomy 구축 + 실증 분석
- **Q3**: Spec-Grounded Repair 구현
- **Q4**: 피드백 평가 + 논문 제출 준비 (ICSE 2027)
