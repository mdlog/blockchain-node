import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from app import app, db

def create_db_if_not_exists():
    """Create PostgreSQL database and user if they don't exist"""
    # Load environment variables
    load_dotenv()
    
    db_host = os.environ.get("PGHOST")
    db_port = os.environ.get("PGPORT", "5432")
    db_user = os.environ.get("PGUSER")
    db_pass = os.environ.get("PGPASSWORD")
    db_name = os.environ.get("PGDATABASE")

    try:
        # Connect to PostgreSQL server with SSL mode
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,  # Use provided user from environment
            password=db_pass,
            database="postgres",
            sslmode="require"  # Enable SSL mode
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Check if database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if not cur.fetchone():
            # Create database if not exists
            cur.execute(f"CREATE DATABASE {db_name}")
            print(f"Created database: {db_name}")

        # Switch connection to new database to set up permissions
        cur.close()
        conn.close()
        
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name,
            sslmode="require"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Grant privileges
        cur.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CURRENT_USER")
        print(f"Granted privileges in database {db_name}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error setting up database: {str(e)}")
        raise

def reset_database():
    """Reset and initialize the database with proper schema"""
    try:
        # Create database if it doesn't exist
        create_db_if_not_exists()
        
        with app.app_context():
            # Drop all tables and their data
            db.drop_all()
            db.session.commit()
            
            # Create all tables fresh
            db.create_all()
            db.session.commit()
            print("Database reset completed successfully!")
            
    except Exception as e:
        print(f"Error during database reset: {str(e)}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    reset_database()
