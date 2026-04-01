# REPORT 2: TIN TUC NGAY - Claude tu search web, khong dung ForexFactory
import urllib.request, ssl, json
from datetime import datetime, timedelta
from telegram_helper import send_message, call_claude_with_retry
from config_loader import load_config, get_secrets, get_active_targets

WEEKDAYS_VI = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]

def call_claude_with_search(prompt, key):
    url = "https://api.anthropic.com/v1/messages"
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 2000,
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
    targets = get_active_targets(cfg,"daily_news")
    if not cfg["reports"]["daily_news"].get("enabled",True): return

    now_ict  = datetime.utcnow() + timedelta(hours=7)
    day_vi   = WEEKDAYS_VI[now_ict.weekday()]
    date_str = now_ict.strftime("%d/%m/%Y")

    prompt = f"""Hôm nay là {day_vi}, {date_str}. Hãy tìm kiếm lịch sự kiện kinh tế USD hôm nay và viết report TIN TỨC NGÀY hoàn chỉnh.

Viết theo đúng format sau (tiếng Việt có dấu, HTML tags cho Telegram):

📰 <b>TIN TỨC NGÀY | {day_vi} - {date_str}</b>
<i>Phân tích các sự kiện USD hôm nay</i>

━━━━━━━━━━━━━━━━━━━━
<b>LỊCH SỰ KIỆN USD HÔM NAY</b>

[Tìm kiếm và liệt kê các sự kiện USD High/Medium impact hôm nay từ ForexFactory hoặc Investing.com]
[Nếu có sự kiện: Cho mỗi sự kiện viết:]

[Icon 🔴 High / 🟠 Medium] <b>[Tên sự kiện]</b> | [Giờ ICT]
Dự báo: [X] | Kỳ trước: [Y]
Nhận định:
- [Ý nghĩa chỉ số này là gì]
- [Xu hướng gần đây]
- [Kịch bản nếu ra cao hơn dự báo]
- [Kịch bản nếu ra thấp hơn dự báo]
USD Bias: [nhận định]

[Nếu không có sự kiện High/Medium: viết 2-3 câu về bối cảnh thị trường hôm nay]

━━━━━━━━━━━━━━━━━━━━
<b>📊 KẾT LUẬN NGÀY {date_str}:</b>
[2-3 câu: Tổng kết USD bias hôm nay, lưu ý phiên London (15:00-17:00 ICT) và NY (20:30 ICT)]
[KHÔNG đề cập số vùng giá vàng cụ thể]

<i>Nguồn: ForexFactory, Investing.com</i>"""

    print(f"[Daily News] Gọi Claude API với web search...")
    content = call_claude_with_retry(prompt, secrets["anthropic_key"], use_search=True)
    if not content:
        content = (f"📰 <b>TIN TỨC NGÀY | {day_vi} - {date_str}</b>\n"
                   f"━━━━━━━━━━━━━━━━━━━━\n"
                   f"⚠️ Không thể tải dữ liệu hôm nay. Vui lòng thử lại sau.")

    print(f"[Daily News] Độ dài: {len(content)} ký tự")
    for t in targets:
        print(f"[Daily News] → {t['name']}")
        ok = send_message(secrets["bot_token"], t["chat_id"], content)
        print(f"  {'✅' if ok else '❌'}")

if __name__ == "__main__":
    main()
