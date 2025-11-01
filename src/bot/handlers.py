import re
import textwrap
import random
from telebot import types

from src.bot.core import bot, MyStates, Command
from src.bot.queries import user_exists, get_random_others_word, add_user_word, get_random_word_for_user, delete_user_word

buttons = []

def create_cards(message, user_id, previous_word = None):
    """Выводим слово для конкретного клиента"""
    global buttons 
    buttons = []
    markup = types.ReplyKeyboardMarkup(row_width=2)
    word = get_random_word_for_user(user_id, previous_word)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['user_id'] = user_id
        data['word'] = word
    if not word:
        add_word_btn = types.KeyboardButton(Command.ADD_WORD)
        markup.add(add_word_btn)
        bot.send_message(message.chat.id, "У вас нет больше слов. Добавьте слово", reply_markup=markup)
        return False
    print(word)
    other_eng_words = get_random_others_word(user_id, word['rus'], 3)
    print(other_eng_words)
    if not other_eng_words:
        add_word_btn = types.KeyboardButton(Command.ADD_WORD)
        markup.add(add_word_btn)
        bot.send_message(message.chat.id, "У вас мало слов. Добавьте слово", reply_markup=markup)
        return False
    other_eng_words.append(word['eng'])
    other_words_btn = [types.KeyboardButton(word) for word in other_eng_words]
    buttons.extend(other_words_btn)
    random.shuffle(buttons)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_btn = types.KeyboardButton(Command.DELETE_WORD)
    next_btn = types.KeyboardButton(Command.NEXT)
    buttons.extend([next_btn, add_word_btn, delete_btn])
    markup.add(*buttons)
    bot.send_message(message.chat.id, f"Выбери перевод слова:\n🇷🇺 {word['rus']}", reply_markup=markup)

@bot.message_handler(commands=['cards', 'start'])
def start(message):    
    """Начало бота"""
    user_id, is_new = user_exists(message.from_user.id, message.from_user.username)
    if is_new:
        text = f"С возвращение {message.from_user.first_name}"
    else:
        text = textwrap.dedent(
            "Привет 👋 Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном для себя темпе.\n"
            "У тебя есть возможность использовать тренажёр, как конструктор, и собирать свою собственную базу для обучения. Для этого воспрользуйся инструментами:\n"
            "   добавить слово ➕,\n"
            "   удалить слово 🔙.\n"
            "Ну что, начнём ⬇️"
        )    
    bot.send_message(message.chat.id, text)
    create_cards(message, user_id)

@bot.message_handler(func=lambda message: message.text == Command.NEXT)
@bot.message_handler(func=lambda message: message.text == Command.CANCEL)
def next_cards(message):
    """Выводим следующее слово"""
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        user_id = data.get('user_id', False)
        previous_word = data.get('word')
    if not user_id:
        bot.send_message(message.chat.id, "Пропишите /start для начала работы:", reply_markup=types.ReplyKeyboardRemove())
        return False
    create_cards(message, user_id, previous_word)

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        user_id = data.get('user_id', False)
        word = data.get('word')
    
    if not user_id:
        bot.send_message(message.chat.id, "Пропишите /start для начала работы", reply_markup=types.ReplyKeyboardRemove())
        return False

    delete_user_word(user_id, word['rus'])
    bot.send_message(message.chat.id, f"Слово \"{word['rus']}\" удалено!")
    create_cards(message, user_id, word)

@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def handle_add_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        user_id = data.get('user_id', False)
    if not user_id:
        bot.send_message(message.chat.id, "Пропишите /start для начала работы:", reply_markup=types.ReplyKeyboardRemove())
        return False  
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(types.KeyboardButton(Command.CANCEL))
    bot.send_message(message.chat.id, "Напиши какое слово хотите добавить:", reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.wait_word, message.chat.id)

@bot.message_handler(state=MyStates.wait_translate)
def handle_wait_translate(message):
    word = message.text
    if len(word.split()) != 1:
        bot.send_message(message.chat.id, f"Укажите одно слово")
        bot.set_state(message.from_user.id, MyStates.wait_translate, message.chat.id)
        return False
    
    if not re.match(r'^[A-Za-z\-]+$', word):
        bot.send_message(message.chat.id, f"Укажите слово на английском")
        bot.set_state(message.from_user.id, MyStates.wait_translate, message.chat.id)
        return False
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        new_rus_word = data.get('new_rus_word')
        user_id = data.get('user_id')

    bot.delete_state(message.from_user.id, message.chat.id)
    word = word.strip().replace(" ", "")
    word = word.capitalize() if word else ""
    
    user_word_success, user_word_message = add_user_word(user_id, new_rus_word, word) 
    if user_word_success:
        bot.send_message(message.chat.id, f"{user_word_message}")
    else:
        bot.send_message(message.chat.id, f"{user_word_message}")
    
    create_cards(message, data['user_id'], data['word'])

@bot.message_handler(state=MyStates.wait_word)
def handle_wait_word(message):
    word = message.text.strip()
    
    if len(word.split()) != 1:
        bot.send_message(message.chat.id, f"Укажите одно слово")
        bot.set_state(message.from_user.id, MyStates.wait_word, message.chat.id)
        return False
    
    if not re.match(r'^[а-яА-ЯёЁ\-]+$', word):
        bot.send_message(message.chat.id, f"Укажите слово на русском")
        bot.set_state(message.from_user.id, MyStates.wait_word, message.chat.id)
        return False

    word = word.strip().replace(" ", "")
    word = word.capitalize() if word else ""
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['new_rus_word'] = word

    bot.send_message(message.chat.id, f"Укажите перевод слова {word}")
    bot.set_state(message.from_user.id, MyStates.wait_translate, message.chat.id)

@bot.message_handler(func=lambda message: True)
def message_reply(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:  
        user_id = data.get('user_id', False)
        word = data.get('word')
    if not user_id:
        bot.send_message(message.chat.id, "Для начала работы бота напишите /start", reply_markup=types.ReplyKeyboardRemove())
        return False
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    hint = ""
    if text == word['eng']:
        hint = f"Верный ответ!\n {word['rus']} -> {word['eng']}"
        bot.send_message(message.chat.id, hint, reply_markup=markup)
        bot.delete_state(message.from_user.id, message.chat.id)
        create_cards(message, user_id, word)
    else:
        for btn in buttons:
            if btn.text == text:
                if '❌' not in btn.text:
                    btn.text = text + '❌'
                break
        hint = f"Допущена ошибка!\n Попробуй ещё раз вспомнить слово 🇷🇺{word['rus']}"
        markup.add(*buttons)
        bot.send_message(message.chat.id, hint, reply_markup=markup)