import os, urllib.request, ssl, json

bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
chat_id   = os.environ.get("TELEGRAM_CHAT_ID", "")
api_key   = os.environ.get("ANTHROPIC_API_KEY", "")

print(f"BOT_TOKEN: {'OK len=' + str(len(bot_token)) if bot_token else 'MISSING'}")
print(f"CHAT_ID:   {'OK len=' + str(len(chat_id)) if chat_id else 'MISSING'}")
print(f"API_KEY:   {'OK len=' + str(len(api_key)) + ' starts=' + api_key[:8] if api_key else 'MISSING'}")

# Thu goi Anthropic API that
if api_key:
    url = "https://api.anthropic.com/v1/messages"
    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "Say hi in 5 words"}],
    }).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            data = json.loads(r.read())
            text = data["content"][0]["text"]
            print(f"Claude API: OK — '{text}'")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Claude API: HTTP {e.code} — {body[:200]}")
    except Exception as e:
        print(f"Claude API Error: {e}")
