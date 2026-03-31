# telegram_helper.py - Ham gui Telegram dung chung, tu dong chia nho
import urllib.request, ssl, json

MAX_LEN = 4000  # Buffer 96 ky tu cho Telegram


def send_telegram(bot_token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": True,
    }).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            result = json.loads(r.read())
            if not result.get("ok"):
                print(f"[Telegram] API error: {result}")
            return result.get("ok", False)
    except Exception as e:
        print(f"[Telegram Error] {e}")
        return False


def send_message(bot_token: str, chat_id: str, text: str) -> bool:
    """
    Tự động chia nhỏ nếu text > MAX_LEN.
    Ưu tiên cắt tại dòng phân cách ━━━ hoặc dòng trống,
    đảm bảo không cắt giữa câu.
    """
    if len(text) <= MAX_LEN:
        return send_telegram(bot_token, chat_id, text)

    # Chia theo dòng, ghép lại thành chunks <= MAX_LEN
    lines = text.split("\n")
    chunks = []
    current = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 cho ký tự \n

        # Nếu thêm dòng này vượt giới hạn → lưu chunk hiện tại
        if current_len + line_len > MAX_LEN and current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0

        current.append(line)
        current_len += line_len

    if current:
        chunks.append("\n".join(current))

    print(f"[Telegram] Chia thành {len(chunks)} tin nhắn")
    ok_all = True
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        print(f"[Telegram] Gửi phần {i+1}/{len(chunks)} ({len(chunk)} ký tự)")
        ok = send_telegram(bot_token, chat_id, chunk.strip())
        if not ok:
            ok_all = False
    return ok_all
