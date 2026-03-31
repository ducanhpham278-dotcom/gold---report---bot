# =============================================================
# REPORT 4: RANGE & NẾN GIÁ (Thứ 2 → Thứ 7, 6:00 ICT)
# =============================================================

import urllib.request, ssl, json
from datetime import datetime, timedelta
from config_loader import load_config, get_secrets, get_active_targets

WEEKDAYS_VI = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]

def send_telegram(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id":chat_id,"text":text,
        "parse_mode":"HTML","disable_web_page_preview":True}).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"[Telegram Error] {e}"); return False

def fetch_ohlc(interval, range_):
    url = (f"https://query2.finance.yahoo.com/v8/finance/chart/GC=F"
           f"?interval={interval}&range={range_}&includePrePost=false")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = json.loads(resp.read())
        result = data["chart"]["result"][0]
        quote  = result["indicators"]["quote"][0]
        candles = []
        for i, ts in enumerate(result["timestamp"]):
            o,h,l,c = quote["open"][i],quote["high"][i],quote["low"][i],quote["close"][i]
            if None in (o,h,l,c): continue
            candles.append({"date":datetime.utcfromtimestamp(ts).strftime("%d/%m/%Y"),
                "open":round(o,2),"high":round(h,2),"low":round(l,2),"close":round(c,2)})
        return candles
    except Exception as e:
        print(f"[Yahoo Error] {e}"); return []

def phan_loai_nen(o, c, h, l):
    body = abs(c-o); total = h-l
    if total == 0: return "Doji — thị trường do dự"
    ratio = body/total; huong = "Tăng (Bullish)" if c >= o else "Giảm (Bearish)"
    if ratio >= 0.7: return f"{huong} — thân lớn, xu hướng mạnh"
    if ratio >= 0.4: return f"{huong} — thân trung bình"
    return f"{huong} — thân nhỏ, do dự"

def build_report(daily, weekly, cfg):
    rc = cfg["reports"]["range"]
    now_ict = datetime.utcnow() + timedelta(hours=7)
    day_vi  = WEEKDAYS_VI[now_ict.weekday()]
    date_str = now_ict.strftime("%d/%m/%Y")

    lines = [f"<b>{rc['header']}</b>","━━━━━━━━━━━━━━━━━━━━",
        f"📅 Cập nhật: {day_vi} - {date_str} | {now_ict.strftime('%H:%M')} ICT"]

    if weekly:
        w = weekly[-1]; w_range = w["high"]-w["low"]; w_mid = round((w["high"]+w["low"])/2,2)
        lines += ["","━━━━━━━━━━━━━━━━━━━━","<b>📊 NẾN TUẦN (W1) — Đang chạy</b>",
            f"Mở cửa   : {w['open']:.2f}",f"Cao nhất : {w['high']:.2f}",
            f"Thấp nhất: {w['low']:.2f}",f"Hiện tại : {w['close']:.2f}",
            f"Range tuần: {w_range:.0f} pip | Điểm giữa: {w_mid:.2f}",
            f"Loại nến : {phan_loai_nen(w['open'],w['close'],w['high'],w['low'])}",
            f"Kháng cự tuần: {w['high']:.2f} | Hỗ trợ tuần: {w['low']:.2f}"]

    if daily and len(daily) >= 2:
        d = daily[-2]; d_range = d["high"]-d["low"]; d_mid = round((d["high"]+d["low"])/2,2)
        lines += ["","━━━━━━━━━━━━━━━━━━━━",f"<b>📉 NẾN NGÀY QUA (D1) — {d['date']}</b>",
            f"Mở cửa   : {d['open']:.2f}",f"Cao nhất : {d['high']:.2f}",
            f"Thấp nhất: {d['low']:.2f}",f"Đóng cửa : {d['close']:.2f}",
            f"Range: {d_range:.0f} pip | Điểm giữa: {d_mid:.2f}",
            f"Loại nến: {phan_loai_nen(d['open'],d['close'],d['high'],d['low'])}"]

    if daily:
        dt = daily[-1]; dt_range = dt["high"]-dt["low"]; dt_mid = round((dt["high"]+dt["low"])/2,2)
        lines += ["","━━━━━━━━━━━━━━━━━━━━",f"<b>📊 NẾN HÔM NAY (D1) — {date_str}</b>",
            f"Mở cửa   : {dt['open']:.2f}",f"Cao nhất : {dt['high']:.2f}",
            f"Thấp nhất: {dt['low']:.2f}",f"Hiện tại : {dt['close']:.2f}",
            f"Range hiện tại: {dt_range:.0f} pip | Điểm giữa: {dt_mid:.2f}",
            f"Xu hướng nến: {phan_loai_nen(dt['open'],dt['close'],dt['high'],dt['low'])}"]
        if weekly and len(daily) >= 2:
            w = weekly[-1]; dp = daily[-2]
            lines += ["","━━━━━━━━━━━━━━━━━━━━","<b>🎯 CÁC VÙNG QUAN TRỌNG HÔM NAY:</b>",
                f"Hỗ trợ mạnh (đáy tuần)      : {w['low']:.2f}",
                f"Hỗ trợ ngày (đáy hôm qua)   : {dp['low']:.2f}",
                f"Điểm giữa ngày qua          : {round((dp['high']+dp['low'])/2,2):.2f}",
                f"Điểm giữa tuần              : {round((w['high']+w['low'])/2,2):.2f}",
                f"Kháng cự ngày (đỉnh hôm qua): {dp['high']:.2f}",
                f"Kháng cự mạnh (đỉnh tuần)   : {w['high']:.2f}"]

    lines += ["","━━━━━━━━━━━━━━━━━━━━","<b>⚡ Lưu ý:</b>"] \
           + [f"- {n}" for n in rc["note_lines"]] + ["",f"<i>{rc['footer']}</i>"]
    return "\n".join(lines)

def main():
    cfg = load_config(); secrets = get_secrets()
    targets = get_active_targets(cfg, "range")
    if not cfg["reports"]["range"].get("enabled", True):
        print("[Range] Disabled — bỏ qua"); return
    daily  = fetch_ohlc("1d","10d"); weekly = fetch_ohlc("1wk","1mo")
    report = build_report(daily, weekly, cfg)
    for t in targets:
        print(f"[Range] → {t['name']}")
        ok = send_telegram(secrets["bot_token"], t["chat_id"], report)
        print(f"  {'✅ OK' if ok else '❌ Thất bại'}")

if __name__ == "__main__":
    main()
