from typing import Dict, List, Optional
from sqlalchemy import delete, func, exc, or_, select
from src.database.base import Session
from src.database.models import User, UserWord, Word

def get_user_words(user_id: int) -> Optional[list[tuple[str, str]]]:
    """Получает список слов пользователя в формате (русское, английское)

    Args:
        user_id (int): ID пользователя

    Returns:
        list[tuple[str, str]]: Список пар (русское слово, английское слово)
    """
    try:
        with Session() as session:
            stmt = (select(Word).join(UserWord, isouter=True).where(or_(UserWord.id_user == user_id, UserWord.id_user.is_(None))))
            words = session.scalars(stmt).all()
            
        return [(word.rus, word.eng) for word in words] if words else None
        
    except exc.SQLAlchemyError as e:
        return None

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
                        
        return user.id, False
    except exc.SQLAlchemyError as e:
        return None, False

def get_random_words(user_id: int, previous_word: str, limit: int = 4) -> Optional[List[Dict]]:
    """Получить рандомно определенное количество слов

    Args:
        user_id (int): Id пользователя
        previous_word (str): Предыдущее слово для исключения
        limit (int): Количество слов для возврата
    Returns:
        List[Dict]: Список слов в виде словарей
    """
    try:
        with Session() as session:
            stmt = (select(Word)
                    .join(UserWord, isouter=True)
                    .where(Word.rus != previous_word,
                        or_(UserWord.id_user == user_id, UserWord.id_user.is_(None)),)
                    .order_by(func.random())
                    .limit(limit))
            
            words = session.scalars(stmt).all()
        return [word.to_dict() for word in words] if words else None
    except exc.SQLAlchemyError as e:
        return None
    
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
        session.rollback()
        return False, error_msg

def _create_new_word(session, rus_word: str, eng_word: str, number: int = 1) -> Word:
    new_word = Word(rus=rus_word, eng=eng_word, number=number)
    session.add(new_word)
    session.flush()
    return new_word

def _create_user_word(session, user_id: int, word_id: int) -> bool:
    new_user_word = UserWord(id_user=user_id, id_word=word_id)
    session.add(new_user_word)
    return True
    
def delete_user_word(user_id: int, word: dict) -> bool:
    """Удаление слова пользователя
    Args:
        user_id (int): ID пользователя из базы
        word (dist): Словарь с информацией о слове

    Returns:
        bool: Возвращает True при удалении, иначе False
    """
    try:
        with Session() as session:

            stmt = select(UserWord).where(
                UserWord.id_user == user_id,
                UserWord.id_word == word['id']
            )
            user_word = session.scalar(stmt)
            if user_word:
                session.delete(user_word)
                word_conn_count = session.scalar(select(func.count(UserWord.id)).where(UserWord.id_word == word['id']))
                if word_conn_count == 0:
                    session.execute(delete(Word).where(Word.id == word['id']))
                
                session.commit()
                return True
            else:
                return False
        
    except exc.SQLAlchemyError as e:
        return False