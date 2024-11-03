import os
import psutil
import logging
from logging.handlers import RotatingFileHandler

# Deployment Configuration
class DeploymentConfig:
    # Flask Configuration
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'blockchain_secret')
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "max_overflow": 20
    }
    
    # Network Configuration
    HOST = "0.0.0.0"
    PORT = int(os.environ.get('NODE_PORT', 5000))
    
    # Node Configuration
    NODE_ROLE = os.environ.get('NODE_ROLE', 'primary')  # 'primary' or 'secondary'
    PRIMARY_NODE_ADDRESS = os.environ.get('PRIMARY_NODE', None)  # Required for secondary nodes
    NODE_NAME = os.environ.get('NODE_NAME', f'node_{PORT}')
    
    # Consensus Configuration
    MIN_NODES = 3
    CONSENSUS_THRESHOLD = 0.67  # 67% of nodes needed for consensus
    NODE_TIMEOUT = 1800  # 30 minutes timeout for inactive nodes
    
    # Logging Configuration
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = 'blockchain_node.log'
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    @classmethod
    def is_primary_node(cls):
        """Check if current node is primary"""
        return cls.NODE_ROLE.lower() == 'primary'
    
    @classmethod
    def validate_config(cls):
        """Validate node configuration"""
        if cls.NODE_ROLE.lower() not in ['primary', 'secondary']:
            raise ValueError("NODE_ROLE must be either 'primary' or 'secondary'")
            
        if cls.NODE_ROLE.lower() == 'secondary' and not cls.PRIMARY_NODE_ADDRESS:
            raise ValueError("PRIMARY_NODE address is required for secondary nodes")
            
        return True

def setup_logging(app):
    """Configure logging for the application"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    formatter = logging.Formatter(DeploymentConfig.LOG_FORMAT)
    
    file_handler = RotatingFileHandler(
        f"logs/{DeploymentConfig.LOG_FILE}",
        maxBytes=DeploymentConfig.LOG_MAX_SIZE,
        backupCount=DeploymentConfig.LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info(f'Blockchain node started - Role: {DeploymentConfig.NODE_ROLE}')

def get_system_stats():
    """Get system monitoring statistics"""
    return {
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        'connections': len(psutil.net_connections()),
        'boot_time': psutil.boot_time(),
        'node_role': DeploymentConfig.NODE_ROLE,
        'node_name': DeploymentConfig.NODE_NAME
    }

def get_node_config():
    """Get current node configuration details"""
    return {
        'role': DeploymentConfig.NODE_ROLE,
        'name': DeploymentConfig.NODE_NAME,
        'port': DeploymentConfig.PORT,
        'primary_node': DeploymentConfig.PRIMARY_NODE_ADDRESS,
        'is_primary': DeploymentConfig.is_primary_node(),
        'consensus_threshold': DeploymentConfig.CONSENSUS_THRESHOLD,
        'min_nodes': DeploymentConfig.MIN_NODES
    }
