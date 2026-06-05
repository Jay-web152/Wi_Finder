"""
Wi_Finder 사용자용 브라우저 GUI

실행:
    python3 app/gui.py

흐름:
- /        : 사용자용 진단 홈
- /run     : 실제 Windows 진단 실행 + 결과 자동 저장
- /samples : 개발용 샘플 목록
- /sample?case=case1_normal : 샘플 결과 확인

주의:
- 실제 진단은 Windows에서만 정상 실행된다.
- macOS에서는 /run 실행 시 Windows 명령어 사용 불가 오류가 뜨는 것이 정상이다.

수정 내용:
- 카드 데이터의 help_text를 details/summary 토글로 표시
- 기본 description은 기존처럼 항상 표시
"""

from __future__ import annotations

import html
import json
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
SAMPLES_DIR = PROJECT_ROOT / "samples"

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import collector
import parser
import diagnosis
import display

HOST = "127.0.0.1"
PORT = 8765

CASE_ORDER = [
    "case1_normal",
    "case2_disconnected",
    "case3_1_connected_no_ip",
    "case3_2_dns_fail",
    "case3_3_external_ping_fail",
]

CASE_LABELS = {
    "case1_normal": "case1_normal - 정상 연결",
    "case2_disconnected": "case2_disconnected - Wi-Fi 미연결",
    "case3_1_connected_no_ip": "case3_1_connected_no_ip - IP 할당 실패",
    "case3_2_dns_fail": "case3_2_dns_fail - DNS 실패",
    "case3_3_external_ping_fail": "case3_3_external_ping_fail - 외부 통신 실패",
}

CODE_META = {
    "NORMAL": {"class": "ok", "label": "정상"},
    "DISCONNECTED": {"class": "bad", "label": "Wi-Fi 미연결"},
    "CONNECTED_NO_IP": {"class": "warn", "label": "IP 할당 실패"},
    "DNS_FAIL": {"class": "warn", "label": "DNS 실패"},
    "EXTERNAL_PING_FAIL": {"class": "warn", "label": "외부 통신 실패"},
    "UNKNOWN": {"class": "unknown", "label": "알 수 없음"},
}

CSS = """
:root {
  --bg: #f4f6f8;
  --panel: #ffffff;
  --text: #111827;
  --muted: #64748b;
  --line: #d0d7de;
  --blue: #2563eb;
  --nav: #1f2937;
  --green-bg: #dcfce7;
  --green-line: #86efac;
  --red-bg: #fee2e2;
  --red-line: #fca5a5;
  --yellow-bg: #fef3c7;
  --yellow-line: #fcd34d;
  --gray-bg: #e5e7eb;
  --gray-line: #cbd5e1;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
}
header {
  background: var(--nav);
  color: white;
  padding: 18px 70px;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: center;
}
header h1 {
  margin: 0;
  font-size: 30px;
}
header p {
  margin: 5px 0 0;
  color: #cbd5e1;
}
nav a {
  color: white;
  text-decoration: none;
  background: rgba(255,255,255,0.12);
  padding: 10px 14px;
  border-radius: 999px;
  font-weight: 800;
  font-size: 14px;
  margin-left: 8px;
}
main {
  max-width: 1180px;
  margin: 0 auto;
  padding: 22px;
}
.hero {
  background: linear-gradient(135deg, #eff6ff, #ecfeff);
  border: 1px solid #bfdbfe;
  border-radius: 22px;
  padding: 28px;
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 28px;
  align-items: center;
  margin-bottom: 22px;
}
.hero h2 {
  font-size: 32px;
  line-height: 1.25;
  margin: 10px 0 14px;
}
.hero p {
  color: #52627a;
  font-size: 16px;
  line-height: 1.7;
}
.pill {
  display: inline-block;
  background: white;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 900;
}
.actions {
  margin-top: 22px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.btn {
  display: inline-block;
  text-decoration: none;
  background: var(--blue);
  color: white;
  border-radius: 13px;
  padding: 13px 18px;
  font-weight: 900;
  border: none;
}
.btn.secondary {
  background: white;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}
.mock {
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 18px;
  overflow: hidden;
  box-shadow: 0 14px 30px rgba(15,23,42,0.10);
}
.mock-top {
  height: 34px;
  background: #e5e7eb;
  display: flex;
  align-items: center;
  padding-left: 12px;
  gap: 7px;
}
.dot {
  width: 11px;
  height: 11px;
  background: #94a3b8;
  border-radius: 50%;
}
.mock-body {
  padding: 20px;
}
.mock-row {
  padding: 13px;
  margin-bottom: 10px;
  border-radius: 10px;
  background: #dcfce7;
  font-weight: 900;
}
.mock-row.warn {
  background: #fef3c7;
}
.steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 22px;
}
.step {
  background: white;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 18px;
}
.num {
  display: inline-flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--blue);
  color: white;
  font-weight: 900;
}
.step h3 {
  margin: 14px 0 8px;
}
.step p {
  color: #52627a;
  line-height: 1.6;
}
.banner {
  border-radius: 18px;
  border: 1px solid var(--gray-line);
  background: var(--gray-bg);
  padding: 22px;
  margin-bottom: 22px;
}
.banner.ok { background: var(--green-bg); border-color: var(--green-line); }
.banner.bad { background: var(--red-bg); border-color: var(--red-line); }
.banner.warn { background: var(--yellow-bg); border-color: var(--yellow-line); }
.banner.unknown { background: var(--gray-bg); border-color: var(--gray-line); }
.badge {
  display: inline-block;
  padding: 5px 10px;
  border-radius: 999px;
  background: rgba(255,255,255,0.72);
  font-weight: 900;
  font-size: 13px;
}
section {
  margin-bottom: 22px;
}
section h3 {
  margin: 0 0 10px;
  font-size: 19px;
}
.cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.card {
  background: white;
  border: 1px solid var(--line);
  border-left: 6px solid #94a3b8;
  border-radius: 16px;
  padding: 16px;
  min-height: 145px;
}
.card.green { border-left-color: #22c55e; }
.card.red { border-left-color: #ef4444; }
.card.yellow { border-left-color: #f59e0b; }
.card.orange { border-left-color: #f97316; }
.card.gray { border-left-color: #94a3b8; }
.card.blue { border-left-color: #2563eb; }
.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-weight: 900;
}
.icon { font-size: 20px; }
.card-value {
  font-size: 23px;
  font-weight: 950;
  margin-top: 11px;
}
.status-label {
  color: var(--muted);
  font-weight: 800;
  margin-top: 4px;
}
.card-desc {
  color: var(--muted);
  margin-top: 10px;
  line-height: 1.45;
  font-size: 14px;
}
.metric-help {
  margin-top: 9px;
  font-size: 13px;
  color: #4b5563;
}
.metric-help summary {
  cursor: pointer;
  font-weight: 900;
  color: #2563eb;
  user-select: none;
}
.metric-help summary:hover {
  text-decoration: underline;
}
.metric-help p {
  margin: 8px 0 0;
  line-height: 1.55;
  color: #374151;
}
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.panel, .table-wrap, .empty, .controls {
  background: white;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 16px;
}
ul {
  margin: 0;
  padding-left: 20px;
  line-height: 1.7;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
th, td {
  border-bottom: 1px solid #e5e7eb;
  padding: 10px;
  text-align: left;
  vertical-align: top;
}
th {
  background: #f8fafc;
  color: #475569;
}
td:nth-child(1) { width: 18%; color: #64748b; font-weight: 800; }
td:nth-child(2) { width: 28%; font-weight: 800; }
.controls {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 18px;
}
select, button {
  font-size: 15px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: white;
}
select { min-width: 420px; }
button {
  background: var(--blue);
  color: white;
  border: none;
  font-weight: 900;
  cursor: pointer;
}
.saved-path {
  margin-top: 12px;
  padding: 12px;
  border-radius: 12px;
  background: rgba(255,255,255,0.65);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  word-break: break-all;
}
@media (max-width: 900px) {
  header { padding: 18px 22px; flex-direction: column; align-items: flex-start; }
  .hero { grid-template-columns: 1fr; }
  .steps, .cards, .two-col { grid-template-columns: 1fr; }
  .controls { flex-direction: column; align-items: stretch; }
  select { min-width: 0; width: 100%; }
}
"""


def e(value: Any) -> str:
    return html.escape(str(value if value is not None else "-"))


def get_cases() -> List[str]:
    if not SAMPLES_DIR.exists():
        return []
    found = [p.name for p in SAMPLES_DIR.iterdir() if p.is_dir()]
    ordered = [case for case in CASE_ORDER if case in found]
    rest = sorted([case for case in found if case not in ordered])
    return ordered + rest


def to_json_file(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def run_real_diagnosis() -> Dict[str, Any]:
    """
    실제 Windows 진단 실행 + 분석용 파일 자동 저장.
    """
    metadata = collector.collect_with_metadata(require_windows=True, timeout=15)

    raw_outputs = metadata.get("raw_outputs", {})
    if not isinstance(raw_outputs, dict):
        raise RuntimeError("raw_outputs가 dict 형태가 아닙니다.")

    saved_dir = collector.save_raw_outputs(raw_outputs)

    parsed = parser.parse_collected_outputs(raw_outputs)
    diagnosis_result = diagnosis.diagnose(parsed)
    display_data = display.build_display_data(diagnosis_result)

    command_results = metadata.get("command_results", {})
    run_metadata = {
        "started_at": metadata.get("started_at"),
        "finished_at": metadata.get("finished_at"),
        "is_windows": metadata.get("is_windows"),
        "saved_dir": str(saved_dir),
    }

    to_json_file(saved_dir / "diagnosis_result.json", diagnosis_result)
    to_json_file(saved_dir / "display_data.json", display_data)
    to_json_file(saved_dir / "command_results.json", command_results)
    to_json_file(saved_dir / "run_metadata.json", run_metadata)

    return {
        "case_name": "실제 진단",
        "saved_dir": str(saved_dir),
        "raw_outputs": raw_outputs,
        "parsed": parsed,
        "diagnosis": diagnosis_result,
        "display": display_data,
    }


def run_sample_case(case_name: str) -> Dict[str, Any]:
    case_dir = SAMPLES_DIR / case_name
    if not case_dir.exists():
        raise FileNotFoundError(f"샘플 폴더를 찾을 수 없습니다: {case_dir}")

    parsed = parser.parse_sample_case(case_dir)
    diagnosis_result = diagnosis.diagnose(parsed)
    display_data = display.build_display_data(diagnosis_result)

    return {
        "case_name": case_name,
        "saved_dir": "",
        "parsed": parsed,
        "diagnosis": diagnosis_result,
        "display": display_data,
    }


def render_card(card: Dict[str, Any]) -> str:
    name = card.get("name") or card.get("title") or "항목"
    value = card.get("value", "-")
    status_label = card.get("status_label") or card.get("status") or ""
    icon = card.get("icon") or ""
    desc = card.get("description") or ""
    help_text = card.get("help_text") or ""
    color = card.get("color") or "gray"

    desc_html = ""
    if desc:
        desc_html = f'<div class="card-desc">{e(desc)}</div>'

    help_html = ""
    if help_text:
        help_html = f"""
        <details class="metric-help">
          <summary>자세히 보기</summary>
          <p>{e(help_text)}</p>
        </details>
        """

    return f"""
    <div class="card {e(color)}">
      <div class="card-head">
        <span class="icon">{e(icon)}</span>
        <span>{e(name)}</span>
      </div>
      <div class="card-value">{e(value)}</div>
      <div class="status-label">{e(status_label)}</div>
      {desc_html}
      {help_html}
    </div>
    """


def render_cards(cards: List[Dict[str, Any]]) -> str:
    if not cards:
        return '<div class="empty">표시할 카드 데이터가 없습니다.</div>'
    card_html = "\n".join(render_card(card) for card in cards)
    return '<div class="cards">' + card_html + "</div>"


def render_list(items: List[Any]) -> str:
    if not items:
        return '<div class="empty">표시할 데이터가 없습니다.</div>'

    rows = []
    for item in items:
        if isinstance(item, dict):
            text = item.get("text") or item.get("value") or item
        else:
            text = item
        rows.append(f"<li>{e(text)}</li>")

    list_html = "\n".join(rows)
    return "<ul>" + list_html + "</ul>"


def render_detail_rows(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return '<div class="empty">상세 정보가 없습니다.</div>'

    trs = []
    for row in rows:
        section = row.get("section") or row.get("category") or "상세"
        name = row.get("name") or row.get("key") or row.get("label") or "항목"
        value = row.get("value", "-")
        trs.append(
            f"<tr><td>{e(section)}</td><td>{e(name)}</td><td>{e(value)}</td></tr>"
        )

    return f"""
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>구분</th><th>항목</th><th>값</th></tr>
        </thead>
        <tbody>{''.join(trs)}</tbody>
      </table>
    </div>
    """


def render_result(result: Dict[str, Any]) -> str:
    diagnosis_result = result["diagnosis"]
    display_data = result["display"]

    code = diagnosis_result.get("code", "UNKNOWN")
    title = diagnosis_result.get("title", "진단 결과")
    summary = diagnosis_result.get("summary", "")
    meta = CODE_META.get(code, CODE_META["UNKNOWN"])

    main_cards = display_data.get("main_cards", [])
    sub_cards = display_data.get("sub_cards", [])
    possible_causes = display_data.get("possible_causes", [])
    recommended_actions = display_data.get("recommended_actions", [])
    detail_rows = display_data.get("detail_rows", [])
    saved_dir = result.get("saved_dir", "")

    saved_html = ""
    if saved_dir:
        saved_html = f"""
        <div class="saved-path">
          분석용 파일 저장 위치: {e(saved_dir)}<br>
          이 폴더를 zip으로 압축해서 공유하면 원문 수집 결과와 진단 JSON을 함께 확인할 수 있습니다.
        </div>
        """

    return f"""
    <section class="banner {e(meta['class'])}">
      <div class="badge">{e(code)} · {e(meta['label'])}</div>
      <h2>{e(title)}</h2>
      <p>{e(summary)}</p>
      {saved_html}
    </section>

    <section>
      <h3>주요 진단 카드</h3>
      {render_cards(main_cards)}
    </section>

    <section>
      <h3>보조 지표</h3>
      {render_cards(sub_cards)}
    </section>

    <section class="two-col">
      <div class="panel">
        <h3>가능한 원인</h3>
        {render_list(possible_causes)}
      </div>
      <div class="panel">
        <h3>추천 조치</h3>
        {render_list(recommended_actions)}
      </div>
    </section>

    <section>
      <h3>상세 정보</h3>
      {render_detail_rows(detail_rows)}
    </section>
    """


def render_home() -> str:
    return """
    <section class="hero">
      <div>
        <span class="pill">Wi_Finder Local Diagnosis</span>
        <h2>캠퍼스 Wi-Fi 접속 상태를<br>로컬 PC에서 바로 진단합니다</h2>
        <p>
          실행 파일을 열면 브라우저 진단 화면이 표시됩니다.
          학생이 진단 시작 버튼을 누르면 Wi-Fi, IP, DNS, 인터넷 연결 상태를 자동으로 점검합니다.
        </p>
        <div class="actions">
          <a class="btn" href="/run">진단 시작</a>
          <a class="btn secondary" href="/samples">개발용 샘플 보기</a>
        </div>
      </div>
      <div class="mock">
        <div class="mock-top"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>
        <div class="mock-body">
          <h3>Wi_Finder 진단 화면</h3>
          <div class="mock-row">Wi-Fi 연결 상태 · 정상</div>
          <div class="mock-row">IP 상태 · 정상</div>
          <div class="mock-row warn">DNS / 인터넷 상태 점검</div>
        </div>
      </div>
    </section>

    <section class="steps">
      <div class="step">
        <span class="num">1</span>
        <h3>실행 파일 클릭</h3>
        <p>학생이 Wi_Finder.exe를 실행합니다.</p>
      </div>
      <div class="step">
        <span class="num">2</span>
        <h3>브라우저 자동 열림</h3>
        <p>로컬 주소에서 진단 화면이 열립니다.</p>
      </div>
      <div class="step">
        <span class="num">3</span>
        <h3>진단 시작 클릭</h3>
        <p>Windows 명령어 결과를 수집하고 분석합니다.</p>
      </div>
      <div class="step">
        <span class="num">4</span>
        <h3>결과 확인</h3>
        <p>Wi-Fi / IP / DNS / 인터넷 상태를 카드로 확인합니다.</p>
      </div>
    </section>
    """


def render_samples(selected_case: str | None = None, error: str | None = None) -> str:
    cases = get_cases()

    if selected_case is None and cases:
        selected_case = cases[0]

    options = []
    for case in cases:
        selected = "selected" if case == selected_case else ""
        label = CASE_LABELS.get(case, case)
        options.append(f'<option value="{e(case)}" {selected}>{e(label)}</option>')

    if error:
        result_html = f"""
        <section class="banner bad">
          <h2>샘플 실행 오류</h2>
          <p>{e(error)}</p>
        </section>
        """
    elif not cases:
        result_html = f"""
        <section class="banner bad">
          <h2>samples 폴더를 찾지 못했습니다</h2>
          <p>확인 경로: {e(SAMPLES_DIR)}</p>
        </section>
        """
    else:
        try:
            result_html = render_result(run_sample_case(selected_case or cases[0]))
        except Exception as exc:
            result_html = f"""
            <section class="banner bad">
              <h2>샘플 실행 오류</h2>
              <p>{e(exc)}</p>
            </section>
            """

    return f"""
    <form class="controls" method="get" action="/sample">
      <label for="case"><strong>샘플 케이스</strong></label>
      <select id="case" name="case">
        {''.join(options)}
      </select>
      <button type="submit">샘플 진단 실행</button>
    </form>
    {result_html}
    """


def render_error(title: str, message: str) -> str:
    return f"""
    <section class="banner bad">
      <div class="badge">ERROR</div>
      <h2>{e(title)}</h2>
      <p>{e(message)}</p>
      <div class="saved-path">
        Mac에서는 실제 Windows 명령어를 실행할 수 없으므로 이 오류가 정상일 수 있습니다.<br>
        실제 진단 테스트는 Windows 환경에서 진행하세요.
      </div>
    </section>
    """


def render_page(content: str, page_title: str = "Wi_Finder") -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(page_title)}</title>
  <style>
{CSS}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Wi_Finder</h1>
      <p>사용자 단말 기반 Wi-Fi 접속 장애 진단</p>
    </div>
    <nav>
      <a href="/">진단 홈</a>
      <a href="/run">진단 시작</a>
      <a href="/samples">샘플 보기</a>
    </nav>
  </header>
  <main>
    {content}
  </main>
</body>
</html>
"""


class WiFinderHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query = parse_qs(parsed_url.query)

            if path == "/":
                page = render_page(render_home(), page_title="Wi_Finder 진단 홈")
            elif path == "/run":
                try:
                    result = run_real_diagnosis()
                    page = render_page(render_result(result), page_title="Wi_Finder 진단 결과")
                except Exception as exc:
                    page = render_page(
                        render_error("진단 실행 오류", str(exc)),
                        page_title="Wi_Finder 진단 오류",
                    )
            elif path == "/samples":
                page = render_page(render_samples(), page_title="Wi_Finder 샘플 보기")
            elif path == "/sample":
                selected_case = query.get("case", [None])[0]
                page = render_page(
                    render_samples(selected_case=selected_case),
                    page_title="Wi_Finder 샘플 결과",
                )
            elif path == "/api/cases":
                self.send_json({"cases": get_cases()})
                return
            else:
                page = render_page(
                    render_error("페이지를 찾을 수 없습니다", path),
                    page_title="Wi_Finder 404",
                )

            self.send_html(page)

        except Exception as exc:
            fallback = (
                "<!doctype html><html><head><meta charset='utf-8'>"
                "<title>Wi_Finder 오류</title></head><body>"
                "<h1>Wi_Finder 내부 오류</h1>"
                f"<pre>{e(type(exc).__name__)}: {e(exc)}</pre>"
                "</body></html>"
            )
            self.send_html(fallback, status=500)

    def send_html(self, page: str, status: int = 200) -> None:
        encoded = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def send_json(self, data: Dict[str, Any]) -> None:
        encoded = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    url = f"http://{HOST}:{PORT}"
    server = ThreadingHTTPServer((HOST, PORT), WiFinderHandler)

    print("=" * 70)
    print("Wi_Finder 사용자용 GUI 서버 실행")
    print(f"브라우저 주소: {url}")
    print("종료하려면 터미널에서 Ctrl + C")
    print("=" * 70)

    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()