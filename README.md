# Wi-Fi Diagnosis Capstone

사용자 단말 기반 캠퍼스 Wi-Fi 접속 장애 진단 및 혼잡 분석 시스템 개발 프로젝트입니다.

## 주요 기능

- Windows Wi-Fi 상태 수집
- IP/DNS/Ping/HTTP 테스트
- 장애 원인 자동 분류
- 로컬 JSON/CSV 저장
- 위치 기반 장애 통계 확장
- DB/API 서버 연동 확장

## 1차 목표

학생 노트북에서 실행 가능한 로컬 Wi-Fi 진단 프로그램 구현

## 기술 스택

- Python
- tkinter 또는 CustomTkinter
- GitHub
- PyInstaller
- 추후 FastAPI 또는 Flask

샘플 기반 통합 테스트 실행 방법

python3 app/test_samples.py

이 테스트는 samples/ 폴더의 5개 case를 대상으로
parser.py → diagnosis.py → display.py 흐름을 검증한다.

기대 결과:
case1_normal                → NORMAL
case2_disconnected          → DISCONNECTED
case3_1_connected_no_ip     → CONNECTED_NO_IP
case3_2_dns_fail            → DNS_FAIL
case3_3_external_ping_fail  → EXTERNAL_PING_FAIL