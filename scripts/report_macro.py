# =============================================================
# REPORT 3: PHÂN TÍCH VĨ MÔ (Thứ 2 → Thứ 7, 6:00 ICT)
# =============================================================

import urllib.request, ssl, json
from datetime import datetime, timedelta
from config_loader import load_config, get_secrets, get_active_targets

WEEKDAYS_VI = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]

def send_telegram(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id":chat_id,"text":text,
        "parse_mode":"HTML","disable_web_page_preview":True}).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"[Telegram Error] {e}"); return False

def call_claude(prompt, anthropic_key):
    url = "https://api.anthropic.com/v1/messages"
    payload = json.dumps({
        "model": "claude-sonnet-4-6", "max_tokens": 1500,
        "system": (
            "Bạn là chuyên gia phân tích thị trường vàng XAUUSD. "
            "Viết hoàn toàn bằng tiếng Việt có dấu. "
            "Dùng HTML tag cho Telegram (<b>, <i>). Không dùng Markdown. "
            "Ngắn gọn, súc tích, tập trung thông tin có giá trị thực tế."
        ),
        "messages": [{"role":"user","content":prompt}],
        "tools": [{"type":"web_search_20250305","name":"web_search"}]
    }).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type":"application/json","x-api-key":anthropic_key,
        "anthropic-version":"2023-06-01","anthropic-beta":"web-search-2025-03-05"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            data = json.loads(resp.read())
            return "".join(b.get("text","") for b in data.get("content",[]) if b.get("type")=="text")
    except Exception as e:
        print(f"[Claude API Error] {e}"); return ""

def build_report(cfg, secrets):
    rc = cfg["reports"]["macro"]
    now_ict = datetime.utcnow() + timedelta(hours=7)
    day_vi  = WEEKDAYS_VI[now_ict.weekday()]
    date_str = now_ict.strftime("%d/%m/%Y")

    extra = rc.get("claude_prompt_extra","")
    prompt = f"""Hôm nay là {day_vi}, {date_str}. Tìm kiếm và tổng hợp tin tức vĩ mô mới nhất về XAUUSD / thị trường vàng trong 24h qua.

Viết report theo cấu trúc sau (tiếng Việt có dấu, dùng HTML tag):

<b>{rc['header']}</b>
━━━━━━━━━━━━━━━━━━━━
📅 Cập nhật: {day_vi} - {date_str} (GMT+7)

<b>1) Diễn biến thị trường hiện tại</b>
[Giá vàng, diễn biến gần đây, biến động đáng chú ý]

<b>2) Các yếu tố vĩ mô chính</b>

🏦 <b>Chính sách tiền tệ (Fed)</b>
[Lãi suất, kỳ vọng thị trường, phát biểu gần nhất]

🌍 <b>Địa chính trị</b>
[Các điểm nóng đang ảnh hưởng tâm lý thị trường]

🏛️ <b>Ngân hàng trung ương & cầu cấu trúc</b>
[Mua ròng NHTW, ETF flows, dự báo ngân hàng lớn]

<b>3) Nhận định tổng quan</b>
[Ngắn hạn / Trung hạn / Dài hạn — không đề cập số vùng giá cụ thể]

<i>{rc['footer']}</i>

{extra}
Lưu ý: KHÔNG đề cập vùng hỗ trợ/kháng cự hay bias hướng giá cụ thể."""

    content = call_claude(prompt, secrets["anthropic_key"])
    if not content:
        return (f"<b>{rc['header']}</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                f"📅 {day_vi} - {date_str} (GMT+7)\n\n"
                f"⚠️ Không thể tải dữ liệu vĩ mô hôm nay. Vui lòng thử lại sau.")
    return content

def main():
    cfg = load_config(); secrets = get_secrets()
    targets = get_active_targets(cfg, "macro")
    if not cfg["reports"]["macro"].get("enabled", True):
        print("[Macro] Disabled — bỏ qua"); return
    report = build_report(cfg, secrets)
    for t in targets:
        print(f"[Macro] → {t['name']}")
        ok = send_telegram(secrets["bot_token"], t["chat_id"], report)
        print(f"  {'✅ OK' if ok else '❌ Thất bại'}")

if __name__ == "__main__":
    main()
