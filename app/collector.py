# app/collector.py
"""
Wi_Finder collector module

Windows 환경에서 네트워크 진단에 필요한 명령어를 실행하고,
그 원문 결과를 dict 형태로 수집한다.

수집 흐름:
collector.py → parser.py → diagnosis.py → display.py → gui.py

주의:
- 이 파일은 Windows에서 실행하는 것을 기본으로 한다.
- macOS/Linux에서는 netsh, ipconfig /all 결과가 Windows와 다르므로
  실제 Wi-Fi 진단용으로는 사용할 수 없다.

2026 수정 내용:
- ping 명령어에 -n 4 -w 1000 옵션을 추가해 진단 시간을 단축했다.
- 명령어별 timeout을 분리해 Wi-Fi 미연결 상태에서도 오래 기다리지 않도록 개선했다.
"""

from __future__ import annotations

import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# =========================
# 수집할 명령어 정의
# =========================

COMMANDS = {
    "netsh_interfaces": [
        "netsh",
        "wlan",
        "show",
        "interfaces",
    ],
    "netsh_networks_bssid": [
        "netsh",
        "wlan",
        "show",
        "networks",
        "mode=bssid",
    ],
    "ipconfig_all": [
        "ipconfig",
        "/all",
    ],
    "ping_8_8_8_8": [
        "ping",
        "8.8.8.8",
        "-n",
        "4",
        "-w",
        "1000",
    ],
    "ping_google": [
        "ping",
        "google.com",
        "-n",
        "4",
        "-w",
        "1000",
    ],
    "nslookup_google": [
        "nslookup",
        "google.com",
    ],
}


# =========================
# 명령어별 timeout
# =========================

COMMAND_TIMEOUTS = {
    "netsh_interfaces": 10,
    "netsh_networks_bssid": 15,
    "ipconfig_all": 10,
    "ping_8_8_8_8": 8,
    "ping_google": 8,
    "nslookup_google": 10,
}


# =========================
# 유틸 함수
# =========================

def is_windows() -> bool:
    """
    현재 실행 환경이 Windows인지 확인한다.
    """
    return platform.system().lower() == "windows"


def _decode_output(data: bytes) -> str:
    """
    subprocess 결과 bytes를 문자열로 변환한다.

    Windows 한글 환경에서는 cp949가 자주 사용되지만,
    환경에 따라 utf-8, utf-16 등이 섞일 수 있으므로 여러 인코딩을 시도한다.
    """
    if not data:
        return ""

    # BOM 기반 UTF-16
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            pass

    # BOM 기반 UTF-8
    if data.startswith(b"\xef\xbb\xbf"):
        try:
            return data.decode("utf-8-sig")
        except UnicodeDecodeError:
            pass

    # null byte가 많으면 UTF-16 계열일 가능성
    if data.count(b"\x00") > len(data) * 0.2:
        for encoding in ["utf-16", "utf-16-le", "utf-16-be"]:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue

    for encoding in ["cp949", "euc-kr", "utf-8", "utf-8-sig"]:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    return data.decode("utf-8", errors="ignore")


def run_command(
    command: List[str],
    timeout: int = 15,
) -> Dict[str, object]:
    """
    명령어 하나를 실행하고 결과를 반환한다.

    반환 예:
    {
        "success": True,
        "returncode": 0,
        "stdout": "...",
        "stderr": "",
        "command": "netsh wlan show interfaces"
    }
    """
    command_text = " ".join(command)

    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            shell=False,
        )

        stdout = _decode_output(completed.stdout)
        stderr = _decode_output(completed.stderr)

        return {
            "success": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "command": command_text,
            "timeout": timeout,
        }

    except FileNotFoundError:
        return {
            "success": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"명령어를 찾을 수 없습니다: {command[0]}",
            "command": command_text,
            "timeout": timeout,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"명령어 실행 시간이 초과되었습니다: {command_text}",
            "command": command_text,
            "timeout": timeout,
        }

    except Exception as e:
        return {
            "success": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"{type(e).__name__}: {e}",
            "command": command_text,
            "timeout": timeout,
        }


def _get_command_timeout(key: str, default_timeout: int) -> int:
    """
    명령어별 timeout 값을 반환한다.
    별도 설정이 없으면 기본 timeout을 사용한다.
    """
    return COMMAND_TIMEOUTS.get(key, default_timeout)


# =========================
# 핵심 수집 함수
# =========================

def collect_raw_outputs(
    require_windows: bool = True,
    timeout: int = 15,
) -> Dict[str, str]:
    """
    parser.py에 전달할 원문 결과 dict를 수집한다.

    parser.py의 parse_collected_outputs()가 기대하는 형태:

    {
        "netsh_interfaces": "...",
        "netsh_networks_bssid": "...",
        "ipconfig_all": "...",
        "ping_8_8_8_8": "...",
        "ping_google": "...",
        "nslookup_google": "..."
    }

    require_windows=True이면 Windows가 아닌 환경에서 실행을 막는다.
    """
    if require_windows and not is_windows():
        raise RuntimeError(
            "collector.py는 Windows 명령어 netsh, ipconfig를 사용하므로 "
            "Windows 환경에서 실행해야 합니다."
        )

    raw_outputs: Dict[str, str] = {}

    for key, command in COMMANDS.items():
        command_timeout = _get_command_timeout(key, timeout)
        result = run_command(command, timeout=command_timeout)

        stdout = str(result.get("stdout", ""))
        stderr = str(result.get("stderr", ""))

        # parser.py는 원문 텍스트를 받으므로 stdout을 우선 사용한다.
        # 실패한 경우에도 stderr를 함께 넣어두면 디버깅에 도움이 된다.
        if stdout:
            raw_outputs[key] = stdout
        else:
            raw_outputs[key] = stderr

    return raw_outputs


def collect_with_metadata(
    require_windows: bool = True,
    timeout: int = 15,
) -> Dict[str, object]:
    """
    수집 원문과 실행 메타데이터를 함께 반환한다.
    GUI 또는 로그 저장용으로 사용할 수 있다.
    """
    if require_windows and not is_windows():
        raise RuntimeError(
            "collector.py는 Windows 명령어 netsh, ipconfig를 사용하므로 "
            "Windows 환경에서 실행해야 합니다."
        )

    command_results: Dict[str, Dict[str, object]] = {}
    raw_outputs: Dict[str, str] = {}

    started_at = datetime.now().isoformat(timespec="seconds")

    for key, command in COMMANDS.items():
        command_timeout = _get_command_timeout(key, timeout)
        result = run_command(command, timeout=command_timeout)

        command_results[key] = result

        stdout = str(result.get("stdout", ""))
        stderr = str(result.get("stderr", ""))

        if stdout:
            raw_outputs[key] = stdout
        else:
            raw_outputs[key] = stderr

    finished_at = datetime.now().isoformat(timespec="seconds")

    return {
        "started_at": started_at,
        "finished_at": finished_at,
        "is_windows": is_windows(),
        "raw_outputs": raw_outputs,
        "command_results": command_results,
    }


# =========================
# 파일 저장 함수
# =========================

def save_raw_outputs(
    raw_outputs: Dict[str, str],
    output_dir: Optional[Path | str] = None,
) -> Path:
    """
    수집한 원문 결과를 txt 파일로 저장한다.

    저장 파일명은 samples 구조와 맞춘다.

    예:
    netsh_interfaces.txt
    netsh_networks_bssid.txt
    ipconfig_all.txt
    ping_8_8_8_8.txt
    ping_google.txt
    nslookup_google.txt
    """
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("collected") / f"run_{timestamp}"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    for key, text in raw_outputs.items():
        file_path = output_dir / f"{key}.txt"
        file_path.write_text(text or "", encoding="utf-8")

    return output_dir


def collect_and_save(
    output_dir: Optional[Path | str] = None,
    require_windows: bool = True,
    timeout: int = 15,
) -> Path:
    """
    명령어를 실행하고 결과를 txt 파일로 저장한다.
    """
    raw_outputs = collect_raw_outputs(
        require_windows=require_windows,
        timeout=timeout,
    )

    return save_raw_outputs(
        raw_outputs=raw_outputs,
        output_dir=output_dir,
    )


# =========================
# parser / diagnosis / display까지 연결
# =========================

def collect_parse_diagnose_display(
    require_windows: bool = True,
    timeout: int = 15,
) -> Dict[str, object]:
    """
    실제 프로그램에서 사용할 수 있는 전체 흐름.

    collector.py → parser.py → diagnosis.py → display.py

    반환값:
    {
        "raw_outputs": ...,
        "parsed": ...,
        "diagnosis": ...,
        "display": ...
    }
    """
    from parser import parse_collected_outputs
    from diagnosis import diagnose
    from display import build_display_data

    raw_outputs = collect_raw_outputs(
        require_windows=require_windows,
        timeout=timeout,
    )

    parsed = parse_collected_outputs(raw_outputs)
    diagnosis_result = diagnose(parsed)
    display_data = build_display_data(diagnosis_result)

    return {
        "raw_outputs": raw_outputs,
        "parsed": parsed,
        "diagnosis": diagnosis_result,
        "display": display_data,
    }


# =========================
# 콘솔 출력 함수
# =========================

def print_collect_summary(metadata: Dict[str, object]) -> None:
    """
    collect_with_metadata() 결과를 콘솔에 보기 좋게 출력한다.
    """
    print("=" * 80)
    print("Wi_Finder collector.py 실행 결과")
    print("=" * 80)
    print(f"시작 시간: {metadata.get('started_at')}")
    print(f"종료 시간: {metadata.get('finished_at')}")
    print(f"Windows 여부: {metadata.get('is_windows')}")
    print()

    command_results = metadata.get("command_results", {})

    if not isinstance(command_results, dict):
        print("명령어 결과가 없습니다.")
        return

    for key, result in command_results.items():
        if not isinstance(result, dict):
            continue

        success = result.get("success")
        returncode = result.get("returncode")
        command = result.get("command")
        timeout = result.get("timeout")
        stdout = str(result.get("stdout", ""))
        stderr = str(result.get("stderr", ""))

        print("-" * 80)
        print(f"[{key}]")
        print(f"command   : {command}")
        print(f"timeout   : {timeout}")
        print(f"success   : {success}")
        print(f"returncode: {returncode}")

        if stdout:
            preview = stdout.replace("\r\n", "\n").splitlines()
            print("stdout 미리보기:")
            for line in preview[:8]:
                print(f"  {line}")

            if len(preview) > 8:
                print(f"  ... ({len(preview) - 8}줄 더 있음)")

        if stderr:
            preview = stderr.replace("\r\n", "\n").splitlines()
            print("stderr 미리보기:")
            for line in preview[:8]:
                print(f"  {line}")

            if len(preview) > 8:
                print(f"  ... ({len(preview) - 8}줄 더 있음)")

        print()


# =========================
# 직접 실행
# =========================

if __name__ == "__main__":
    """
    Windows 팀원 PC에서 실행 예:

    python app/collector.py

    실행하면:
    1. Windows 명령어 실행
    2. 결과 미리보기 출력
    3. collected/run_YYYYMMDD_HHMMSS/ 폴더에 txt 저장
    """
    try:
        metadata = collect_with_metadata(require_windows=True)
        print_collect_summary(metadata)

        raw_outputs = metadata.get("raw_outputs", {})

        if isinstance(raw_outputs, dict):
            saved_dir = save_raw_outputs(raw_outputs)
            print("=" * 80)
            print(f"수집 결과 저장 완료: {saved_dir}")
            print("=" * 80)

    except RuntimeError as e:
        print("[ERROR]")
        print(e)
        print()
        print("이 파일은 Windows 환경에서 실행해야 합니다.")