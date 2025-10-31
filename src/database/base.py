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
    Base.metadata.create_all(engine)

def drop_tables():
    Base.metadata.drop_all(engine)