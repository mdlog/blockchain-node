from flask import jsonify, render_template
from app import app, db
from models import Block, Transaction, Node
from deployment_config import get_system_stats
from datetime import datetime, timedelta
import psutil

@app.route('/monitor/status')
def monitor_status():
    # Get system stats
    system_stats = get_system_stats()
    
    # Get blockchain stats
    blockchain_stats = {
        'total_blocks': Block.query.count(),
        'total_transactions': Transaction.query.count(),
        'last_block_time': Block.query.order_by(Block.timestamp.desc())
                          .first().timestamp if Block.query.first() else None
    }
    
    # Get node stats
    total_nodes = Node.query.count()
    active_nodes = Node.query.filter(
        Node.last_seen >= datetime.utcnow() - timedelta(minutes=30)
    ).count()
    
    node_stats = {
        'total_nodes': total_nodes,
        'active_nodes': active_nodes,
        'sync_status': 'synced' if active_nodes == total_nodes else 'syncing'
    }
    
    return render_template('monitor_status.html',
                         system_stats=system_stats,
                         blockchain_stats=blockchain_stats,
                         node_stats=node_stats)

@app.route('/monitor/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': _check_database(),
        'memory_usage': psutil.Process().memory_percent()
    })

def _check_database():
    """Check database connectivity"""
    try:
        db.session.execute('SELECT 1')
        return True
    except Exception:
        return False
