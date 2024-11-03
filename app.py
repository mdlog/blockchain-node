import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "blockchain_secret"

# Construct database URL from environment variables if not provided directly
if not os.environ.get("DATABASE_URL"):
    db_user = os.environ.get("PGUSER")
    db_password = os.environ.get("PGPASSWORD")
    db_host = os.environ.get("PGHOST")
    db_port = os.environ.get("PGPORT")
    db_name = os.environ.get("PGDATABASE")
    
    if all([db_user, db_password, db_host, db_port, db_name]):
        os.environ["DATABASE_URL"] = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Get database URL and ensure proper format
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Convert URLs if they use deprecated postgres:// scheme
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    # Remove asyncpg if present
    if "postgresql+asyncpg://" in database_url:
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure SQLAlchemy pool settings
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 1800,
}

db.init_app(app)

def init_db():
    """Initialize database and create tables"""
    with app.app_context():
        import models  # Import models after db initialization
        db.create_all()  # Create all tables

# Only create tables if this file is run directly
if __name__ == "__main__":
    init_db()
