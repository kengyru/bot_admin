# -*- coding: utf-8 -*-
"""
Точка входа: запуск бота для автоматической обработки заявок на вступление в группу.
Обрабатываются события ChatJoinRequest: приветствие в ЛС, капча по кнопке, одобрение/отклонение за 2 мин.
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from handlers import join_router, messages_router

# Настройка логирования: кто подал заявку, прошёл проверку или нет
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(join_router)
    dp.include_router(messages_router)

    logger.info("Бот запущен. Ожидаются заявки на вступление в чаты: %s", config.CHAT_IDS)
    # Важно: без chat_join_request бот не получит заявки на вступление
    await dp.start_polling(
        bot,
        allowed_updates=["message", "callback_query", "chat_join_request"],
    )


if __name__ == "__main__":
    asyncio.run(main())
