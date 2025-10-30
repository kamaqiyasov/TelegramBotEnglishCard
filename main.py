import random
import re
import textwrap
from sqlalchemy import func
from models import UserWord, Word, Session, add_sample_data, User
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

print("bot is Runing")

state_storage = StateMemoryStorage()
token_bot = "8353207320:AAE3F8bNYfyAudCFO6pJyJBxfg1NZX_es88"
bot = TeleBot(token_bot, state_storage=state_storage)

# add_sample_data() Запустить один раз

class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'
    CANCEL = 'Отмена ❌'

class MyStates(StatesGroup):
    target_word = State()
    wait_word = State()
    wait_translate = State()

def user_exists(telegram_id, telegram_username):
    """Проверяем есть ли такой пользователь"""
    with Session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(telegram_id = telegram_id, telegram_username = telegram_username)
            session.add(user)
            session.commit()            
            words = session.query(Word).filter(Word.is_main == True).all()        
            for word in words:
                user_word = UserWord(id_user=user.id, id_word=word.id)
                session.add(user_word)
            session.commit()
            return user.id, False
        return user.id, True

def get_word_for_user(user_id, previous_word):
    """Получаем все слова для конкретного клиента"""
    with Session() as session:
        if previous_word is None:
            user_words = session.query(UserWord).filter_by(id_user=user_id).all()            
        else:
            previous_word_ids = [id for (id,) in session.query(Word.id).filter(Word.rus == previous_word['rus']).all()] 
            user_words = session.query(UserWord).filter(UserWord.id_user == user_id, UserWord.id_word.notin_(previous_word_ids)).all()
        
        if user_words:
            user_word = random.choice(user_words)
            return {"rus": user_word.word.rus, "eng": user_word.word.eng}
        return False
        
def get_random_others_word(count, user_id, word):
    """Получаем рандомные английские слова без учета текущего слова"""
    with Session() as session:
        excluded_words = [eng for (eng,) in session.query(Word.eng).filter(Word.rus == word['rus']).all()]
        word_ids = [id_word for (id_word,) in session.query(UserWord.id_word).filter(UserWord.id_user == user_id).all()]
        print(word_ids)
        if len(word_ids) <= count:
            return False
        other_words = (session.query(Word)
                 .filter(Word.rus != word['rus'])
                 .filter(Word.id.in_(word_ids))
                 .filter(Word.eng.notin_(excluded_words))
                 .order_by(func.random())
                 .limit(count)
                 .all())
    return [word.eng for word in other_words]

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

def create_cards(message, user_id, previous_word = None):
    """Выводим слово для конкретного клиента"""
    global buttons 
    buttons = []
    markup = types.ReplyKeyboardMarkup(row_width=2)
    word = get_word_for_user(user_id, previous_word)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['user_id'] = user_id
        data['word'] = word
        print(f"{user_id=} {word=}")
    if not word:
        add_word_btn = types.KeyboardButton(Command.ADD_WORD)
        markup.add(add_word_btn)
        bot.send_message(message.chat.id, "У вас нет больше слов. Добавьте слово", reply_markup=markup)
        return False
    other_eng_words = get_random_others_word(3, user_id, word)
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

    with Session() as session:
        word_ids = [id for (id,) in session.query(Word.id).filter(Word.rus == word['rus']).all()]
        session.query(UserWord).filter(
            UserWord.id_user == user_id,
            UserWord.id_word.in_(word_ids)
        ).delete()        
        session.commit()
    bot.send_message(message.chat.id, f"Слово \"{word['rus']}\" удалено!")
    create_cards(message, user_id, word)

def add_new_word(user_id, rus, eng):
    """Добавить новое слово в базу"""
    with Session() as session:
        words = session.query(Word).filter(Word.rus == rus).order_by(Word.number.desc()).all()
        if not words:
            new_word = Word(rus=rus, eng=eng)
            session.add(new_word)
            session.flush()
            new_user_word =UserWord(id_user=user_id, id_word=new_word.id)
            session.add(new_user_word)
            session.commit()
            return True
        
        for word in words:
            if eng != word.eng:
                new_word = Word(rus=rus, eng=eng, number=words[0].number + 1)
                session.add(new_word)
                session.flush()
                new_user_word =UserWord(id_user=user_id, id_word=new_word.id)
                session.add(new_user_word)
                session.commit()
                return True  

            user_word_exists = session.query(UserWord).filter(UserWord.id_user == user_id, UserWord.id_word == word.id).first()
            if not user_word_exists:
                new_user_word = UserWord(id_user=user_id, id_word=word.id)
                session.add(new_user_word)
                session.commit()
                return True
        
        return False
        
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
    new_word = add_new_word(user_id, new_rus_word, word) 
    if new_word:
        bot.send_message(message.chat.id, f"Новое слово добавлено {new_rus_word} -> {word}")
    else:
        bot.send_message(message.chat.id, f"Такое слово уже существует")
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

bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)