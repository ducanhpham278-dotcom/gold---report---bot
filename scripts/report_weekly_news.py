# REPORT 1: TIN TUC TUAN - Chi dung thisweek feed, gui Chu nhat 6:00 ICT
import urllib.request, ssl, json, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from itertools import groupby
from config_loader import load_config, get_secrets, get_active_targets

IMPACT_EMOJI = {"High": "🔴", "Medium": "🟠", "Low": "⚪"}
DAY_VI = {
    "Monday": "Thứ 2", "Tuesday": "Thứ 3", "Wednesday": "Thứ 4",
    "Thursday": "Thứ 5", "Friday": "Thứ 6", "Saturday": "Thứ 7", "Sunday": "Chủ nhật",
}

def send_telegram(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": True}).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"[Telegram Error] {e}"); return False

def fetch_ff_events():
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(url, context=ctx, timeout=15) as resp:
            data = resp.read()
    except Exception as e:
        print(f"[FF Error] {e}"); return []

    root = ET.fromstring(data)
    events = []
    for e in root.findall("event"):
        country = e.findtext("country", ""); impact = e.findtext("impact", "")
        if country != "USD" or impact not in ("High", "Medium"): continue
        date_str = e.findtext("date", ""); time_str = e.findtext("time", "")
        try: dt = datetime.strptime(date_str, "%m-%d-%Y")
        except ValueError: continue
        try:
            t = datetime.strptime(time_str.strip(), "%I:%M%p")
            ict_time = f"{(t.hour+11)%24:02d}:{t.minute:02d}"
        except ValueError: ict_time = time_str
        events.append({"dt": dt, "day_name": dt.strftime("%A"),
            "date_vi": dt.strftime("%d/%m"), "time_ict": ict_time,
            "impact": impact, "title": e.findtext("title", ""),
            "forecast": e.findtext("forecast", "") or "—",
            "previous": e.findtext("previous", "") or "—"})
    events.sort(key=lambda x: (x["dt"], x["time_ict"]))
    return events

def build_report(events, cfg):
    rc = cfg["reports"]["weekly_news"]
    now_ict = datetime.utcnow() + timedelta(hours=7)
    if events:
        week_start = events[0]["dt"].strftime("%d/%m")
        week_end   = events[-1]["dt"].strftime("%d/%m/%Y")
        week_str   = f"{week_start} - {week_end}"
    else:
        next_mon = now_ict + timedelta(days=1)
        next_fri = now_ict + timedelta(days=5)
        week_str = f"{next_mon.strftime('%d/%m')} - {next_fri.strftime('%d/%m/%Y')}"

    lines = [f"<b>{rc['header']}</b>", "━━━━━━━━━━━━━━━━━━━━",
        f"📅 Tuần: {week_str}",
        f"🕘 Cập nhật: {now_ict.strftime('%d/%m/%Y %H:%M')} ICT", "",
        "<b>Lịch sự kiện USD quan trọng tuần này</b>",
        "<i>(High 🔴 | Medium 🟠 — giờ ICT)</i>"]

    for day_name, group in groupby(events, key=lambda x: x["day_name"]):
        day_events = list(group)
        lines += ["\n━━━━━━━━━━━━━━━━━━━━",
            f"<b>📌 {DAY_VI.get(day_name, day_name)} - {day_events[0]['date_vi']}</b>"]
        for ev in day_events:
            lines += [
                f"\n{IMPACT_EMOJI.get(ev['impact'],'⚪')} <b>{ev['title']}</b> | {ev['time_ict']} ICT",
                f"Dự báo: {ev['forecast']} | Kỳ trước: {ev['previous']}"]

    if not events:
        lines.append("\n⚠️ Chưa có dữ liệu lịch sự kiện tuần này từ ForexFactory.")

    lines += ["", "━━━━━━━━━━━━━━━━━━━━", "<b>📊 Lưu ý giao dịch tuần:</b>"] \
           + [f"- {n}" for n in rc["note_lines"]] + ["", f"<i>{rc['footer']}</i>"]
    return "\n".join(lines)

def main():
    cfg = load_config(); secrets = get_secrets()
    targets = get_active_targets(cfg, "weekly_news")
    if not cfg["reports"]["weekly_news"].get("enabled", True):
        print("[Weekly News] Disabled"); return
    events = fetch_ff_events()
    print(f"[Weekly News] {len(events)} sự kiện USD High/Medium tuần này")
    report = build_report(events, cfg)
    for t in targets:
        print(f"[Weekly News] → {t['name']}")
        ok = send_telegram(secrets["bot_token"], t["chat_id"], report)
        print(f"  {'✅ OK' if ok else '❌ Thất bại'}")

if __name__ == "__main__":
    main()
