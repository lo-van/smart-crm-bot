# Деплой Smart CRM Bot на VPS (Ubuntu)
В этой инструкции описан процесс установки и запуска бота и веб-панели на сервере с Ubuntu 20.04/22.04/24.04.

## 1. Подготовка сервера
Подключитесь к серверу по SSH и выполните базовую настройку:\
`apt update && apt upgrade -y`\
`apt install -y python3-pip python3-venv git`

## 2. Клонирование репозитория
`git clone https://github.com/lo-van/smart-crm-bot.git /opt/smart-crm-bot`\
`cd /opt/smart-crm-bot`

## 3. Переменные окружения
Создайте файл `.env` в корне проекта:\
`nano /opt/smart-crm-bot/.env`

## 4. Виртуальное окружение и зависимости
```cd /opt/smart-crm-bot `
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt```

## 5. Создание сессии Telethon (userbot)
Первый запуск userbot потребует ввода номера телефона и кода подтверждения. Выполните авторизацию один раз вручную:\
`python3 userbot.py <ваш_telegram_id>`

После успешного входа появится файл `userbot_session.session`. В дальнейшем он будет использоваться автоматически.

## 6. Systemd‑сервис для бота
Создайте файл `/etc/systemd/system/smart-crm-bot.service`:\
```[Unit]`
Description=Smart CRM Bot
After=network.target
[Service]
Type=simple
User=root
WorkingDirectory=/opt/smart-crm-bot
Environment="PATH=/opt/smart-crm-bot/venv/bin"
ExecStart=/opt/smart-crm-bot/venv/bin/python main.py
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target```

Запустите сервис:
`systemctl daemon-reload`
`systemctl enable --now smart-crm-bot.service`

Проверьте статус:\
`systemctl status smart-crm-bot.service`

## 7. Веб‑панель (FastAPI)
Убедитесь, что в виртуальном окружении установлен `uvicorn`. Если нет:\
`source /opt/smart-crm-bot/venv/bin/activate`
`pip install uvicorn`

Создайте systemd‑сервис для веб‑панели `/etc/systemd/system/smart-crm-web.service`:\
`[Unit]`\
`Description=Smart CRM Web Panel`\
`After=network.target`\
`[Service]`\
`Type=simple`\
`User=root`\
`WorkingDirectory=/opt/smart-crm-bot`\
`Environment="PATH=/opt/smart-crm-bot/venv/bin"`\
`ExecStart=/opt/smart-crm-bot/venv/bin/uvicorn webapp.app:app --host 127.0.0.1 --port 8001`\
`Restart=always`\
`RestartSec=10`\
`[Install]`\
`WantedBy=multi-user.target`

Запустите:\
`systemctl daemon-reload`
`systemctl enable --now smart-crm-web.service`

## 8. Nginx как reverse proxy (поддомен crm.example.com)
Создайте конфиг `/etc/nginx/sites-available/crm`:\
`server {`\
`    listen 80;`\
    `server_name crm.example.com;   # замените на ваш домен`

`    location / {`\
        `proxy_pass http://127.0.0.1:8001;`\
        `proxy_set_header Host $host;`\
        `proxy_set_header X-Real-IP $remote_addr;`\
        `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`\
        `proxy_set_header X-Forwarded-Proto $scheme;`\
   ` }`\
`}`

Включите сайт и перезагрузите nginx:\
`ln -s /etc/nginx/sites-available/crm /etc/nginx/sites-enabled/`\
`nginx -t`\
`systemctl reload nginx`

Для HTTPS выполните:\
`certbot --nginx -d crm.example.com`

## 9. Первоначальная синхронизация
В Telegram отправьте боту команду `/sync`. Дождитесь завершения синхронизации контактов и сообщений.

## 10. Обновление из репозитория
При выходе новых версий на сервере выполните:\
`cd /opt/smart-crm-bot`\
`git pull origin main`\
`systemctl restart smart-crm-bot.service`\
`systemctl restart smart-crm-web.service`

### Дополнительно
+ Логи бота: `journalctl -u smart-crm-bot.service -f`
+ Логи веб‑панели: `journalctl -u smart-crm-web.service -f`
+ Настройка автотегирования: отправьте боту команду `/autotag`
+ Подробнее о функциях бота читайте в [README.md]() и [INSTALL.md]()
