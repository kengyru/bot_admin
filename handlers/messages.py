# -*- coding: utf-8 -*-
"""
Обработка нажатий на кнопку капчи и одобрение/отклонение заявки.
"""
import logging
from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import CommandStart

import config
from storage import get, pop, update, cancel_timeout
from .join_requests import CAPTCHA_PREFIX, CAPTCHA_CANCEL, make_captcha_keyboard

logger = logging.getLogger(__name__)
router = Router(name="messages")


@router.message(F.chat.type == "private", CommandStart())
async def cmd_start(message: Message, bot: Bot) -> None:
    """Ответ на /start в личку: приветствие и подсказка."""
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return
    # Если есть активная заявка — подсказка пройти капчу
    data = await get(user_id)
    if data:
        await message.answer(
            "У тебя есть активная заявка. Выбери правильный ответ на пример в сообщении выше."
        )
        return
    await message.answer(
        "Привет! Я бот для вступления в группу.\n\n"
        "Перейди по ссылке на группу и нажми «Подать заявку». После этого я напишу тебе здесь и попрошу нажать кнопку — тогда заявку одобрят."
    )


@router.message(F.chat.id == config.CHAT_ID)
async def ignore_group_messages(message: Message) -> None:
    """Игнорируем сообщения в группе (чтобы не было «Update is not handled» в логах)."""
    pass


@router.message(F.chat.type == "private")
async def on_private_message(message: Message, bot: Bot) -> None:
    """
    При капче заявка одобряется только при нажатии правильной кнопки.
    Если пользователь пишет текст — просим выбрать ответ кнопками.
    """
    user_id = message.from_user.id if message.from_user else None
    if not user_id:
        return
    data = await get(user_id)
    logger.info("Личное сообщение от user_id=%s, есть активная заявка: %s", user_id, "да" if data else "нет")
    if not data:
        return
    # Капча: одобрение только по кнопке с правильным ответом
    if data.get("correct_answer") is not None:
        await message.answer("Выбери правильный ответ на кнопках выше.")
        return
    cancelled = await cancel_timeout(user_id)
    data = await pop(user_id)
    if not data:
        return
    chat_id = data["chat_id"]
    try:
        await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        logger.info("Заявка одобрена (по сообщению в ЛС): user_id=%s, chat_id=%s", user_id, chat_id)
    except Exception as e:
        logger.exception("Ошибка при одобрении заявки: %s", e)
        return
    await message.answer("Добро пожаловать! Твоя заявка одобрена.")


@router.callback_query(F.data.startswith(CAPTCHA_PREFIX))
async def on_captcha_answer(callback: CallbackQuery, bot: Bot) -> None:
    """
    Пользователь нажал кнопку: ответ капчи или «Отменить заявку».
    """
    user_id = callback.from_user.id
    if not user_id:
        await callback.answer("Ошибка.")
        return

    # «Отменить заявку» — отклоняем и разрешаем подать заявку заново по ссылке
    if callback.data == CAPTCHA_CANCEL:
        data = await get(user_id)
        if not data:
            await callback.answer("Заявка уже обработана.")
            return
        chat_id = data["chat_id"]
        await cancel_timeout(user_id)
        await pop(user_id)
        try:
            await bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
            logger.info("Заявка отменена пользователем: user_id=%s, chat_id=%s", user_id, chat_id)
        except Exception as e:
            logger.exception("Ошибка при отклонении заявки: %s", e)
        try:
            await callback.message.edit_text(
                "Заявка отменена. Можешь подать заявку снова по ссылке на группу."
            )
        except Exception:
            await bot.send_message(
                user_id,
                "Заявка отменена. Можешь подать заявку снова по ссылке на группу.",
            )
        await callback.answer()
        return

    try:
        answer = int(callback.data.replace(CAPTCHA_PREFIX, ""))
    except ValueError:
        await callback.answer("Ошибка.")
        return

    data = await get(user_id)
    if not data:
        await callback.answer("Заявка уже обработана или время вышло.")
        return

    chat_id = data["chat_id"]
    correct = data.get("correct_answer")
    attempts_left = data.get("attempts_left", 2)

    if correct is None:
        # Старая заявка без капчи — считаем что прошёл
        await cancel_timeout(user_id)
        await pop(user_id)
        try:
            await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            logger.info("Заявка одобрена: user_id=%s, chat_id=%s", user_id, chat_id)
        except Exception as e:
            logger.exception("Ошибка при одобрении заявки: %s", e)
            await callback.answer("Ошибка.")
            return
        try:
            await callback.message.edit_text("Добро пожаловать! Твоя заявка одобрена.")
        except Exception:
            await bot.send_message(user_id, "Добро пожаловать! Твоя заявка одобрена.")
        await callback.answer()
        return

    if answer != correct:
        attempts_left -= 1
        if attempts_left > 0:
            # Ещё одна попытка — новый пример
            keyboard, new_correct, question = make_captcha_keyboard()
            try:
                await callback.message.edit_text(
                    f"Неверно. Осталась {attempts_left} попытка. Попробуй ещё раз:\n{question}",
                    reply_markup=keyboard,
                )
            except Exception:
                await bot.send_message(
                    user_id,
                    f"Неверно. Осталась {attempts_left} попытка. Попробуй ещё раз:\n{question}",
                    reply_markup=keyboard,
                )
            await update(user_id, correct_answer=new_correct, attempts_left=attempts_left)
            await callback.answer("Неверно. Попробуй ещё раз.")
            return

        # Попытки кончились — отклоняем
        await pop(user_id)
        try:
            await bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
            logger.info("Заявка отклонена (неверная капча, попытки исчерпаны): user_id=%s, chat_id=%s", user_id, chat_id)
        except Exception as e:
            logger.exception("Ошибка при отклонении заявки: %s", e)
        try:
            await callback.message.edit_text(
                "Неверный ответ. Заявка отклонена.\n\nМожешь подать заявку заново по ссылке на группу."
            )
        except Exception:
            await bot.send_message(
                user_id,
                "Неверный ответ. Заявка отклонена.\n\nМожешь подать заявку заново по ссылке на группу.",
            )
        await callback.answer("Неверно.")
        return

    await cancel_timeout(user_id)
    await pop(user_id)
    try:
        await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        logger.info("Заявка одобрена (капча верна): user_id=%s, chat_id=%s", user_id, chat_id)
    except Exception as e:
        logger.exception("Ошибка при одобрении заявки: %s", e)
        await callback.answer("Ошибка.")
        return

    try:
        await callback.message.edit_text("Добро пожаловать! Твоя заявка одобрена.")
    except Exception:
        await bot.send_message(user_id, "Добро пожаловать! Твоя заявка одобрена.")

    await callback.answer("Верно!")
