# REPORT 1: TIN TUC TUAN - Claude API tong hop noi dung
import urllib.request, ssl, json, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from config_loader import load_config, get_secrets, get_active_targets

DAY_VI = {
    "Monday":"Thứ 2","Tuesday":"Thứ 3","Wednesday":"Thứ 4",
    "Thursday":"Thứ 5","Friday":"Thứ 6","Saturday":"Thứ 7","Sunday":"Chủ nhật"
}

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

def fetch_ff_events():
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
        date_str = e.findtext("date",""); time_str = e.findtext("time","")
        try: dt = datetime.strptime(date_str,"%m-%d-%Y")
        except: continue
        try:
            t = datetime.strptime(time_str.strip(),"%I:%M%p")
            ict = f"{(t.hour+11)%24:02d}:{t.minute:02d}"
        except: ict = time_str
        events.append({"date":dt.strftime("%d/%m"),"day":DAY_VI.get(dt.strftime("%A"),dt.strftime("%A")),
            "time_ict":ict,"impact":impact,"title":e.findtext("title",""),
            "forecast":e.findtext("forecast","") or "—","previous":e.findtext("previous","") or "—"})
    return sorted(events, key=lambda x:(x["date"],x["time_ict"]))

def call_claude(prompt, key):
    url = "https://api.anthropic.com/v1/messages"
    payload = json.dumps({"model":"claude-sonnet-4-6","max_tokens":2000,
        "system":(
            "Bạn là chuyên gia phân tích XAUUSD. Viết tiếng Việt có dấu đầy đủ. "
            "Dùng HTML tags (<b>,<i>) cho Telegram. KHÔNG dùng Markdown, KHÔNG dùng **. "
            "Viết đầy đủ, không bỏ sót mục nào. Không thêm ghi chú ngoài nội dung yêu cầu."
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
    targets = get_active_targets(cfg,"weekly_news")
    if not cfg["reports"]["weekly_news"].get("enabled",True): return

    events = fetch_ff_events()
    now_ict = datetime.utcnow() + timedelta(hours=7)

    # Chuẩn bị dữ liệu sự kiện dạng text cho Claude
    events_text = ""
    current_day = ""
    for ev in events:
        if ev["day"] != current_day:
            current_day = ev["day"]
            events_text += f"\n{ev['day']} {ev['date']}:\n"
        icon = "🔴" if ev["impact"]=="High" else "🟠"
        events_text += f"  {icon} {ev['title']} | {ev['time_ict']} ICT | F:{ev['forecast']} P:{ev['previous']}\n"

    if not events_text:
        events_text = "Không có dữ liệu sự kiện USD tuần này."

    prompt = f"""Hôm nay là Chủ nhật {now_ict.strftime('%d/%m/%Y')}. Dưới đây là lịch sự kiện USD tuần này từ ForexFactory:

{events_text}

Hãy viết report TIN TỨC TUẦN theo đúng format sau (tiếng Việt có dấu, HTML tags):

📅 <b>TÓM TẮT TIN TỨC TUẦN | {now_ict.strftime('%d/%m')} - {(now_ict+timedelta(days=5)).strftime('%d/%m/%Y')}</b>
<i>Các sự kiện USD quan trọng ảnh hưởng XAUUSD</i>

[Liệt kê từng ngày có sự kiện, mỗi ngày 1 section]
Cho mỗi ngày viết: tiêu đề ngày in đậm, rồi từng sự kiện với:
- Emoji impact (🔴 High / 🟠 Medium) + tên sự kiện in đậm + giờ ICT
- Dự báo và kỳ trước
- 1-2 câu nhận định ngắn: USD Bias và tác động đến vàng

Cuối cùng viết phần:
━━━━━━━━━━━━━━━━━━━━
<b>📊 KẾT LUẬN USD BIAS TUẦN:</b>
[2-3 câu tổng kết xu hướng USD tuần này và tác động đến vàng. KHÔNG đề cập số giá vàng cụ thể]

<i>Nguồn: ForexFactory Calendar</i>"""

    content = call_claude(prompt, secrets["anthropic_key"])
    if not content:
        content = f"📅 <b>LỊCH TIN TỨC TUẦN</b>\n━━━━━━━━━━━━━━━━━━━━\n{events_text}\n<i>Nguồn: ForexFactory</i>"

    for t in targets:
        print(f"[Weekly] → {t['name']}")
        ok = send_telegram(secrets["bot_token"], t["chat_id"], content)
        print(f"  {'✅' if ok else '❌'}")

if __name__ == "__main__":
    main()
