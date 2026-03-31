# REPORT 2: TIN TUC NGAY - Claude API tong hop noi dung
import urllib.request, ssl, json, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from config_loader import load_config, get_secrets, get_active_targets

def send_telegram(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id":chat_id,"text":text,
        "parse_mode":"HTML","disable_web_page_preview":True}).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url,data=payload,headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,context=ctx,timeout=15) as r:
            return json.loads(r.read()).get("ok",False)
    except Exception as e:
        print(f"[Telegram Error] {e}"); return False

def fetch_today_events():
    now_ict   = datetime.utcnow() + timedelta(hours=7)
    today_str = now_ict.strftime("%m-%d-%Y")
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(url,context=ctx,timeout=15) as r:
            root = ET.fromstring(r.read())
    except Exception as e:
        print(f"[FF Error] {e}"); return []
    events = []
    for e in root.findall("event"):
        if e.findtext("country","") != "USD": continue
        impact = e.findtext("impact","")
        if impact not in ("High","Medium"): continue
        if e.findtext("date","") != today_str: continue
        time_str = e.findtext("time","")
        try:
            t = datetime.strptime(time_str.strip(),"%I:%M%p")
            ict = f"{(t.hour+11)%24:02d}:{t.minute:02d}"
        except: ict = time_str
        events.append({"time_ict":ict,"impact":impact,"title":e.findtext("title",""),
            "forecast":e.findtext("forecast","") or "—","previous":e.findtext("previous","") or "—"})
    return sorted(events, key=lambda x: x["time_ict"])

def call_claude(prompt, key):
    url = "https://api.anthropic.com/v1/messages"
    payload = json.dumps({"model":"claude-sonnet-4-6","max_tokens":2000,
        "system":(
            "Bạn là chuyên gia phân tích XAUUSD. Viết tiếng Việt có dấu đầy đủ. "
            "Dùng HTML tags (<b>,<i>) cho Telegram. KHÔNG dùng Markdown, KHÔNG dùng **. "
            "Viết đầy đủ, không bỏ sót mục nào."
        ),
        "messages":[{"role":"user","content":prompt}]
    }).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url,data=payload,headers={
        "Content-Type":"application/json","x-api-key":key,
        "anthropic-version":"2023-06-01"})
    try:
        with urllib.request.urlopen(req,context=ctx,timeout=60) as r:
            data = json.loads(r.read())
            return "".join(b.get("text","") for b in data.get("content",[]) if b.get("type")=="text")
    except Exception as e:
        print(f"[Claude Error] {e}"); return ""

def main():
    cfg = load_config(); secrets = get_secrets()
    targets = get_active_targets(cfg,"daily_news")
    if not cfg["reports"]["daily_news"].get("enabled",True): return

    now_ict = datetime.utcnow() + timedelta(hours=7)
    weekdays = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]
    day_vi   = weekdays[now_ict.weekday()]
    date_str = now_ict.strftime("%d/%m/%Y")

    events = fetch_today_events()
    print(f"[Daily] {len(events)} sự kiện hôm nay ({now_ict.strftime('%m-%d-%Y')} ICT)")

    if not events:
        events_text = "Hôm nay không có sự kiện USD High/Medium."
    else:
        events_text = ""
        for ev in events:
            icon = "🔴" if ev["impact"]=="High" else "🟠"
            events_text += f"{icon} {ev['title']} | {ev['time_ict']} ICT | F:{ev['forecast']} P:{ev['previous']}\n"

    prompt = f"""Hôm nay là {day_vi}, {date_str}. Dữ liệu sự kiện USD hôm nay từ ForexFactory:

{events_text}

Hãy viết report TIN TỨC NGÀY theo format sau (tiếng Việt có dấu, HTML tags):

📰 <b>TIN TỨC NGÀY | {day_vi} - {date_str}</b>
<i>Phân tích các sự kiện USD hôm nay</i>

━━━━━━━━━━━━━━━━━━━━
<b>LỊCH SỰ KIỆN USD HÔM NAY</b>

[Nếu có sự kiện: Cho mỗi sự kiện viết 1 block gồm:]
[Icon + Tên sự kiện in đậm + giờ ICT]
Dự báo: X | Kỳ trước: Y
[3-4 câu nhận định: ý nghĩa chỉ số, xu hướng gần đây, kịch bản ra cao/thấp hơn dự báo ảnh hưởng USD thế nào]
USD Bias: [nhận định]

[Nếu không có sự kiện: giải thích ngắn thị trường hôm nay]

━━━━━━━━━━━━━━━━━━━━
<b>📊 KẾT LUẬN NGÀY {date_str}:</b>
[2-3 câu tổng kết: USD bias hôm nay, lưu ý giao dịch phiên London/NY. KHÔNG đề cập số giá vàng cụ thể]

<i>Nguồn: ForexFactory Calendar</i>"""

    content = call_claude(prompt, secrets["anthropic_key"])
    if not content:
        content = f"📰 <b>TIN TỨC NGÀY | {day_vi} - {date_str}</b>\n━━━━━━━━━━━━━━━━━━━━\n{events_text}"

    for t in targets:
        print(f"[Daily] → {t['name']}")
        ok = send_telegram(secrets["bot_token"], t["chat_id"], content)
        print(f"  {'✅' if ok else '❌'}")

if __name__ == "__main__":
    main()
