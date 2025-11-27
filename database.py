from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Get DATABASE_URL from environment variable
# Render automatically provides DATABASE_URL (internal URL) when you link the database to your service
# For local development, you can set DATABASE_URL in your .env file
# Note: Use INTERNAL URL when both services are on Render, EXTERNAL URL for local development
DATABASE_URL = os.getenv("DATABASE_URL")

# Check if we're in production (on Render) and DATABASE_URL is missing
if not DATABASE_URL:
    # Check if we're likely on Render
    # Render sets RENDER=true or we can check for Render's deployment directory
    is_render = (
        os.getenv("RENDER") is not None 
        or os.path.exists("/opt/render")  # Render's deployment directory
    )
    if is_render:
        raise ValueError(
            "DATABASE_URL environment variable is not set! "
            "Please link your PostgreSQL database to your service in Render, "
            "or manually set DATABASE_URL in your service's environment variables."
        )
    else:
        # Local development fallback
        DATABASE_URL = "postgresql://postgres:Sahil%402000@localhost/aihub"
        print("⚠️  Using local database fallback. Set DATABASE_URL in .env for production database.")

# Log database connection (without password for security)
db_info = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "unknown"
print(f"📦 Connecting to database: ...@{db_info}")

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
