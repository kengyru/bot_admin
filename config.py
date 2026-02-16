# -*- coding: utf-8 -*-
"""
Конфигурация бота: загрузка переменных окружения из .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота (получить у @BotFather)
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
# ID чата/группы для одобрения заявок (числовой, например -1001234567890)
CHAT_ID: int = int(os.getenv("CHAT_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env")
if not CHAT_ID:
    raise ValueError("CHAT_ID не задан в .env")
