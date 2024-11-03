# Blockchain Node Deployment Guide

## Prerequisites
- Python 3.11+
- PostgreSQL database
- Git

## Environment Setup
1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` file with your configuration:
```env
# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here

# PostgreSQL Database Configuration
PGHOST=localhost
PGPORT=5432
PGUSER=your_username
PGPASSWORD=your_password
PGDATABASE=your_database_name

# Node Configuration (Optional)
NODE_ROLE=primary
NODE_PORT=5000
NODE_NAME=blockchain_node
PRIMARY_NODE=http://primary-node-address:5000
```

## Installation
1. Clone the repository:
```bash
git clone <repository-url>
cd blockchain-node
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python3 reset_db.py
```

4. Start the node:
```bash
python3 main.py
```

## Multi-Node Deployment Guide

### 1. Network Configuration

#### Primary Node Setup
1. Configure environment variables in `.env`:
```env
NODE_ROLE=primary
NODE_PORT=5000
NODE_NAME=primary_node
```

2. Update firewall rules:
```bash
sudo ufw allow 5000/tcp
```

#### Secondary Nodes Setup
1. Configure environment variables in `.env`:
```env
NODE_ROLE=secondary
NODE_PORT=5001  # Increment for each secondary node
NODE_NAME=secondary_node_1
PRIMARY_NODE=http://<primary-node-ip>:5000
```

2. Configure firewall:
```bash
sudo ufw allow 5001/tcp  # Match port with NODE_PORT
```

### 2. Node Synchronization Process

#### Starting Primary Node
1. Initialize primary node database:
```bash
python3 reset_db.py
```

2. Start primary node:
```bash
python3 main.py
```

#### Adding Secondary Nodes
1. Initialize secondary node database:
```bash
python3 reset_db.py
```

2. Register with primary node:
```bash
curl -X POST http://<primary-node>:5000/nodes/register \
     -H "Content-Type: application/json" \
     -d '{"nodes": ["http://<secondary-node>:5001"]}'
```

3. Start secondary node:
```bash
python3 main.py
```

### 3. Node Validation and Monitoring

#### Validation Requirements
- Minimum 3 active nodes required for consensus
- 67% of active nodes must agree for consensus
- Nodes considered inactive after 30 minutes without communication

#### Monitoring Node Status
1. Check node status:
- Visit `/monitor/status` for system statistics
- View `/explorer/validation-guide` for consensus status

2. Verify node synchronization:
```bash
curl http://<node-address>:5000/nodes/resolve
```

3. View primary node:
```bash
curl http://<node-address>:5000/nodes/primary
```

### 4. Troubleshooting

#### Common Issues
1. Node Connection Issues:
- Verify firewall settings
- Check PRIMARY_NODE address is correct
- Ensure database connection is working

2. Consensus Problems:
- Verify minimum node requirement (3 nodes)
- Check node synchronization status
- Validate network connectivity

3. Database Issues:
- Check .env configuration
- Verify PostgreSQL is running
- Ensure database exists and is accessible

#### Logs and Diagnostics
- Check logs in `logs/blockchain_node.log`
- Use monitoring dashboard at `/monitor/status`
- View validation status at `/explorer/validation-guide`

### 5. Security Best Practices

1. Network Security:
- Use HTTPS in production
- Implement proper firewall rules
- Regular security updates
- Strong database passwords

2. Node Authentication:
- Validate node identities
- Monitor for suspicious activities
- Regular audit of registered nodes

3. Data Protection:
- Regular database backups
- Secure environment variables
- Encrypt sensitive data

## Running the Node
The node will automatically:
- Initialize database tables if they don't exist
- Start the Flask server on configured port
- Enable monitoring endpoints
- Set up logging in the logs directory

### Monitoring
Available monitoring endpoints:
- `/monitor/status`: System and blockchain stats
- `/monitor/health`: Health check endpoint
- `/explorer/validation-guide`: Node validation status

### Logging
Logs are stored in `logs` directory:
- Maximum file size: 10MB
- Keeps last 5 log files
- Log format: `timestamp - name - level - message`
