from app import app, db
from deployment_config import DeploymentConfig, setup_logging
from models import Node
from datetime import datetime
import os
from reset_db import create_db_if_not_exists

if __name__ == "__main__":
    try:
        # Create database and user if they don't exist
        create_db_if_not_exists()
        
        # Load deployment configuration
        app.config.from_object(DeploymentConfig)
        
        # Setup logging
        setup_logging(app)
        
        with app.app_context():
            from node_manager import *
            from wallet_routes import *
            from explorer_routes import *
            from contract_routes import *
            from monitoring_routes import *
            
            # Create tables if they don't exist
            db.create_all()
            
            # Register current node automatically
            host = os.environ.get('REPL_SLUG', 'localhost')
            port = DeploymentConfig.PORT
            current_node_address = f"{host}:{port}"
            
            node = Node.query.filter_by(address=current_node_address).first()
            if not node:
                node = Node(address=current_node_address)
                db.session.add(node)
            node.last_seen = datetime.utcnow()
            db.session.commit()
            
            # Start the server
            app.run(
                host=DeploymentConfig.HOST,
                port=DeploymentConfig.PORT
            )
    except Exception as e:
        print(f"Error during startup: {str(e)}")
        raise
