# src/notifier.py
# ============================================================
# 推播到 Telegram
# 需要先跟 @BotFather 申請 Bot，拿到 token，
# 再跟你的 Bot 說一句話、呼叫 getUpdates 拿到你的 chat_id
# ============================================================

import os
import requests


def send_telegram_message(text: str) -> bool:
    """
    用環境變數 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 寄送訊息。
    成功回傳 True，失敗印出錯誤並回傳 False（不中斷主流程）。
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[WARN] 未設定 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID，略過推播")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # Telegram 單則訊息上限約 4096 字元，超過就截斷並提示
    if len(text) > 4000:
        text = text[:3900] + "\n\n...(內容過長，已截斷)"

    try:
        resp = requests.post(
            url,
            data={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] Telegram 推播失敗: {e}")
        return False
