# REPORT 1: TIN TUC TUAN - Claude tu search web
import urllib.request, ssl, json
from datetime import datetime, timedelta
from telegram_helper import send_message, call_claude_with_retry
from config_loader import load_config, get_secrets, get_active_targets

WEEKDAYS_VI = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]

def call_claude_with_search(prompt, key):
    url = "https://api.anthropic.com/v1/messages"
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 2500,
        "system": (
            "Bạn là chuyên gia phân tích XAUUSD. "
            "Viết HOÀN TOÀN bằng tiếng Việt có dấu đầy đủ. "
            "Dùng HTML tags (<b>,<i>) cho Telegram. "
            "KHÔNG dùng Markdown, KHÔNG dùng **, *, #. "
            "Viết đầy đủ tất cả các mục, không bỏ sót."
        ),
        "messages": [{"role":"user","content":prompt}],
        "tools": [{"type":"web_search_20250305","name":"web_search"}]
    }).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url,data=payload,headers={
        "Content-Type":"application/json","x-api-key":key,
        "anthropic-version":"2023-06-01","anthropic-beta":"web-search-2025-03-05"})
    try:
        with urllib.request.urlopen(req,context=ctx,timeout=90) as r:
            data = json.loads(r.read())
            return "".join(b.get("text","") for b in data.get("content",[]) if b.get("type")=="text")
    except Exception as e:
        print(f"[Claude Error] {e}"); return ""

def main():
    cfg = load_config(); secrets = get_secrets()
    targets = get_active_targets(cfg,"weekly_news")
    if not cfg["reports"]["weekly_news"].get("enabled",True): return

    now_ict  = datetime.utcnow() + timedelta(hours=7)
    day_vi   = WEEKDAYS_VI[now_ict.weekday()]
    date_str = now_ict.strftime("%d/%m/%Y")
    week_end = (now_ict + timedelta(days=5)).strftime("%d/%m/%Y")

    prompt = f"""Hôm nay là Chủ nhật, {date_str}. Hãy tìm kiếm lịch sự kiện kinh tế USD tuần tới và viết report TIN TỨC TUẦN hoàn chỉnh.

Viết theo đúng format sau (tiếng Việt có dấu, HTML tags cho Telegram):

📅 <b>TÓM TẮT TIN TỨC TUẦN | {date_str} - {week_end}</b>
<i>Các sự kiện USD quan trọng ảnh hưởng XAUUSD</i>

[Tìm kiếm lịch sự kiện USD tuần tới từ ForexFactory hoặc Investing.com economic calendar]
[Nhóm theo từng ngày, mỗi ngày 1 section:]

━━━━━━━━━━━━━━━━━━━━
<b>📌 [Thứ] - [Ngày/Tháng]</b>

[Cho mỗi sự kiện High/Medium:]
[🔴 High / 🟠 Medium] <b>[Tên sự kiện]</b> | [Giờ ICT]
Dự báo: [X] | Kỳ trước: [Y]
USD Bias: [nhận định ngắn 1 câu về tác động USD]
Nhận định: [1-2 câu phân tích]

[Lặp lại cho các ngày có sự kiện trong tuần]

━━━━━━━━━━━━━━━━━━━━
<b>📊 KẾT LUẬN USD BIAS TUẦN:</b>
[2-3 câu tổng kết xu hướng USD tuần này và tác động đến vàng]
[KHÔNG đề cập số vùng giá vàng cụ thể]

<i>Nguồn: ForexFactory, Investing.com</i>"""

    print(f"[Weekly News] Gọi Claude API với web search...")
    content = call_claude_with_retry(prompt, secrets["anthropic_key"], use_search=True)
    if not content:
        content = (f"📅 <b>TIN TỨC TUẦN | {date_str} - {week_end}</b>\n"
                   f"━━━━━━━━━━━━━━━━━━━━\n"
                   f"⚠️ Không thể tải dữ liệu tuần tới. Vui lòng thử lại sau.")

    print(f"[Weekly News] Độ dài: {len(content)} ký tự")
    for t in targets:
        print(f"[Weekly News] → {t['name']}")
        ok = send_message(secrets["bot_token"], t["chat_id"], content)
        print(f"  {'✅' if ok else '❌'}")

if __name__ == "__main__":
    main()
