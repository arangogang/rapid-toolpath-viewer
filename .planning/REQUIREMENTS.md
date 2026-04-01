# Requirements: ABB RAPID Toolpath Viewer

**Defined:** 2026-03-30
**Core Value:** .mod 파일을 열면 즉시 3D 툴패스가 렌더링되고, 각 워크포인트를 클릭하면 해당 RAPID 코드 줄로 이동할 수 있어야 한다.

## v1 Requirements

### File Loading

- [x] **FILE-01**: 사용자가 파일 다이얼로그를 통해 .mod 파일을 열 수 있다
- [x] **FILE-02**: 파일 로드 후 파일명이 상단 타이틀바에 표시된다

### RAPID Parsing

- [x] **PARS-01**: MoveL 명령어를 파싱하여 선형 이동 경로를 추출한다
- [x] **PARS-02**: MoveJ 명령어를 파싱하여 조인트 이동 경로를 추출한다
- [x] **PARS-03**: MoveC 명령어를 파싱하여 원호 이동 경로를 추출한다 (CirPoint + endpoint)
- [x] **PARS-04**: MoveAbsJ는 파싱하되 3D 렌더링에서 제외한다 (코드 패널에는 표시)
- [x] **PARS-05**: robtarget 데이터 타입을 파싱한다 (pos x/y/z + orient q1-q4)
- [x] **PARS-06**: 멀티라인 robtarget 선언을 올바르게 파싱한다 (세미콜론 기반 토크나이징)
- [x] **PARS-07**: 파싱 시 각 Move 명령어에 소스 줄 번호를 저장한다 (코드 링크용)
- [x] **PARS-08**: 여러 PROC가 있는 .mod 파일에서 표시할 PROC을 선택할 수 있다

### 3D Rendering

- [x] **REND-01**: 툴패스 경로를 3D로 렌더링한다 (MoveL=실선, MoveJ=점선, MoveC=호선)
- [x] **REND-02**: 각 워크포인트(robtarget)에 마커를 표시한다
- [x] **REND-03**: XYZ 좌표축 인디케이터를 뷰포트 코너에 표시한다
- [x] **REND-04**: 각 워크포인트에 TCP 방향을 RGB 축 트라이어드로 시각화한다 (쿼터니언 → 회전행렬 변환)
- [x] **REND-05**: OpenGL 3.3 Core Profile + VBO/VAO 아키텍처를 사용한다

### Camera Controls

- [x] **CAM-01**: 마우스 드래그로 3D 뷰를 오비트(회전)할 수 있다
- [x] **CAM-02**: 마우스 스크롤로 줌 인/아웃할 수 있다
- [x] **CAM-03**: 마우스 중클릭 드래그로 팬(이동)할 수 있다

### Step Playback

- [ ] **PLAY-01**: Step 앞으로 버튼으로 다음 워크포인트로 이동한다
- [ ] **PLAY-02**: Step 뒤로 버튼으로 이전 워크포인트로 이동한다
- [ ] **PLAY-03**: Play 버튼으로 자동 재생한다 (워크포인트를 순서대로 이동)
- [x] **PLAY-04**: 현재 선택된 워크포인트가 3D 뷰어에서 시각적으로 강조된다
- [x] **PLAY-05**: 현재 재생 위치가 "포인트 N / 전체 M" 형식으로 표시된다
- [x] **PLAY-06**: 재생 속도 슬라이더 (0.5x ~ 10x)로 자동 재생 속도를 조절할 수 있다
- [x] **PLAY-07**: 스크러버 슬라이더로 전체 경로에서 임의 위치로 즉시 이동할 수 있다

### Code Panel

- [x] **CODE-01**: RAPID 코드가 우측 패널에 표시된다
- [x] **CODE-02**: RAPID 키워드가 신택스 하이라이트된다 (MoveL, MoveJ, PROC 등)
- [x] **CODE-03**: 현재 선택된 워크포인트에 해당하는 코드 줄이 하이라이트된다

### Bidirectional Code-to-3D Linking

- [x] **LINK-01**: 3D 뷰어에서 워크포인트를 클릭하면 코드 패널이 해당 줄로 스크롤된다
- [x] **LINK-02**: 코드 패널에서 Move 명령어 줄을 클릭하면 3D 뷰어에서 해당 포인트가 선택된다

## v1.1 Requirements

Requirements for milestone v1.1: Toolpath Editing. Each maps to roadmap phases.

### Edit Infrastructure

- [x] **EDIT-01**: Mutable EditModel 레이어 — frozen 파서 토큰 위에 편집 가능한 래퍼, 모든 편집 기능의 기반
- [x] **EDIT-02**: QUndoStack 기반 Undo/Redo (Ctrl+Z/Y) — 모든 편집 작업을 QUndoCommand로 래핑

### Selection

- [x] **SEL-01**: 3D 뷰어에서 워크포인트 클릭으로 단일 선택, 선택 시 RAPID 코드 줄 하이라이트 연동
- [x] **SEL-02**: Shift/Ctrl 클릭으로 다중 선택 지원, 선택된 포인트들 시각적 구분

### Inspection

- [ ] **INSP-01**: 선택된 포인트의 속성 패널 표시 — 좌표(X,Y,Z), 속도, zone값, 레이저 on/off 상태

### Modification

- [ ] **MOD-01**: 좌표 오프셋 수정 — X,Y,Z 델타값 입력으로 선택된 워크포인트 이동
- [ ] **MOD-02**: 속성 수정 — 속도, zone값, 레이저 on/off 변경
- [ ] **MOD-03**: 웨이포인트 삭제 — 삭제 후 다음 패스 연결(기존 경로 유지) 또는 끊기(레이저 OFF 이동) 옵션
- [ ] **MOD-04**: 연속 추가 — 오프셋 입력 후 추가 포인트 계속 생성, 기존 속성 복사

### Export

- [ ] **EXP-01**: 수정된 .mod 파일 다른 이름으로 저장 — 원본 포맷/주석 보존 (소스 텍스트 패칭 방식)

## v2 Requirements

### Playback Enhancement

- **ENH-01**: 경로를 따라 마커가 부드럽게 이동하는 애니메이션 재생 (구간 보간)
- **ENH-02**: 속도(speeddata) / 존(zonedata) 데이터 오버레이 (경로 색상 그라디언트)

### Path Analysis

- **ANAL-01**: 경로 통계 패널 (총 길이, 포인트 수, 이동 타입 분류)
- **ANAL-02**: 코드 패널 텍스트 검색

### Advanced Editing

- **ADV-01**: 드래그로 워크포인트 3D 이동 (직접 조작)
- **ADV-02**: 다중 선택 일괄 배치 편집 (배치 오프셋, 배치 속성 변경)
- **ADV-03**: 복사/붙여넣기 워크포인트 시퀀스

### Extended Parsing

- **EXT-01**: wobj (work object) 좌표계 파싱 및 변환 시각화
- **EXT-02**: 여러 .mod 파일을 하나의 뷰어에 로드 (멀티 모듈)

## Out of Scope

| Feature | Reason |
|---------|--------|
| ABB 로봇 암 3D 모델 | 키네마틱 솔버 + 로봇 모델 필요, 코드 검증 목적에 불필요 |
| RAPID 코드 편집 | 뷰어 전용 — IDE 기능 제외 |
| 충돌 감지 / 도달 가능성 분석 | RobotStudio 수준의 복잡도 |
| 실시간 로봇 연결 (EGM) | 완전히 다른 제품 카테고리 |
| .pgf 프로젝트 파일 파싱 | 멀티 모듈/시스템 구조 복잡도 |
| CAD 모델 임포트 (STEP/IGES) | 별도 파싱 라이브러리 필요, v2+ 고려 |
| RAPID 코드 직접 텍스트 편집 | IDE 기능, 별도 도구 사용 |
| 원본 파일 덮어쓰기 저장 | 안전성 — Save As만 지원 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FILE-01 | Phase 1 | Complete |
| FILE-02 | Phase 1 | Complete |
| PARS-01 | Phase 1 | Complete |
| PARS-02 | Phase 1 | Complete |
| PARS-03 | Phase 1 | Complete |
| PARS-04 | Phase 1 | Complete |
| PARS-05 | Phase 1 | Complete |
| PARS-06 | Phase 1 | Complete |
| PARS-07 | Phase 1 | Complete |
| PARS-08 | Phase 3 | Complete |
| REND-01 | Phase 2 | Complete |
| REND-02 | Phase 2 | Complete |
| REND-03 | Phase 2 | Complete |
| REND-04 | Phase 3 | Complete |
| REND-05 | Phase 2 | Complete |
| CAM-01 | Phase 2 | Complete |
| CAM-02 | Phase 2 | Complete |
| CAM-03 | Phase 2 | Complete |
| PLAY-01 | Phase 3 | Pending |
| PLAY-02 | Phase 3 | Pending |
| PLAY-03 | Phase 3 | Pending |
| PLAY-06 | Phase 3 | Complete |
| PLAY-07 | Phase 3 | Complete |
| PLAY-04 | Phase 3 | Complete |
| PLAY-05 | Phase 3 | Complete |
| CODE-01 | Phase 3 | Complete |
| CODE-02 | Phase 3 | Complete |
| CODE-03 | Phase 3 | Complete |
| LINK-01 | Phase 3 | Complete |
| LINK-02 | Phase 3 | Complete |
| EDIT-01 | Phase 4 | Complete |
| EDIT-02 | Phase 4 | Complete |
| SEL-01 | Phase 4 | Complete |
| SEL-02 | Phase 4 | Complete |
| INSP-01 | Phase 4 | Pending |
| MOD-01 | Phase 5 | Pending |
| MOD-02 | Phase 5 | Pending |
| MOD-03 | Phase 5 | Pending |
| MOD-04 | Phase 5 | Pending |
| EXP-01 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 30 total (all complete)
- v1.1 requirements: 10 total
- Mapped to phases: 10/10
- Unmapped: 0

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-04-01 after roadmap creation for v1.1*
