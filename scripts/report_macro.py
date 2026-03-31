# REPORT 3: PHAN TICH VI MO - Fix: tang max_tokens, prompt ro rang hon
import urllib.request, ssl, json
from datetime import datetime, timedelta
from config_loader import load_config, get_secrets, get_active_targets

WEEKDAYS_VI = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]

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

def send_telegram_long(bot_token, chat_id, text):
    """Tự động chia nhỏ nếu text quá 4096 ký tự (giới hạn Telegram)."""
    MAX = 4000
    if len(text) <= MAX:
        return send_telegram(bot_token, chat_id, text)
    # Chia theo dòng, giữ nguyên format
    lines = text.split("\n")
    chunk = ""; results = []
    for line in lines:
        if len(chunk) + len(line) + 1 > MAX:
            results.append(send_telegram(bot_token, chat_id, chunk.strip()))
            chunk = line + "\n"
        else:
            chunk += line + "\n"
    if chunk.strip():
        results.append(send_telegram(bot_token, chat_id, chunk.strip()))
    return all(results)

def call_claude(prompt, anthropic_key):
    url = "https://api.anthropic.com/v1/messages"
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 2500,
        "system": (
            "Bạn là chuyên gia phân tích thị trường vàng XAUUSD. "
            "Viết HOÀN TOÀN bằng tiếng Việt có dấu đầy đủ. "
            "Dùng HTML tag cho Telegram: <b>bold</b>, <i>italic</i>. "
            "KHÔNG dùng Markdown (không dùng **, *, #). "
            "KHÔNG dùng ký tự đặc biệt ngoài HTML tags. "
            "Viết đầy đủ TẤT CẢ các mục được yêu cầu, không được bỏ sót mục nào. "
            "Mỗi mục phải có ít nhất 2-3 câu nội dung thực chất."
        ),
        "messages": [{"role": "user", "content": prompt}],
        "tools": [{"type": "web_search_20250305", "name": "web_search"}]
    }).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json", "x-api-key": anthropic_key,
        "anthropic-version": "2023-06-01", "anthropic-beta": "web-search-2025-03-05"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=90) as resp:
            data = json.loads(resp.read())
            return "".join(b.get("text","") for b in data.get("content",[]) if b.get("type")=="text")
    except Exception as e:
        print(f"[Claude API Error] {e}"); return ""

def build_report(cfg, secrets):
    rc = cfg["reports"]["macro"]
    now_ict  = datetime.utcnow() + timedelta(hours=7)
    day_vi   = WEEKDAYS_VI[now_ict.weekday()]
    date_str = now_ict.strftime("%d/%m/%Y")
    extra    = rc.get("claude_prompt_extra", "")

    prompt = f"""Hôm nay là {day_vi}, {date_str}. Hãy tìm kiếm tin tức vĩ mô mới nhất trong 24h qua về thị trường vàng XAUUSD và viết report HOÀN CHỈNH theo đúng cấu trúc sau.

BẮT BUỘC phải viết đầy đủ TẤT CẢ 3 phần chính và các mục con. Không được bỏ sót bất kỳ mục nào:

<b>📊 GOLD / XAUUSD — PHÂN TÍCH VĨ MÔ &amp; CƠ BẢN</b>
━━━━━━━━━━━━━━━━━━━━
📅 Cập nhật: {day_vi} - {date_str} (GMT+7)

<b>1) Diễn biến thị trường hiện tại</b>
[Viết 3-4 câu: Giá vàng đang ở mức nào, diễn biến gần đây, so sánh với đỉnh/đáy gần nhất]

<b>2) Các yếu tố vĩ mô chính</b>

🏦 <b>Chính sách tiền tệ (Fed)</b>
[Viết 3-4 câu: Lãi suất hiện tại, kỳ vọng thị trường, dot plot, CME FedWatch, phát biểu gần nhất]

🌍 <b>Địa chính trị</b>
[Viết 3-4 câu: Xung đột Mỹ-Iran, thuế quan, các điểm nóng đang ảnh hưởng tâm lý thị trường]

🏛️ <b>Ngân hàng trung ương &amp; cầu cấu trúc</b>
[Viết 3-4 câu: Mua ròng NHTW, ETF flows, dự báo của JPMorgan/UBS/Goldman Sachs]

<b>3) Nhận định tổng quan</b>
[Viết 3-4 câu: Ngắn hạn, trung hạn, dài hạn. KHÔNG đề cập số vùng hỗ trợ/kháng cự cụ thể]

<i>Nguồn: [liệt kê các nguồn đã tham khảo]</i>

{extra}
LƯU Ý QUAN TRỌNG:
- Viết tiếng Việt có dấu đầy đủ
- Dùng HTML tags, KHÔNG dùng Markdown
- Viết ĐẦY ĐỦ tất cả các mục, không được dừng giữa chừng"""

    content = call_claude(prompt, secrets["anthropic_key"])
    if not content:
        return (f"<b>📊 GOLD / XAUUSD — PHÂN TÍCH VĨ MÔ &amp; CƠ BẢN</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 {day_vi} - {date_str} (GMT+7)\n\n"
                f"⚠️ Không thể tải dữ liệu vĩ mô hôm nay. Vui lòng thử lại sau.")
    return content

def main():
    cfg = load_config(); secrets = get_secrets()
    targets = get_active_targets(cfg, "macro")
    if not cfg["reports"]["macro"].get("enabled", True):
        print("[Macro] Disabled"); return
    print("[Macro] Đang gọi Claude API...")
    report = build_report(cfg, secrets)
    print(f"[Macro] Độ dài report: {len(report)} ký tự")
    for t in targets:
        print(f"[Macro] → {t['name']}")
        ok = send_telegram_long(secrets["bot_token"], t["chat_id"], report)
        print(f"  {'✅ OK' if ok else '❌ Thất bại'}")

if __name__ == "__main__":
    main()
