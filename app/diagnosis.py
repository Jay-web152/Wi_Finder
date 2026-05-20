# app/diagnosis.py
"""
Wi_Finder diagnosis module

parser.py가 만든 파싱 결과(dict)를 받아서
Wi-Fi 접속 상태를 사람이 이해하기 쉬운 진단 결과로 변환한다.

진단 대상 case:
- NORMAL
- DISCONNECTED
- CONNECTED_NO_IP
- DNS_FAIL
- EXTERNAL_PING_FAIL
- UNKNOWN
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


# =========================
# 진단 코드 상수
# =========================

NORMAL = "NORMAL"
DISCONNECTED = "DISCONNECTED"
CONNECTED_NO_IP = "CONNECTED_NO_IP"
DNS_FAIL = "DNS_FAIL"
EXTERNAL_PING_FAIL = "EXTERNAL_PING_FAIL"
UNKNOWN = "UNKNOWN"


# =========================
# 진단 결과 모델
# =========================

@dataclass
class DiagnosisResult:
    code: str
    level: str
    title: str
    summary: str
    possible_causes: List[str]
    recommended_actions: List[str]
    indicators: Dict[str, Any]
    detail: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =========================
# 안전한 값 추출 함수
# =========================

def _get_section(parsed: Dict[str, Any], section_name: str) -> Dict[str, Any]:
    value = parsed.get(section_name)
    if isinstance(value, dict):
        return value
    return {}


def _get_bool(section: Dict[str, Any], key: str, default: bool = False) -> bool:
    value = section.get(key, default)
    return bool(value)


def _get_int(section: Dict[str, Any], key: str, default: Optional[int] = None) -> Optional[int]:
    value = section.get(key, default)

    if value is None:
        return default

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_float(section: Dict[str, Any], key: str, default: Optional[float] = None) -> Optional[float]:
    value = section.get(key, default)

    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_str(section: Dict[str, Any], key: str, default: Optional[str] = None) -> Optional[str]:
    value = section.get(key, default)

    if value is None:
        return default

    return str(value)


def _is_success(section: Dict[str, Any]) -> bool:
    return bool(section.get("success", False))


def _has_valid_dns_server(dns_servers: Any) -> bool:
    """
    DNS 서버가 있는지 판단한다.

    parser.py 기준:
    - dns_servers: list[str]
    - 127.0.0.1만 있는 경우는 정상 DNS로 보기 어렵다.
    """
    if not dns_servers:
        return False

    if not isinstance(dns_servers, list):
        return False

    valid_servers = [
        server for server in dns_servers
        if server and server != "127.0.0.1"
    ]

    return len(valid_servers) > 0


def _has_valid_resolved_addresses(addresses: Any) -> bool:
    """
    nslookup 결과 주소가 정상적인지 판단한다.

    127.0.0.1만 있는 경우는 정상 DNS 조회 성공으로 보지 않는다.
    """
    if not addresses:
        return False

    if not isinstance(addresses, list):
        return False

    valid_addresses = [
        address for address in addresses
        if address and address != "127.0.0.1"
    ]

    return len(valid_addresses) > 0


# =========================
# 지표 생성 함수
# =========================

def _build_indicators(parsed: Dict[str, Any]) -> Dict[str, Any]:
    netsh = _get_section(parsed, "netsh_interfaces")
    bssid_info = _get_section(parsed, "netsh_networks_bssid")
    ipconfig = _get_section(parsed, "ipconfig")
    ping_8 = _get_section(parsed, "ping_8_8_8_8")
    ping_google = _get_section(parsed, "ping_google")
    nslookup = _get_section(parsed, "nslookup_google")

    wifi_connected = _get_bool(netsh, "wifi_connected")
    ssid = _get_str(netsh, "ssid")
    signal_percent = _get_int(netsh, "signal_percent")
    band = _get_str(netsh, "band")
    channel = _get_int(netsh, "channel")
    receive_rate = _get_float(netsh, "receive_rate_mbps")
    transmit_rate = _get_float(netsh, "transmit_rate_mbps")

    ipv4_address = _get_str(ipconfig, "ipv4_address")
    is_apipa = _get_bool(ipconfig, "is_apipa")
    has_ipv4 = _get_bool(ipconfig, "has_ipv4")
    has_gateway = _get_bool(ipconfig, "has_gateway")
    has_dns = _get_bool(ipconfig, "has_dns")
    dns_servers = ipconfig.get("dns_servers", [])

    ping_8_success = _is_success(ping_8)
    ping_google_success = _is_success(ping_google)
    nslookup_success = _is_success(nslookup)

    dns_lookup_valid = nslookup_success and _has_valid_resolved_addresses(
        nslookup.get("resolved_addresses", [])
    )

    eduroam_detected = _get_bool(bssid_info, "eduroam_detected")
    eduroam_bssid_count = _get_int(bssid_info, "eduroam_bssid_count", 0)
    strongest_eduroam_signal = _get_int(
        bssid_info,
        "strongest_eduroam_signal_percent"
    )

    return {
        "wifi": {
            "connected": wifi_connected,
            "ssid": ssid,
            "signal_percent": signal_percent,
            "band": band,
            "channel": channel,
            "receive_rate_mbps": receive_rate,
            "transmit_rate_mbps": transmit_rate,
        },
        "nearby_eduroam": {
            "detected": eduroam_detected,
            "bssid_count": eduroam_bssid_count,
            "strongest_signal_percent": strongest_eduroam_signal,
        },
        "ip": {
            "ipv4_address": ipv4_address,
            "has_ipv4": has_ipv4,
            "is_apipa": is_apipa,
            "has_gateway": has_gateway,
        },
        "dns": {
            "has_dns": has_dns,
            "dns_servers": dns_servers,
            "has_valid_dns_server": _has_valid_dns_server(dns_servers),
            "nslookup_success": nslookup_success,
            "dns_lookup_valid": dns_lookup_valid,
        },
        "internet": {
            "ping_8_8_8_8_success": ping_8_success,
            "ping_google_success": ping_google_success,
            "ping_8_8_8_8_loss_percent": ping_8.get("packet_loss_percent"),
            "ping_google_loss_percent": ping_google.get("packet_loss_percent"),
            "ping_8_8_8_8_avg_latency_ms": ping_8.get("avg_latency_ms"),
            "ping_google_avg_latency_ms": ping_google.get("avg_latency_ms"),
        },
    }


def _build_detail(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    GUI 상세 정보 영역에 넣기 좋은 원본 요약 데이터.
    """
    netsh = _get_section(parsed, "netsh_interfaces")
    bssid_info = _get_section(parsed, "netsh_networks_bssid")
    ipconfig = _get_section(parsed, "ipconfig")
    ping_8 = _get_section(parsed, "ping_8_8_8_8")
    ping_google = _get_section(parsed, "ping_google")
    nslookup = _get_section(parsed, "nslookup_google")

    return {
        "ssid": netsh.get("ssid"),
        "bssid": netsh.get("bssid"),
        "profile": netsh.get("profile"),
        "auth": netsh.get("auth"),
        "cipher": netsh.get("cipher"),
        "signal_percent": netsh.get("signal_percent"),
        "band": netsh.get("band"),
        "channel": netsh.get("channel"),
        "receive_rate_mbps": netsh.get("receive_rate_mbps"),
        "transmit_rate_mbps": netsh.get("transmit_rate_mbps"),
        "eduroam_detected": bssid_info.get("eduroam_detected"),
        "eduroam_bssid_count": bssid_info.get("eduroam_bssid_count"),
        "strongest_eduroam_signal_percent": bssid_info.get(
            "strongest_eduroam_signal_percent"
        ),
        "ipv4_address": ipconfig.get("ipv4_address"),
        "gateway": ipconfig.get("gateway"),
        "dns_servers": ipconfig.get("dns_servers"),
        "dhcp_enabled": ipconfig.get("dhcp_enabled"),
        "media_disconnected": ipconfig.get("media_disconnected"),
        "ping_8_8_8_8": ping_8,
        "ping_google": ping_google,
        "nslookup_google": nslookup,
    }


# =========================
# 핵심 진단 함수
# =========================

def diagnose(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    parser.py의 결과 dict를 받아 진단 결과 dict를 반환한다.

    판단 순서가 매우 중요하다.

    1. Wi-Fi 미연결
    2. IP 없음 또는 APIPA
    3. IP 있음 + 8.8.8.8 ping 성공 + DNS 실패
    4. DNS 성공 + 외부 ping 실패
    5. 정상
    """

    netsh = _get_section(parsed, "netsh_interfaces")
    bssid_info = _get_section(parsed, "netsh_networks_bssid")
    ipconfig = _get_section(parsed, "ipconfig")
    ping_8 = _get_section(parsed, "ping_8_8_8_8")
    ping_google = _get_section(parsed, "ping_google")
    nslookup = _get_section(parsed, "nslookup_google")

    indicators = _build_indicators(parsed)
    detail = _build_detail(parsed)

    wifi_connected = _get_bool(netsh, "wifi_connected")
    ssid = _get_str(netsh, "ssid")

    eduroam_detected = _get_bool(bssid_info, "eduroam_detected")
    strongest_eduroam_signal = _get_int(
        bssid_info,
        "strongest_eduroam_signal_percent"
    )

    has_ipv4 = _get_bool(ipconfig, "has_ipv4")
    is_apipa = _get_bool(ipconfig, "is_apipa")
    has_gateway = _get_bool(ipconfig, "has_gateway")
    dns_servers = ipconfig.get("dns_servers", [])

    ping_8_success = _is_success(ping_8)
    ping_google_success = _is_success(ping_google)

    nslookup_success = _is_success(nslookup)
    nslookup_valid = nslookup_success and _has_valid_resolved_addresses(
        nslookup.get("resolved_addresses", [])
    )

    has_valid_dns_server = _has_valid_dns_server(dns_servers)

    # =========================
    # 1. Wi-Fi 미연결
    # =========================
    if not wifi_connected:
        if eduroam_detected:
            summary = (
                "eduroam은 주변에서 감지되지만 현재 단말은 Wi-Fi에 연결되어 있지 않습니다."
            )
        else:
            summary = (
                "현재 단말이 Wi-Fi에 연결되어 있지 않고 주변에서 eduroam도 감지되지 않았습니다."
            )

        return DiagnosisResult(
            code=DISCONNECTED,
            level="error",
            title="Wi-Fi가 연결되어 있지 않음",
            summary=summary,
            possible_causes=[
                "사용자가 eduroam에 연결하지 않음",
                "Wi-Fi 어댑터가 꺼져 있음",
                "eduroam 프로필 설정 오류",
                "인증 정보 또는 계정 정보 오류",
                "주변 AP 신호는 있으나 자동 연결이 실패함",
            ],
            recommended_actions=[
                "Windows Wi-Fi 목록에서 eduroam을 직접 선택해 연결해보세요.",
                "Wi-Fi가 켜져 있는지 확인하세요.",
                "eduroam 프로필을 삭제한 뒤 다시 설정해보세요.",
                "학교 계정 ID와 비밀번호가 올바른지 확인하세요.",
                "같은 장소에서 다른 사람의 eduroam 연결 여부를 확인해보세요.",
            ],
            indicators=indicators,
            detail={
                **detail,
                "diagnosis_note": {
                    "eduroam_detected": eduroam_detected,
                    "strongest_eduroam_signal_percent": strongest_eduroam_signal,
                    "important": "이 상태에서는 ping 결과보다 Wi-Fi 연결 상태를 우선 판단합니다.",
                },
            },
        ).to_dict()

    # =========================
    # 2. Wi-Fi 연결됨 + IP 없음/APIPA
    # =========================
    if not has_ipv4 or is_apipa or not has_gateway:
        return DiagnosisResult(
            code=CONNECTED_NO_IP,
            level="error",
            title="Wi-Fi는 연결됐지만 IP를 정상적으로 받지 못함",
            summary=(
                "eduroam에는 연결되어 있지만 정상적인 IPv4 주소나 게이트웨이를 받지 못했습니다. "
                "DHCP 또는 네트워크 IP 할당 문제일 가능성이 큽니다."
            ),
            possible_causes=[
                "DHCP 서버 응답 실패",
                "AP 또는 네트워크 장비의 IP 할당 문제",
                "인증은 되었지만 내부 네트워크 진입이 정상 처리되지 않음",
                "Windows 네트워크 설정 문제",
                "일시적인 AP 또는 컨트롤러 장애",
            ],
            recommended_actions=[
                "Wi-Fi 연결을 끊었다가 다시 연결해보세요.",
                "명령 프롬프트에서 ipconfig /release 후 ipconfig /renew를 실행해보세요.",
                "노트북을 재부팅한 뒤 다시 연결해보세요.",
                "같은 장소에서 다른 사용자도 IP를 받지 못하는지 확인해보세요.",
                "관리자에게 DHCP 또는 AP 상태 점검을 요청하세요.",
            ],
            indicators=indicators,
            detail=detail,
        ).to_dict()

    # =========================
    # 3. DNS 실패
    # 조건:
    # - Wi-Fi 연결됨
    # - IP 정상
    # - 게이트웨이 있음
    # - 8.8.8.8 ping 성공
    # - google.com ping 실패 또는 nslookup 실패
    # =========================
    dns_failed = (
        ping_8_success
        and has_ipv4
        and has_gateway
        and (
            not ping_google_success
            or not nslookup_valid
            or not has_valid_dns_server
        )
    )

    if dns_failed:
        return DiagnosisResult(
            code=DNS_FAIL,
            level="warning",
            title="DNS 문제로 웹사이트 주소를 찾지 못함",
            summary=(
                "인터넷 IP로 직접 통신은 가능하지만 google.com 같은 도메인 주소 변환에 실패했습니다. "
                "DNS 서버 설정 또는 DNS 응답 문제일 가능성이 큽니다."
            ),
            possible_causes=[
                "DNS 서버가 127.0.0.1 등 비정상 값으로 설정됨",
                "DNS 서버 응답 실패",
                "학교 내부 DNS 또는 통신사 DNS 문제",
                "보안 프로그램 또는 VPN이 DNS 요청을 가로챔",
                "일시적인 DNS 캐시 문제",
            ],
            recommended_actions=[
                "Wi-Fi를 끊었다가 다시 연결해보세요.",
                "명령 프롬프트에서 ipconfig /flushdns를 실행해보세요.",
                "DNS 서버 값이 정상적으로 할당되었는지 확인하세요.",
                "VPN 또는 보안 프로그램을 잠시 비활성화한 뒤 다시 확인해보세요.",
                "관리자에게 DNS 서버 상태 점검을 요청하세요.",
            ],
            indicators=indicators,
            detail=detail,
        ).to_dict()

    # =========================
    # 4. 외부 Ping 실패
    # 조건:
    # - Wi-Fi 연결됨
    # - IP 정상
    # - DNS 조회 정상
    # - 8.8.8.8 ping 실패
    # =========================
    external_ping_failed = (
        has_ipv4
        and has_gateway
        and nslookup_valid
        and not ping_8_success
    )

    if external_ping_failed:
        return DiagnosisResult(
            code=EXTERNAL_PING_FAIL,
            level="warning",
            title="DNS는 정상이나 외부 통신이 실패함",
            summary=(
                "웹사이트 주소 확인은 가능하지만 외부 IP로 ping 통신이 실패했습니다. "
                "방화벽, 보안 프로그램, 라우팅, 네트워크 장비 문제일 수 있습니다."
            ),
            possible_causes=[
                "외부 ICMP ping 차단",
                "방화벽 또는 보안 프로그램 차단",
                "VPN 또는 프록시 설정 문제",
                "라우팅 문제",
                "학교 네트워크 장비 또는 상위 회선 문제",
            ],
            recommended_actions=[
                "웹 브라우저로 실제 인터넷 접속이 되는지 확인해보세요.",
                "보안 프로그램 또는 VPN을 잠시 끄고 다시 테스트해보세요.",
                "다른 사이트 접속도 실패하는지 확인하세요.",
                "같은 장소의 다른 사용자도 외부 접속이 안 되는지 확인하세요.",
                "관리자에게 방화벽, 라우팅, 상위 회선 상태 점검을 요청하세요.",
            ],
            indicators=indicators,
            detail=detail,
        ).to_dict()

    # =========================
    # 5. 정상
    # 조건:
    # - Wi-Fi 연결됨
    # - IP 정상
    # - 게이트웨이 있음
    # - DNS 정상
    # - ping 성공
    # =========================
    normal = (
        wifi_connected
        and ssid is not None
        and has_ipv4
        and not is_apipa
        and has_gateway
        and has_valid_dns_server
        and nslookup_valid
        and ping_8_success
        and ping_google_success
    )

    if normal:
        return DiagnosisResult(
            code=NORMAL,
            level="success",
            title="Wi-Fi 연결 정상",
            summary=(
                "eduroam 연결, IP 할당, DNS 조회, 외부 통신이 모두 정상으로 확인되었습니다."
            ),
            possible_causes=[],
            recommended_actions=[
                "현재 네트워크 상태는 정상입니다.",
                "문제가 특정 웹사이트에서만 발생한다면 해당 사이트 또는 브라우저 문제일 수 있습니다.",
            ],
            indicators=indicators,
            detail=detail,
        ).to_dict()

    # =========================
    # 6. 알 수 없는 상태
    # =========================
    return DiagnosisResult(
        code=UNKNOWN,
        level="unknown",
        title="정확한 원인을 분류하기 어려움",
        summary=(
            "수집된 결과만으로는 정상, DNS 문제, IP 할당 문제, 외부 통신 문제 중 하나로 "
            "명확하게 분류하기 어렵습니다."
        ),
        possible_causes=[
            "일부 명령어 결과 누락",
            "ping 또는 nslookup 결과가 비일관적임",
            "네트워크가 테스트 중간에 변동됨",
            "방화벽 정책 때문에 ping 결과만 실패함",
            "parser.py에서 일부 값을 제대로 추출하지 못함",
        ],
        recommended_actions=[
            "같은 위치에서 다시 진단을 실행해보세요.",
            "수집된 txt 파일이 모두 존재하는지 확인하세요.",
            "Wi-Fi 연결 직후 바로 테스트하지 말고 10초 정도 기다린 뒤 다시 실행해보세요.",
            "브라우저 접속 여부도 함께 확인하세요.",
            "필요하면 원본 명령어 결과 txt 파일을 확인하세요.",
        ],
        indicators=indicators,
        detail=detail,
    ).to_dict()


# =========================
# GUI 표시용 간단 요약 생성
# =========================

def build_display_summary(diagnosis: Dict[str, Any]) -> Dict[str, Any]:
    """
    GUI 카드형 대시보드에서 바로 쓰기 쉬운 요약 데이터 생성.

    gui.py나 display.py에서 이 함수를 사용하면 된다.
    """

    indicators = diagnosis.get("indicators", {})

    wifi = indicators.get("wifi", {})
    ip = indicators.get("ip", {})
    dns = indicators.get("dns", {})
    internet = indicators.get("internet", {})

    code = diagnosis.get("code", UNKNOWN)

    return {
        "status_code": code,
        "level": diagnosis.get("level"),
        "title": diagnosis.get("title"),
        "summary": diagnosis.get("summary"),
        "cards": [
            {
                "name": "Wi-Fi 연결 상태",
                "value": "연결됨" if wifi.get("connected") else "연결 안 됨",
                "status": "success" if wifi.get("connected") else "error",
            },
            {
                "name": "연결된 Wi-Fi",
                "value": wifi.get("ssid") or "-",
                "status": "success" if wifi.get("ssid") else "warning",
            },
            {
                "name": "신호 세기",
                "value": (
                    f"{wifi.get('signal_percent')}%"
                    if wifi.get("signal_percent") is not None
                    else "-"
                ),
                "status": _signal_status(wifi.get("signal_percent")),
            },
            {
                "name": "IP 주소 상태",
                "value": _ip_status_text(ip),
                "status": _ip_status_level(ip),
            },
            {
                "name": "인터넷 연결",
                "value": (
                    "정상"
                    if internet.get("ping_8_8_8_8_success")
                    else "실패"
                ),
                "status": (
                    "success"
                    if internet.get("ping_8_8_8_8_success")
                    else "error"
                ),
            },
            {
                "name": "웹사이트 주소 확인",
                "value": (
                    "정상"
                    if dns.get("dns_lookup_valid")
                    else "실패"
                ),
                "status": (
                    "success"
                    if dns.get("dns_lookup_valid")
                    else "error"
                ),
            },
            {
                "name": "응답 속도",
                "value": _latency_text(internet),
                "status": _latency_status(internet),
            },
            {
                "name": "무선 연결 속도",
                "value": _wifi_rate_text(wifi),
                "status": "info",
            },
            {
                "name": "채널",
                "value": _channel_text(wifi),
                "status": "info",
            },
        ],
    }


def _signal_status(signal_percent: Any) -> str:
    if signal_percent is None:
        return "unknown"

    try:
        signal = int(signal_percent)
    except (TypeError, ValueError):
        return "unknown"

    if signal >= 70:
        return "success"
    if signal >= 40:
        return "warning"
    return "error"


def _ip_status_text(ip: Dict[str, Any]) -> str:
    if not ip.get("has_ipv4"):
        return "IPv4 없음"

    if ip.get("is_apipa"):
        return "APIPA 주소"

    if not ip.get("has_gateway"):
        return "게이트웨이 없음"

    return "정상"


def _ip_status_level(ip: Dict[str, Any]) -> str:
    if not ip.get("has_ipv4"):
        return "error"

    if ip.get("is_apipa"):
        return "error"

    if not ip.get("has_gateway"):
        return "warning"

    return "success"


def _latency_text(internet: Dict[str, Any]) -> str:
    latency = internet.get("ping_8_8_8_8_avg_latency_ms")

    if latency is None:
        latency = internet.get("ping_google_avg_latency_ms")

    if latency is None:
        return "-"

    return f"{latency} ms"


def _latency_status(internet: Dict[str, Any]) -> str:
    latency = internet.get("ping_8_8_8_8_avg_latency_ms")

    if latency is None:
        latency = internet.get("ping_google_avg_latency_ms")

    if latency is None:
        return "unknown"

    try:
        latency = float(latency)
    except (TypeError, ValueError):
        return "unknown"

    if latency <= 50:
        return "success"
    if latency <= 100:
        return "warning"
    return "error"


def _wifi_rate_text(wifi: Dict[str, Any]) -> str:
    rx = wifi.get("receive_rate_mbps")
    tx = wifi.get("transmit_rate_mbps")

    if rx is None and tx is None:
        return "-"

    if rx is not None and tx is not None:
        return f"수신 {rx} Mbps / 전송 {tx} Mbps"

    if rx is not None:
        return f"수신 {rx} Mbps"

    return f"전송 {tx} Mbps"


def _channel_text(wifi: Dict[str, Any]) -> str:
    channel = wifi.get("channel")
    band = wifi.get("band")

    if channel is None and band is None:
        return "-"

    if channel is not None and band is not None:
        return f"{channel}번 / {band}"

    if channel is not None:
        return f"{channel}번"

    return str(band)


# =========================
# 단독 실행 테스트용
# =========================

if __name__ == "__main__":
    """
    이 파일을 단독 실행하면 간단한 샘플 dict로 동작을 확인한다.

    실제 samples 폴더 전체 테스트는 나중에 test_diagnosis.py
    또는 별도 테스트 스크립트에서 parser.py와 연결해서 실행하면 된다.
    """

    sample_parsed = {
        "netsh_interfaces": {
            "wifi_connected": True,
            "ssid": "eduroam",
            "bssid": "9e:ba:5f:26:72:65",
            "signal_percent": 75,
            "channel": 149,
            "band": "5GHz",
            "receive_rate_mbps": 390.0,
            "transmit_rate_mbps": 390.0,
            "auth": "WPA2-엔터프라이즈",
            "cipher": "CCMP",
            "profile": "eduroam",
        },
        "netsh_networks_bssid": {
            "eduroam_detected": True,
            "eduroam_bssid_count": 6,
            "strongest_eduroam_signal_percent": 100,
        },
        "ipconfig": {
            "ipv4_address": "192.168.0.10",
            "is_apipa": False,
            "has_ipv4": True,
            "gateway": "192.168.0.1",
            "has_gateway": True,
            "dns_servers": ["168.126.63.1"],
            "has_dns": True,
            "dhcp_enabled": True,
            "media_disconnected": False,
        },
        "ping_8_8_8_8": {
            "success": True,
            "packet_loss_percent": 0,
            "avg_latency_ms": 20,
            "host_not_found": False,
            "general_failure": False,
            "resolved_ip": None,
        },
        "ping_google": {
            "success": True,
            "packet_loss_percent": 0,
            "avg_latency_ms": 25,
            "host_not_found": False,
            "general_failure": False,
            "resolved_ip": "142.251.119.113",
        },
        "nslookup_google": {
            "success": True,
            "dns_server": "kns.kornet.net",
            "resolved_addresses": [
                "142.251.118.102",
                "142.251.118.101",
            ],
        },
    }

    result = diagnose(sample_parsed)
    display = build_display_summary(result)

    print("=== Diagnosis Result ===")
    print(result)

    print("\n=== Display Summary ===")
    print(display)