# =============================================================
# config_loader.py — Đọc config.json & secrets từ env
# Dùng chung cho tất cả report scripts
# =============================================================

import json
import os
from pathlib import Path


def load_config() -> dict:
    """Đọc config.json từ thư mục gốc project."""
    config_path = Path(__file__).parent.parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_secrets() -> dict:
    """Lấy secrets từ environment variables (GitHub Secrets)."""
    return {
        "bot_token":      os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "anthropic_key":  os.environ.get("ANTHROPIC_API_KEY", ""),
    }


def get_active_targets(config: dict, report_type: str) -> list[dict]:
    """
    Trả về danh sách các Telegram target đang enabled
    và đăng ký nhận report_type này.
    """
    targets = []
    for t in config["telegram"]["targets"]:
        if t.get("enabled", True) and report_type in t.get("reports", []):
            targets.append(t)
    return targets
