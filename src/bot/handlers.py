import re
import textwrap
import random
import logging
from telebot import types
from src.bot.core import bot, MyStates, Command
from src.bot.queries import get_or_create_user, get_random_others_word, add_user_word, get_random_word_for_user, delete_user_word, get_user_words, update_word_learned

logger = logging.getLogger(__name__)

def create_cards(message, user_id, previous_word = ""):
    """Выводим слово для конкретного клиента"""
    try:
        markup = types.ReplyKeyboardMarkup(row_width=2)
        # Получаем случайное слово
        word = get_random_word_for_user(user_id, previous_word)
        # Устанавливаем состояние 
        bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)

        if not word:
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            markup.add(add_word_btn)
            bot.send_message(message.chat.id, "У вас нет больше слов. Добавьте слово", reply_markup=markup)
            return False
        
        # Получаем случайные неправильные варианты
        other_eng_words = get_random_others_word(user_id, word['rus'], 3)
        
        if not other_eng_words:
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            markup.add(add_word_btn)
            bot.send_message(message.chat.id, "У вас мало слов. Добавьте слово", reply_markup=markup)
            return False
        
        # Формируем кнопки из вариантов ответа
        answer_options = other_eng_words + [word['eng']]
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
            data['word'] = word
            data['word']['attempts'] = 1
        
        markup.add(*answer_buttons)
        # markup.add(next_btn, add_word_btn, delete_btn)
        
        bot.send_message(message.chat.id, f"Выбери перевод слова:\n🇷🇺 {word['rus']}", reply_markup=markup)
        
    except Exception as e:
        logger.error(f"Ошибка при выводе слов create_cards: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка. Попробуйте позже.")

@bot.message_handler(commands=['cards', 'start'])
def start(message):
    """Обработчик команд /start и /cards для начала работы с ботом."""
    try:
        # Создаем нового пользователя или находит существующего
        user_id, user_was_exist = get_or_create_user(message.from_user.id, message.from_user.username)

        if user_id is None:
            logger.error(f"Пользователь не добавлен")
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
          
    except Exception as e:
        logger.error(f"Ошибка в команде /start: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка. Попробуйте позже.")

@bot.message_handler(func=lambda message: message.text == Command.NEXT)
@bot.message_handler(func=lambda message: message.text == Command.CANCEL)
def next_cards(message):
    """Обработчик команд "Далее" или "Отмена" """
    try:
        # Получаем данные пользователя из временного хранилища
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            user_id = data.get('user_id', False)
            previous_word = data.get('word', '')
        
        if not user_id:
            logger.warning(f"Пользователь не добавлен")
            bot.send_message(message.chat.id, "Пропишите /start для начала работы:", reply_markup=types.ReplyKeyboardRemove())
            return
        
        create_cards(message, user_id, previous_word.get('rus', ''))
        
    except Exception as e:
        logger.error(f"Ошибка при next_cards: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при загрузке карточек")

@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    """Обработчик команды удаления слова из коллекции пользователя"""
    try:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            user_id = data.get('user_id', False)
            word = data.get('word', False)
        
        if not user_id:
            logger.warning(f"Пользователь не добавлен")
            bot.send_message(message.chat.id, "Пропишите /start для начала работы:", reply_markup=types.ReplyKeyboardRemove())
            return
        
        if not word.get('rus'):
            logger.warning(f"Ошибка при удалении слова. Не получилось взять слово из хранилища")
            bot.send_message(message.chat.id, "Не удалось определить слово для удаления")
            create_cards(message, user_id)
            return
            
        success = delete_user_word(user_id, word.get('rus'))
        if success:
            response_text = f"Слово \"{word.get('rus', '')}\" удалено!"
        else:
            response_text = f"Ошибка при удалении слова \"{word.get('rus', '')}\" "

        bot.send_message(message.chat.id, response_text)    
        create_cards(message, user_id, word.get('rus'))
        
    except Exception as e:
        logger.error(f"Ошибка при delete_word: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при удалении карточки")

@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    """Обработчик команды добавления нового слова в коллекцию пользователя."""
    try:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            user_id = data.get('user_id', False)
        
        if not user_id:
            logger.warning(f"Пользователь не добавлен")
            bot.send_message(message.chat.id, "Пропишите /start для начала работы:", reply_markup=types.ReplyKeyboardRemove())
            return
        
        # Добавляем кнопку отмена
        markup = types.ReplyKeyboardMarkup(row_width=2)
        markup.add(types.KeyboardButton(Command.CANCEL))
        
        bot.send_message(message.chat.id, "Напишите какое слово хотите добавить:", reply_markup=markup)
        # Ждем слова на русском
        bot.set_state(message.from_user.id, MyStates.wait_word, message.chat.id)
        
    except Exception as e:
        logger.error(f"Ошибка при add_word: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при добавлении слова")
            
@bot.message_handler(state=MyStates.wait_translate)
def handle_wait_translate(message):
    """Обработчик ввода перевода на английском"""
    try:
        word = message.text
        
        if len(word.split()) != 1:
            bot.send_message(message.chat.id, f"Укажите одно слово")
            bot.set_state(message.from_user.id, MyStates.wait_translate, message.chat.id)
            return
    
        if not re.match(r'^[A-Za-z\-]+$', word):
            bot.send_message(message.chat.id, f"Укажите слово на английском")
            bot.set_state(message.from_user.id, MyStates.wait_translate, message.chat.id)
            return
        
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            new_rus_word = data.get('new_rus_word')
            user_id = data.get('user_id')

        bot.delete_state(message.from_user.id, message.chat.id)
        word = word.strip().replace(" ", "")
        word = word.capitalize() if word else ""
        
        user_word_success, user_word_message = add_user_word(user_id, new_rus_word, word)
        bot.send_message(message.chat.id, f"{user_word_message}")
        if user_word_success:
            user_words = get_user_words(user_id)
            count_words_text = f"Сейчас вы изучаете {len(user_words)} слов"
            bot.send_message(message.chat.id, count_words_text)
        create_cards(message, data['user_id'], data['word']['rus'])
        
    except Exception as e:
        logger.error(f"Ошибка при add_word: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при добавлении слова")

@bot.message_handler(state=MyStates.wait_word)
def handle_wait_word(message):
    """Обработчик ввода слова на русском"""
    try:
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
            
    except Exception as e:
        logger.error(f"Ошибка при handle_wait_word: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при обработке русского слова")

@bot.message_handler(func=lambda message: True)
def message_reply(message):
    """Обработчик основного взаимодействия с пользователем"""
    try:
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:  
            user_id = data.get('user_id', False)
            word = data.get('word', [])
            buttons = data.get('buttons', [])
            
        if not user_id:
            bot.send_message(message.chat.id, "Для начала работы бота напишите /start", reply_markup=types.ReplyKeyboardRemove())
            return 
        
        if not word:
            bot.send_message(message.chat.id, "Сессия завершена. Начните заново /start")
            bot.delete_state(message.from_user.id, message.chat.id)
            return
        
        word_attempts = int(word['attempts'])
        logger.info(f"Слово {word['userword_id']}:{word['rus']}, попытка номер {word_attempts}")
        text = message.text.replace('❌', '').strip()
        if text.lower() == word['eng'].lower():
            hint = f"Верный ответ!\n {word['rus']} -> {word['eng']}"
            bot.send_message(message.chat.id, hint, reply_markup=types.ReplyKeyboardRemove())
            bot.delete_state(message.from_user.id, message.chat.id)
            
            # Если угадывает со 2 попытки, то слово изучено 
            if word_attempts <= 2:
                update_word_learned(word.get('userword_id'), True)
            
            create_cards(message, user_id, word['rus'])
        else:
            updated_buttons = []
            word_attempts += 1
            for btn in buttons:
                btn_text = btn.text
                clean_text = btn_text
                if btn_text.lower() == text.lower():
                    updated_buttons.append(types.KeyboardButton(clean_text + ' ❌'))
                else:
                    updated_buttons.append(types.KeyboardButton(clean_text))
                
                # Если угадывает со 2 попытки, то слово не изучено 
                if word_attempts >= 2:
                    update_word_learned(word.get('userword_id'), False)
                
            with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
                data['buttons'] = updated_buttons
                data['word']['attempts'] = word_attempts
                
            markup = types.ReplyKeyboardMarkup(row_width=2)
            markup.add(*updated_buttons)

            hint = f"Допущена ошибка!\n Попробуй ещё раз вспомнить слово 🇷🇺{word['rus']}"
            bot.send_message(message.chat.id, hint, reply_markup=markup)
            
    except Exception as e:
        logger.error(f"Ошибка в message_reply для пользователя {message.from_user.id}: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка. Попробуйте снова /start")