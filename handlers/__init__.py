# -*- coding: utf-8 -*-
"""
Обработчики событий бота: заявки на вступление и сообщения (капча).
"""
from .join_requests import router as join_router
from .messages import router as messages_router

__all__ = ["join_router", "messages_router"]
