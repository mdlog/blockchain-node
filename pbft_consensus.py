from datetime import datetime
from app import db
from models import Node, Block, Transaction
from enum import Enum
import hashlib
from wallet import Wallet

class MessageType(Enum):
    PREPARE = "PREPARE"
    COMMIT = "COMMIT"
    VIEWCHANGE = "VIEWCHANGE"

class ValidationError:
    def __init__(self, code, message):
        self.code = code
        self.message = message

class PBFTConsensus:
    MIN_NODES = 3
    
    def __init__(self, node_threshold=0.67):
        self.node_threshold = node_threshold  # % of nodes needed for consensus
        self.current_view = 0  # current view number
        self.primary_node = None
        self._update_primary()
        self.validation_errors = []

    def _update_primary(self):
        """Updates the primary node based on view number"""
        nodes = Node.query.order_by(Node.id).all()
        if nodes:
            self.primary_node = nodes[self.current_view % len(nodes)]
        
    def _calculate_block_hash(self, block):
        """Calculate hash for block validation"""
        block_string = f"{block.previous_hash}{block.transactions}{block.nonce}".encode()
        return hashlib.sha256(block_string).hexdigest()

    def _clear_validation_errors(self):
        """Clear previous validation errors"""
        self.validation_errors = []

    def _add_validation_error(self, code, message):
        """Add a validation error"""
        self.validation_errors.append(ValidationError(code, message))

    def get_validation_errors(self):
        """Get all validation errors from the last validation"""
        return self.validation_errors

    def validate_block(self, block):
        """Validate a block using PBFT consensus with detailed error reporting"""
        self._clear_validation_errors()
        
        # Check if we have enough nodes for consensus
        total_nodes = Node.query.count()
        if total_nodes < self.MIN_NODES:
            self._add_validation_error("INSUFFICIENT_NODES", 
                f"Network requires minimum {self.MIN_NODES} nodes for consensus validation. Currently have {total_nodes} nodes.")
            return False
        
        # Check for active nodes
        active_nodes = Node.query.filter(
            Node.last_seen >= datetime.utcnow().replace(hour=datetime.utcnow().hour-1)
        ).count()
        
        required_nodes = int(total_nodes * self.node_threshold)
        if active_nodes < required_nodes:
            self._add_validation_error("INACTIVE_NODES", 
                f"Insufficient active nodes. Need {required_nodes} active nodes, but only {active_nodes} are online.")
            return False

        # Verify block integrity
        if not self._verify_block_integrity(block):
            return False

        return True

    def _verify_block_integrity(self, block):
        """Verify the integrity of a block with detailed error reporting"""
        # Verify previous hash links correctly
        prev_block = Block.query.filter_by(hash=block.previous_hash).first()
        if not prev_block and block.previous_hash != "0"*64:  # Allow genesis block
            self._add_validation_error("INVALID_PREV_HASH", 
                "Previous block not found in chain - possible chain split detected")
            return False
            
        # Verify block hash
        calculated_hash = self._calculate_block_hash(block)
        if calculated_hash != block.hash:
            self._add_validation_error("INVALID_BLOCK_HASH", 
                f"Block hash mismatch. Expected: {calculated_hash}")
            return False

        # Verify transaction signatures
        for tx in block.transactions:
            if not self._verify_transaction(tx):
                return False

        return True

    def _verify_transaction(self, transaction):
        """Verify a single transaction's signature"""
        try:
            if not transaction.signature or not transaction.public_key:
                self._add_validation_error("MISSING_SIGNATURE", 
                    f"Transaction {transaction.id} is missing required signature or public key")
                return False

            if not Wallet.verify_signature(
                transaction.public_key,
                transaction.signature,
                transaction.get_signing_data()
            ):
                self._add_validation_error("INVALID_SIGNATURE", 
                    f"Transaction {transaction.id} has an invalid signature")
                return False

            return True
        except Exception as e:
            self._add_validation_error("VERIFICATION_ERROR", 
                f"Error verifying transaction {transaction.id}: {str(e)}")
            return False

    def initiate_view_change(self):
        """Initiate a view change when primary node is suspected faulty"""
        self.current_view += 1
        self._update_primary()
        return self.current_view

    def get_primary_node(self):
        """Get current primary node"""
        return self.primary_node

    def get_network_status(self):
        """Get current network status and requirements"""
        total_nodes = Node.query.count()
        active_nodes = Node.query.filter(
            Node.last_seen >= datetime.utcnow().replace(hour=datetime.utcnow().hour-1)
        ).count()
        required_nodes = max(self.MIN_NODES, int(total_nodes * self.node_threshold))
        
        return {
            'total_nodes': total_nodes,
            'active_nodes': active_nodes,
            'required_nodes': required_nodes,
            'min_nodes': self.MIN_NODES,
            'consensus_threshold': self.node_threshold,
            'is_ready': active_nodes >= required_nodes
        }
