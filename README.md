# Wi_Finder

## 1. 프로젝트 개요

**Wi_Finder**는 사용자 단말 기반 캠퍼스 Wi-Fi 접속 장애 진단 프로그램입니다.

학교 AP 로그나 RADIUS 서버 로그를 직접 확인하지 않고, 사용자의 Windows 노트북에서 실행 가능한 네트워크 명령어 결과를 수집하여 Wi-Fi 접속 상태를 분석합니다.

사용자는 프로그램을 실행한 뒤 브라우저 화면에서 **진단 시작** 버튼을 누르면 됩니다. 이후 프로그램이 자동으로 Wi-Fi, IP, DNS, 인터넷 연결 상태를 점검하고 결과를 카드 형태로 보여줍니다.

## 2. 프로젝트 목적

캠퍼스 Wi-Fi 장애는 사용자의 위치, 단말 상태, IP 할당 여부, DNS 설정, 외부 통신 가능 여부에 따라 원인이 달라질 수 있습니다.

Wi_Finder는 사용자의 PC에서 직접 수집한 네트워크 정보를 기반으로 다음과 같은 문제를 빠르게 분류하는 것을 목표로 합니다.

* Wi-Fi 미연결
* IP 할당 실패
* DNS 문제
* 외부 통신 실패
* 정상 연결 상태
* 기타 분류가 어려운 상태

이를 통해 사용자는 단순히 “인터넷이 안 된다”가 아니라, 어느 단계에서 문제가 발생했는지 확인할 수 있습니다.

## 3. 주요 기능

Wi_Finder는 다음 기능을 제공합니다.

* 브라우저 기반 로컬 GUI 제공
* Windows 네트워크 명령어 자동 실행
* Wi-Fi 연결 상태 확인
* SSID, BSSID, 신호 세기, 채널, 무선 연결 속도 확인
* IPv4 주소, 게이트웨이, DNS 서버 확인
* ping 결과 기반 인터넷 연결 상태 확인
* nslookup 결과 기반 DNS 상태 확인
* 진단 결과 카드 표시
* 보조 지표 표시
* 카드별 자세한 설명 토글 제공
* 원문 txt 및 분석 json 자동 저장

## 4. 진단 흐름

Wi_Finder의 기본 흐름은 다음과 같습니다.

```text
사용자가 Wi_Finder 실행
→ 브라우저 기반 GUI 자동 실행
→ 진단 시작 버튼 클릭
→ Windows 네트워크 명령어 자동 실행
→ 원문 txt 수집
→ parser.py로 파싱
→ diagnosis.py로 진단
→ display.py로 화면 표시용 데이터 생성
→ gui.py에서 결과 표시
→ collected/run_날짜시간 폴더에 결과 저장
```

## 5. 실행 방식

Wi_Finder는 외부 서버에 접속하는 웹서비스가 아니라, 사용자의 PC에서 실행되는 로컬 프로그램입니다.

브라우저 화면은 다음 주소에서 열립니다.

```text
http://127.0.0.1:8765
```

또는:

```text
http://localhost:8765
```

진단은 사용자의 Windows PC에서 직접 수행됩니다.

## 6. 프로젝트 구조

```text
Wi_Finder/
├─ app/
│  ├─ collector.py
│  ├─ parser.py
│  ├─ diagnosis.py
│  ├─ display.py
│  ├─ gui.py
│  └─ test_samples.py
│
├─ samples/
│  ├─ case1_normal/
│  ├─ case2_disconnected/
│  ├─ case3_1_connected_no_ip/
│  ├─ case3_2_dns_fail/
│  └─ case3_3_external_ping_fail/
│
├─ collected/
│  └─ run_YYYYMMDD_HHMMSS/
│
└─ README.md
```

## 7. 주요 파일 설명

### app/collector.py

Windows 명령어를 실행하여 네트워크 원문 결과를 수집합니다.

실행하는 주요 명령어는 다음과 같습니다.

```text
netsh wlan show interfaces
netsh wlan show networks mode=bssid
ipconfig /all
ping 8.8.8.8 -n 4 -w 1000
ping google.com -n 4 -w 1000
nslookup google.com
```

수집된 결과는 txt 파일로 저장됩니다.

### app/parser.py

collector.py가 수집한 원문 txt를 분석 가능한 dict 구조로 변환합니다.

파싱 항목은 다음과 같습니다.

* Wi-Fi 연결 여부
* SSID
* BSSID / AP BSSID
* 신호 세기
* 채널
* 수신/전송 속도
* IPv4 주소
* APIPA 여부
* 게이트웨이
* DNS 서버
* ping 성공 여부
* packet loss
* 평균 응답 시간
* nslookup 성공 여부
* 주변 eduroam 감지 여부

### app/diagnosis.py

parser.py의 결과를 바탕으로 장애 유형을 분류합니다.

진단 코드는 다음과 같습니다.

```text
NORMAL
DISCONNECTED
CONNECTED_NO_IP
DNS_FAIL
EXTERNAL_PING_FAIL
UNKNOWN
```

### app/display.py

diagnosis.py의 진단 결과를 GUI에서 표시하기 좋은 카드 데이터로 변환합니다.

생성되는 주요 데이터는 다음과 같습니다.

* diagnosis
* main_cards
* sub_cards
* detail_rows
* possible_causes
* recommended_actions

### app/gui.py

브라우저 기반 사용자용 GUI를 실행합니다.

제공하는 경로는 다음과 같습니다.

```text
/
→ 진단 홈

/run
→ 실제 Windows 진단 실행

/samples
→ 개발용 샘플 보기

/sample?case=case1_normal
→ 특정 샘플 결과 보기
```

## 8. Python으로 실행하는 방법

Windows에서 프로젝트 폴더를 연 뒤 PowerShell 또는 터미널을 실행합니다.

```powershell
python app/gui.py
```

만약 `python` 명령어가 동작하지 않으면 다음 명령어를 사용합니다.

```powershell
py app/gui.py
```

실행 후 브라우저가 자동으로 열리면 **진단 시작** 버튼을 클릭합니다.

## 9. exe 실행 방법

최종 사용자용 실행 파일이 제공되는 경우 다음 파일을 실행합니다.

```text
Wi_Finder.exe
```

실행하면 브라우저가 자동으로 열리고 진단 화면이 표시됩니다.

사용자는 다음 순서로 진행하면 됩니다.

```text
1. Wi_Finder.exe 실행
2. 브라우저 진단 화면 확인
3. 진단 시작 버튼 클릭
4. 결과 카드 확인
5. 필요 시 collected 폴더 압축 후 관리자에게 전달
```

## 10. 진단 결과 종류

### NORMAL

Wi-Fi 연결, IP 할당, DNS, 외부 인터넷 통신이 정상인 상태입니다.

### DISCONNECTED

Wi-Fi가 연결되어 있지 않은 상태입니다.

가능한 원인:

* Wi-Fi가 꺼져 있음
* eduroam에 연결하지 않음
* 저장된 Wi-Fi 프로필 문제
* 인증 정보 오류
* 주변 AP 신호는 있으나 자동 연결 실패

### CONNECTED_NO_IP

Wi-Fi는 연결됐지만 정상적인 IP 주소를 받지 못한 상태입니다.

가능한 원인:

* DHCP 서버 응답 실패
* AP 또는 네트워크 장비 문제
* 인증 후 내부 네트워크 진입 실패
* Windows 네트워크 설정 문제
* AP 또는 컨트롤러 장애

### DNS_FAIL

IP 통신은 가능하지만 웹사이트 주소 변환에 실패한 상태입니다.

가능한 원인:

* DNS 서버 설정 오류
* DNS 서버 응답 실패
* 127.x.x.x 같은 비정상 DNS 설정
* VPN 또는 보안 프로그램 영향
* DNS 캐시 문제

### EXTERNAL_PING_FAIL

DNS 조회는 가능하지만 외부 IP 통신이 실패한 상태입니다.

가능한 원인:

* 외부 ICMP ping 차단
* 방화벽 또는 보안 프로그램 차단
* 라우팅 문제
* 학교 네트워크 장비 문제
* 상위 인터넷 회선 문제

### UNKNOWN

수집된 결과만으로는 정확한 원인을 분류하기 어려운 상태입니다.

가능한 원인:

* 일부 명령어 결과 누락
* 네트워크 상태가 테스트 중간에 변동됨
* 방화벽 정책 때문에 일부 테스트만 실패
* parser가 일부 값을 추출하지 못함

## 11. GUI 카드 설명

Wi_Finder는 결과를 크게 두 영역으로 보여줍니다.

### 주요 진단 카드

* Wi-Fi 연결 상태
* 연결된 Wi-Fi
* 신호 세기
* IP 주소 상태
* 인터넷 연결
* 웹사이트 주소 확인

### 보조 지표

* 응답 속도
* 끊김 정도
* 무선 연결 속도
* 채널
* 주변 eduroam 감지

각 카드에는 기본 설명이 표시되며, 일부 카드에는 **자세히 보기** 토글이 제공됩니다.

자세히 보기 토글을 누르면 일반 사용자도 이해할 수 있도록 해당 지표의 의미와 판단 기준을 확인할 수 있습니다.

예를 들어 무선 연결 속도는 실제 인터넷 속도와 완전히 같은 값은 아니지만, 노트북과 Wi-Fi 장비 사이의 연결 품질과 관련이 있습니다. 값이 낮으면 인터넷 체감 속도도 느려질 수 있습니다.

## 12. 결과 저장 위치

진단을 실행하면 프로젝트 폴더 안에 `collected` 폴더가 자동으로 생성됩니다.

저장 구조는 다음과 같습니다.

```text
collected/
└─ run_YYYYMMDD_HHMMSS/
   ├─ netsh_interfaces.txt
   ├─ netsh_networks_bssid.txt
   ├─ ipconfig_all.txt
   ├─ ping_8_8_8_8.txt
   ├─ ping_google.txt
   ├─ nslookup_google.txt
   ├─ diagnosis_result.json
   ├─ display_data.json
   ├─ command_results.json
   └─ run_metadata.json
```

`collected` 폴더는 처음부터 없어도 됩니다. 진단 시작 버튼을 누르면 자동으로 생성됩니다.

## 13. 저장 파일 설명

### netsh_interfaces.txt

현재 연결된 Wi-Fi 인터페이스 정보를 저장합니다.

포함 정보:

* SSID
* BSSID
* 신호 세기
* 채널
* 수신/전송 속도
* 인증 방식
* 암호 방식

### netsh_networks_bssid.txt

주변에서 감지되는 Wi-Fi 목록과 BSSID 정보를 저장합니다.

### ipconfig_all.txt

Windows IP 설정 정보를 저장합니다.

포함 정보:

* IPv4 주소
* 기본 게이트웨이
* DNS 서버
* DHCP 사용 여부
* 미디어 연결 상태

### ping_8_8_8_8.txt

외부 IP와 직접 통신이 가능한지 확인한 결과입니다.

### ping_google.txt

도메인 주소를 사용한 통신이 가능한지 확인한 결과입니다.

### nslookup_google.txt

DNS 서버가 google.com 주소를 IP로 변환할 수 있는지 확인한 결과입니다.

### diagnosis_result.json

진단 로직의 최종 결과를 저장합니다.

### display_data.json

GUI 표시용 카드 데이터를 저장합니다.

### command_results.json

각 명령어의 실행 성공 여부, return code, timeout, stderr 등을 저장합니다.

### run_metadata.json

진단 시작 시간, 종료 시간, 저장 경로 등을 저장합니다.

## 14. 샘플 테스트 방법

개발자는 samples 폴더의 테스트 케이스를 이용하여 전체 진단 로직을 검증할 수 있습니다.

```bash
python3 app/test_samples.py
```

Windows에서는 다음 명령어도 사용할 수 있습니다.

```powershell
python app/test_samples.py
```

또는:

```powershell
py app/test_samples.py
```

정상 결과 예시는 다음과 같습니다.

```text
=== Test Result ===
PASS: 5
FAIL: 0

모든 samples case가 기대한 진단 결과와 일치합니다.
```

## 15. 샘플 케이스 설명

### case1_normal

Wi-Fi 연결, IP 할당, DNS, 외부 통신이 모두 정상인 상태입니다.

기대 결과:

```text
NORMAL
```

### case2_disconnected

Wi-Fi가 연결되어 있지 않은 상태입니다.

기대 결과:

```text
DISCONNECTED
```

### case3_1_connected_no_ip

Wi-Fi는 연결됐지만 IP를 정상적으로 받지 못한 상태입니다.

기대 결과:

```text
CONNECTED_NO_IP
```

### case3_2_dns_fail

IP 통신은 가능하지만 DNS 조회가 실패한 상태입니다.

기대 결과:

```text
DNS_FAIL
```

### case3_3_external_ping_fail

DNS 조회는 가능하지만 외부 ping 통신이 실패한 상태입니다.

기대 결과:

```text
EXTERNAL_PING_FAIL
```

## 16. 팀원 테스트 방법

팀원은 Windows PC에서 다음 순서로 테스트합니다.

```text
1. GitHub에서 최신 코드 받기
2. 프로젝트 폴더 열기
3. PowerShell 또는 터미널 실행
4. python app/gui.py 실행
5. 브라우저가 열리면 진단 시작 클릭
6. 결과 화면 캡처
7. collected/run_날짜시간 폴더를 zip으로 압축
8. 결과 화면 캡처와 zip 파일 전달
```

기존 프로젝트 폴더가 있는 경우 최신 코드를 받습니다.

```bash
git pull
```

실행 명령어:

```powershell
python app/gui.py
```

또는:

```powershell
py app/gui.py
```

## 17. 팀원 테스트 시 보내야 할 자료

팀원은 테스트 후 다음 자료를 전달합니다.

```text
1. 진단 결과 화면 캡처
2. collected/run_YYYYMMDD_HHMMSS 폴더 zip 파일
3. 테스트 당시 상황 설명
```

상황 설명 예시:

```text
집 Wi-Fi 정상 연결 상태
학교 eduroam 연결 상태
Wi-Fi 연결 해제 상태
휴대폰 핫스팟 연결 상태
DNS 설정을 임의로 바꾼 상태
```

## 18. 테스트 시 권장 케이스

최소한 다음 3가지 상황을 테스트하는 것을 권장합니다.

```text
1. 정상 Wi-Fi 연결 상태
2. Wi-Fi 연결 해제 상태
3. 학교 eduroam 또는 다른 네트워크 연결 상태
```

추가로 가능하다면 다음 상황도 테스트할 수 있습니다.

```text
1. IP 할당 실패 상황
2. DNS 실패 상황
3. 외부 통신 실패 상황
```

다만 위 3개 장애 상황은 실제 환경에서 만들기 어려울 수 있으므로 필수는 아닙니다.

## 19. 주의사항

* 실제 진단은 Windows 환경에서만 정상 동작합니다.
* macOS나 Linux에서는 `netsh`, `ipconfig /all` 명령어가 Windows와 다르기 때문에 실제 진단이 불가능합니다.
* macOS에서 `/run` 실행 시 Windows 명령어 오류가 발생하는 것은 정상입니다.
* 샘플 결과 확인은 macOS에서도 가능합니다.
* 일부 보안 프로그램이나 방화벽은 ping 결과에 영향을 줄 수 있습니다.
* ping이 실패하더라도 웹 브라우저 접속은 가능할 수 있습니다.
* 무선 연결 속도는 실제 인터넷 다운로드 속도와 완전히 같은 값이 아닙니다.
* 무선 연결 속도는 노트북과 Wi-Fi 장비 사이의 연결 품질을 보여주는 보조 지표입니다.

## 20. 최근 개선 사항

최근 테스트 결과를 바탕으로 다음 사항을 개선했습니다.

### DNS 오진 방지

이전에는 `nslookup`만 실패해도 DNS 문제로 진단될 수 있었습니다.

수정 후에는 `ping google.com`이 성공하면 사용자 관점에서 도메인 기반 통신은 가능한 것으로 보고, 전체 진단을 정상으로 판단합니다.

즉 다음 상황은 더 이상 DNS 장애로 오진하지 않습니다.

```text
ping 8.8.8.8 성공
ping google.com 성공
nslookup 실패
```

이 경우 결과는 `NORMAL`로 판단하고, 내부적으로는 DNS 확인 경고 메모를 남깁니다.

### 127.x.x.x DNS 비정상 처리

기존에는 `127.0.0.1`만 비정상 DNS로 처리했지만, 수정 후에는 `127.0.0.0/8` 전체를 비정상 DNS로 처리합니다.

예:

```text
127.0.0.1
127.0.0.2
127.10.0.1
```

### AP BSSID 파싱 개선

Windows 출력에서 BSSID가 다음과 같이 나오는 경우도 처리하도록 개선했습니다.

```text
AP BSSID : xx:xx:xx:xx:xx:xx
```

기존에는 일부 환경에서 BSSID가 `None`으로 나올 수 있었지만, 수정 후에는 `BSSID`와 `AP BSSID` 형식을 모두 처리합니다.

### ping timeout 단축

Wi-Fi 미연결이나 장애 상황에서 진단 시간이 길어지지 않도록 ping 명령어를 개선했습니다.

```text
ping 8.8.8.8 -n 4 -w 1000
ping google.com -n 4 -w 1000
```

### GUI 도움말 토글 추가

기본 설명은 간단하게 표시하고, 자세한 설명은 `자세히 보기` 토글로 확인할 수 있도록 개선했습니다.

## 21. 최종 목표

최종 목표는 사용자가 별도 명령어를 몰라도 다음 흐름으로 Wi-Fi 상태를 진단하는 것입니다.

```text
Wi_Finder.exe 실행
→ 브라우저 자동 열림
→ 진단 시작 클릭
→ Wi-Fi / IP / DNS / 인터넷 상태 자동 점검
→ 결과 카드 확인
→ 필요 시 collected 폴더를 관리자에게 전달
```

## 22. 개발 상태

현재 구현된 주요 기능은 다음과 같습니다.


collector.py 구현 완료
parser.py 구현 완료
diagnosis.py 구현 완료
display.py 구현 완료
gui.py 구현 완료
samples 기반 테스트 완료
팀원 Windows 실환경 테스트 완료
GUI 설명 토글 개선 완료
Wi_Finder.exe 패키징
exe 실행 테스트
최종 발표자료 정리
최종 보고서 작성

