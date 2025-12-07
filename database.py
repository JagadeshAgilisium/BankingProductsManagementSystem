from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

db_engine = create_engine(
    settings.DB_URL, 
    connect_args={"check_same_thread": False},
    echo=False
)

LocalSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

Base = declarative_base()

def obtain_db_session():
    dbSession = LocalSession()
    try:
        yield dbSession
    finally:
        dbSession.close()