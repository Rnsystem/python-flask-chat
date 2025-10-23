# config.py
import os

class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret")  # 本番は必須で環境変数から
    RECAPTCHA_PUBLIC_KEY = os.environ.get("RECAPTCHA_PUBLIC_KEY", "")
    RECAPTCHA_PRIVATE_KEY = os.environ.get("RECAPTCHA_PRIVATE_KEY", "")
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
    SLACK_CHANNEL_PREFIX = os.environ.get("SLACK_CHANNEL_PREFIX", "customer-")
    ADMIN_USERS = os.environ.get("ADMIN_USERS", "").split(",") if os.environ.get("ADMIN_USERS") else []
    SESSION_WAIT_TIME = int(os.environ.get("SESSION_WAIT_TIME", "300"))
