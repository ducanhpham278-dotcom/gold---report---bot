# REPORT 3: PHAN TICH VI MO
from datetime import datetime, timedelta
from telegram_helper import send_message, call_claude_with_retry
from config_loader import load_config, get_secrets, get_active_targets

WEEKDAYS_VI = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]

def main():
    cfg = load_config()
    secrets = get_secrets()
    targets = get_active_targets(cfg, "macro")
    if not cfg["reports"]["macro"].get("enabled", True):
        return

    now_ict  = datetime.utcnow() + timedelta(hours=7)
    day_vi   = WEEKDAYS_VI[now_ict.weekday()]
    date_str = now_ict.strftime("%d/%m/%Y")
    extra    = cfg["reports"]["macro"].get("claude_prompt_extra", "")

    prompt = f"""Hôm nay là {day_vi}, {date_str}. Tìm kiếm tin tức vĩ mô mới nhất 24h qua về XAUUSD và viết report PHÂN TÍCH VĨ MÔ đầy đủ.

Viết bằng tiếng Việt có dấu. Chỉ dùng <b> và <i> cho định dạng. Dùng ━ để kẻ ngang.

Cấu trúc bắt buộc đầy đủ:

📊 <b>GOLD / XAUUSD — PHÂN TÍCH VĨ MÔ & CƠ BẢN</b>
━━━━━━━━━━━━━━━━━━━━
📅 Cập nhật: {day_vi} - {date_str} (GMT+7)

<b>1) Diễn biến thị trường hiện tại</b>
3-4 câu về giá vàng hiện tại, range trong ngày, so sánh đỉnh/đáy gần nhất.

<b>2) Các yếu tố vĩ mô chính</b>

🏦 <b>Chính sách tiền tệ (Fed)</b>
3-4 câu về lãi suất, CME FedWatch, dot plot, phát biểu Fed gần nhất.

🌍 <b>Địa chính trị</b>
3-4 câu về xung đột, thuế quan, căng thẳng thương mại ảnh hưởng thị trường.

🏛️ <b>Ngân hàng trung ương & cầu cấu trúc</b>
3-4 câu về mua ròng NHTW, ETF flows, dự báo JPMorgan/UBS/Goldman.

<b>3) Nhận định tổng quan</b>
3-4 câu ngắn hạn, trung hạn, dài hạn. KHÔNG đề cập số vùng hỗ trợ/kháng cự.

<i>Nguồn: [liệt kê nguồn]</i>

{extra}"""

    print("[Macro] Gọi Claude API...")
    content = call_claude_with_retry(prompt, secrets["anthropic_key"], use_search=True, max_tokens=2500)
    if not content:
        content = f"📊 <b>GOLD / XAUUSD — PHÂN TÍCH VĨ MÔ</b>\n\n⚠️ Không thể tải dữ liệu hôm nay."

    print(f"[Macro] {len(content)} ký tự")
    for t in targets:
        print(f"[Macro] → {t['name']}")
        ok = send_message(secrets["bot_token"], t["chat_id"], content)
        print(f"  {'✅' if ok else '❌'}")

if __name__ == "__main__":
    main()
