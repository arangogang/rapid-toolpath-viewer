# ABB RAPID Toolpath Viewer

## What This Is

ABB RAPID 로봇 프로그램 파일(.mod)을 불러와 툴패스를 3D로 시각화하는 Windows 데스크탑 애플리케이션이다. 로봇 엔지니어가 RAPID 코드를 실제 로봇에 올리기 전에 경로의 정확성을 검증하는 도구다.

## Core Value

.mod 파일을 열면 즉시 3D 툴패스가 렌더링되고, 각 워크포인트를 클릭하면 해당 RAPID 코드 줄로 이동할 수 있어야 한다.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] ABB RAPID .mod 파일 로드 (파일 다이얼로그)
- [ ] 전체 Move 명령어 파싱: MoveJ, MoveL, MoveC, MoveAbsJ
- [ ] 3D 뷰어: 툴패스 경로 선 렌더링 (MoveL=실선, MoveJ=점선 구분)
- [ ] 3D 뷰어: 워크포인트(robtarget) 마커 표시
- [ ] 3D 뷰어: TCP 워크오브제트 좌표계 시각화
- [ ] 마우스 드래그로 3D 오비트/줌/팬 (카메라 컨트롤)
- [ ] 단계 재생: Step 뒤로/앞으로, Play 자동 재생
- [ ] 현재 재생 포인트 ↔ RAPID 코드 줄 링크 (포인트 선택 시 코드 하이라이트)

### Out of Scope

- ABB 로봇 암 3D 모델 — v1에서 불필요, TCP 경로만으로 검증 가능
- 실시간 로봇 연결/통신 — 오프라인 검증 도구로 충분
- RAPID 코드 편집 기능 — 뷰어 전용, IDE 기능은 별도 도구 사용
- 충돌 감지/시뮬레이션 — RobotStudio 수준의 복잡도, v1 범위 외

## Context

- ABB RAPID는 ABB 산업용 로봇의 프로그래밍 언어. `.mod` 파일이 주요 프로그램 파일
- robtarget 데이터 타입이 워크포인트 위치/방향 정보를 담음 (pos + orient)
- MoveL = 선형 이동, MoveJ = 조인트 이동, MoveC = 원호 이동, MoveAbsJ = 절대 조인트 이동
- 사용 목적: 실제 로봇 가동 전 코드 검증 (현장 운용)
- Python + PyQt6 + PyOpenGL 기반 Windows 데스크탑 앱

## Constraints

- **Tech Stack**: Python + PyQt6 + PyOpenGL — 빠른 구현, 사용자가 명시적 선택
- **Platform**: Windows 데스크탑 전용
- **Scope**: 코드 검증 뷰어 — 편집/시뮬레이션 기능 없음

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| PyOpenGL for 3D rendering | PyQt6 내장 QOpenGLWidget과 통합 용이, Python 생태계 내 처리 | — Pending |
| 로봇 모델 미포함 | TCP 경로 시각화만으로 v1 검증 목적 충족, 복잡도 절감 | — Pending |
| .mod 파일 단독 파싱 | 실용적 v1 범위, .pgf 등 멀티파일 구조는 v2 고려 | — Pending |

---
*Last updated: 2026-03-30 after initial project setup*
