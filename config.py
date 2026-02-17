# -*- coding: utf-8 -*-
"""
Конфигурация бота: загрузка переменных окружения из .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота (получить у @BotFather)
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
# ID чатов/групп для одобрения заявок (через запятую: -1001061812516,-1001130616556)
_raw = os.getenv("CHAT_ID", "").strip()
CHAT_IDS: list[int] = [int(x.strip()) for x in _raw.split(",") if x.strip()]

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env")
if not CHAT_IDS:
    raise ValueError("CHAT_ID не задан в .env (можно несколько через запятую)")
