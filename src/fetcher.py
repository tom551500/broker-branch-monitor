# src/fetcher.py
# ============================================================
# 抓取富邦e01證券網站的「分點進出排行」公開頁面
# 資料源：https://fubon-ebrokerdj.fbs.com.tw
# 這是網頁爬蟲，不是正式 API；網站結構異動時可能需要調整 parse_table()
# ============================================================

import re
import time
import random

import requests
from bs4 import BeautifulSoup

HEAD_BROKER = "9600"
BASE_URL = "https://fubon-ebrokerdj.fbs.com.tw/z/zg/zgb/zgb0.djhtm"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def safe_int(s: str) -> int:
    if s is None:
        return 0
    s = s.strip().replace(",", "")
    if s in ("", "--", "-"):
        return 0
    try:
        return int(s)
    except ValueError:
        m = re.search(r"-?\d+", s)
        return int(m.group()) if m else 0


def fetch_html(url: str, timeout: int = 20, retries: int = 5, base_sleep: float = 1.0) -> str:
    """帶重試機制的 HTML 抓取，避免偶發性失敗就整支程式掛掉。"""
    headers = {
        "User-Agent": UA,
        "Referer": "https://fubon-ebrokerdj.fbs.com.tw/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            for enc in ("cp950", "big5", "utf-8"):
                try:
                    r.encoding = enc
                    if r.status_code == 200 and r.text and len(r.text) > 100:
                        return r.text
                except Exception:
                    continue
            last_err = RuntimeError(f"HTTP {r.status_code}")
        except Exception as e:
            last_err = e
        time.sleep(base_sleep * (2 ** attempt) + random.uniform(0, 0.5))
    raise last_err


def parse_table(html: str) -> dict:
    """解析分點進出排行表格，回傳 {股票代號: {name, buy, sell, net}}。"""
    soup = BeautifulSoup(html, "html.parser")
    res = {}
    pat = re.compile(
        r"GenLink2stk\(\s*['\"]AS(\w+)['\"]\s*,\s*['\"](.+?)['\"]\s*\)"
    )
    for tr in soup.find_all("tr"):
        tr_text = tr.decode_contents()
        m = pat.search(tr_text)
        if not m:
            continue
        sid = m.group(1)
        name = m.group(2)
        tds = tr.find_all("td", class_=re.compile(r"t3n[01]"))
        if len(tds) < 3:
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
        buy_txt = tds[0].get_text(strip=True)
        sell_txt = tds[1].get_text(strip=True)
        net_txt = tds[2].get_text(strip=True)
        res[sid] = {
            "name": name,
            "buy": safe_int(buy_txt),
            "sell": safe_int(sell_txt),
            "net": safe_int(net_txt),
        }
    return res


def fetch_broker_activity(broker_id: str, days: int) -> dict:
    """
    查詢單一分點在過去 N 天，買賣了哪些股票（張數）。
    回傳 {股票代號: {name, buy, sell, net}}
    """
    url_qty = f"{BASE_URL}?a={HEAD_BROKER}&b={broker_id}&c=E&d={days}"
    html_qty = fetch_html(url_qty)
    return parse_table(html_qty)
