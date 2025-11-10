import json

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from settings import setting


SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://{}:{}@{}/{}?options=-c%20TimeZone=Asia%2FShanghai".format(
    setting.pg_user,
    setting.pg_password,
    setting.pg_host,
    setting.pg_db,
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_recycle=60 * 5, 
    pool_pre_ping=True,
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
    json_deserializer=lambda obj: json.loads(obj)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

