import random
import logging
from typing import Any, Dict, Optional
from sqlalchemy import and_, delete, func, exc, select
from src.database.base import Session
from src.database.models import User, UserWord, Word

logger = logging.getLogger(__name__)

def get_user_words(user_id: int) -> list[tuple[str, str]] | bool:
    """Получает список слов пользователя в формате (русское, английское)

    Args:
        user_id (int): ID пользователя

    Returns:
        llist[tuple[str, str]]: Список пар (русское слово, английское слово)
        bool: False в случае ошибки
    """
    try:
        with Session() as session:
            user_words = session.execute(select(Word.rus, Word.eng)
                                         .join(UserWord, UserWord.id_word == Word.id)
                                         .where(UserWord.id_user == user_id)
                                         ).all()
            if user_words:
                user_word_list = [(user_word.rus, user_word.eng) for user_word in user_words]
                session.commit()
                
                return user_word_list
            else:
                logger.warning(f"Список слов пуст для {user_id}")
                return False
        
    except exc.SQLAlchemyError as e:
        logger.error(f"Ошибка базы: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при получении всех слов get_user_words: {e}")
        return False

def update_word_learned(userword_id: int, learned: bool) -> bool:
    """Обновляет статус изучения слова пользователя

    Args:
        userword_id (int): D связи пользователь-слово для обновления
        learned (bool): Новый статус изучения слова 

    Returns:
        bool: True при успешном обновлении, False при ошибке
    """
    try:
        with Session() as session:
            
            user_word = session.query(UserWord).get(userword_id)
            if not user_word:
                logger.warning(f"Запись UserWord с id {userword_id} не найдена")
                return False
                
            user_word.learned = learned
            session.commit()
        
        return True
    
    except exc.SQLAlchemyError as e:
        logger.error(f"Ошибка базы: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка при обновлении статистики mark_attempt_result: {e}")
        return False

def get_or_create_user(telegram_id: int, telegram_username: str) -> tuple[Optional[int], bool]:
    """Проверка на пользователя

    Args:
    telegram_id (int): Telegram id пользователя
    telegram_username (str): Ник пользователя
    
    Returns:
        tuple[int, bool]: Кортеж где:
            - int: ID пользователя в базе или None при ошибке
            - bool: True если пользователь существовал, False если создан новый
    """
    try:
        with Session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                return user.id, True

            user = User(telegram_id = telegram_id, telegram_username = telegram_username)
            session.add(user)
            session.commit()
                    
            words = session.query(Word).filter(Word.is_main == True).all()        
            for word in words:
                user_word = UserWord(id_user=user.id, id_word=word.id)
                session.add(user_word)
            
            session.commit()
            logger.info(f"Добавлен новый пользователь ID: {user.id}, Telegram_ID: {telegram_id}, Username: {telegram_username}")
            
            return user.id, False
    except exc.SQLAlchemyError as e:
        logger.error(f"Ошибка базы: {e}")
        return None, False
    except Exception as e:
        logger.error(f"Ошибка при получении данных get_random_word_for_user: {e}")
        return None, False

def get_random_word_for_user(user_id: int, previous_word: str) -> Optional[Dict[str, Any]]:
    """Получить случайное слово для пользователя
    
    Args:
    user_id (int): ID пользователя
    previous_word (str): Предыдущее русское слово
    
    Returns:
        Optional[dict]: Словарь с данными слова если найдено, иначе None
    """
    try:
        with Session() as session:
            stmt = (
                select(Word, UserWord)
                .join(UserWord, UserWord.id_word == Word.id)
                .where(UserWord.id_user == user_id,
                       Word.rus != previous_word,
                       UserWord.learned == False))
            
            words = session.execute(stmt).all()
            
            # Берем любые слова, если все изучено
            if not words:
                logger.info(f"Все слова изучены для пользователя {user_id}, берем любые слова")
                stmt = (
                    select(Word, UserWord)
                    .join(UserWord, UserWord.id_word == Word.id)
                    .where(UserWord.id_user == user_id,
                        Word.rus != previous_word))
                
                words = session.execute(stmt).all()
            
            if not words:
                logger.warning(f"Нет доступных слов для пользователя {user_id}")
                return None
            
            top_words = words[:min(10, len(words))]
            random_word, user_word = random.choice(top_words)
            
            # user_word.attempt_word += 1
            session.commit()
        
            return {"rus": random_word.rus, "eng": random_word.eng, "userword_id": user_word.id}
        
    except exc.SQLAlchemyError as e:
        logger.error(f"Ошибка базы: {e}")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении данных get_random_word_for_user: {e}")
        return None
    
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
                        .distinct(Word.eng)
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
    logger.info(f"Удаление слова {rus_word}")
    try:
        with Session() as session:
            
            # Находим все id слов с этим русским словом
            all_word_ids = session.execute(
                select(Word.id)
                .where(Word.rus == rus_word)
                ).scalars().all()
    
            # Удаляем связи конкретного пользователя с этими словами из UserWord
            session.execute(
                delete(UserWord).where(
                    and_(UserWord.id_user == user_id,
                         UserWord.id_word.in_(all_word_ids))))              
            logger.info(f"Связи пользователя {user_id} со словом {rus_word} удалены")
            
            # Находим неосновные слова для удаления из Word
            non_main_word = session.execute(
                select(Word).where(
                    and_(Word.rus == rus_word,
                         Word.is_main == False))
                ).scalars().all()
            
            for word in non_main_word:
                # Проверяем связь слова с другими пользователями 
                other_connections = session.execute(
                    select(UserWord).where(UserWord.id_word == word.id).limit(1)
                    ).first()

                if not other_connections:
                    session.execute(delete(Word).where(Word.id == word.id))
                    logger.info(f"Слово {rus_word} пользователя {user_id} удалено")
                
            session.commit()
            return True
        
    except exc.SQLAlchemyError as e:
        logger.error(f"Ошибка базы: {e}")
        return False
    except Exception as e:
        logger.error(f"Ошибка в коде delete_user_word: {e}")
        return False