# REPORT 4: RANGE & NEN GIA
# Uu tien doc tu TradingView (ohlc_d1.json), fallback Yahoo Finance
import urllib.request, ssl, json, base64, os
from datetime import datetime, timedelta
from telegram_helper import send_message
from config_loader import load_config, get_secrets, get_active_targets

WEEKDAYS_VI = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]
REPO = "ducanhpham278-dotcom/gold---report---bot"

def read_github(path, gh_token):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {gh_token}",
               "Accept": "application/vnd.github.v3+json"}
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            resp = json.loads(r.read())
            return json.loads(base64.b64decode(resp["content"]).decode("utf-8"))
    except Exception as e:
        print(f"[GitHub] {path}: {e}")
        return None

def fetch_ohlc_yahoo(interval, range_):
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
        print(f"[Yahoo] {e}"); return []

def phan_loai(o, c, h, l):
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
    is_weekend = now_ict.weekday() >= 5

    # === LAY DU LIEU OHLC ===
    # Uu tien: TradingView ohlc_d1.json
    # Fallback: Yahoo Finance
    source = "Yahoo Finance"
    dp = None  # nen ngay gan nhat da dong

    if gh_token:
        d1_data = read_github("data/ohlc_d1.json", gh_token)
        if d1_data:
            dp = {
                "date":  d1_data.get("date", ""),
                "open":  float(d1_data.get("open",  0)),
                "high":  float(d1_data.get("high",  0)),
                "low":   float(d1_data.get("low",   0)),
                "close": float(d1_data.get("close", 0)),
            }
            source = "TradingView"
            print(f"[Range] Dùng TradingView D1: {dp['date']}")

    # Fallback Yahoo neu chua co TradingView
    if not dp:
        daily = fetch_ohlc_yahoo("1d", "10d")
        if daily and len(daily) >= 2:
            dp = daily[-2]
            print(f"[Range] Fallback Yahoo D1: {dp['date']}")

    # Weekly tu Yahoo (chua co TradingView W1)
    weekly = fetch_ohlc_yahoo("1wk", "1mo")
    w_last = weekly[-1] if weekly else None

    # === GIA CHUAN ===
    gia_chuan = None
    gia_chuan_txt = "⏳ Chưa có (chờ 22:00 ICT)"
    if gh_token:
        gc = read_github("data/gia_chuan.json", gh_token)
        if gc:
            gia_chuan = float(gc.get("close", 0))
            gia_chuan_txt = f"{gia_chuan:.2f}"
            print(f"[Range] Giá chuẩn: {gia_chuan_txt}")

    # === BUILD REPORT ===
    lines = [
        "📈 <b>GOLD / XAUUSD — RANGE &amp; NẾN GIÁ</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📅 Cập nhật: {day_vi} - {date_str} | {time_str} ICT",
    ]

    # Nen tuan: chi hien cuoi tuan
    if is_weekend and w_last:
        w_range_chay = round(w_last["high"] - w_last["low"], 2)
        w_range_dm   = round(abs(w_last["close"] - w_last["open"]), 2)
        lines += [
            "", "━━━━━━━━━━━━━━━━━━━━",
            "<b>📊 NẾN TUẦN (W1) — Đã đóng</b>",
            f"Mở cửa   : {w_last['open']:.2f}",
            f"Cao nhất : {w_last['high']:.2f}",
            f"Thấp nhất: {w_last['low']:.2f}",
            f"Đóng cửa : {w_last['close']:.2f}",
            f"Range chạy   : {w_range_chay:.2f} (Cao - Thấp)",
            f"Range đóng mở: {w_range_dm:.2f} ({'Tăng' if w_last['close']>=w_last['open'] else 'Giảm'})",
            f"Loại nến : {phan_loai(w_last['open'],w_last['close'],w_last['high'],w_last['low'])}",
        ]

    # Nen ngay gan nhat da dong
    if dp:
        dp_range_chay = round(dp["high"] - dp["low"], 2)
        dp_range_dm   = round(abs(dp["close"] - dp["open"]), 2)
        lines += [
            "", "━━━━━━━━━━━━━━━━━━━━",
            f"<b>📉 NẾN NGÀY GẦN NHẤT (D1) — {dp['date']}</b>",
            f"Mở cửa   : {dp['open']:.2f}",
            f"Cao nhất : {dp['high']:.2f}",
            f"Thấp nhất: {dp['low']:.2f}",
            f"Đóng cửa : {dp['close']:.2f}",
            f"Range chạy   : {dp_range_chay:.2f} (Cao - Thấp)",
            f"Range đóng mở: {dp_range_dm:.2f} ({'Tăng' if dp['close']>=dp['open'] else 'Giảm'})",
            f"Giá chuẩn    : {gia_chuan_txt}",
            f"Loại nến : {phan_loai(dp['open'],dp['close'],dp['high'],dp['low'])}",
        ]

        # Vung quan trong
        lines += [
            "", "━━━━━━━━━━━━━━━━━━━━",
            "<b>🎯 CÁC VÙNG QUAN TRỌNG HÔM NAY:</b>",
        ]
        if w_last:
            lines.append(f"Hỗ trợ mạnh (đáy tuần)       : {w_last['low']:.2f}")
        lines += [
            f"Hỗ trợ ngày (đáy hôm qua)    : {dp['low']:.2f}",
            f"Giá chuẩn 21:00 ICT          : {gia_chuan_txt}",
            f"Kháng cự ngày (đỉnh hôm qua) : {dp['high']:.2f}",
        ]
        if w_last:
            lines.append(f"Kháng cự mạnh (đỉnh tuần)    : {w_last['high']:.2f}")

        # Kich ban
        buy_zone = f"{gia_chuan:.2f}" if gia_chuan else f"{dp['close']:.2f}"
        lines += [
            "", "━━━━━━━━━━━━━━━━━━━━",
            "<b>📋 KỊCH BẢN GIAO DỊCH HÔM NAY:</b>",
            f"✅ <b>BUY:</b> Pullback về vùng {buy_zone} – {dp['low']:.2f}",
            f"SL: Dưới {dp['low']-15:.2f} | TP: {dp['high']:.2f}",
            f"❌ <b>SELL:</b> Bác bỏ tại kháng cự {dp['high']:.2f}",
            f"SL: Trên {dp['high']+15:.2f} | TP: {buy_zone} → {dp['low']:.2f}",
            "⚡ Lưu ý: Tránh vào lệnh trước tin quan trọng 30 phút",
        ]

    lines.append(f"\n<i>Nguồn: {source} (OHLC) + TradingView (Giá chuẩn)</i>")

    content = "\n".join(lines)
    print(f"[Range] {len(content)} ký tự")
    for t in targets:
        print(f"[Range] → {t['name']}")
        ok = send_message(secrets["bot_token"], t["chat_id"], content)
        print(f"  {'✅' if ok else '❌'}")

if __name__ == "__main__":
    main()
