# REPORT 4: RANGE & NEN GIA
import urllib.request, ssl, json
from datetime import datetime, timedelta
from telegram_helper import send_message, call_claude_with_retry
from config_loader import load_config, get_secrets, get_active_targets

WEEKDAYS_VI = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]

def fetch_ohlc(interval, range_):
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
            candles.append({"date": datetime.utcfromtimestamp(ts).strftime("%d/%m/%Y"),
                "open":round(o,2),"high":round(h,2),"low":round(l,2),"close":round(c,2)})
        return candles
    except Exception as e:
        print(f"[Yahoo Error] {e}"); return []

def phan_loai_nen(o,c,h,l):
    body=abs(c-o); total=h-l
    if total==0: return "Doji"
    r=body/total; huong="Tăng (Bullish)" if c>=o else "Giảm (Bearish)"
    if r>=0.7: return f"{huong} — thân lớn"
    if r>=0.4: return f"{huong} — thân trung bình"
    return f"{huong} — thân nhỏ, do dự"

def main():
    cfg = load_config()
    secrets = get_secrets()
    targets = get_active_targets(cfg, "range")
    if not cfg["reports"]["range"].get("enabled", True):
        return

    now_ict  = datetime.utcnow() + timedelta(hours=7)
    day_vi   = WEEKDAYS_VI[now_ict.weekday()]
    date_str = now_ict.strftime("%d/%m/%Y")

    daily  = fetch_ohlc("1d", "10d")
    weekly = fetch_ohlc("1wk", "1mo")

    data_text = f"Dữ liệu giá XAUUSD (Gold Futures GC=F) ngày {date_str}:\n\n"
    if weekly:
        w = weekly[-1]; w_range=w["high"]-w["low"]; w_mid=round((w["high"]+w["low"])/2,2)
        data_text += (f"NẾN TUẦN đang chạy:\n"
                      f"  Open:{w['open']} High:{w['high']} Low:{w['low']} Close:{w['close']}\n"
                      f"  Range:{w_range:.0f} | Midpoint:{w_mid} | {phan_loai_nen(w['open'],w['close'],w['high'],w['low'])}\n\n")
    if daily and len(daily)>=2:
        dp=daily[-2]; dp_range=dp["high"]-dp["low"]; dp_mid=round((dp["high"]+dp["low"])/2,2)
        data_text += (f"NẾN NGÀY QUA ({dp['date']}):\n"
                      f"  Open:{dp['open']} High:{dp['high']} Low:{dp['low']} Close:{dp['close']}\n"
                      f"  Range:{dp_range:.0f} | Midpoint:{dp_mid} | {phan_loai_nen(dp['open'],dp['close'],dp['high'],dp['low'])}\n\n")
    if daily:
        dt=daily[-1]; dt_range=dt["high"]-dt["low"]; dt_mid=round((dt["high"]+dt["low"])/2,2)
        data_text += (f"NẾN HÔM NAY ({date_str}):\n"
                      f"  Open:{dt['open']} High:{dt['high']} Low:{dt['low']} Close:{dt['close']}\n"
                      f"  Range:{dt_range:.0f} | Midpoint:{dt_mid} | {phan_loai_nen(dt['open'],dt['close'],dt['high'],dt['low'])}\n\n")

    prompt = f"""Dưới đây là dữ liệu giá XAUUSD hôm nay ({day_vi}, {date_str}):

{data_text}

Viết report PHÂN TÍCH RANGE & NẾN GIÁ. Bằng tiếng Việt có dấu. Chỉ dùng <b> và <i>. Dùng ━ để kẻ ngang.

Cấu trúc:
📈 <b>GOLD / XAUUSD — RANGE & NẾN GIÁ</b>
━━━━━━━━━━━━━━━━━━━━
📅 Cập nhật: {day_vi} - {date_str} | {now_ict.strftime('%H:%M')} ICT

━━━━━━━━━━━━━━━━━━━━
<b>📊 NẾN TUẦN (W1) — Đang chạy</b>
[OHLC từ dữ liệu trên, range, midpoint, loại nến]
1-2 câu nhận định cấu trúc nến tuần.

━━━━━━━━━━━━━━━━━━━━
<b>📉 NẾN NGÀY QUA (D1)</b>
[OHLC từ dữ liệu trên]
1-2 câu nhận định nến đóng cửa.

━━━━━━━━━━━━━━━━━━━━
<b>📊 NẾN HÔM NAY (D1) — Mới mở cửa</b>
[OHLC từ dữ liệu trên]
1-2 câu nhận định.

━━━━━━━━━━━━━━━━━━━━
<b>🎯 CÁC VÙNG QUAN TRỌNG HÔM NAY:</b>
Hỗ trợ mạnh (đáy tuần)       : [số]
Hỗ trợ ngày (đáy hôm qua)    : [số]
Điểm giữa ngày qua           : [số]
Điểm giữa tuần               : [số]
Kháng cự ngày (đỉnh hôm qua) : [số]
Kháng cự mạnh (đỉnh tuần)    : [số]

━━━━━━━━━━━━━━━━━━━━
<b>📋 KỊCH BẢN GIAO DỊCH HÔM NAY:</b>
✅ <b>BUY:</b> [vùng entry | SL | TP]
❌ <b>SELL:</b> [vùng entry | SL | TP]
⚡ Lưu ý: [1 câu quan trọng nhất]

<i>Nguồn: Yahoo Finance (GC=F Gold Futures)</i>"""

    print("[Range] Gọi Claude API...")
    content = call_claude_with_retry(prompt, secrets["anthropic_key"], use_search=False, max_tokens=2000)
    if not content:
        content = f"📈 <b>RANGE & NẾN GIÁ</b>\n━━━━━━━━━━━━━━━━━━━━\n{data_text}"

    print(f"[Range] {len(content)} ký tự")
    for t in targets:
        print(f"[Range] → {t['name']}")
        ok = send_message(secrets["bot_token"], t["chat_id"], content)
        print(f"  {'✅' if ok else '❌'}")

if __name__ == "__main__":
    main()
