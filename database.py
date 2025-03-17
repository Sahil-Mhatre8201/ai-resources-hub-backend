from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# DATABASE_URL = "postgresql://postgres:Sahil%402000@localhost/aihub"
DATABASE_URL = "postgresql://ai_hub_database_user:VtPXWKaVFQNnw1mWvMMCyxwVMq7al0ue@dpg-cvbs1qofnakc73do2md0-a.oregon-postgres.render.com/ai_hub_database"

# Create database engine
engine = create_engine(DATABASE_URL)

# Create a session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
