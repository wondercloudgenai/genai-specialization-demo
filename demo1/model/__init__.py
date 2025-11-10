from sqlalchemy import text

from model.database import engine, Base, SessionLocal
from model.model_cvinfo import *
from model.model_jobdata import *
from model.model_user import *
from model.model_interview_evaluation import *

with SessionLocal() as session:
    print("创建Postgresql Extension Vector")
    session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    session.commit()
Base.metadata.create_all(bind=engine)
