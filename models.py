from sqlalchemy import ForeignKey, Integer, String, create_engine, Boolean, BigInteger, Identity, create_engine
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column, sessionmaker
from config import settings

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

class User(BaseModel):
    __tablename__ = "user"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_username: Mapped[str] = mapped_column(String, nullable=True)

    userword: Mapped[list["UserWord"]] = relationship("UserWord", back_populates="user", cascade="all, delete-orphan")

    word: Mapped[list["Word"]] = relationship(
        "Word",
        secondary="userword",
        back_populates="user",
        viewonly=True
    )

class UserWord(BaseModel):
    __tablename__ = "userword"

    id_user: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    id_word:Mapped[int] = mapped_column(ForeignKey("word.id"), nullable=False)
    learned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempt_word: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="userword")
    word: Mapped["Word"] = relationship("Word", back_populates="userword")

class Word(BaseModel):
    __tablename__ = "word"
    
    rus: Mapped[str] = mapped_column(nullable=False) 
    eng: Mapped[str] = mapped_column(nullable=False)
    number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    userword: Mapped[list["UserWord"]] = relationship("UserWord", back_populates="word", cascade="all, delete-orphan")

    user: Mapped[list["User"]] = relationship(
        "User",
        secondary="userword",
        back_populates="word",
        viewonly=True
    )

    def __repr__(self):
        return f"{self.id}: {self.rus} -> {self.eng} [{self.number}]"

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

# Base.metadata.drop_all(engine) Запустить один раз
Base.metadata.create_all(engine)