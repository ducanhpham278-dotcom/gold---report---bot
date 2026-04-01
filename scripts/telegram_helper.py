# telegram_helper.py - Ham gui Telegram + retry Claude API
import urllib.request, ssl, json, time

MAX_LEN = 4000


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
    """Tự động chia nhỏ nếu text > MAX_LEN."""
    if len(text) <= MAX_LEN:
        return send_telegram(bot_token, chat_id, text)

    lines = text.split("\n")
    chunks = []
    current = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1
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
        if i < len(chunks) - 1:
            time.sleep(1)  # Tránh spam Telegram
    return ok_all


def call_claude_with_retry(prompt: str, key: str, use_search: bool = True,
                           max_tokens: int = 2500, max_retries: int = 3) -> str:
    """
    Gọi Claude API với retry tự động khi gặp lỗi 529 (Overloaded).
    Mỗi lần retry chờ lâu hơn: 30s, 60s, 90s.
    """
    url = "https://api.anthropic.com/v1/messages"
    tools = [{"type": "web_search_20250305", "name": "web_search"}] if use_search else []
    headers = {
        "Content-Type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    }
    if use_search:
        headers["anthropic-beta"] = "web-search-2025-03-05"

    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": max_tokens,
        "system": (
            "Bạn là chuyên gia phân tích XAUUSD. "
            "Viết HOÀN TOÀN bằng tiếng Việt có dấu đầy đủ. "
            "Dùng HTML tags (<b>,<i>) cho Telegram. "
            "KHÔNG dùng Markdown, KHÔNG dùng **, *, #. "
            "Viết đầy đủ tất cả các mục, không bỏ sót."
        ),
        "messages": [{"role": "user", "content": prompt}],
        **({"tools": tools} if tools else {}),
    }).encode("utf-8")

    ctx = ssl.create_default_context()

    for attempt in range(max_retries):
        wait = (attempt + 1) * 30  # 30s, 60s, 90s
        try:
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=120) as r:
                data = json.loads(r.read())
                return "".join(
                    b.get("text", "") for b in data.get("content", [])
                    if b.get("type") == "text"
                )
        except urllib.error.HTTPError as e:
            status = e.code
            if status == 529 and attempt < max_retries - 1:
                print(f"[Claude] 529 Overloaded — thử lại sau {wait}s (lần {attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                print(f"[Claude Error] HTTP {status}: {e.reason}")
                return ""
        except Exception as e:
            print(f"[Claude Error] {e}")
            if attempt < max_retries - 1:
                print(f"[Claude] Thử lại sau {wait}s...")
                time.sleep(wait)
            else:
                return ""

    return ""
