import re
import textwrap
import random
from telebot import types
from src.bot.core import bot, MyStates, Command
from src.bot.queries import get_or_create_user, add_user_word, delete_user_word, get_random_words, get_user_words

def create_cards(message, user_id, previous_word = ""):
    """Выводим слово для конкретного клиента"""
    markup = types.ReplyKeyboardMarkup(row_width=2)
    # Получаем случайное слово
    words = get_random_words(user_id, previous_word)

    if not words:
        add_word_btn = types.KeyboardButton(Command.ADD_WORD)
        markup.add(add_word_btn)
        bot.send_message(message.chat.id, "Слова не найдены, попробуйте добавить слово", reply_markup=markup)
        return False
    
    # Устанавливаем состояние
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    
    # Формируем кнопки из вариантов ответа
    current_word = random.choice(words)
    answer_options = [word['eng'] for word in words]    
    answer_buttons = [types.KeyboardButton(str(word_text)) for word_text in answer_options]
    random.shuffle(answer_buttons)
    
    # Формируем кнопки действий
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_btn = types.KeyboardButton(Command.DELETE_WORD)
    next_btn = types.KeyboardButton(Command.NEXT)
    answer_buttons.extend([next_btn, add_word_btn, delete_btn])
    
    # Сохраняем данные в состоянии для использования в обработчике
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['buttons'] = answer_buttons
        data['user_id'] = user_id
        data['current_word'] = current_word
    
    markup.add(*answer_buttons)
    
    bot.send_message(message.chat.id, f"Выбери перевод слова:\n🇷🇺 {current_word['rus']}", reply_markup=markup)


@bot.message_handler(commands=['cards', 'start'])
def start(message):
    """Обработчик команд /start и /cards для начала работы с ботом."""
    # Создаем нового пользователя или находит существующего
    user_id, user_was_exist = get_or_create_user(message.from_user.id, message.from_user.username)

    if user_id is None:
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте позже")
        return

    if user_was_exist:
        text = f"С возвращением, {message.from_user.first_name}"
    else:
        text = textwrap.dedent(
            "Привет 👋 Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном для себя темпе.\n"
            "У тебя есть возможность использовать тренажёр, как конструктор, и собирать свою собственную базу для обучения. Для этого воспользуйся инструментами:\n"
            "   добавить слово ➕,\n"
            "   удалить слово 🔙.\n"
            "Ну что, начнём ⬇️")
    
    bot.send_message(message.chat.id, text)
    create_cards(message, user_id)

@bot.message_handler(func=lambda message: message.text == Command.NEXT)
@bot.message_handler(func=lambda message: message.text == Command.CANCEL)
def next_cards(message):
    """Обработчик команд "Далее" и "Отмена" """
    # Получаем данные пользователя из временного хранилища
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        user_id = data.get('user_id', False)
        previous_word = data.get('current_word', False)
    
    if not user_id:
        bot.send_message(message.chat.id, "Пропишите /start для начала работы", reply_markup=types.ReplyKeyboardRemove())
        return
    
    if not previous_word:
        bot.send_message(message.chat.id, "Что то пошло не так! Пропишите /start для начала работы", reply_markup=types.ReplyKeyboardRemove())
        return
    
    create_cards(message, user_id, previous_word['rus'])

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    """Обработчик команды удаления слова из коллекции пользователя"""
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        user_id = data.get('user_id', False)
        current_word = data.get('current_word', False)
    
    if not user_id:
        bot.send_message(message.chat.id, "Пропишите /start для начала работы:", reply_markup=types.ReplyKeyboardRemove())
        return
    
    if not current_word:
        bot.send_message(message.chat.id, "Не удалось определить слово для удаления")
        create_cards(message, user_id)
        return
        
    success = delete_user_word(user_id, current_word)
    if success:
        response_text = f"Слово \"{current_word.get('rus', '')}\" удалено!"
    else:
        response_text = f"Слово \"{current_word.get('rus', '')}\" является базовым. Его нельзя удалить!"

    bot.send_message(message.chat.id, response_text)
    create_cards(message, user_id, current_word.get('rus'))
        
@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    """Обработчик команды добавления нового слова в коллекцию пользователя."""
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        user_id = data.get('user_id', False)
    
    if not user_id:
        bot.send_message(message.chat.id, "Пропишите /start для начала работы", reply_markup=types.ReplyKeyboardRemove())
        return
    
    # Добавляем кнопку отмена
    markup = types.ReplyKeyboardMarkup(row_width=2)
    markup.add(types.KeyboardButton(Command.CANCEL))
    
    bot.send_message(message.chat.id, "Напишите какое слово хотите добавить:", reply_markup=markup)
    # Ждем слова на русском
    bot.set_state(message.from_user.id, MyStates.wait_word, message.chat.id)
            
@bot.message_handler(state=MyStates.wait_translate)
def handle_wait_translate(message):
    """Обработчик ввода перевода на английском"""
    word_translation = message.text 
    if len(word_translation.split()) != 1:
        bot.send_message(message.chat.id, f"Укажите одно слово")
        bot.set_state(message.from_user.id, MyStates.wait_translate, message.chat.id)
        return

    if not re.match(r'^[A-Za-z\-]+$', word_translation):
        bot.send_message(message.chat.id, f"Укажите слово на английском")
        bot.set_state(message.from_user.id, MyStates.wait_translate, message.chat.id)
        return
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        new_rus_word = data.get('new_rus_word')
        user_id = data.get('user_id')

    bot.delete_state(message.from_user.id, message.chat.id)
    word_translation = word_translation.strip().replace(" ", "")
    word_translation = word_translation.capitalize() if word_translation else ""
    
    user_word_success, user_word_message = add_user_word(user_id, new_rus_word, word_translation)
    bot.send_message(message.chat.id, user_word_message)
    if user_word_success:
        user_words = get_user_words(user_id)
        if user_words:
            count_words_text = f"Сейчас вы изучаете {len(user_words)} слов"
            bot.send_message(message.chat.id, count_words_text)
    create_cards(message, user_id, new_rus_word)

@bot.message_handler(state=MyStates.wait_word)
def handle_wait_word(message):
    """Обработчик ввода слова на русском"""
    word = message.text.strip() 
    if len(word.split()) != 1:
        bot.send_message(message.chat.id, f"Укажите одно слово")
        bot.set_state(message.from_user.id, MyStates.wait_word, message.chat.id)
        return

    if not re.match(r'^[а-яА-ЯёЁ\-]+$', word):
        bot.send_message(message.chat.id, f"Укажите слово на русском")
        bot.set_state(message.from_user.id, MyStates.wait_word, message.chat.id)
        return

    word = word.strip().replace(" ", "")
    word = word.capitalize() if word else ""
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['new_rus_word'] = word

    bot.send_message(message.chat.id, f"Укажите перевод слова {word}")
    bot.set_state(message.from_user.id, MyStates.wait_translate, message.chat.id)

@bot.message_handler(func=lambda message: True)
def message_reply(message):    
    """Обработчик основного взаимодействия с пользователем"""
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:  
        user_id = data.get('user_id', False)
        current_word = data.get('current_word', [])
        buttons = data.get('buttons', [])
        
    if not user_id:
        bot.send_message(message.chat.id, "Для начала работы бота напишите /start", reply_markup=types.ReplyKeyboardRemove())
        return 
    
    if not current_word:
        bot.send_message(message.chat.id, "Сессия завершена. Начните заново /start")
        bot.delete_state(message.from_user.id, message.chat.id)
        return
    
    text = message.text.replace('❌', '').strip()
    
    if text.lower() == current_word['eng'].lower():
        hint = f"Верный ответ!\n {current_word['rus']} -> {current_word['eng']}"
        bot.send_message(message.chat.id, hint, reply_markup=types.ReplyKeyboardRemove())
        bot.delete_state(message.from_user.id, message.chat.id)    

        create_cards(message, user_id, current_word['rus'])
    else:
        updated_buttons = []
        for btn in buttons:
            btn_text = btn.text
            clean_text = btn_text
            if btn_text.lower() == text.lower():
                updated_buttons.append(types.KeyboardButton(clean_text + ' ❌'))
            else:
                updated_buttons.append(types.KeyboardButton(clean_text))
            
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['buttons'] = updated_buttons
            
        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add(*updated_buttons)

        hint = f"Допущена ошибка!\n Попробуй ещё раз вспомнить слово 🇷🇺{current_word['rus']}"
        bot.send_message(message.chat.id, hint, reply_markup=markup)