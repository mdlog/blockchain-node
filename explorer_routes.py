from flask import render_template, request, jsonify, redirect, url_for
from app import app, db
from models import Block, Transaction, Node
from datetime import datetime, timedelta
from consensus import ConsensusManager
from blockchain import Blockchain
from pbft_consensus import PBFTConsensus

blockchain = Blockchain()
consensus_manager = ConsensusManager(blockchain)
pbft = PBFTConsensus()

@app.route('/explorer')
def explorer_dashboard():
    # Get chain statistics
    current_block_height = Block.query.count()
    total_txns = Transaction.query.count()
    pending_blocks = Block.query.filter_by(validation_status='pending').count()
    invalid_blocks = Block.query.filter_by(validation_status='invalid').count()
    
    # Get node status information
    active_nodes = Node.query.filter(
        Node.last_seen >= datetime.utcnow() - timedelta(minutes=30)
    ).all()
    
    total_nodes = Node.query.count()
    active_node_count = len(active_nodes)
    
    # Calculate sync status
    sync_status = "Synced"
    if total_nodes > 1:  # Only check sync if we have peers
        consensus_manager.resolve_conflicts()  # Check for chain updates
        sync_status = "Syncing..." if consensus_manager.resolve_conflicts() else "Synced"
    
    # Get primary node
    primary_node = consensus_manager.pbft.get_primary_node()
    
    stats = {
        'chain_length': current_block_height,
        'total_transactions': total_txns,
        'active_nodes': active_node_count,
        'total_nodes': total_nodes,
        'sync_status': sync_status,
        'primary_node': primary_node.address if primary_node else 'None',
        'pending_blocks': pending_blocks,
        'invalid_blocks': invalid_blocks
    }
    
    # Get recent blocks and transactions
    recent_blocks = Block.query.order_by(Block.id.desc()).limit(5).all()
    recent_transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(5).all()
    
    return render_template('explorer.html',
                         stats=stats,
                         recent_blocks=recent_blocks,
                         recent_transactions=recent_transactions)

@app.route('/explorer/validation-guide')
def validation_guide():
    """Display the block validation guide and instructions"""
    network_status = pbft.get_network_status()
    return render_template('block_validation.html', network_status=network_status)

@app.route('/explorer/block/<int:block_id>')
def block_detail(block_id):
    block = Block.query.get_or_404(block_id)
    validation_errors = []
    if block.validation_status == 'invalid':
        pbft.validate_block(block)  # This will populate validation errors
        validation_errors = pbft.get_validation_errors()
    return render_template('block_detail.html', 
                         block=block,
                         validation_errors=validation_errors)

@app.route('/explorer/block/<int:block_id>/validate', methods=['POST'])
def validate_block(block_id):
    block = Block.query.get_or_404(block_id)
    
    # Only validate pending blocks
    if block.validation_status != 'pending':
        return jsonify({'message': 'Block is already validated'}), 400
    
    # Check network requirements first
    network_status = pbft.get_network_status()
    if not network_status['is_ready']:
        return jsonify({
            'message': f'Network requires minimum {network_status["min_nodes"]} active nodes for validation. ' +
                      f'Currently have {network_status["active_nodes"]} active nodes.'
        }), 400
    
    # Perform validation using PBFT consensus
    is_valid = pbft.validate_block(block)
    validation_errors = pbft.get_validation_errors()
    
    # Update block status
    block.validation_status = 'validated' if is_valid else 'invalid'
    block.validation_timestamp = datetime.utcnow()
    
    # Store validation errors if any
    if validation_errors:
        block.set_validation_errors([{'code': err.code, 'message': err.message} 
                                 for err in validation_errors])
    
    db.session.commit()
    
    if request.headers.get('Content-Type') == 'application/json':
        return jsonify({
            'status': block.validation_status,
            'timestamp': block.validation_timestamp.isoformat(),
            'errors': [{'code': err.code, 'message': err.message} 
                      for err in validation_errors] if validation_errors else []
        })
    
    return redirect(url_for('block_detail', block_id=block_id))

@app.route('/explorer/transaction/<int:tx_id>')
def transaction_detail(tx_id):
    transaction = Transaction.query.get_or_404(tx_id)
    return render_template('transaction_detail.html', transaction=transaction)

@app.route('/explorer/blocks')
def block_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = Block.query.order_by(Block.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    blocks = pagination.items
    return render_template('blocks.html',
                         blocks=blocks,
                         pagination=pagination)

@app.route('/explorer/transactions')
def transaction_list():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = Transaction.query.order_by(Transaction.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    transactions = pagination.items
    return render_template('transactions.html',
                         transactions=transactions,
                         pagination=pagination)
