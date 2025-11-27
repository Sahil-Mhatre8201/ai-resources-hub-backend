from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Get DATABASE_URL from environment variable
# Render automatically provides DATABASE_URL (internal URL) when you link the database to your service
# For local development, you can set DATABASE_URL in your .env file
# Note: Use INTERNAL URL when both services are on Render, EXTERNAL URL for local development
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:Sahil%402000@localhost/aihub"
)

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
