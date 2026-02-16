# -*- coding: utf-8 -*-
"""
Обработка заявок на вступление в чат (ChatJoinRequest).
Отправка приветствия и капчи (пример: 5+3?) в личку, таймаут 2 минуты.
"""
import asyncio
import logging
import random
from aiogram import Bot, Router, F
from aiogram.types import ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton
import config
from storage import add, pop, cancel_timeout

logger = logging.getLogger(__name__)
router = Router(name="join_requests")

# Префикс callback для кнопок капчи: captcha_<число> или captcha_cancel
CAPTCHA_PREFIX = "captcha_"
CAPTCHA_CANCEL = "captcha_cancel"


def make_captcha_keyboard() -> tuple[InlineKeyboardMarkup, int, str]:
    """
    Случайный пример: a + b = ?. Возвращает (клавиатура, правильный ответ, текст вопроса).
    """
    a = random.randint(2, 12)
    b = random.randint(2, 12)
    correct = a + b
    question = f"Сколько будет {a}+{b}?"
    wrong = []
    while len(wrong) < 3:
        x = random.randint(1, 25)
        if x != correct and x not in wrong:
            wrong.append(x)
    options = [correct] + wrong
    random.shuffle(options)
    row_answers = [
        InlineKeyboardButton(text=str(n), callback_data=f"{CAPTCHA_PREFIX}{n}")
        for n in options
    ]
    row_cancel = [InlineKeyboardButton(text="Отменить заявку", callback_data=CAPTCHA_CANCEL)]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[row_answers, row_cancel])
    return keyboard, correct, question


async def _timeout_cleanup(bot: Bot, user_id: int, chat_id: int, message_ids: list[int]) -> None:
    """
    Действия по истечении 2 минут: отклонить заявку, удалить наши сообщения в ЛС.
    """
    data = await pop(user_id)
    if not data:
        return  # Уже обработано (одобрено по капче)
    try:
        await bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
        logger.info("Заявка отклонена по таймауту: user_id=%s, chat_id=%s", user_id, chat_id)
    except Exception as e:
        logger.exception("Ошибка при отклонении заявки: %s", e)
    # Удаляем отправленные ботом сообщения в личке (очистка диалога)
    for mid in message_ids:
        try:
            await bot.delete_message(chat_id=user_id, message_id=mid)
        except Exception as e:
            logger.debug("Не удалось удалить сообщение %s: %s", mid, e)


@router.chat_join_request()
async def on_join_request(event: ChatJoinRequest, bot: Bot) -> None:
    """
    Новая заявка на вступление: приветствие в ЛС, кнопка-капча, таймер 2 мин.
    """
    chat_id = int(event.chat.id)
    user = event.from_user
    user_id = user.id
    logger.info("Заявка на вступление получена! chat_id=%s, user_id=%s, username=%s",
                chat_id, user_id, user.username)
    if chat_id != config.CHAT_ID:
        logger.info("Заявка из другого чата (id=%s), ожидался %s — пропуск", chat_id, config.CHAT_ID)
        return

    logger.info("Получена заявка на вступление: user_id=%s, username=%s, chat_id=%s",
                user_id, user.username, chat_id)

    message_ids: list[int] = []
    correct_answer: int | None = None
    if not user.is_bot:
        try:
            keyboard, correct_answer, question = make_captcha_keyboard()
            # answer_pm() использует user_chat_id — бот может писать в ЛС 5 минут без /start
            msg = await event.answer_pm(
                "Привет! Ты подал заявку на вступление в группу.\n\n"
                f"Подтверди, что ты не бот — выбери правильный ответ:\n{question}\n\nУ тебя 2 минуты.",
                reply_markup=keyboard,
            )
            message_ids.append(msg.message_id)
        except Exception as e:
            logger.warning("Не удалось написать пользователю %s в ЛС: %s", user_id, e)
    else:
        logger.info("Заявка от бота, будет отклонена по таймауту: user_id=%s", user_id)

    # Таймаут 2 минуты: после него — decline и удаление сообщений в ЛС
    async def timeout_task() -> None:
        await asyncio.sleep(120)
        await _timeout_cleanup(bot, user_id, chat_id, message_ids)

    task = asyncio.create_task(timeout_task())
    await add(user_id, chat_id, message_ids, task, correct_answer=correct_answer, attempts_left=2)
