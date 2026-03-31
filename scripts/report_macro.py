# REPORT 3: PHAN TICH VI MO - Claude API + web search, tu dong chia nho neu qua dai
import urllib.request, ssl, json
from datetime import datetime, timedelta
from config_loader import load_config, get_secrets, get_active_targets

WEEKDAYS_VI = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]

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

def send_long(bot_token, chat_id, text):
    """Chia nhỏ message nếu quá 4000 ký tự."""
    if len(text) <= 4000:
        return send_telegram(bot_token, chat_id, text)
    # Chia tại dòng trống (paragraph break)
    parts = text.split("\n\n")
    chunk = ""; ok_all = True
    for part in parts:
        if len(chunk) + len(part) + 2 > 4000:
            if chunk:
                ok_all = send_telegram(bot_token, chat_id, chunk.strip()) and ok_all
            chunk = part + "\n\n"
        else:
            chunk += part + "\n\n"
    if chunk.strip():
        ok_all = send_telegram(bot_token, chat_id, chunk.strip()) and ok_all
    return ok_all

def call_claude_with_search(prompt, key):
    url = "https://api.anthropic.com/v1/messages"
    payload = json.dumps({"model":"claude-sonnet-4-6","max_tokens":2500,
        "system":(
            "Bạn là chuyên gia phân tích thị trường vàng XAUUSD. "
            "Viết HOÀN TOÀN bằng tiếng Việt có dấu đầy đủ. "
            "Dùng HTML tags (<b>,<i>) cho Telegram. "
            "KHÔNG dùng Markdown. KHÔNG dùng ** hay # hay *. "
            "Viết ĐẦY ĐỦ tất cả các mục, không được dừng giữa chừng hay bỏ sót mục nào."
        ),
        "messages":[{"role":"user","content":prompt}],
        "tools":[{"type":"web_search_20250305","name":"web_search"}]
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
    targets = get_active_targets(cfg,"macro")
    if not cfg["reports"]["macro"].get("enabled",True): return

    now_ict  = datetime.utcnow() + timedelta(hours=7)
    day_vi   = WEEKDAYS_VI[now_ict.weekday()]
    date_str = now_ict.strftime("%d/%m/%Y")
    extra    = cfg["reports"]["macro"].get("claude_prompt_extra","")

    prompt = f"""Hôm nay là {day_vi}, {date_str}. Hãy tìm kiếm tin tức vĩ mô mới nhất trong 24h qua về thị trường vàng XAUUSD.

Viết report PHÂN TÍCH VĨ MÔ hoàn chỉnh theo đúng format sau. BẮT BUỘC viết đầy đủ TẤT CẢ các mục:

📊 <b>GOLD / XAUUSD — PHÂN TÍCH VĨ MÔ &amp; CƠ BẢN</b>
━━━━━━━━━━━━━━━━━━━━
📅 Cập nhật: {day_vi} - {date_str} (GMT+7)

<b>1) Diễn biến thị trường hiện tại</b>
[3-4 câu: Giá vàng spot đang ở mức nào, range trong ngày, so sánh với đỉnh/đáy gần nhất, diễn biến đáng chú ý]

<b>2) Các yếu tố vĩ mô chính</b>

🏦 <b>Chính sách tiền tệ (Fed)</b>
[3-4 câu: Lãi suất hiện tại, kỳ vọng cắt giảm, CME FedWatch, phát biểu Fed gần nhất, dot plot]

🌍 <b>Địa chính trị</b>
[3-4 câu: Xung đột khu vực, thuế quan, căng thẳng thương mại, các sự kiện đang ảnh hưởng tâm lý thị trường]

🏛️ <b>Ngân hàng trung ương &amp; cầu cấu trúc</b>
[3-4 câu: Mua ròng NHTW (PBoC, ECB...), ETF flows, dự báo năm 2026 của JPMorgan/UBS/Goldman]

<b>3) Nhận định tổng quan</b>
[3-4 câu: Ngắn hạn, trung hạn, dài hạn. KHÔNG đề cập số vùng hỗ trợ/kháng cự hay bias hướng giá cụ thể]

<i>Nguồn: [liệt kê các nguồn đã tham khảo]</i>

{extra}"""

    print("[Macro] Gọi Claude API với web search...")
    content = call_claude_with_search(prompt, secrets["anthropic_key"])
    if not content:
        content = (f"📊 <b>GOLD / XAUUSD — PHÂN TÍCH VĨ MÔ &amp; CƠ BẢN</b>\n"
                   f"━━━━━━━━━━━━━━━━━━━━\n📅 {day_vi} - {date_str} (GMT+7)\n\n"
                   f"⚠️ Không thể tải dữ liệu vĩ mô hôm nay. Vui lòng thử lại sau.")

    print(f"[Macro] Độ dài: {len(content)} ký tự")
    for t in targets:
        print(f"[Macro] → {t['name']}")
        ok = send_long(secrets["bot_token"], t["chat_id"], content)
        print(f"  {'✅' if ok else '❌'}")

if __name__ == "__main__":
    main()
