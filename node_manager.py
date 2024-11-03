from flask import jsonify, request
from app import app, db
from models import Block, Transaction, Node
from blockchain import Blockchain
from consensus import ConsensusManager

with app.app_context():
    blockchain = Blockchain()
    consensus = ConsensusManager(blockchain)

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    
    if not nodes:
        return jsonify({'message': 'Please supply valid nodes'}), 400

    for node in nodes:
        consensus.register_node(node)

    primary_node = consensus.pbft.get_primary_node()
    return jsonify({
        'message': 'New nodes added', 
        'nodes': [n.address for n in Node.query.all()],
        'primary_node': primary_node.address if primary_node else None
    }), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus_route():
    replaced = consensus.resolve_conflicts()
    
    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': [b.to_dict() for b in Block.query.all()]
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': [b.to_dict() for b in Block.query.all()]
        }
    return jsonify(response), 200

@app.route('/nodes/primary', methods=['GET'])
def get_primary_node():
    primary = consensus.pbft.get_primary_node()
    return jsonify({
        'primary_node': primary.address if primary else None,
        'current_view': consensus.pbft.current_view
    }), 200

@app.route('/nodes/view-change', methods=['POST'])
def request_view_change():
    new_view = consensus.pbft.initiate_view_change()
    primary = consensus.pbft.get_primary_node()
    return jsonify({
        'message': 'View change initiated',
        'new_view': new_view,
        'new_primary': primary.address if primary else None
    }), 200

@app.route('/chain', methods=['GET'])
def get_chain():
    blocks = Block.query.all()
    chain = []
    for block in blocks:
        chain.append({
            'index': block.id,
            'timestamp': block.timestamp.isoformat(),
            'previous_hash': block.previous_hash,
            'hash': block.hash,
            'nonce': block.nonce,
            'transactions': [{
                'sender': tx.sender,
                'recipient': tx.recipient,
                'amount': tx.amount
            } for tx in block.transactions]
        })
    
    primary = consensus.pbft.get_primary_node()
    return jsonify({
        'chain': chain,
        'length': len(chain),
        'primary_node': primary.address if primary else None
    }), 200
