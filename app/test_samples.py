from pathlib import Path

from parser import parse_sample_case
from diagnosis import diagnose
from display import build_display_data


SAMPLES_DIR = Path("samples")

EXPECTED = {
    "case1_normal": "NORMAL",
    "case2_disconnected": "DISCONNECTED",
    "case3_1_connected_no_ip": "CONNECTED_NO_IP",
    "case3_2_dns_fail": "DNS_FAIL",
    "case3_3_external_ping_fail": "EXTERNAL_PING_FAIL",
}


def main():
    print("=== Wi_Finder Sample Integration Test ===\n")

    passed = 0
    failed = 0

    for case_name, expected_code in EXPECTED.items():
        case_dir = SAMPLES_DIR / case_name

        if not case_dir.exists():
            print(f"[FAIL] {case_name}")
            print(f"  - samples folder not found: {case_dir}\n")
            failed += 1
            continue

        try:
            parsed = parse_sample_case(case_dir)
            diagnosis_result = diagnose(parsed)
            display_data = build_display_data(diagnosis_result)

            actual_code = diagnosis_result.get("code")

            main_cards = display_data.get("main_cards", [])
            sub_cards = display_data.get("sub_cards", [])
            detail_rows = display_data.get("detail_rows", [])

            if actual_code == expected_code:
                print(f"[PASS] {case_name}")
                print(f"  expected   : {expected_code}")
                print(f"  actual     : {actual_code}")
                print(f"  title      : {diagnosis_result.get('title')}")
                print(f"  main_cards : {len(main_cards)}")
                print(f"  sub_cards  : {len(sub_cards)}")
                print(f"  detail_rows: {len(detail_rows)}\n")
                passed += 1
            else:
                print(f"[FAIL] {case_name}")
                print(f"  expected   : {expected_code}")
                print(f"  actual     : {actual_code}")
                print(f"  title      : {diagnosis_result.get('title')}")
                print(f"  summary    : {diagnosis_result.get('summary')}")
                print(f"  main_cards : {len(main_cards)}")
                print(f"  sub_cards  : {len(sub_cards)}")
                print(f"  detail_rows: {len(detail_rows)}\n")
                failed += 1

        except Exception as e:
            print(f"[ERROR] {case_name}")
            print(f"  error: {e}\n")
            failed += 1

    print("=== Test Result ===")
    print(f"PASS: {passed}")
    print(f"FAIL: {failed}")

    if failed == 0:
        print("\n모든 samples case가 기대한 진단 결과와 일치합니다.")
    else:
        print("\n일부 case의 진단 결과가 기대값과 다릅니다. parser.py, diagnosis.py, display.py를 확인해야 합니다.")


if __name__ == "__main__":
    main()