# telegram_helper.py - Ham gui Telegram + retry Claude API + clean HTML
import urllib.request, ssl, json, time, re

MAX_LEN = 4000


def clean_html(text: str) -> str:
    """
    Làm sạch HTML trước khi gửi Telegram.
    Chỉ giữ lại các tag Telegram hỗ trợ: <b>, <i>, <code>, <pre>, <a>.
    Xóa hoặc escape các tag khác.
    """
    # Cac tag Telegram cho phep
    allowed = {"b", "i", "code", "pre", "a"}

    # Xoa cac tag khong duoc phep (giu noi dung ben trong)
    def replace_tag(m):
        tag = m.group(1).lower().split()[0].lstrip("/")
        if tag in allowed:
            return m.group(0)
        # Xoa tag, giu noi dung
        return ""

    text = re.sub(r"<(/?\w+[^>]*)>", replace_tag, text)

    # Escape & neu khong phai entity
    text = re.sub(r"&(?!amp;|lt;|gt;|quot;|apos;)", "&amp;", text)

    # Xoa cac dong chi co whitespace
    lines = [l.rstrip() for l in text.split("\n")]
    # Giu toi da 2 dong trong lien tiep
    result = []
    blank = 0
    for line in lines:
        if line == "":
            blank += 1
            if blank <= 2:
                result.append(line)
        else:
            blank = 0
            result.append(line)

    return "\n".join(result)


def send_telegram(bot_token: str, chat_id: str, text: str) -> bool:
    text = clean_html(text)
    if not text.strip():
        return True

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            result = json.loads(r.read())
            if not result.get("ok"):
                print(f"[Telegram] API error: {result}")
                # Neu van loi 400, thu gui khong parse_mode
                return _send_plain(bot_token, chat_id, text)
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[Telegram Error] HTTP {e.code}: {body}")
        if e.code == 400:
            # Fallback: strip tat ca HTML, gui plain text
            print("[Telegram] Fallback: gui plain text...")
            plain = re.sub(r"<[^>]+>", "", text)
            return _send_plain(bot_token, chat_id, plain)
        return False
    except Exception as e:
        print(f"[Telegram Error] {e}")
        return False


def _send_plain(bot_token: str, chat_id: str, text: str) -> bool:
    """Gửi plain text không có parse_mode."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }).encode("utf-8")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            return json.loads(r.read()).get("ok", False)
    except Exception as e:
        print(f"[Telegram Plain Error] {e}")
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
            time.sleep(1)
    return ok_all


def call_claude_with_retry(prompt: str, key: str, use_search: bool = True,
                           max_tokens: int = 2500, max_retries: int = 3) -> str:
    """Gọi Claude API với retry tự động khi gặp 529."""
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
            "Chỉ dùng các HTML tag sau cho Telegram: <b>, <i>. "
            "KHÔNG dùng các tag khác như <h1>, <h2>, <ul>, <li>, <p>, <br>, <strong>, <em>. "
            "KHÔNG dùng Markdown, KHÔNG dùng **, *, #, ---, ===. "
            "Dùng ký tự ━ để tạo đường kẻ phân cách. "
            "Viết đầy đủ tất cả các mục, không bỏ sót."
        ),
        "messages": [{"role": "user", "content": prompt}],
        **({"tools": tools} if tools else {}),
    }).encode("utf-8")

    ctx = ssl.create_default_context()

    for attempt in range(max_retries):
        wait = (attempt + 1) * 30
        try:
            req = urllib.request.Request(url, data=payload, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=120) as r:
                data = json.loads(r.read())
                return "".join(
                    b.get("text", "") for b in data.get("content", [])
                    if b.get("type") == "text"
                )
        except urllib.error.HTTPError as e:
            if e.code in (529, 429) and attempt < max_retries - 1:
                print(f"[Claude] 529 Overloaded — thử lại sau {wait}s ({attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                print(f"[Claude Error] HTTP {e.code}: {e.reason}")
                return ""
        except Exception as e:
            print(f"[Claude Error] {e}")
            if attempt < max_retries - 1:
                time.sleep(wait)
            else:
                return ""
    return ""
