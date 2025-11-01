import random
import logging
from sqlalchemy import func, exc, select
from src.database.base import Session
from src.database.models import User, UserWord, Word

logger = logging.getLogger(__name__)

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

def get_random_word_for_user(user_id: int, previous__rus_word: str):
    """Получить случайное слово для пользователя"""
    with Session() as session:
        previous__rus_word = 'Мир'
        if previous__rus_word is None:
            user_words = get_user_words(session, user_id)
        else:
            user_words = get_user_words(session, user_id)
            for user in  user_words:
                "ТУТ"
            # user_words1 = select(user_words)
            # print(user_words1)
            # session.execute(user_words1).scalars().all()
            
def get_user_words(session, user_id: int) -> UserWord:
    """Получить все слова пользователя

    Args:
        session (Session): Текущий session
        user_id (int): ID пользователя

    Returns:
        obj: Объект класса UserWord
    """
    user_words = (
        select(Word)
        .join(UserWord, UserWord.id_word == Word.id)
        .where(UserWord.id_user == user_id)
    )
    
    return session.scalars(user_words).all()

def get_random_others_word(user_id: int, rus_word: str, count: int = 3) -> list:
    """Получить случайные слова пользователя, исключая указанное русское слово

    Args:
    user_id (int): ID пользователя
    rus_word (str): Русское слово
    count (int): Количество случайных слов 
    
    Returns:
        list: Список случайных английских слов
    """
    try:
        with Session() as session:
            # Исключаем другие переводы для данного русского слова
            exclude_words = select(Word.eng).where(Word.rus == rus_word).scalar_subquery()
            
            subquery = (select(Word)
                        .join(UserWord, UserWord.id_word == Word.id)
                        .where(UserWord.id_user == user_id,
                               ~Word.eng.in_(exclude_words))
                        .distinct()
                        .subquery())
            
            stmt = (select(subquery.c.eng)
                    .order_by(func.random())
                    .limit(count))
        
            random_words = session.execute(stmt).scalars().all()

            if len(random_words) < count:
                return []
        
        return random_words
    
    except exc.SQLAlchemyError as e:
        logger.error(f"Ошибка базы: {e}")
        return []
    except Exception as e:
        logger.error(f"Ошибка при получении данных get_random_others_word: {e}")
        return []
        
def add_user_word(user_id: int, rus_word: str, eng_word: str) -> tuple[bool, str]:
    """Добавление слова в словарь пользователя

    Если слово с русским переводом уже существует, проверяет английский перевод.
    Если английский перевод отличается - создает новую версию слова.
    Если перевод совпадает - добавляет связь с пользователем.
    
    Args:
        user_id (int): ID пользователя
        rus_word (str): Русское слово
        eng_word (str): Английский перевод

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        with Session() as session:
            # Ищем существующие слова с таким русским переводом
            existing_words = session.query(Word).filter(Word.rus == rus_word).order_by(Word.number.desc()).all()

            if not existing_words:
                # Создаем новое слово
                word = _create_new_word(session, rus_word, eng_word)
                _create_user_word(session, user_id, word.id)
                session.commit()
                return True, "Слово успешно добавлено"
            
            # Проверяем существующие слова
            for word in existing_words:
                if eng_word != word.eng:
                    # Перевод отличается - создаем новую версию
                    word = _create_new_word(session, rus_word, eng_word, existing_words[0].number + 1)
                    _create_user_word(session, user_id, word.id)
                    session.commit()
                    return True, "Создана новая версия слова"
                
                # Переводы совпадают - проверяем связь с пользователем
                user_word_exists = session.query(UserWord).filter(UserWord.id_user == user_id, UserWord.id_word == word.id).first()
                if not user_word_exists:
                    # Создаем связь пользователь-слово
                    _create_user_word(session, user_id, word.id)
                    session.commit()
                    return True, "Слово добавлено в словарь"
            
            return False, "Слово уже существует в вашем словаре"
        
    except exc.SQLAlchemyError as e:
        error_msg = f"Ошибка базы данных: {e}"
        logger.error(error_msg)
        session.rollback()
        return False, error_msg
    except Exception as e:
        error_msg = f"Ошибка при добавлении слова add_user_word: {e}"
        logger.error(error_msg)
        return [False, error_msg]

def _create_new_word(session, rus_word: str, eng_word: str, number: int = 1) -> Word:
    new_word = Word(rus=rus_word, eng=eng_word, number=number)
    session.add(new_word)
    session.flush()
    logger.info(f"Создано новое слово ID {new_word.id}: '{new_word.rus}' -> '{new_word.eng}'")
    return new_word

def _create_user_word(session, user_id: int, word_id: int) -> bool:
    new_user_word = UserWord(id_user=user_id, id_word=word_id)
    session.add(new_user_word)
    logger.info(f"Добавлена связь: пользователь {user_id} -> слово {word_id}")
    return True
    
def delete_user_word(user_id: int, rus_word: str) -> bool:
    """Удаление всех слов из словаря пользователя с указанным русским словом

    Args:
        user_id (int): ID пользователя из базы
        rus_word (str): Русское слово для удаления

    Returns:
        bool: Возвращает True при удалении, иначе False
    """
    logger.info(f"Удаление слова '{rus_word}' для пользователя {user_id}")
    try:
        with Session() as session:
            word_ids = [id for (id,) in session.query(Word.id).filter(Word.rus == rus_word).all()]
            
            if not word_ids:
                logger.warning(f"Слово '{rus_word}' не найдено в базе")
                return False
            
            deleted_count = session.query(UserWord).filter(
                UserWord.id_user == user_id,
                UserWord.id_word.in_(word_ids)
            ).delete()       
            
            session.commit()
        
        logger.info(f"Удалено {deleted_count} записей. Слово '{rus_word}' для пользователя {user_id}")
        return True
    except exc.SQLAlchemyError as e:
        logger.error(f"Ошибка базы: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка в коде delete_user_word: {e}")
        return False