import requests
from app import db
from models import Block, Node, Transaction
from datetime import datetime, timedelta
from pbft_consensus import PBFTConsensus

class ConsensusManager:
    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.pbft = PBFTConsensus()

    def register_node(self, address):
        """Register a new node in the network"""
        node = Node.query.filter_by(address=address).first()
        if not node:
            node = Node(address=address)
            db.session.add(node)
        node.last_seen = datetime.utcnow()
        db.session.commit()

        # Update PBFT primary if needed
        if Node.query.count() == 1:  # First node becomes primary
            self.pbft._update_primary()

    def remove_stale_nodes(self):
        """Remove nodes that haven't been seen recently"""
        stale_threshold = datetime.utcnow() - timedelta(minutes=30)
        stale_nodes = Node.query.filter(Node.last_seen < stale_threshold).all()
        
        primary_changed = any(node.id == self.pbft.primary_node.id for node in stale_nodes)
        
        Node.query.filter(Node.last_seen < stale_threshold).delete()
        db.session.commit()
        
        if primary_changed:
            self.pbft.initiate_view_change()

    def resolve_conflicts(self):
        """Resolve conflicts between nodes using both PoW and PBFT"""
        nodes = Node.query.all()
        new_chain = None
        max_length = len(Block.query.all())
        
        # Get current primary node
        primary_node = self.pbft.get_primary_node()
        
        for node in nodes:
            try:
                response = requests.get(f'http://{node.address}/chain')
                if response.status_code == 200:
                    length = response.json()['length']
                    chain = response.json()['chain']

                    # Give priority to primary node's chain if valid
                    if node.id == primary_node.id and length >= max_length and self._validate_chain(chain):
                        max_length = length
                        new_chain = chain
                    # Consider other nodes' chains
                    elif length > max_length and self._validate_chain(chain):
                        max_length = length
                        new_chain = chain
            except:
                if node.id == primary_node.id:
                    # Initiate view change if primary node is unreachable
                    self.pbft.initiate_view_change()
                continue

        if new_chain:
            self._replace_chain(new_chain)
            return True
        return False

    def _validate_chain(self, chain):
        """Validate chain using both PoW and PBFT"""
        if not self.blockchain.is_valid_chain(chain):
            return False
            
        # Additional PBFT validation for recent blocks
        recent_blocks = chain[-10:]  # Validate last 10 blocks
        for block_data in recent_blocks:
            block = Block(
                previous_hash=block_data['previous_hash'],
                hash=block_data['hash'],
                nonce=block_data['nonce']
            )
            if not self.pbft.validate_block(block):
                return False
                
        return True

    def _replace_chain(self, new_chain):
        """Replace the current chain with new validated chain"""
        # Clear existing chain
        Block.query.delete()
        
        # Add new blocks
        for block_data in new_chain:
            block = Block(
                previous_hash=block_data['previous_hash'],
                hash=block_data['hash'],
                nonce=block_data['nonce']
            )
            
            # Add transactions
            for tx_data in block_data.get('transactions', []):
                transaction = Transaction(
                    sender=tx_data['sender'],
                    recipient=tx_data['recipient'],
                    amount=tx_data['amount']
                )
                block.transactions.append(transaction)
                
            db.session.add(block)
            
        db.session.commit()
