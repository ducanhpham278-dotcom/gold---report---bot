# REPORT 2: TIN TUC NGAY
import json
from datetime import datetime, timedelta
from telegram_helper import send_message, call_claude_with_retry
from config_loader import load_config, get_secrets, get_active_targets

WEEKDAYS_VI = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]

def main():
    cfg = load_config()
    secrets = get_secrets()
    targets = get_active_targets(cfg, "daily_news")
    if not cfg["reports"]["daily_news"].get("enabled", True):
        return

    now_ict  = datetime.utcnow() + timedelta(hours=7)
    day_vi   = WEEKDAYS_VI[now_ict.weekday()]
    date_str = now_ict.strftime("%d/%m/%Y")

    prompt = f"""Hôm nay là {day_vi}, {date_str}. Tìm kiếm lịch sự kiện kinh tế USD hôm nay và viết report TIN TỨC NGÀY.

Viết bằng tiếng Việt có dấu. Chỉ dùng <b> và <i> cho định dạng. Dùng ━ để kẻ ngang.

Cấu trúc:
📰 <b>TIN TỨC NGÀY | {day_vi} - {date_str}</b>

━━━━━━━━━━━━━━━━━━━━
<b>LỊCH SỰ KIỆN USD HÔM NAY</b>

[Với mỗi sự kiện High/Medium:]
🔴 hoặc 🟠 <b>Tên sự kiện</b> | Giờ ICT
Dự báo: X | Kỳ trước: Y
Nhận định: 2-3 câu phân tích ý nghĩa và tác động USD

[Nếu không có sự kiện: ghi rõ và nêu bối cảnh thị trường]

━━━━━━━━━━━━━━━━━━━━
<b>📊 KẾT LUẬN NGÀY {date_str}:</b>
2-3 câu tổng kết USD bias và lưu ý giao dịch. KHÔNG đề cập số giá vàng."""

    print("[Daily News] Gọi Claude API...")
    content = call_claude_with_retry(prompt, secrets["anthropic_key"], use_search=True, max_tokens=2000)
    if not content:
        content = f"📰 <b>TIN TỨC NGÀY | {day_vi} - {date_str}</b>\n\n⚠️ Không thể tải dữ liệu hôm nay."

    print(f"[Daily News] {len(content)} ký tự")
    for t in targets:
        print(f"[Daily News] → {t['name']}")
        ok = send_message(secrets["bot_token"], t["chat_id"], content)
        print(f"  {'✅' if ok else '❌'}")

if __name__ == "__main__":
    main()
