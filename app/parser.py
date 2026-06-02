from pathlib import Path
from typing import Union
import re


# =========================
# 파일 읽기
# =========================

def read_text_file(file_path):
    """
    txt 파일을 안전하게 읽는다.
    Windows 명령어 출력은 utf-8, utf-8-sig, cp949, euc-kr, utf-16 등이 섞일 수 있다.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return ""

    data = file_path.read_bytes()

    if not data:
        return ""

    # BOM 기반 UTF-16 감지
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            pass

    # BOM 기반 UTF-8 감지
    if data.startswith(b"\xef\xbb\xbf"):
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            pass

    # UTF-16인데 BOM이 없는 경우 보정
    if data.count(b"\x00") > len(data) * 0.2:
        for encoding in ["utf-16", "utf-16-le", "utf-16-be"]:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue

    for encoding in ["utf-8", "utf-8-sig", "cp949", "euc-kr"]:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    return data.decode("utf-8", errors="ignore")


def extract_value_after_colon(line):
    """
    'SSID : eduroam' 같은 줄에서 ':' 뒤 값만 추출한다.
    """
    if ":" not in line:
        return ""

    return line.split(":", 1)[1].strip()


def extract_first_ipv4(text):
    """
    문자열에서 첫 번째 IPv4 주소를 추출한다.
    """
    match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", text)
    return match.group(1) if match else None


def normalize_spaces(text):
    """
    여러 공백을 하나로 줄여 비교를 안정적으로 만든다.
    """
    return " ".join(str(text).strip().split())


def is_invalid_loopback_or_placeholder_ip(ip):
    """
    DNS 응답 주소로 보기 어려운 IP인지 판단한다.

    - 127.x.x.x: 루프백
    - 169.254.x.x: APIPA
    - 0.0.0.0: placeholder
    """
    if ip is None:
        return True

    ip = str(ip).strip()

    if not ip:
        return True

    if ip == "0.0.0.0":
        return True

    if ip.startswith("127."):
        return True

    if ip.startswith("169.254."):
        return True

    return False


# =========================
# ipconfig Wi-Fi 섹션 추출
# =========================

def extract_wifi_adapter_section(text):
    """
    ipconfig /all 출력에서 실제 Wi-Fi 어댑터 섹션만 추출한다.

    전체 ipconfig를 그대로 파싱하면 이더넷, Bluetooth, 가상 어댑터의
    '미디어 연결 끊김'을 Wi-Fi 문제로 오판할 수 있다.
    """
    lines = text.splitlines()
    start_index = None
    end_index = len(lines)

    for i, line in enumerate(lines):
        stripped = line.strip()
        lower = stripped.lower()

        is_section_header = stripped.endswith(":") and (
            "어댑터" in stripped or "adapter" in lower
        )

        if not is_section_header:
            continue

        # 한국어 Windows
        if stripped.startswith("무선 LAN 어댑터 Wi-Fi"):
            start_index = i
            break

        # 영어 Windows
        if lower.startswith("wireless lan adapter wi-fi"):
            start_index = i
            break

        # Wi-Fi 2, Wi-Fi 3 등 대응
        # Microsoft Wi-Fi Direct Virtual Adapter 같은 가상 어댑터는 제외
        if "wi-fi" in lower and "direct" not in lower and "virtual" not in lower:
            start_index = i
            break

    if start_index is None:
        return text

    for i in range(start_index + 1, len(lines)):
        stripped = lines[i].strip()
        lower = stripped.lower()

        is_next_section_header = stripped.endswith(":") and (
            "어댑터" in stripped or "adapter" in lower
        )

        if is_next_section_header:
            end_index = i
            break

    return "\n".join(lines[start_index:end_index])


# =========================
# netsh wlan show interfaces 파싱
# =========================

def parse_netsh_interfaces(text):
    """
    netsh wlan show interfaces 결과 파싱.

    추출 항목:
    - Wi-Fi 연결 여부
    - SSID
    - BSSID
    - 신호 세기
    - 채널
    - 2.4GHz / 5GHz 대역
    - 수신 속도
    - 전송 속도
    - 인증 방식
    - 암호 방식
    - 프로필

    수정 포인트:
    - Windows 출력에서 BSSID가 'AP BSSID'로 나오는 경우도 처리한다.
    """
    result = {
        "wifi_connected": False,
        "ssid": None,
        "bssid": None,
        "signal_percent": None,
        "channel": None,

        # GUI 보조지표용 추가 값
        "band": None,
        "receive_rate_mbps": None,
        "transmit_rate_mbps": None,
        "auth": None,
        "cipher": None,
        "profile": None,
    }

    lines = text.splitlines()

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        normalized = normalize_spaces(stripped)
        normalized_lower = normalized.lower()

        # 상태: 연결됨 / 연결되지 않음
        if stripped.startswith("상태") or lower.startswith("state"):
            value = extract_value_after_colon(stripped).lower()

            if "연결됨" in value or "connected" in value:
                result["wifi_connected"] = True

            if "연결되지" in value or "disconnected" in value:
                result["wifi_connected"] = False

        # SSID
        # 주의:
        # AP BSSID 줄에 SSID가 포함되어 있으므로,
        # BSSID/AP BSSID 줄은 SSID로 처리하지 않는다.
        if (
            stripped.startswith("SSID")
            and not stripped.startswith("BSSID")
            and not normalized_lower.startswith("ap bssid")
        ):
            value = extract_value_after_colon(stripped)
            if value:
                result["ssid"] = value

        # BSSID / AP BSSID
        # 예:
        # BSSID                   : 00:11:22:33:44:55
        # AP BSSID                : 50:e4:e0:b8:98:f1
        bssid_match = re.match(
            r"^(?:AP\s+)?BSSID\s*:\s*(.+)$",
            normalized,
            flags=re.IGNORECASE,
        )
        if bssid_match:
            value = bssid_match.group(1).strip()
            if value:
                result["bssid"] = value

        # 인증 방식
        if stripped.startswith("인증") or lower.startswith("authentication"):
            value = extract_value_after_colon(stripped)
            if value:
                result["auth"] = value

        # 암호 방식
        if stripped.startswith("암호") or lower.startswith("cipher"):
            value = extract_value_after_colon(stripped)
            if value:
                result["cipher"] = value

        # 채널
        if stripped.startswith("채널") or lower.startswith("channel"):
            value = extract_value_after_colon(stripped)
            match = re.search(r"(\d+)", value)
            if match:
                result["channel"] = int(match.group(1))

        # 수신 속도(Mbps)
        if stripped.startswith("수신 속도") or lower.startswith("receive rate"):
            value = extract_value_after_colon(stripped)
            match = re.search(r"(\d+(?:\.\d+)?)", value)
            if match:
                result["receive_rate_mbps"] = float(match.group(1))

        # 전송 속도(Mbps)
        if stripped.startswith("전송 속도") or lower.startswith("transmit rate"):
            value = extract_value_after_colon(stripped)
            match = re.search(r"(\d+(?:\.\d+)?)", value)
            if match:
                result["transmit_rate_mbps"] = float(match.group(1))

        # 신호
        if stripped.startswith("신호") or lower.startswith("signal"):
            value = extract_value_after_colon(stripped)
            match = re.search(r"(\d+)\s*%", value)
            if match:
                result["signal_percent"] = int(match.group(1))

        # 프로필
        if stripped.startswith("프로필") or lower.startswith("profile"):
            value = extract_value_after_colon(stripped)
            if value:
                result["profile"] = value

    # 인코딩 깨짐 보정:
    # SSID 또는 BSSID가 있으면 연결된 인터페이스 정보로 판단
    if result["ssid"] is not None or result["bssid"] is not None:
        result["wifi_connected"] = True

    # 신호 보정
    if result["signal_percent"] is None:
        percent_matches = re.findall(r"(\d+)\s*%", text)
        if percent_matches:
            result["signal_percent"] = int(percent_matches[-1])

    # 채널 보정
    if result["channel"] is None and result["bssid"] is not None:
        bssid_index = None

        for i, line in enumerate(lines):
            if re.search(r"(?:AP\s+)?BSSID", line, flags=re.IGNORECASE):
                bssid_index = i
                break

        if bssid_index is not None:
            for line in lines[bssid_index + 1:]:
                value = extract_value_after_colon(line.strip())
                match = re.search(r"\b(\d{1,3})\b", value)

                if match:
                    number = int(match.group(1))

                    if 1 <= number <= 196:
                        result["channel"] = number
                        break

    # 채널 기반 대역 표시
    if result["channel"] is not None:
        if 1 <= result["channel"] <= 14:
            result["band"] = "2.4GHz"
        elif result["channel"] >= 30:
            result["band"] = "5GHz"
        else:
            result["band"] = "확인 불가"

    # 인코딩이 깨져서 수신/전송 속도 라벨을 못 읽은 경우 보정
    # 예: 433.3, 433.3 같은 소수점 속도값은 남아 있는 경우가 많음
    if result["receive_rate_mbps"] is None or result["transmit_rate_mbps"] is None:
        decimal_numbers = re.findall(r"\b(\d+\.\d+)\b", text)

        speed_candidates = []
        for value in decimal_numbers:
            number = float(value)

            # 채널, 퍼센트 같은 값이 아니라 무선 속도 후보만 대략 추림
            if number >= 10:
                speed_candidates.append(number)

        if len(speed_candidates) >= 2:
            if result["receive_rate_mbps"] is None:
                result["receive_rate_mbps"] = speed_candidates[-2]

            if result["transmit_rate_mbps"] is None:
                result["transmit_rate_mbps"] = speed_candidates[-1]

    return result


# =========================
# netsh wlan show networks mode=bssid 파싱
# =========================

def parse_netsh_networks_bssid(text):
    """
    netsh wlan show networks mode=bssid 결과 파싱.

    목적:
    - 주변에서 eduroam SSID가 감지되는지 확인
    - eduroam 관련 BSSID 개수 확인
    - 가장 강한 eduroam 신호 세기 확인

    주의:
    현재는 1차 개발용 단순 파싱이다.
    """
    result = {
        "eduroam_detected": False,
        "eduroam_bssid_count": 0,
        "strongest_eduroam_signal_percent": None,
    }

    lines = text.splitlines()
    current_ssid_is_eduroam = False

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        # SSID 줄 감지
        # 예: SSID 1 : eduroam
        # 예: SSID 2 : WiFi_Name
        if lower.startswith("ssid"):
            value = extract_value_after_colon(stripped)

            if value.lower() == "eduroam":
                result["eduroam_detected"] = True
                current_ssid_is_eduroam = True
            else:
                current_ssid_is_eduroam = False

        # eduroam 블록 안의 BSSID 개수
        if current_ssid_is_eduroam and "bssid" in lower:
            result["eduroam_bssid_count"] += 1

        # eduroam 블록 안의 신호 세기
        if current_ssid_is_eduroam:
            if "신호" in stripped or "signal" in lower:
                value = extract_value_after_colon(stripped)
                match = re.search(r"(\d+)\s*%", value)

                if match:
                    signal = int(match.group(1))

                    if result["strongest_eduroam_signal_percent"] is None:
                        result["strongest_eduroam_signal_percent"] = signal
                    else:
                        result["strongest_eduroam_signal_percent"] = max(
                            result["strongest_eduroam_signal_percent"],
                            signal
                        )

    # 인코딩 깨짐 또는 구조 차이 보정
    if not result["eduroam_detected"] and "eduroam" in text.lower():
        result["eduroam_detected"] = True

    # BSSID 개수 보정
    if result["eduroam_bssid_count"] == 0 and result["eduroam_detected"]:
        bssid_matches = re.findall(
            r"([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}|[0-9a-fA-F]{2}(?:-[0-9a-fA-F]{2}){5})",
            text
        )
        result["eduroam_bssid_count"] = len(bssid_matches)

    # 신호 세기 보정
    if result["strongest_eduroam_signal_percent"] is None and result["eduroam_detected"]:
        signal_matches = re.findall(r"(\d+)\s*%", text)

        if signal_matches:
            result["strongest_eduroam_signal_percent"] = max(
                int(value) for value in signal_matches
            )

    return result


# =========================
# ipconfig /all 파싱
# =========================

def parse_ipconfig_all(text):
    """
    ipconfig /all 결과 파싱.

    핵심 판단 항목:
    - IPv4 주소
    - 169.254.x.x APIPA 여부
    - 기본 게이트웨이
    - DNS 서버
    - DHCP 사용 여부
    - Wi-Fi 미디어 연결 끊김 여부
    """
    text = extract_wifi_adapter_section(text)

    result = {
        "ipv4_address": None,
        "is_apipa": False,
        "has_ipv4": False,
        "gateway": None,
        "has_gateway": False,
        "dns_servers": [],
        "has_dns": False,
        "dhcp_enabled": None,
        "media_disconnected": False,
    }

    lines = text.splitlines()

    for index, line in enumerate(lines):
        stripped = line.strip()
        lower = stripped.lower()

        # 미디어 연결 끊김
        if "미디어 연결 끊김" in stripped or "media disconnected" in lower:
            result["media_disconnected"] = True

        # DHCP 사용
        if stripped.startswith("DHCP 사용") or lower.startswith("dhcp enabled"):
            value = extract_value_after_colon(stripped).lower()

            if "예" in value or "yes" in value:
                result["dhcp_enabled"] = True
            elif "아니요" in value or "no" in value:
                result["dhcp_enabled"] = False

        # IPv4 주소
        if "IPv4" in stripped or "ipv4" in lower:
            value = extract_value_after_colon(stripped)
            ipv4 = extract_first_ipv4(value)

            if ipv4:
                result["ipv4_address"] = ipv4
                result["has_ipv4"] = True

                if ipv4.startswith("169.254."):
                    result["is_apipa"] = True

        # 기본 게이트웨이
        if stripped.startswith("기본 게이트웨이") or lower.startswith("default gateway"):
            value = extract_value_after_colon(stripped)
            gateway = extract_first_ipv4(value)

            if gateway:
                result["gateway"] = gateway
                result["has_gateway"] = True
            else:
                # Windows 출력은 다음 줄에 게이트웨이가 나오는 경우가 있음
                if index + 1 < len(lines):
                    next_line = lines[index + 1].strip()
                    next_gateway = extract_first_ipv4(next_line)

                    if next_gateway:
                        result["gateway"] = next_gateway
                        result["has_gateway"] = True

        # DNS 서버
        if stripped.startswith("DNS 서버") or lower.startswith("dns servers"):
            value = extract_value_after_colon(stripped)

            dns_matches = re.findall(r"(\d{1,3}(?:\.\d{1,3}){3})", value)
            result["dns_servers"].extend(dns_matches)

            # 다음 줄에 이어지는 DNS 주소 파싱
            next_index = index + 1

            while next_index < len(lines):
                next_line = lines[next_index].strip()

                if not next_line:
                    break

                # 다음 설정 항목이 시작되면 종료
                if ":" in next_line:
                    break

                extra_dns = re.findall(r"(\d{1,3}(?:\.\d{1,3}){3})", next_line)

                if extra_dns:
                    result["dns_servers"].extend(extra_dns)
                    next_index += 1
                else:
                    break

    # 보정:
    # 한글 키워드가 깨져 IPv4 라벨을 못 찾는 경우,
    # Wi-Fi 섹션 안에서 IPv4 후보를 직접 찾는다.
    if not result["has_ipv4"]:
        ip_candidates = re.findall(r"(\d{1,3}(?:\.\d{1,3}){3})", text)

        # APIPA 주소는 connected_no_ip 판단에 중요하므로 최우선
        for ip in ip_candidates:
            if ip.startswith("169.254."):
                result["ipv4_address"] = ip
                result["has_ipv4"] = True
                result["is_apipa"] = True
                break

        # APIPA가 없으면 사설 IP 대역을 IPv4 후보로 사용
        if not result["has_ipv4"]:
            for ip in ip_candidates:
                if (
                    ip.startswith("10.")
                    or ip.startswith("172.")
                    or ip.startswith("192.168.")
                ):
                    result["ipv4_address"] = ip
                    result["has_ipv4"] = True
                    break

    result["dns_servers"] = list(dict.fromkeys(result["dns_servers"]))
    result["has_dns"] = len(result["dns_servers"]) > 0

    return result


# =========================
# ping 결과 파싱
# =========================

def parse_ping(text):
    """
    ping 결과 파싱.

    추출 항목:
    - 성공 여부
    - 손실률
    - 평균 지연시간
    - 호스트 찾기 실패 여부
    - 일반 오류 여부
    - 도메인이 IP로 변환되었는지
    """
    result = {
        "success": False,
        "packet_loss_percent": None,
        "avg_latency_ms": None,
        "host_not_found": False,
        "general_failure": False,
        "resolved_ip": None,
    }

    lower_text = text.lower()

    # 호스트 찾기 실패
    if "호스트를 찾을 수 없습니다" in text or "could not find host" in lower_text:
        result["host_not_found"] = True

    # 일반 오류
    if "일반 오류" in text or "general failure" in lower_text:
        result["general_failure"] = True

    # timeout 문구
    if "시간이 초과" in text or "timed out" in lower_text:
        # timeout 자체만으로 success를 결정하지는 않고,
        # 아래 packet loss가 있으면 packet loss 기준으로 판단한다.
        pass

    # 예: Ping google.com [142.250.207.110] 32바이트 데이터 사용
    resolved_match = re.search(r"\[(\d{1,3}(?:\.\d{1,3}){3})\]", text)
    if resolved_match:
        result["resolved_ip"] = resolved_match.group(1)

    # 손실률
    # 예: 손실 = 0 (0% 손실)
    # 예: Lost = 0 (0% loss)
    loss_match = re.search(r"\((\d+)%\s*손실\)", text)
    if not loss_match:
        loss_match = re.search(r"\((\d+)%\s*loss\)", lower_text)

    if loss_match:
        result["packet_loss_percent"] = int(loss_match.group(1))

    # 평균 지연시간
    # 예: 평균 = 61ms
    # 예: Average = 61ms
    avg_match = re.search(r"평균\s*=\s*(\d+)ms", text)
    if not avg_match:
        avg_match = re.search(r"average\s*=\s*(\d+)ms", lower_text)

    if avg_match:
        result["avg_latency_ms"] = int(avg_match.group(1))

    # 성공 판단
    if result["packet_loss_percent"] is not None:
        result["success"] = result["packet_loss_percent"] < 100

    # 호스트 찾기 실패나 일반 오류면 실패로 고정
    if result["host_not_found"] or result["general_failure"]:
        result["success"] = False

    return result


# =========================
# nslookup 결과 파싱
# =========================

def parse_nslookup(text):
    """
    nslookup google.com 결과 파싱.

    핵심:
    - DNS 서버 이름
    - DNS 서버 주소
    - google.com 주소가 반환되었는지

    수정 포인트:
    - 기존 방식은 Address 줄의 IP를 모두 resolved_addresses에 넣었다.
    - 그러면 DNS 서버 주소만 있어도 google.com 응답 주소처럼 오판할 수 있다.
    - 이제 Server/서버 바로 다음의 Address는 dns_server_address로 분리하고,
      Name/이름 이후에 나오는 Address만 resolved_addresses로 본다.
    """
    result = {
        "success": False,
        "dns_server": None,
        "dns_server_address": None,
        "resolved_addresses": [],
    }

    lines = text.splitlines()
    lower_text = text.lower()

    in_answer_section = False
    last_key_was_server = False

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if not stripped:
            continue

        # Server: 또는 서버:
        if lower.startswith("server") or stripped.startswith("서버"):
            value = extract_value_after_colon(stripped)
            if value:
                result["dns_server"] = value
            last_key_was_server = True
            continue

        # Name: 또는 이름:
        # 이 이후의 Address / Addresses는 실제 조회 대상 응답으로 판단한다.
        if lower.startswith("name") or stripped.startswith("이름"):
            in_answer_section = True
            last_key_was_server = False
            continue

        # Non-authoritative answer 문구 이후에도 응답 영역으로 판단
        if "non-authoritative answer" in lower or "권한 없는 응답" in stripped:
            in_answer_section = True
            last_key_was_server = False
            continue

        ip_matches = re.findall(r"(\d{1,3}(?:\.\d{1,3}){3})", stripped)

        if not ip_matches:
            last_key_was_server = False
            continue

        # Server/서버 바로 다음 Address는 DNS 서버 주소로 본다.
        # 예:
        # 서버:    kns.kornet.net
        # Address: 168.126.63.1
        if last_key_was_server and (
            lower.startswith("address")
            or lower.startswith("addresses")
            or stripped.startswith("주소")
        ):
            result["dns_server_address"] = ip_matches[0]
            last_key_was_server = False
            continue

        # Name/이름 이후의 Address는 google.com 조회 결과로 본다.
        if in_answer_section:
            for ip in ip_matches:
                result["resolved_addresses"].append(ip)

        last_key_was_server = False

    result["resolved_addresses"] = list(dict.fromkeys(result["resolved_addresses"]))

    meaningful_addresses = [
        ip for ip in result["resolved_addresses"]
        if not is_invalid_loopback_or_placeholder_ip(ip)
    ]

    # 성공 판단:
    # - google 관련 조회 결과이고
    # - 의미 있는 응답 IP가 하나 이상 있어야 성공
    if "google" in lower_text and len(meaningful_addresses) > 0:
        result["success"] = True

    # 실패 문구 보정
    failure_patterns = [
        "can't find",
        "cannot find",
        "could not find",
        "non-existent domain",
        "dns request timed out",
        "request timed out",
        "timeout",
        "시간이 초과",
        "찾을 수 없습니다",
    ]

    if any(pattern in lower_text for pattern in failure_patterns):
        # 실패 문구가 있고 실제 응답 주소가 없으면 실패
        if len(meaningful_addresses) == 0:
            result["success"] = False

    return result


# =========================
# 하나의 sample case 폴더 파싱
# =========================

def parse_sample_case(case_dir):
    """
    하나의 sample case 폴더를 읽어서 전체 진단 입력 데이터로 변환한다.

    예:
    parse_sample_case("samples/case1_normal")
    """
    case_path = Path(case_dir)

    netsh_interfaces_text = read_text_file(case_path / "netsh_interfaces.txt")
    netsh_networks_text = read_text_file(case_path / "netsh_networks_bssid.txt")
    ipconfig_text = read_text_file(case_path / "ipconfig_all.txt")
    ping_8_text = read_text_file(case_path / "ping_8_8_8_8.txt")
    ping_google_text = read_text_file(case_path / "ping_google.txt")
    nslookup_text = read_text_file(case_path / "nslookup_google.txt")

    parsed = {
        "case_name": case_path.name,
        "netsh_interfaces": parse_netsh_interfaces(netsh_interfaces_text),
        "netsh_networks_bssid": parse_netsh_networks_bssid(netsh_networks_text),
        "ipconfig": parse_ipconfig_all(ipconfig_text),
        "ping_8_8_8_8": parse_ping(ping_8_text),
        "ping_google": parse_ping(ping_google_text),
        "nslookup_google": parse_nslookup(nslookup_text),
    }

    return parsed


# =========================
# 실제 collector 결과 파싱용
# =========================

def parse_collected_outputs(raw_outputs):
    """
    실제 프로그램에서 collector.py가 수집한 원문 결과를 파싱한다.

    collector.py는 아래 형태의 dict를 반환하면 된다.

    {
        "netsh_interfaces": "...",
        "netsh_networks_bssid": "...",
        "ipconfig_all": "...",
        "ping_8_8_8_8": "...",
        "ping_google": "...",
        "nslookup_google": "..."
    }
    """
    parsed = {
        "case_name": "live",
        "netsh_interfaces": parse_netsh_interfaces(
            raw_outputs.get("netsh_interfaces", "")
        ),
        "netsh_networks_bssid": parse_netsh_networks_bssid(
            raw_outputs.get("netsh_networks_bssid", "")
        ),
        "ipconfig": parse_ipconfig_all(
            raw_outputs.get("ipconfig_all", "")
        ),
        "ping_8_8_8_8": parse_ping(
            raw_outputs.get("ping_8_8_8_8", "")
        ),
        "ping_google": parse_ping(
            raw_outputs.get("ping_google", "")
        ),
        "nslookup_google": parse_nslookup(
            raw_outputs.get("nslookup_google", "")
        ),
    }

    return parsed


# =========================
# 직접 실행 테스트
# =========================

if __name__ == "__main__":
    from pprint import pprint

    sample_cases = [
        "samples/case1_normal",
        "samples/case2_disconnected",
        "samples/case3_1_connected_no_ip",
        "samples/case3_2_dns_fail",
        "samples/case3_3_external_ping_fail",
    ]

    for case in sample_cases:
        print("=" * 80)
        print(case)
        print("=" * 80)

        parsed = parse_sample_case(case)

        pprint({
            "case_name": parsed["case_name"],
            "netsh_interfaces": parsed["netsh_interfaces"],
            "netsh_networks_bssid": parsed["netsh_networks_bssid"],
            "ipconfig": parsed["ipconfig"],
            "ping_8_8_8_8": parsed["ping_8_8_8_8"],
            "ping_google": parsed["ping_google"],
            "nslookup_google": parsed["nslookup_google"],
        })

        print()