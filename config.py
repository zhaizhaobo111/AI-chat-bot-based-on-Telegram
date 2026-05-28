import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MIMO_API_KEY = os.getenv("MIMO_API_KEY")
MIMO_BASE_URL = os.getenv("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
MIMO_MODEL = os.getenv("MIMO_MODEL", "mimo-v2.5-pro")

# 每个用户最多保留的对话轮数
MAX_HISTORY_ROUNDS = 20

# 代理配置（Clash Mi 默认端口）
PROXY_URL = os.getenv("PROXY_URL", "http://127.0.0.1:7890")
