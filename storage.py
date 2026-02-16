# -*- coding: utf-8 -*-
"""
Временное хранилище заявок на вступление (in-memory).
Структура: user_id -> {chat_id, message_ids[], timeout_task, correct_answer?, attempts_left}
"""
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Словарь активных заявок: user_id -> данные заявки
_pending: dict[int, dict[str, Any]] = {}
_lock = asyncio.Lock()


async def add(
    user_id: int,
    chat_id: int,
    message_ids: list[int],
    timeout_task: asyncio.Task,
    correct_answer: int | None = None,
    attempts_left: int = 2,
) -> None:
    """Добавить заявку. correct_answer — правильный ответ капчи, attempts_left — попыток на капчу."""
    async with _lock:
        _pending[user_id] = {
            "chat_id": chat_id,
            "message_ids": message_ids,
            "timeout_task": timeout_task,
            "correct_answer": correct_answer,
            "attempts_left": attempts_left,
        }
    logger.debug("Заявка добавлена: user_id=%s, chat_id=%s", user_id, chat_id)


async def update(user_id: int, **kwargs: Any) -> bool:
    """Обновить поля заявки (например correct_answer, attempts_left). Возвращает True если заявка найдена."""
    async with _lock:
        if user_id not in _pending:
            return False
        for key, value in kwargs.items():
            _pending[user_id][key] = value
    return True


async def get(user_id: int) -> dict[str, Any] | None:
    """Получить данные заявки по user_id."""
    async with _lock:
        return _pending.get(user_id)


async def pop(user_id: int) -> dict[str, Any] | None:
    """Удалить заявку из хранилища и вернуть её данные."""
    async with _lock:
        return _pending.pop(user_id, None)


async def cancel_timeout(user_id: int) -> bool:
    """Отменить таймаут для заявки (если пользователь прошёл проверку)."""
    data = await get(user_id)
    if not data:
        return False
    task = data.get("timeout_task")
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return True
    return False
