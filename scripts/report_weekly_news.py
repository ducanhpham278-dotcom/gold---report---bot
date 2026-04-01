# REPORT 1: TIN TUC TUAN
from datetime import datetime, timedelta
from telegram_helper import send_message, call_claude_with_retry
from config_loader import load_config, get_secrets, get_active_targets

WEEKDAYS_VI = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]

def main():
    cfg = load_config()
    secrets = get_secrets()
    targets = get_active_targets(cfg, "weekly_news")
    if not cfg["reports"]["weekly_news"].get("enabled", True):
        return

    now_ict  = datetime.utcnow() + timedelta(hours=7)
    date_str = now_ict.strftime("%d/%m/%Y")
    week_end = (now_ict + timedelta(days=5)).strftime("%d/%m/%Y")

    prompt = f"""Hôm nay là Chủ nhật, {date_str}. Tìm kiếm lịch sự kiện kinh tế USD tuần tới và viết report TIN TỨC TUẦN.

Viết bằng tiếng Việt có dấu. Chỉ dùng <b> và <i> cho định dạng. Dùng ━ để kẻ ngang.

Cấu trúc:
📅 <b>TÓM TẮT TIN TỨC TUẦN | {date_str} - {week_end}</b>
<i>Các sự kiện USD quan trọng ảnh hưởng XAUUSD</i>

[Nhóm theo từng ngày có sự kiện:]
━━━━━━━━━━━━━━━━━━━━
<b>📌 Thứ X - DD/MM</b>

🔴 hoặc 🟠 <b>Tên sự kiện</b> | Giờ ICT
Dự báo: X | Kỳ trước: Y
USD Bias: 1 câu nhận định
Nhận định: 1-2 câu phân tích

[Lặp cho các ngày khác]

━━━━━━━━━━━━━━━━━━━━
<b>📊 KẾT LUẬN USD BIAS TUẦN:</b>
2-3 câu tổng kết. KHÔNG đề cập số giá vàng."""

    print("[Weekly News] Gọi Claude API...")
    content = call_claude_with_retry(prompt, secrets["anthropic_key"], use_search=True, max_tokens=2500)
    if not content:
        content = f"📅 <b>TIN TỨC TUẦN | {date_str} - {week_end}</b>\n\n⚠️ Không thể tải dữ liệu."

    print(f"[Weekly News] {len(content)} ký tự")
    for t in targets:
        print(f"[Weekly News] → {t['name']}")
        ok = send_message(secrets["bot_token"], t["chat_id"], content)
        print(f"  {'✅' if ok else '❌'}")

if __name__ == "__main__":
    main()
