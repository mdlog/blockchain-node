import hashlib
from datetime import datetime
from app import db
from models import Block, Transaction
from proof_of_work import ProofOfWork
from wallet import Wallet

class Blockchain:
    def __init__(self):
        self.pow = ProofOfWork()
        self._initialize_chain()

    def _initialize_chain(self):
        if not Block.query.first():
            self._create_genesis_block()

    def _create_genesis_block(self):
        genesis_block = Block(
            previous_hash="0"*64,
            hash=self._calculate_hash("0"*64, [], 0),
            nonce=0
        )
        db.session.add(genesis_block)
        db.session.commit()

    def _calculate_hash(self, previous_hash, transactions, nonce):
        block_string = f"{previous_hash}{transactions}{nonce}".encode()
        return hashlib.sha256(block_string).hexdigest()

    def _verify_transactions(self, transactions):
        """Verify all transactions in a block"""
        for tx in transactions:
            if not Wallet.verify_signature(
                tx.public_key,
                tx.signature,
                tx.get_signing_data()
            ):
                return False
        return True

    def create_block(self, transactions):
        # Verify all transactions first
        if not self._verify_transactions(transactions):
            raise ValueError("Invalid transaction signatures detected")

        previous_block = Block.query.order_by(Block.id.desc()).first()
        nonce = self.pow.find_nonce(previous_block.hash, transactions)
        
        new_block = Block(
            previous_hash=previous_block.hash,
            hash=self._calculate_hash(previous_block.hash, transactions, nonce),
            nonce=nonce
        )
        
        for tx in transactions:
            new_block.transactions.append(tx)

        db.session.add(new_block)
        db.session.commit()
        return new_block

    def is_valid_chain(self):
        blocks = Block.query.order_by(Block.id).all()
        for i in range(1, len(blocks)):
            if blocks[i].previous_hash != blocks[i-1].hash:
                return False
            if not self.pow.is_valid_proof(blocks[i].nonce, blocks[i].previous_hash, blocks[i].transactions):
                return False
            if not self._verify_transactions(blocks[i].transactions):
                return False
        return True
