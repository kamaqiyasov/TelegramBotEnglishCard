import random
from sqlalchemy import func
from src.database.base import Session
from src.database.models import User, UserWord, Word

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

def delete_user_word(user_id, word):
    with Session() as session:
        word_ids = [id for (id,) in session.query(Word.id).filter(Word.rus == word['rus']).all()]
        session.query(UserWord).filter(
            UserWord.id_user == user_id,
            UserWord.id_word.in_(word_ids)
        ).delete()        
        session.commit()
    return True