# app/display.py
"""
Wi_Finder display module

diagnosis.py의 진단 결과를 GUI에서 사용하기 쉬운 형태로 변환한다.

역할:
- 진단 코드 NORMAL, DNS_FAIL 같은 값을 사용자 친화적인 화면 데이터로 변환
- 카드형 대시보드에 표시할 항목 생성
- 상세 정보 영역에 표시할 항목 생성
- 상태별 색상/레벨/아이콘 정보 제공

주의:
이 파일은 실제 GUI를 그리지 않는다.
GUI에서 사용할 "표시용 데이터"만 만든다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# =========================
# 상태 표시 기본 정보
# =========================

STATUS_META = {
    "success": {
        "label": "정상",
        "icon": "✅",
        "color": "green",
    },
    "warning": {
        "label": "주의",
        "icon": "⚠️",
        "color": "orange",
    },
    "error": {
        "label": "문제",
        "icon": "❌",
        "color": "red",
    },
    "info": {
        "label": "정보",
        "icon": "ℹ️",
        "color": "blue",
    },
    "unknown": {
        "label": "확인 필요",
        "icon": "❔",
        "color": "gray",
    },
}


DIAGNOSIS_META = {
    "NORMAL": {
        "short_label": "정상",
        "user_message": "현재 Wi-Fi 연결 상태가 정상입니다.",
    },
    "DISCONNECTED": {
        "short_label": "Wi-Fi 미연결",
        "user_message": "단말이 eduroam에 연결되어 있지 않습니다.",
    },
    "CONNECTED_NO_IP": {
        "short_label": "IP 할당 실패",
        "user_message": "Wi-Fi는 연결됐지만 IP 주소를 정상적으로 받지 못했습니다.",
    },
    "DNS_FAIL": {
        "short_label": "DNS 문제",
        "user_message": "인터넷 IP 통신은 가능하지만 웹사이트 주소 변환에 실패했습니다.",
    },
    "EXTERNAL_PING_FAIL": {
        "short_label": "외부 통신 문제",
        "user_message": "DNS 조회는 가능하지만 외부 통신 테스트가 실패했습니다.",
    },
    "UNKNOWN": {
        "short_label": "분류 불가",
        "user_message": "수집된 정보만으로는 원인을 명확히 분류하기 어렵습니다.",
    },
}


# =========================
# 공통 유틸
# =========================

def _safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    중첩 dict에서 안전하게 값을 가져온다.

    예:
    _safe_get(result, "indicators", "wifi", "ssid")
    """
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return default

        current = current.get(key)

        if current is None:
            return default

    return current


def _status_meta(status: str) -> Dict[str, str]:
    return STATUS_META.get(status, STATUS_META["unknown"])


def _format_bool(value: Any) -> str:
    if value is True:
        return "예"
    if value is False:
        return "아니오"
    return "-"


def _format_list(value: Any) -> str:
    if isinstance(value, list):
        if not value:
            return "-"
        return ", ".join(str(item) for item in value)

    if value is None:
        return "-"

    return str(value)


def _format_percent(value: Any) -> str:
    if value is None:
        return "-"

    return f"{value}%"


def _format_ms(value: Any) -> str:
    if value is None:
        return "-"

    return f"{value} ms"


def _format_mbps(value: Any) -> str:
    if value is None:
        return "-"

    return f"{value} Mbps"


def _card(
    name: str,
    value: Any,
    status: str,
    description: str = "",
) -> Dict[str, Any]:
    meta = _status_meta(status)

    return {
        "name": name,
        "value": "-" if value is None else value,
        "status": status,
        "status_label": meta["label"],
        "icon": meta["icon"],
        "color": meta["color"],
        "description": description,
    }


def _detail(
    name: str,
    value: Any,
    description: str = "",
) -> Dict[str, Any]:
    return {
        "name": name,
        "value": "-" if value is None else value,
        "description": description,
    }


# =========================
# 상태 판단 보조 함수
# =========================

def _wifi_status(wifi: Dict[str, Any]) -> str:
    return "success" if wifi.get("connected") else "error"


def _ssid_status(wifi: Dict[str, Any]) -> str:
    ssid = wifi.get("ssid")

    if ssid == "eduroam":
        return "success"

    if ssid:
        return "warning"

    return "error"


def _signal_status(signal_percent: Optional[int]) -> str:
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


def _ip_status(ip: Dict[str, Any]) -> str:
    if not ip.get("has_ipv4"):
        return "error"

    if ip.get("is_apipa"):
        return "error"

    if not ip.get("has_gateway"):
        return "warning"

    return "success"


def _dns_status(dns: Dict[str, Any]) -> str:
    if dns.get("dns_lookup_valid"):
        return "success"

    if dns.get("has_dns") or dns.get("has_valid_dns_server"):
        return "warning"

    return "error"


def _internet_status(internet: Dict[str, Any]) -> str:
    if internet.get("ping_8_8_8_8_success") and internet.get("ping_google_success"):
        return "success"

    if internet.get("ping_8_8_8_8_success") or internet.get("ping_google_success"):
        return "warning"

    return "error"


def _latency_status(latency_ms: Any) -> str:
    if latency_ms is None:
        return "unknown"

    try:
        latency = float(latency_ms)
    except (TypeError, ValueError):
        return "unknown"

    if latency <= 50:
        return "success"

    if latency <= 100:
        return "warning"

    return "error"


def _loss_status(loss_percent: Any) -> str:
    if loss_percent is None:
        return "unknown"

    try:
        loss = int(loss_percent)
    except (TypeError, ValueError):
        return "unknown"

    if loss == 0:
        return "success"

    if loss < 100:
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


def _dns_status_text(dns: Dict[str, Any]) -> str:
    if dns.get("dns_lookup_valid"):
        return "정상"

    if dns.get("has_dns") or dns.get("has_valid_dns_server"):
        return "확인 필요"

    return "실패"


def _internet_status_text(internet: Dict[str, Any]) -> str:
    ping_8 = internet.get("ping_8_8_8_8_success")
    ping_google = internet.get("ping_google_success")

    if ping_8 and ping_google:
        return "정상"

    if ping_8 and not ping_google:
        return "IP 통신만 가능"

    if not ping_8 and ping_google:
        return "일부 가능"

    return "실패"


def _rate_text(wifi: Dict[str, Any]) -> str:
    rx = wifi.get("receive_rate_mbps")
    tx = wifi.get("transmit_rate_mbps")

    if rx is None and tx is None:
        return "-"

    if rx is not None and tx is not None:
        return f"수신 {_format_mbps(rx)} / 전송 {_format_mbps(tx)}"

    if rx is not None:
        return f"수신 {_format_mbps(rx)}"

    return f"전송 {_format_mbps(tx)}"


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


def _main_latency(internet: Dict[str, Any]) -> Any:
    latency = internet.get("ping_8_8_8_8_avg_latency_ms")

    if latency is not None:
        return latency

    return internet.get("ping_google_avg_latency_ms")


def _main_loss(internet: Dict[str, Any]) -> Any:
    loss = internet.get("ping_8_8_8_8_loss_percent")

    if loss is not None:
        return loss

    return internet.get("ping_google_loss_percent")


# =========================
# 카드 생성
# =========================

def build_main_cards(diagnosis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    GUI 상단 핵심 카드 생성.

    예:
    - Wi-Fi 연결 상태
    - 연결된 Wi-Fi
    - 신호 세기
    - IP 주소 상태
    - 인터넷 연결
    - 웹사이트 주소 확인
    """

    indicators = diagnosis_result.get("indicators", {})

    wifi = indicators.get("wifi", {})
    ip = indicators.get("ip", {})
    dns = indicators.get("dns", {})
    internet = indicators.get("internet", {})

    return [
        _card(
            name="Wi-Fi 연결 상태",
            value="연결됨" if wifi.get("connected") else "연결 안 됨",
            status=_wifi_status(wifi),
            description="현재 단말이 Wi-Fi에 연결되어 있는지 확인합니다.",
        ),
        _card(
            name="연결된 Wi-Fi",
            value=wifi.get("ssid") or "-",
            status=_ssid_status(wifi),
            description="현재 연결된 SSID가 eduroam인지 확인합니다.",
        ),
        _card(
            name="신호 세기",
            value=_format_percent(wifi.get("signal_percent")),
            status=_signal_status(wifi.get("signal_percent")),
            description="무선 AP와 단말 사이의 신호 품질입니다.",
        ),
        _card(
            name="IP 주소 상태",
            value=_ip_status_text(ip),
            status=_ip_status(ip),
            description="IPv4 주소와 게이트웨이를 정상적으로 받았는지 확인합니다.",
        ),
        _card(
            name="인터넷 연결",
            value=_internet_status_text(internet),
            status=_internet_status(internet),
            description="8.8.8.8 및 google.com ping 결과를 기반으로 판단합니다.",
        ),
        _card(
            name="웹사이트 주소 확인",
            value=_dns_status_text(dns),
            status=_dns_status(dns),
            description="google.com 주소를 IP로 변환할 수 있는지 확인합니다.",
        ),
    ]


def build_sub_cards(diagnosis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    GUI 보조 지표 카드 생성.

    예:
    - 응답 속도
    - 끊김 정도
    - 무선 연결 속도
    - 채널
    - 주변 eduroam 감지
    """

    indicators = diagnosis_result.get("indicators", {})

    wifi = indicators.get("wifi", {})
    internet = indicators.get("internet", {})
    nearby = indicators.get("nearby_eduroam", {})

    latency = _main_latency(internet)
    loss = _main_loss(internet)

    nearby_text = "감지됨" if nearby.get("detected") else "감지 안 됨"

    if nearby.get("bssid_count") is not None:
        nearby_text += f" / BSSID {nearby.get('bssid_count')}개"

    return [
        _card(
            name="응답 속도",
            value=_format_ms(latency),
            status=_latency_status(latency),
            description="ping 평균 응답 시간입니다.",
        ),
        _card(
            name="끊김 정도",
            value=_format_percent(loss),
            status=_loss_status(loss),
            description="ping 패킷 손실률입니다.",
        ),
        _card(
            name="무선 연결 속도",
            value=_rate_text(wifi),
            status="info",
            description="Windows에서 확인된 Wi-Fi 수신/전송 속도입니다.",
        ),
        _card(
            name="채널",
            value=_channel_text(wifi),
            status="info",
            description="현재 연결된 무선 채널과 대역입니다.",
        ),
        _card(
            name="주변 eduroam 감지",
            value=nearby_text,
            status="success" if nearby.get("detected") else "warning",
            description="주변 AP 목록에서 eduroam이 감지되는지 확인합니다.",
        ),
    ]


# =========================
# 상세 정보 생성
# =========================

def build_detail_rows(diagnosis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    GUI 하단 상세 정보 영역 데이터 생성.
    """

    detail = diagnosis_result.get("detail", {})

    ping_8 = detail.get("ping_8_8_8_8", {})
    ping_google = detail.get("ping_google", {})
    nslookup = detail.get("nslookup_google", {})

    return [
        _detail("SSID", detail.get("ssid")),
        _detail("BSSID", detail.get("bssid")),
        _detail("프로필", detail.get("profile")),
        _detail("인증 방식", detail.get("auth")),
        _detail("암호 방식", detail.get("cipher")),
        _detail("신호 세기", _format_percent(detail.get("signal_percent"))),
        _detail("무선 대역", detail.get("band")),
        _detail("채널", detail.get("channel")),
        _detail("수신 속도", _format_mbps(detail.get("receive_rate_mbps"))),
        _detail("전송 속도", _format_mbps(detail.get("transmit_rate_mbps"))),
        _detail("주변 eduroam 감지", _format_bool(detail.get("eduroam_detected"))),
        _detail("주변 eduroam BSSID 수", detail.get("eduroam_bssid_count")),
        _detail(
            "가장 강한 eduroam 신호",
            _format_percent(detail.get("strongest_eduroam_signal_percent")),
        ),
        _detail("IPv4 주소", detail.get("ipv4_address")),
        _detail("기본 게이트웨이", detail.get("gateway")),
        _detail("DNS 서버", _format_list(detail.get("dns_servers"))),
        _detail("DHCP 사용", _format_bool(detail.get("dhcp_enabled"))),
        _detail("미디어 연결 끊김", _format_bool(detail.get("media_disconnected"))),
        _detail("8.8.8.8 Ping 성공", _format_bool(ping_8.get("success"))),
        _detail("8.8.8.8 손실률", _format_percent(ping_8.get("packet_loss_percent"))),
        _detail("8.8.8.8 평균 응답", _format_ms(ping_8.get("avg_latency_ms"))),
        _detail("Google Ping 성공", _format_bool(ping_google.get("success"))),
        _detail("Google Ping 손실률", _format_percent(ping_google.get("packet_loss_percent"))),
        _detail("Google Ping 평균 응답", _format_ms(ping_google.get("avg_latency_ms"))),
        _detail("Google Ping 변환 IP", ping_google.get("resolved_ip")),
        _detail("nslookup 성공", _format_bool(nslookup.get("success"))),
        _detail("nslookup DNS 서버", nslookup.get("dns_server")),
        _detail("nslookup 결과 주소", _format_list(nslookup.get("resolved_addresses"))),
    ]


# =========================
# 전체 표시 데이터 생성
# =========================

def build_display_data(diagnosis_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    diagnosis.py 결과를 GUI 표시용 데이터로 변환한다.

    반환 구조 예:

    {
        "diagnosis": {...},
        "main_cards": [...],
        "sub_cards": [...],
        "detail_rows": [...],
        "actions": [...],
        "causes": [...]
    }
    """

    code = diagnosis_result.get("code", "UNKNOWN")
    level = diagnosis_result.get("level", "unknown")

    diagnosis_meta = DIAGNOSIS_META.get(code, DIAGNOSIS_META["UNKNOWN"])
    level_meta = _status_meta(level)

    return {
        "diagnosis": {
            "code": code,
            "level": level,
            "level_label": level_meta["label"],
            "icon": level_meta["icon"],
            "color": level_meta["color"],
            "short_label": diagnosis_meta["short_label"],
            "title": diagnosis_result.get("title", "진단 결과 없음"),
            "summary": diagnosis_result.get("summary", ""),
            "user_message": diagnosis_meta["user_message"],
        },
        "main_cards": build_main_cards(diagnosis_result),
        "sub_cards": build_sub_cards(diagnosis_result),
        "detail_rows": build_detail_rows(diagnosis_result),
        "possible_causes": diagnosis_result.get("possible_causes", []),
        "recommended_actions": diagnosis_result.get("recommended_actions", []),
    }


# =========================
# 콘솔 출력용 함수
# =========================

def print_display_data(display_data: Dict[str, Any]) -> None:
    """
    개발 중 콘솔에서 display_data를 보기 좋게 출력한다.
    GUI 완성 후에는 필수 함수는 아니다.
    """

    diagnosis = display_data.get("diagnosis", {})

    print("=" * 80)
    print("진단 결과")
    print("=" * 80)
    print(f"{diagnosis.get('icon')} {diagnosis.get('title')}")
    print(f"상태: {diagnosis.get('level_label')} / 코드: {diagnosis.get('code')}")
    print(f"요약: {diagnosis.get('summary')}")
    print()

    print("[핵심 상태]")
    for card in display_data.get("main_cards", []):
        print(
            f"- {card.get('icon')} {card.get('name')}: "
            f"{card.get('value')} ({card.get('status_label')})"
        )

    print()
    print("[보조 지표]")
    for card in display_data.get("sub_cards", []):
        print(
            f"- {card.get('icon')} {card.get('name')}: "
            f"{card.get('value')} ({card.get('status_label')})"
        )

    print()

    causes = display_data.get("possible_causes", [])
    if causes:
        print("[가능한 원인]")
        for cause in causes:
            print(f"- {cause}")
        print()

    actions = display_data.get("recommended_actions", [])
    if actions:
        print("[권장 조치]")
        for action in actions:
            print(f"- {action}")
        print()

    print("[상세 정보]")
    for row in display_data.get("detail_rows", []):
        print(f"- {row.get('name')}: {row.get('value')}")

    print()


# =========================
# 단독 실행 테스트용
# =========================

if __name__ == "__main__":
    """
    이 파일만 단독 실행할 때는 간단한 더미 diagnosis_result로 확인한다.

    실제 sample 기반 테스트는 test_display.py에서 수행한다.
    """

    dummy_diagnosis_result = {
        "code": "NORMAL",
        "level": "success",
        "title": "Wi-Fi 연결 정상",
        "summary": "eduroam 연결, IP 할당, DNS 조회, 외부 통신이 모두 정상입니다.",
        "possible_causes": [],
        "recommended_actions": [
            "현재 네트워크 상태는 정상입니다.",
        ],
        "indicators": {
            "wifi": {
                "connected": True,
                "ssid": "eduroam",
                "signal_percent": 75,
                "band": "5GHz",
                "channel": 149,
                "receive_rate_mbps": 390.0,
                "transmit_rate_mbps": 390.0,
            },
            "nearby_eduroam": {
                "detected": True,
                "bssid_count": 6,
                "strongest_signal_percent": 100,
            },
            "ip": {
                "ipv4_address": "192.168.0.10",
                "has_ipv4": True,
                "is_apipa": False,
                "has_gateway": True,
            },
            "dns": {
                "has_dns": True,
                "dns_servers": ["168.126.63.1"],
                "has_valid_dns_server": True,
                "nslookup_success": True,
                "dns_lookup_valid": True,
            },
            "internet": {
                "ping_8_8_8_8_success": True,
                "ping_google_success": True,
                "ping_8_8_8_8_loss_percent": 0,
                "ping_google_loss_percent": 0,
                "ping_8_8_8_8_avg_latency_ms": 20,
                "ping_google_avg_latency_ms": 25,
            },
        },
        "detail": {
            "ssid": "eduroam",
            "bssid": "9e:ba:5f:26:72:65",
            "profile": "eduroam",
            "auth": "WPA2-엔터프라이즈",
            "cipher": "CCMP",
            "signal_percent": 75,
            "band": "5GHz",
            "channel": 149,
            "receive_rate_mbps": 390.0,
            "transmit_rate_mbps": 390.0,
            "eduroam_detected": True,
            "eduroam_bssid_count": 6,
            "strongest_eduroam_signal_percent": 100,
            "ipv4_address": "192.168.0.10",
            "gateway": "192.168.0.1",
            "dns_servers": ["168.126.63.1"],
            "dhcp_enabled": True,
            "media_disconnected": False,
            "ping_8_8_8_8": {
                "success": True,
                "packet_loss_percent": 0,
                "avg_latency_ms": 20,
            },
            "ping_google": {
                "success": True,
                "packet_loss_percent": 0,
                "avg_latency_ms": 25,
                "resolved_ip": "142.251.119.113",
            },
            "nslookup_google": {
                "success": True,
                "dns_server": "kns.kornet.net",
                "resolved_addresses": ["142.251.118.102"],
            },
        },
    }

    display = build_display_data(dummy_diagnosis_result)
    print_display_data(display)