from src import LOGGER, DATABASE_URL
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from sqlalchemy_utils import database_exists

LOGGER.info("Database URL: {}".format(DATABASE_URL))

def initialise_engine() -> scoped_session:
    global engine
    engine = create_engine(DATABASE_URL, echo=False)
    BASE.metadata.bind = engine
    BASE.metadata.create_all(engine)
    return scoped_session(sessionmaker(bind=engine, autoflush=False))

BASE = declarative_base()
SESSION = initialise_engine()