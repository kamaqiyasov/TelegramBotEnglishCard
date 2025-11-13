import requests
from telebot import TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

from src.config import settings

class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'
    CANCEL = 'Отмена ❌'

class MyStates(StatesGroup):
    target_word = State()
    wait_word = State()
    wait_translate = State()

state_storage = StateMemoryStorage()
bot = TeleBot(settings.TELEGRAM_TOKEN, state_storage=state_storage)
bot.add_custom_filter(custom_filters.StateFilter(bot))
print("Бот запущен!")