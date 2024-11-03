from app import db
from datetime import datetime
import json

class Node(db.Model):
    __tablename__ = 'node'
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(256), unique=True, nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

class Block(db.Model):
    __tablename__ = 'block'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    previous_hash = db.Column(db.String(64), nullable=False)
    hash = db.Column(db.String(64), unique=True, nullable=False)
    nonce = db.Column(db.Integer, nullable=False)
    validation_status = db.Column(db.String(20), default='pending')  # pending, validated, invalid
    validation_timestamp = db.Column(db.DateTime)
    validation_errors = db.Column(db.Text)  # JSON string of validation errors
    
    # Define relationships with lazy loading to prevent circular dependencies
    transactions = db.relationship('Transaction', backref='block', lazy='select')
    contracts = db.relationship('SmartContract', backref='block', lazy='select')

    def to_dict(self):
        return {
            'index': self.id,
            'timestamp': self.timestamp.isoformat(),
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'nonce': self.nonce,
            'validation_status': self.validation_status,
            'validation_timestamp': self.validation_timestamp.isoformat() if self.validation_timestamp else None,
            'validation_errors': json.loads(self.validation_errors) if self.validation_errors else None,
            'transactions': [tx.to_dict() for tx in self.transactions]
        }
    
    def set_validation_errors(self, errors):
        """Set validation errors as JSON string"""
        self.validation_errors = json.dumps(errors) if errors else None
    
    def get_validation_errors(self):
        """Get validation errors as Python object"""
        return json.loads(self.validation_errors) if self.validation_errors else None

class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(256), nullable=False)
    recipient = db.Column(db.String(256), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    block_id = db.Column(db.Integer, db.ForeignKey('block.id', ondelete='CASCADE'), nullable=True)
    signature = db.Column(db.Text, nullable=True)
    public_key = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        return {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'timestamp': self.timestamp.isoformat(),
            'signature': self.signature,
            'public_key': self.public_key
        }

    def get_signing_data(self):
        """Get transaction data for signing"""
        return {
            'sender': self.sender,
            'recipient': self.recipient,
            'amount': self.amount,
            'timestamp': self.timestamp.isoformat()
        }

class SmartContract(db.Model):
    __tablename__ = 'smart_contract'
    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(64), unique=True, nullable=False)
    creator = db.Column(db.String(256), nullable=False)
    code = db.Column(db.Text, nullable=False)
    abi = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    block_id = db.Column(db.Integer, db.ForeignKey('block.id', ondelete='CASCADE'), nullable=True)
    state = db.Column(db.Text, default='{}')
    
    # Define relationship with lazy loading
    calls = db.relationship('ContractCall', backref='contract', lazy='select')
    
    def get_state(self):
        return json.loads(self.state)
    
    def set_state(self, new_state):
        self.state = json.dumps(new_state)
    
    def to_dict(self):
        return {
            'address': self.address,
            'creator': self.creator,
            'code': self.code,
            'abi': self.abi,
            'created_at': self.created_at.isoformat(),
            'state': self.get_state()
        }

class ContractCall(db.Model):
    __tablename__ = 'contract_call'
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('smart_contract.id', ondelete='CASCADE'))
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id', ondelete='CASCADE'))
    function_name = db.Column(db.String(64), nullable=False)
    arguments = db.Column(db.Text, nullable=False)
    result = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Define relationships with lazy loading
    transaction = db.relationship('Transaction', backref=db.backref('contract_calls', lazy='select'))
    
    def get_arguments(self):
        return json.loads(self.arguments)
    
    def set_arguments(self, args):
        self.arguments = json.dumps(args)
    
    def get_result(self):
        return json.loads(self.result) if self.result else None
    
    def set_result(self, result):
        self.result = json.dumps(result)
