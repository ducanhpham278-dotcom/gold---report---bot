# REPORT 5: PHAN TICH EMA & RSI
# Doc du lieu tu GitHub, phan tich va gui Telegram
import urllib.request, ssl, json, base64, os
from datetime import datetime, timedelta
from telegram_helper import send_message
from config_loader import load_config, get_secrets, get_active_targets

WEEKDAYS_VI = ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"]

# Map timeframe code -> ten hien thi
TF_NAME = {"15": "M15", "60": "H1", "240": "H4", "1D": "D1", "D": "D1"}

def get_file_from_github(path: str, gh_token: str) -> dict | None:
    """Doc file JSON tu private GitHub repo."""
    url = f"https://api.github.com/repos/ducanhpham278-dotcom/gold---report---bot/contents/{path}"
    headers = {
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            resp = json.loads(r.read())
            content = base64.b64decode(resp["content"]).decode("utf-8")
            return json.loads(content)
    except Exception as e:
        print(f"[GitHub] Không đọc được {path}: {e}")
        return None

def check_divergence(rsi_vals: list, price_vals: list, mode: str) -> str:
    """
    Phat hien phan ki RSI.
    mode: 'high' cho phan ki am (dinh), 'low' cho phan ki duong (day)
    rsi_vals, price_vals: [hien_tai, nen_1, nen_2, nen_3, nen_4]
    """
    if len(rsi_vals) < 3 or len(price_vals) < 3:
        return "Không đủ dữ liệu"
    
    if mode == "high":
        # Phan ki am: gia tang dinh cao hon, RSI tang dinh thap hon
        if price_vals[0] > price_vals[2] and rsi_vals[0] < rsi_vals[2]:
            return "⚠️ Phân kỳ âm (Bearish) — Giá đỉnh cao hơn nhưng RSI đỉnh thấp hơn → Cảnh báo đảo chiều giảm"
        # Phan ki duong an: gia giam dinh thap hon, RSI giam dinh cao hon
        if price_vals[0] < price_vals[2] and rsi_vals[0] > rsi_vals[2]:
            return "📈 Phân kỳ ẩn tăng — RSI mạnh hơn giá → Xu hướng tăng tiếp diễn"
    else:  # low
        # Phan ki duong: gia tao day thap hon, RSI tao day cao hon
        if price_vals[0] < price_vals[2] and rsi_vals[0] > rsi_vals[2]:
            return "⚠️ Phân kỳ dương (Bullish) — Giá đáy thấp hơn nhưng RSI đáy cao hơn → Tín hiệu đảo chiều tăng"
        # Phan ki am an: gia tang day cao hon, RSI tang day thap hon
        if price_vals[0] > price_vals[2] and rsi_vals[0] < rsi_vals[2]:
            return "📉 Phân kỳ ẩn giảm — RSI yếu hơn giá → Xu hướng giảm tiếp diễn"
    
    return "Không có phân kỳ rõ ràng"

def analyze_tf(data: dict, tf_name: str) -> dict:
    """Phan tich EMA va RSI cho 1 khung thoi gian."""
    ema34 = float(data.get("ema34", 0))
    ema89 = float(data.get("ema89", 0))
    rsi   = float(data.get("rsi",   50))
    rsi1  = float(data.get("rsi1",  50))
    rsi2  = float(data.get("rsi2",  50))
    rsi3  = float(data.get("rsi3",  50))
    rsi4  = float(data.get("rsi4",  50))
    high1 = float(data.get("high1", 0))
    high2 = float(data.get("high2", 0))
    high3 = float(data.get("high3", 0))
    low1  = float(data.get("low1",  0))
    low2  = float(data.get("low2",  0))
    low3  = float(data.get("low3",  0))
    close = float(data.get("close", 0))

    # EMA trend
    if ema34 > ema89:
        ema_trend = "✅ Tăng (EMA34 > EMA89)"
        ema_gap   = round(ema34 - ema89, 2)
        ema_note  = f"Khoảng cách: {ema_gap:.2f}"
    else:
        ema_trend = "❌ Giảm (EMA34 < EMA89)"
        ema_gap   = round(ema89 - ema34, 2)
        ema_note  = f"Khoảng cách: {ema_gap:.2f}"

    # RSI level
    if rsi >= 70:
        rsi_level = f"⚠️ Quá mua ({rsi:.1f})"
    elif rsi >= 50:
        rsi_level = f"✅ Tăng ({rsi:.1f})"
    elif rsi >= 30:
        rsi_level = f"❌ Giảm ({rsi:.1f})"
    else:
        rsi_level = f"⚠️ Quá bán ({rsi:.1f})"

    # Phan ki RSI - dung high cho phan ki am, low cho phan ki duong
    div_bear = check_divergence(
        [rsi, rsi1, rsi2, rsi3],
        [high1, high2, high3, 0],  # so sanh dinh
        "high"
    )
    div_bull = check_divergence(
        [rsi, rsi1, rsi2, rsi3],
        [low1, low2, low3, 0],     # so sanh day
        "low"
    )

    # Chon phan ki nao ro rang hon
    if "Phân kỳ" in div_bear and "Phân kỳ" in div_bull:
        divergence = f"{div_bear}\n    {div_bull}"
    elif "Phân kỳ" in div_bear:
        divergence = div_bear
    elif "Phân kỳ" in div_bull:
        divergence = div_bull
    else:
        divergence = "Không có phân kỳ"

    return {
        "tf":         tf_name,
        "ema_trend":  ema_trend,
        "ema34":      round(ema34, 2),
        "ema89":      round(ema89, 2),
        "ema_note":   ema_note,
        "rsi_level":  rsi_level,
        "rsi":        round(rsi, 1),
        "divergence": divergence,
    }

def summarize_trend(analyses: list) -> str:
    """Tong hop xu huong chung tu tat ca cac khung."""
    up = sum(1 for a in analyses if "Tăng" in a["ema_trend"])
    dn = sum(1 for a in analyses if "Giảm" in a["ema_trend"])
    total = len(analyses)

    # Lay rieng H4 va H1 de phan tich context
    h4 = next((a for a in analyses if a["tf"] == "H4"), None)
    h1 = next((a for a in analyses if a["tf"] == "H1"), None)
    m15 = next((a for a in analyses if a["tf"] == "M15"), None)
    d1 = next((a for a in analyses if a["tf"] == "D1"), None)

    if up >= 3:
        overall = "📈 <b>XU HƯỚNG TĂNG</b>"
        if m15 and "Giảm" in m15["ema_trend"]:
            context = "M15 giảm trong xu hướng tăng → Đang điều chỉnh ngắn hạn, cơ hội mua"
        else:
            context = "Đa khung ủng hộ tăng → Xu hướng mạnh"
    elif dn >= 3:
        overall = "📉 <b>XU HƯỚNG GIẢM</b>"
        if m15 and "Tăng" in m15["ema_trend"]:
            context = "M15 tăng trong xu hướng giảm → Đang hồi phục ngắn hạn, cơ hội bán"
        else:
            context = "Đa khung ủng hộ giảm → Xu hướng mạnh"
    elif up == 2 and dn == 2:
        overall = "⚖️ <b>GIẰNG CO</b>"
        context = "Các khung mâu thuẫn → Thị trường chưa có hướng rõ ràng, nên đứng ngoài"
    elif h4 and h1 and "Tăng" in h4["ema_trend"] and "Tăng" in h1["ema_trend"]:
        overall = "📈 <b>XU HƯỚNG TĂNG</b> (H1+H4)"
        context = "H1 và H4 ủng hộ tăng là chủ đạo"
        if m15 and "Giảm" in m15["ema_trend"]:
            context += " | M15 giảm → Nhịp điều chỉnh nhỏ"
    else:
        overall = "🔄 <b>TRUNG LẬP</b>"
        context = f"Tăng: {up}/{total} khung | Giảm: {dn}/{total} khung"

    return f"{overall}\n{context}"

def main():
    cfg     = load_config()
    secrets = get_secrets()
    targets = get_active_targets(cfg, "daily_news")  # Dung chung targets
    
    gh_token = os.environ.get("GH_TOKEN", "")
    if not gh_token:
        print("[EMA RSI] Không có GH_TOKEN trong environment")
        return

    now_ict  = datetime.utcnow() + timedelta(hours=7)
    day_vi   = WEEKDAYS_VI[now_ict.weekday()]
    date_str = now_ict.strftime("%d/%m/%Y")
    time_str = now_ict.strftime("%H:%M")

    # Doc du lieu 4 khung tu GitHub
    tf_files = {
        "M15": "data/ema_rsi_15.json",
        "H1":  "data/ema_rsi_60.json",
        "H4":  "data/ema_rsi_240.json",
        "D1":  "data/ema_rsi_1D.json",
    }

    analyses = []
    missing  = []
    for tf_name, path in tf_files.items():
        data = get_file_from_github(path, gh_token)
        if data:
            analyses.append(analyze_tf(data, tf_name))
            print(f"[EMA RSI] ✅ {tf_name}")
        else:
            missing.append(tf_name)
            print(f"[EMA RSI] ❌ Thiếu dữ liệu {tf_name}")

    if not analyses:
        print("[EMA RSI] Không có dữ liệu nào — bỏ qua")
        return

    # Build report
    lines = [
        f"📊 <b>GOLD / XAUUSD — PHÂN TÍCH EMA &amp; RSI</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📅 {day_vi} - {date_str} | {time_str} ICT",
        "",
    ]

    # Tong hop xu huong
    trend_summary = summarize_trend(analyses)
    lines += [
        f"<b>🎯 XU HƯỚNG TỔNG THỂ:</b>",
        trend_summary,
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "<b>CHI TIẾT TỪNG KHUNG:</b>",
    ]

    # Chi tiet tung khung
    for a in analyses:
        lines += [
            "",
            f"<b>▶ {a['tf']}</b>",
            f"EMA : {a['ema_trend']}",
            f"     EMA34={a['ema34']} | EMA89={a['ema89']} | {a['ema_note']}",
            f"RSI : {a['rsi_level']}",
            f"Phân kỳ: {a['divergence']}",
        ]

    if missing:
        lines += ["", f"<i>⚠️ Chưa có dữ liệu: {', '.join(missing)}</i>"]

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "<i>Nguồn: TradingView (EMA34, EMA89, RSI14)</i>",
    ]

    content = "\n".join(lines)
    print(f"[EMA RSI] {len(content)} ký tự")

    for t in targets:
        print(f"[EMA RSI] → {t['name']}")
        ok = send_message(secrets["bot_token"], t["chat_id"], content)
        print(f"  {'✅' if ok else '❌'}")

if __name__ == "__main__":
    main()
