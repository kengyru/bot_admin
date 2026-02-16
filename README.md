# Telegram-бот: автоматическая обработка заявок на вступление в группу

Бот на **Python** (aiogram 3.x) обрабатывает заявки на вступление в группу (Chat Join Requests): приветствие в ЛС, проверка «на человечность» по кнопке, одобрение или отклонение за 2 минуты.

## Установка

```bash
pip install -r requirements.txt
```

## Настройка

1. Скопируйте `.env.example` в `.env`:
   ```bash
   copy .env.example .env
   ```
2. В `.env` укажите:
   - **BOT_TOKEN** — токен от [@BotFather](https://t.me/BotFather)
   - **CHAT_ID** — числовой ID группы (например, `-1001234567890`). Как получить: добавьте бота [@userinfobot](https://t.me/userinfobot) в группу и перешлите любое сообщение из группы — он покажет ID.

3. В группе:
   - Добавьте бота администратором с правом **«Приглашать пользователей по ссылке»** (или «добавление пользователей»).
   - Включите режим «Заявки на вступление» (группа должна быть с включённой заявкой на вступление).

## Запуск

```bash
python main.py
```

## Логика работы

1. Пользователь подаёт заявку на вступление в группу.
2. Бот отправляет ему в личку приветствие и кнопку «Я человек — нажми сюда».
3. Если пользователь нажимает кнопку **в течение 2 минут**:
   - заявка **одобряется**;
   - в ЛС приходит: «Добро пожаловать!»
4. Если пользователь **не нажал** кнопку за 2 минуты или заявка от бота:
   - заявка **отклоняется**;
   - сообщения бота в ЛС **удаляются**.

Все действия логируются (кто подал заявку, одобрена или отклонена).

---

## Docker

Сборка и запуск в контейнере:

```bash
# Сборка образа
docker build -t bot_admin .

# Запуск (файл .env должен быть в текущей папке)
docker run --rm --env-file .env bot_admin
```

Через docker-compose (с автоперезапуском):

```bash
# Рядом с проектом должен лежать .env
docker compose up -d --build
```

Остановка: `docker compose down`.

---

## Очистка сервера от старого проекта

Перед выкладкой нового бота останови и убери старый проект.

**Если старый бот был в Docker / docker-compose:**
```bash
cd /path/to/old_bot_admin   # папка старого проекта
docker compose down
cd ..
rm -rf old_bot_admin        # или как называлась папка
```

**Удалить неиспользуемые образы и контейнеры (по желанию):**
```bash
docker container prune -f
docker image prune -f
```

**Если старый бот запускался через systemd:**
```bash
sudo systemctl stop bot_admin
sudo systemctl disable bot_admin
sudo rm /etc/systemd/system/bot_admin.service
sudo systemctl daemon-reload
```
Потом удали папку старого проекта: `rm -rf /path/to/old_bot_admin`.

**Если старый бот просто крутился в screen/tmux:** зайди в сессию и заверши процесс (Ctrl+C), затем выйди из screen/tmux и при необходимости удали папку проекта.

После этого можно ставить новый проект по шагам ниже.

---

## Как посмотреть, что сейчас на сервере

**Docker — какие контейнеры запущены:**
```bash
docker ps
```
Все контейнеры (включая остановленные): `docker ps -a`.

**Какой образ и откуда папка у контейнера:**
```bash
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
docker inspect имя_контейнера --format '{{.Config.WorkingDir}}'
```

**Сервисы systemd с «bot» в имени:**
```bash
systemctl list-units --type=service | grep -i bot
# или
systemctl list-units --all | grep bot
```

**Процессы Python (если бот без Docker):**
```bash
ps aux | grep python
```

**Папки с проектами (типичные места):**
```bash
ls -la /home
ls -la /var/www
ls -la ~
```

**Логи контейнера bot_admin (если через docker-compose):**
```bash
cd /path/to/bot_admin
docker compose logs -f
```

**Логи systemd-сервиса:**
```bash
journalctl -u bot_admin -f
```

---

## Запуск на сервере

1. **Склонируй репозиторий** на сервер:
   ```bash
   git clone https://github.com/kengyru/bot_admin.git
   cd bot_admin
   ```

2. **Создай `.env`** в папке проекта:
   ```bash
   cp .env.example .env
   nano .env   # или любой редактор
   ```
   Заполни `BOT_TOKEN` и `CHAT_ID`.

3. **Вариант А — через Docker:**
   ```bash
   docker compose up -d --build
   ```
   Логи: `docker compose logs -f`

4. **Вариант Б — без Docker (Python на сервере):**
   ```bash
   pip install -r requirements.txt
   python main.py
   ```
   Чтобы бот работал после выхода из SSH, используй `screen`, `tmux` или systemd.

5. **Пример unit для systemd** (если без Docker), создай `/etc/systemd/system/bot_admin.service`:
   ```ini
   [Unit]
   Description=Telegram bot_admin
   After=network.target

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/path/to/bot_admin
   ExecStart=/usr/bin/python3 main.py
   Restart=always
   EnvironmentFile=/path/to/bot_admin/.env

   [Install]
   WantedBy=multi-user.target
   ```
   Затем: `systemctl daemon-reload`, `systemctl enable --now bot_admin`.
