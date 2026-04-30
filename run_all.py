import subprocess
import sys
from pathlib import Path
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

RUN_LOG_PATH = LOG_DIR / "run_all_log.txt"


def write_log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = f"[{now}] {message}"
    print(text)

    with RUN_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(text + "\n")


def run_script(script_name):
    script_path = PROJECT_ROOT / script_name

    if not script_path.exists():
        write_log(f"[錯誤] 找不到 {script_name}")
        return False

    write_log(f"開始執行：{script_name}")

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.stdout:
        write_log(f"[{script_name} 輸出]")
        print(result.stdout)

    if result.stderr:
        write_log(f"[{script_name} 錯誤]")
        print(result.stderr)

    if result.returncode != 0:
        write_log(f"[失敗] {script_name} return code = {result.returncode}")
        return False

    write_log(f"[完成] {script_name}")
    return True


def main():
    write_log("========== Crypto Flow Radar 一鍵流程開始 ==========")

    ok_macro = run_script("update_macro_data.py")

    if not ok_macro:
        write_log("[中止] 宏觀資料更新失敗，未執行 app.py")
        return

    ok_report = run_script("app.py")

    if not ok_report:
        write_log("[失敗] 報告產生失敗")
        return

    write_log("========== Crypto Flow Radar 一鍵流程完成 ==========")


if __name__ == "__main__":
    main()