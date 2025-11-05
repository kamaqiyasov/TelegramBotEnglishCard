# TelegramBotEnglishCard

Бот для изучения английских слов с использованием карточек и интервального повторения (Spaced Repetition System).

## Возможности

- Создание карточек со словами и переводами
- Интервальное повторение для эффективного запоминания
- Удаление карточек

## Установка и запуск

### Предварительные требования

- Python 3.8+
- Telegram Bot Token от [@BotFather](https://t.me/BotFather)
- PostgreSQL база данных

### Клонирование репозитория

```bash
git clone https://github.com/kamaqiyasov/TelegramBotEnglishCard.git
cd TelegramBotEnglishCard
```

### Установка зависимостей
```
pip install -r requirements.txt
```

### Быстрый старт

#### 1. Получите токен бота
- Напишите [@BotFather](https://t.me/BotFather) в Telegram
- Команда: `/newbot`
- Придумайте имя боту
- Получите токен (выглядит как `123456789:ABCdefGHIjklMnopQRstuVWXyz`)

#### 2. Настройте окружение
Создайте файл `.env` и заполните его (пример файла .env.example):

#### 3. Запуск бота
```
python -m src.main
```