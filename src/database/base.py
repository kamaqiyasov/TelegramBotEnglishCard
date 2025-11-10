from sqlalchemy import create_engine, Identity
from sqlalchemy.orm import declarative_base, sessionmaker, Mapped, mapped_column
from src.config import settings

Base = declarative_base()

engine = create_engine(
    url=settings.DATABASE_URL_psycopg,
    # echo=True
)
Session = sessionmaker(bind=engine)

class BaseModel(Base):
    __abstract__ = True
    __allow_unmapped__ = True

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)

def create_tables():
    from src.database.models import Word
    
    Base.metadata.create_all(engine)

    with Session() as session:
        if session.query(Word).count() == 0:
            add_sample_data(session)

def drop_tables():
    Base.metadata.drop_all(engine)

def add_sample_data(session):
    from src.database.models import Word
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

    for record in data:
        model = {
            'Word': Word,
        }[record.get('model')]
        session.add(model(id=record.get('pk'), **record.get('fields')))
        session.commit()