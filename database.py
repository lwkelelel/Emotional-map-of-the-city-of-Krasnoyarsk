from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = "sqlite:///emotions.db"

engine = create_engine(DATABASE_URL, echo=True)
db_session = scoped_session(sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
))

Base = declarative_base()
Base.query = db_session.query_property()