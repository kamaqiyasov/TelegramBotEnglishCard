from src.database.base import Session
from src.database.models import Word

def add_sample_data():
    data = [
        {"model": "Word", "fields": {"rus": "Мир", "eng": "Peace", "is_main": True, "number": 1}},
        {"model": "Word", "fields": {"rus": "Мир", "eng": "World", "is_main": False, "number": 3}},
        {"model": "Word", "fields": {"rus": "Мир", "eng": "Universe", "is_main": True, "number": 2}},
        {"model": "Word", "fields": {"rus": "Покой", "eng": "Peace", "is_main": True}},
        {"model": "Word", "fields": {"rus": "Солнце", "eng": "Sun", "is_main": True}},
        {"model": "Word", "fields": {"rus": "Телефон", "eng": "Phone", "is_main": True}},
        {"model": "Word", "fields": {"rus": "Мышь", "eng": "Mouse", "is_main": True}},
        {"model": "Word", "fields": {"rus": "Кнопка", "eng": "Button", "is_main": True}},
        {"model": "Word", "fields": {"rus": "Ручка", "eng": "Pen", "is_main": True}},
        {"model": "Word", "fields": {"rus": "Шоколад", "eng": "Chocolate", "is_main": True}},
        {"model": "Word", "fields": {"rus": "Кружка", "eng": "Cup", "is_main": True}},
        {"model": "Word", "fields": {"rus": "Часы", "eng": "Watch", "is_main": True}},
        {"model": "Word", "fields": {"rus": "Сыр", "eng": "Cheese", "is_main": True}},
    ]

    with Session() as session:
        for record in data:
            model = {
                'Word': Word,
            }[record.get('model')]
            session.add(model(id=record.get('pk'), **record.get('fields')))
            session.commit()