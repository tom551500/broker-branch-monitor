# src/run_report.py
# ============================================================
# 主流程：
#   1. 依序查詢 LEGEND_BROKERS 裡每個分點今天買賣了哪些股票
#   2. 過濾成只保留出現在 WATCHLIST（你的 56 檔清單）裡的股票
#   3. 淨買賣超超過 NOTIFY_THRESHOLD 張的才列入推播內容
#   4. 組成訊息，推播到 Telegram
#   5. 同時輸出一份 JSON 到 output/，留存歷史紀錄
# ============================================================

import os
import json
import time
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from config import LEGEND_BROKERS, WATCHLIST, DEFAULT_DAYS, NOTIFY_THRESHOLD
from fetcher import fetch_broker_activity
from notifier import send_telegram_message

TZ = ZoneInfo("Asia/Taipei")


def ensure_output_dir():
    os.makedirs("output", exist_ok=True)


def now_taipei():
    return datetime.now(TZ)


def build_report(days: int):
    """
    回傳:
      hits: list of dict，每筆是「某分點對你清單裡某股票」的買賣紀錄
      summary: dict，本次執行的統計資訊（給 JSON 存檔與除錯用）
    """
    start_time = now_taipei()
    hits = []
    errors = []
    broker_ok = 0
    broker_fail = 0

    for broker_id, broker_name in LEGEND_BROKERS.items():
        try:
            activity = fetch_broker_activity(broker_id, days)

            for sid, info in activity.items():
                if sid not in WATCHLIST:
                    continue  # 不在你的監控清單裡，跳過

                net = info["net"]
                if abs(net) < NOTIFY_THRESHOLD:
                    continue  # 變動太小，視為雜訊

                hits.append({
                    "日期": start_time.strftime("%Y-%m-%d"),
                    "分點": broker_name,
                    "分點代號": broker_id,
                    "代碼": sid,
                    "名稱": WATCHLIST.get(sid) or info["name"],
                    "買進": info["buy"],
                    "賣出": info["sell"],
                    "淨超": net,
                })

            broker_ok += 1
            # 禮貌性延遲，避免短時間內對同一網站連續發送請求
            time.sleep(1.5 + random.uniform(0, 0.5))

        except Exception as e:
            broker_fail += 1
            msg = f"{broker_name}({broker_id}) 查詢失敗：{e}"
            errors.append(msg)
            print(f"[WARN] {msg}")

    # 淨超絕對值大到小排序，重點優先看
    hits.sort(key=lambda r: abs(r["淨超"]), reverse=True)

    summary = {
        "generated_at": start_time.isoformat(),
        "timezone": "Asia/Taipei",
        "days": days,
        "watchlist_size": len(WATCHLIST),
        "brokers_total": len(LEGEND_BROKERS),
        "brokers_ok": broker_ok,
        "brokers_fail": broker_fail,
        "hits_count": len(hits),
        "errors": errors,
    }
    return hits, summary


def format_message(hits: list, summary: dict) -> str:
    date_str = summary["generated_at"][:10]

    if not hits:
        return (
            f"📊 <b>分點監控日報 {date_str}</b>\n\n"
            f"今天監控的 {summary['brokers_total']} 個分點，"
            f"在你的 {summary['watchlist_size']} 檔清單裡沒有達到門檻的進出。\n"
            f"（門檻：淨超絕對值 ≥ {NOTIFY_THRESHOLD} 張）"
        )

    lines = [f"📊 <b>分點監控日報 {date_str}</b>", ""]
    for h in hits:
        sign = "🔴買超" if h["淨超"] > 0 else "🟢賣超"
        lines.append(
            f"{sign} <b>{h['名稱']}({h['代碼']})</b>\n"
            f"　分點：{h['分點']}　"
            f"買{h['買進']:,} / 賣{h['賣出']:,} / 淨{h['淨超']:+,}張"
        )

    if summary["errors"]:
        lines.append("")
        lines.append(f"⚠️ {summary['brokers_fail']} 個分點查詢失敗，詳見 output/summary.json")

    return "\n".join(lines)


def main():
    ensure_output_dir()
    days = int(os.getenv("DAYS", str(DEFAULT_DAYS)))

    hits, summary = build_report(days)
    message = format_message(hits, summary)

    print(message)
    print("-" * 40)

    sent = send_telegram_message(message)
    summary["telegram_sent"] = sent

    ymd = now_taipei().strftime("%Y%m%d")
    summary_path = os.path.join("output", f"summary_{ymd}.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({"hits": hits, "summary": summary}, f, ensure_ascii=False, indent=2)

    print(f"[OK] Summary: {summary_path}")

    if summary["brokers_ok"] == 0:
        # 全部分點都查詢失敗，視為本次執行失敗，讓 GitHub Actions 標紅方便你注意到
        raise SystemExit(1)


if __name__ == "__main__":
    main()
