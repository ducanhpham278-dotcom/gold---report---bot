# REPORT 4: RANGE & NEN GIA - Doc du lieu tu TradingView qua GitHub
import urllib.request, ssl, json, base64, os
from datetime import datetime, timedelta
from telegram_helper import send_message
from config_loader import load_config, get_secrets, get_active_targets

WEEKDAYS_VI = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]
REPO = "ducanhpham278-dotcom/gold---report---bot"

def read_github_file(path: str, gh_token: str) -> dict | None:
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            resp = json.loads(r.read())
            return json.loads(base64.b64decode(resp["content"]).decode("utf-8"))
    except Exception as e:
        print(f"[GitHub] Không đọc được {path}: {e}")
        return None

def fetch_ohlc_yahoo(interval, range_):
    """Fallback: lay OHLC tu Yahoo Finance neu khong co TradingView data."""
    url = (f"https://query2.finance.yahoo.com/v8/finance/chart/GC=F"
           f"?interval={interval}&range={range_}&includePrePost=false")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            data = json.loads(r.read())
        result = data["chart"]["result"][0]
        q = result["indicators"]["quote"][0]
        candles = []
        for i, ts in enumerate(result["timestamp"]):
            o,h,l,c = q["open"][i],q["high"][i],q["low"][i],q["close"][i]
            if None in (o,h,l,c): continue
            candles.append({
                "date":  datetime.utcfromtimestamp(ts).strftime("%d/%m/%Y"),
                "open":  round(o,2), "high": round(h,2),
                "low":   round(l,2), "close":round(c,2)
            })
        return candles
    except Exception as e:
        print(f"[Yahoo Error] {e}"); return []

def phan_loai_nen(o, c, h, l):
    body = abs(c-o); total = h-l
    if total == 0: return "Doji"
    r = body/total
    huong = "Tăng (Bullish)" if c >= o else "Giảm (Bearish)"
    if r >= 0.7: return f"{huong} — thân lớn"
    if r >= 0.4: return f"{huong} — thân trung bình"
    return f"{huong} — thân nhỏ, do dự"

def main():
    cfg     = load_config()
    secrets = get_secrets()
    targets = get_active_targets(cfg, "range")
    if not cfg["reports"]["range"].get("enabled", True):
        return

    gh_token = os.environ.get("GH_TOKEN", "")
    now_ict  = datetime.utcnow() + timedelta(hours=7)
    day_vi   = WEEKDAYS_VI[now_ict.weekday()]
    date_str = now_ict.strftime("%d/%m/%Y")
    time_str = now_ict.strftime("%H:%M")
    is_weekend = now_ict.weekday() >= 5  # Thu 7 hoac CN

    # --- Lay du lieu nen ngay tu Yahoo Finance ---
    daily  = fetch_ohlc_yahoo("1d", "10d")
    weekly = fetch_ohlc_yahoo("1wk", "1mo")

    # --- Lay Gia Chuan 21:00 ICT tu GitHub ---
    gia_chuan = None
    gia_chuan_note = "⏳ Chưa có (chờ 22:00 ICT)"
    if gh_token:
        gc_data = read_github_file("data/gia_chuan.json", gh_token)
        if gc_data:
            gia_chuan = float(gc_data.get("close", 0))
            gia_chuan_note = f"{gia_chuan:.2f}"
            print(f"[Range] Giá chuẩn 21:00 ICT: {gia_chuan_note}")

    lines = [
        f"📈 <b>GOLD / XAUUSD — RANGE &amp; NẾN GIÁ</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📅 Cập nhật: {day_vi} - {date_str} | {time_str} ICT",
    ]

    # --- Nen tuan: chi gui vao Thu 7 hoac CN ---
    if is_weekend and weekly and len(weekly) >= 1:
        w = weekly[-1]
        w_range_chay  = round(w["high"] - w["low"], 2)
        w_range_dm    = round(abs(w["close"] - w["open"]), 2)
        w_dm_huong    = "Tăng" if w["close"] >= w["open"] else "Giảm"
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            f"<b>📊 NẾN TUẦN (W1) — Đã đóng</b>",
            f"Mở cửa  : {w['open']:.2f}",
            f"Cao nhất: {w['high']:.2f}",
            f"Thấp nhất: {w['low']:.2f}",
            f"Đóng cửa: {w['close']:.2f}",
            f"Range chạy   : {w_range_chay:.2f} (Cao - Thấp)",
            f"Range đóng mở: {w_range_dm:.2f} ({w_dm_huong})",
            f"Loại nến: {phan_loai_nen(w['open'],w['close'],w['high'],w['low'])}",
        ]
    elif is_weekend:
        lines += ["", "<i>⏳ Chưa có dữ liệu nến tuần</i>"]

    # --- Nen ngay gan nhat da dong cua ---
    if daily and len(daily) >= 2:
        # Nen ngay hom qua (da dong cua)
        dp = daily[-2]
        dp_range_chay = round(dp["high"] - dp["low"], 2)
        dp_range_dm   = round(abs(dp["close"] - dp["open"]), 2)
        dp_dm_huong   = "Tăng" if dp["close"] >= dp["open"] else "Giảm"
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            f"<b>📉 NẾN NGÀY GẦN NHẤT (D1) — {dp['date']}</b>",
            f"Mở cửa  : {dp['open']:.2f}",
            f"Cao nhất: {dp['high']:.2f}",
            f"Thấp nhất: {dp['low']:.2f}",
            f"Đóng cửa: {dp['close']:.2f}",
            f"Range chạy   : {dp_range_chay:.2f} (Cao - Thấp)",
            f"Range đóng mở: {dp_range_dm:.2f} ({dp_dm_huong})",
            f"Giá chuẩn    : {gia_chuan_note}",
            f"Loại nến: {phan_loai_nen(dp['open'],dp['close'],dp['high'],dp['low'])}",
        ]

        # Vung quan trong
        w_last = weekly[-1] if weekly else None
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "<b>🎯 CÁC VÙNG QUAN TRỌNG HÔM NAY:</b>",
        ]
        if w_last:
            lines += [
                f"Hỗ trợ mạnh (đáy tuần)       : {w_last['low']:.2f}",
            ]
        lines += [
            f"Hỗ trợ ngày (đáy hôm qua)    : {dp['low']:.2f}",
            f"Giá chuẩn 21:00 ICT          : {gia_chuan_note}",
        ]
        if w_last:
            lines += [
                f"Kháng cự ngày (đỉnh hôm qua) : {dp['high']:.2f}",
                f"Kháng cự mạnh (đỉnh tuần)    : {w_last['high']:.2f}",
            ]
        else:
            lines += [
                f"Kháng cự ngày (đỉnh hôm qua) : {dp['high']:.2f}",
            ]

        # Kich ban giao dich
        lines += [
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "<b>📋 KỊCH BẢN GIAO DỊCH HÔM NAY:</b>",
            f"✅ <b>BUY:</b> Pullback về vùng {gia_chuan:.2f if gia_chuan else dp['close']:.2f} – {dp['low']:.2f}",
            f"SL: Dưới {dp['low'] - 15:.2f} | TP: {dp['high']:.2f}",
            f"❌ <b>SELL:</b> Bác bỏ tại kháng cự {dp['high']:.2f}",
            f"SL: Trên {dp['high'] + 15:.2f} | TP: {gia_chuan:.2f if gia_chuan else dp['close']:.2f} → {dp['low']:.2f}",
            "⚡ Lưu ý: Tránh vào lệnh trước tin quan trọng 30 phút",
        ]

    lines += [
        "",
        "<i>Nguồn: Yahoo Finance (OHLC) + TradingView (Giá chuẩn)</i>",
    ]

    content = "\n".join(lines)
    print(f"[Range] {len(content)} ký tự")
    for t in targets:
        print(f"[Range] → {t['name']}")
        ok = send_message(secrets["bot_token"], t["chat_id"], content)
        print(f"  {'✅' if ok else '❌'}")

if __name__ == "__main__":
    main()
