# Установка и запуск Smart CRM Bot

## Требования
- Python 3.10 или выше
- Аккаунт Telegram (для userbot-функций)
- Сервер с Ubuntu (или локальная машина) с доступом к Telegram API (VPN/прокси при необходимости)

## Локальная установка (для разработки)
1. Клонируйте репозиторий:
   ```bash 
   git clone https://github.com/lo-van/smart-crm-bot.git
   cd smart-crm-bot

2. Создайте виртуальное окружение и установите зависимости:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

3. Создайте файл .env в корне проекта со следующим содержимым:
   ```bash 
   BOT_TOKEN=<токен от BotFather>
   API_ID=<ваш api_id с my.telegram.org>
   API_HASH=<ваш api_hash с my.telegram.org>

4. Запустите бота:
   ```bash 
   python main.py

5. В Telegram отправьте команду /start, затем /sync для первой синхронизации контактов.

## Развёртывание на сервере (VPS)
Подробная инструкция находится в [DEPLOY.md](DEPLOY.md) (при наличии) или в вики проекта.

## Примечание по LLM-функциональности
В коде предусмотрена возможность подключения языковых моделей (LLM) для улучшения поиска и генерации ледоколов, но в текущей версии они не реализованы. Вы можете легко добавить свою модель, изменив файлы llm.py и icebreaker.py. Примеры интеграции с OpenAI, DeepSeek, Ollama и другими API приведены в документации по разработке.

## Лицензия
MIT
