# =============================================================
# REPORT 2: TIN TỨC NGÀY (Thứ 2 → Thứ 7, 6:00 ICT)
# =============================================================

import urllib.request, ssl, json, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from config_loader import load_config, get_secrets, get_active_targets

IMPACT_EMOJI = {"High": "🔴", "Medium": "🟠", "Low": "⚪"}
WEEKDAYS_VI  = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]
USD_BIAS = {
    "Non-Farm":            "Sự kiện lớn nhất tháng — biến động mạnh cả 2 chiều",
    "NFP":                 "Sự kiện lớn nhất tháng — biến động mạnh cả 2 chiều",
    "JOLTS":               "Phản ánh nhu cầu tuyển dụng — xu hướng giảm dần hỗ trợ Fed dovish",
    "Consumer Confidence": "Tâm lý NTD — ra thấp hơn dự báo thường làm USD yếu",
    "CPI":                 "Lạm phát — ra cao hơn dự báo: USD mạnh, Fed hawkish",
    "PPI":                 "Lạm phát sản xuất — chỉ báo sớm của CPI",
    "Retail Sales":        "Sức chi tiêu NTD — ra mạnh hỗ trợ USD",
    "GDP":                 "Tăng trưởng kinh tế — nền tảng cho chính sách Fed",
    "ISM":                 "PMI sản xuất/dịch vụ — trên 50 tích cực cho USD",
    "PMI":                 "Chỉ số nhà quản trị mua hàng — trên 50 tích cực",
    "Unemployment Claims": "Đơn xin trợ cấp thất nghiệp — ra thấp hơn dự báo: USD mạnh",
    "Unemployment Rate":   "Tỷ lệ thất nghiệp — tăng: Fed lo ngại, dovish",
    "ADP":                 "Việc làm tư nhân — tín hiệu sớm trước NFP",
    "Powell":              "Phát biểu Chủ tịch Fed — rủi ro biến động cao bất ngờ",
    "FOMC":                "Quyết định/phát biểu Fed — định hướng chính sách tiền tệ",
    "Durable Goods":       "Đơn hàng hàng hóa bền — chỉ báo đầu tư doanh nghiệp",
}

def get_bias(title):
    for kw, bias in USD_BIAS.items():
        if kw.lower() in title.lower(): return bias
    return "Theo dõi phản ứng giá thực tế sau khi số liệu ra"

def send_telegram(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id,"text": text,
        "parse_mode":"HTML","disable_web_page_preview":True}).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"[Telegram Error] {e}"); return False

def fetch_today_events():
    today_ict = (datetime.utcnow() + timedelta(hours=7)).strftime("%m-%d-%Y")
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(url, context=ctx, timeout=15) as resp:
            data = resp.read()
    except Exception as e:
        print(f"[FF Error] {e}"); return []
    root = ET.fromstring(data); events = []
    for e in root.findall("event"):
        country = e.findtext("country",""); impact = e.findtext("impact","")
        date_str = e.findtext("date","")
        if country != "USD" or impact not in ("High","Medium") or date_str != today_ict: continue
        time_str = e.findtext("time",""); title = e.findtext("title","")
        try:
            t = datetime.strptime(time_str.strip(), "%I:%M%p")
            ict_time = f"{(t.hour+11)%24:02d}:{t.minute:02d}"
        except ValueError: ict_time = time_str
        events.append({"time_ict":ict_time,"impact":impact,"title":title,
            "forecast":e.findtext("forecast","") or "—","previous":e.findtext("previous","") or "—",
            "bias":get_bias(title)})
    events.sort(key=lambda x: x["time_ict"]); return events

def build_report(events, cfg):
    rc = cfg["reports"]["daily_news"]
    now_ict = datetime.utcnow() + timedelta(hours=7)
    day_vi  = WEEKDAYS_VI[now_ict.weekday()]
    lines = [f"<b>{rc['header']}</b>","━━━━━━━━━━━━━━━━━━━━",
        f"📅 Ngày: {day_vi} - {now_ict.strftime('%d/%m/%Y')}",
        f"🕘 Cập nhật: {now_ict.strftime('%H:%M')} ICT"]
    if not events:
        lines += ["","✅ Hôm nay <b>không có sự kiện USD High/Medium</b>.",
            "Thị trường có thể giao dịch ít biến động hơn.",
            "Theo dõi tin địa chính trị và biến động kỹ thuật."]
    else:
        lines += ["",f"<b>Có {len(events)} sự kiện USD quan trọng hôm nay:</b>"]
        for ev in events:
            lines += ["","━━━━━━━━━━━━━━━━━━━━",
                f"{IMPACT_EMOJI.get(ev['impact'],'⚪')} <b>{ev['title']}</b> | {ev['time_ict']} ICT",
                f"Dự báo: {ev['forecast']} | Kỳ trước: {ev['previous']}",
                f"📌 {ev['bias']}"]
    lines += ["","━━━━━━━━━━━━━━━━━━━━","<b>⚡ Lưu ý giao dịch hôm nay:</b>"] \
           + [f"- {n}" for n in rc["note_lines"]] + ["",f"<i>{rc['footer']}</i>"]
    return "\n".join(lines)

def main():
    cfg = load_config(); secrets = get_secrets()
    targets = get_active_targets(cfg, "daily_news")
    if not cfg["reports"]["daily_news"].get("enabled", True):
        print("[Daily News] Disabled — bỏ qua"); return
    events = fetch_today_events()
    report = build_report(events, cfg)
    for t in targets:
        print(f"[Daily News] → {t['name']}")
        ok = send_telegram(secrets["bot_token"], t["chat_id"], report)
        print(f"  {'✅ OK' if ok else '❌ Thất bại'}")

if __name__ == "__main__":
    main()
