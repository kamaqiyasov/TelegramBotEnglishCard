from sqlalchemy import ForeignKey, Integer, String, Boolean, BigInteger
from sqlalchemy.orm import relationship, Mapped, mapped_column
from src.database.base import BaseModel

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
    
    def to_dict(self):
        return {
            'id': self.id,
            'rus': self.rus,
            'eng': self.eng,
            'number': self.number,
            'is_main': self.is_main,
        }