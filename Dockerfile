# Telegram-бот: заявки на вступление в группу
FROM python:3.12-slim

WORKDIR /app

# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код бота
COPY config.py main.py storage.py ./
COPY handlers/ ./handlers/

# Запуск (BOT_TOKEN и CHAT_ID передаются через env на сервере)
CMD ["python", "-u", "main.py"]
