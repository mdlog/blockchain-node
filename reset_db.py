import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from app import app, db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_db_if_not_exists():
    """Create PostgreSQL database and user if they don't exist"""
    # Load environment variables
    load_dotenv()
    
    db_host = os.environ.get("PGHOST")
    db_port = os.environ.get("PGPORT", "5432")
    db_user = os.environ.get("PGUSER")
    db_pass = os.environ.get("PGPASSWORD")
    db_name = os.environ.get("PGDATABASE")

    if not all([db_host, db_port, db_user, db_pass, db_name]):
        raise ValueError("Missing required database configuration. Please check environment variables.")

    try:
        # Connect to default database first
        logger.info("Connecting to PostgreSQL server...")
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database="postgres",
            sslmode="prefer"  # Allow SSL but don't require it for local connections
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Check if database exists
        logger.info(f"Checking if database {db_name} exists...")
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cur.fetchone()
        
        if not exists:
            logger.info(f"Creating database {db_name}...")
            # Close existing connections to the database if it exists
            cur.execute("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = %s
                AND pid <> pg_backend_pid()
            """, (db_name,))
            
            # Create database
            cur.execute(f"CREATE DATABASE {db_name}")
            logger.info(f"Database {db_name} created successfully")

        # Close first connection
        cur.close()
        conn.close()

        # Connect to the target database to set up permissions
        logger.info(f"Connecting to {db_name} to configure permissions...")
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name,
            sslmode="prefer"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Grant necessary privileges
        logger.info("Setting up database privileges...")
        cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}")
        cur.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CURRENT_USER")
        cur.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO CURRENT_USER")
        logger.info("Database privileges configured successfully")

        cur.close()
        conn.close()
        logger.info("Database setup completed successfully")

    except psycopg2.Error as e:
        logger.error(f"PostgreSQL Error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database setup: {e}")
        raise

def reset_database():
    """Reset and initialize the database with proper schema"""
    try:
        # Create database if it doesn't exist
        create_db_if_not_exists()
        
        # Use Flask application context
        with app.app_context():
            logger.info("Dropping all existing tables...")
            db.drop_all()
            db.session.remove()  # Clear any existing sessions
            
            logger.info("Creating all tables...")
            db.create_all()
            db.session.commit()
            logger.info("Database reset completed successfully!")
            
    except Exception as e:
        logger.error(f"Error during database reset: {e}")
        db.session.rollback()
        raise

if __name__ == "__main__":
    reset_database()
