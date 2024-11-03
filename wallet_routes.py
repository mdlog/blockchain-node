from flask import jsonify, request, render_template, session, redirect, url_for
from app import app, db
from models import Transaction
from wallet import Wallet
from datetime import datetime

# Store wallets in memory (in production, this should be properly persisted)
wallets = {}

@app.route('/')
def index():
    wallet_address = session.get('wallet_address')
    balance = None
    if wallet_address:
        # Calculate balance from all confirmed transactions
        received = Transaction.query.filter_by(recipient=wallet_address).all()
        sent = Transaction.query.filter_by(sender=wallet_address).all()
        balance = sum(tx.amount for tx in received) - sum(tx.amount for tx in sent)
    
    return render_template('index.html', 
                         wallet_address=wallet_address,
                         balance=balance)

@app.route('/wallet/create', methods=['POST'])
def create_wallet():
    wallet = Wallet()
    public_key = wallet.generate_keys()
    private_key = wallet.export_private_key()
    
    # Store the wallet address in session
    session['wallet_address'] = public_key
    
    # If it's a form submission, render the response in HTML
    if request.headers.get('Content-Type') != 'application/json':
        return render_template('wallet_created.html', 
                             public_key=public_key, 
                             private_key=private_key)
    
    # For API requests, return JSON
    return jsonify({
        'public_key': public_key,
        'private_key': private_key
    }), 201

@app.route('/wallet/balance', methods=['GET', 'POST'])
def check_balance():
    if request.method == 'POST':
        wallet_address = request.form.get('wallet_address')
        if wallet_address:
            session['wallet_address'] = wallet_address
    else:
        wallet_address = request.args.get('public_key')
        
    if not wallet_address:
        return redirect(url_for('index'))
        
    # Calculate balance from all confirmed transactions
    received = Transaction.query.filter_by(recipient=wallet_address).all()
    sent = Transaction.query.filter_by(sender=wallet_address).all()
    balance = sum(tx.amount for tx in received) - sum(tx.amount for tx in sent)
    
    if request.headers.get('Content-Type') == 'application/json':
        return jsonify({'balance': balance}), 200
        
    return redirect(url_for('index'))

@app.route('/transaction/create', methods=['POST'])
def create_transaction():
    # Handle form data
    if request.headers.get('Content-Type') != 'application/json':
        values = request.form
    else:
        values = request.get_json()
        
    required = ['sender_private_key', 'sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return jsonify({'message': 'Missing values'}), 400

    # Create wallet and import private key
    wallet = Wallet()
    if not wallet.import_private_key(values['sender_private_key']):
        return jsonify({'message': 'Invalid private key'}), 400

    # Create and sign transaction
    transaction = Transaction(
        sender=values['sender'],
        recipient=values['recipient'],
        amount=float(values['amount']),
        timestamp=datetime.utcnow(),
        public_key=wallet.get_public_key_string()
    )

    # Sign the transaction
    try:
        transaction.signature = wallet.sign_transaction(transaction.get_signing_data())
    except Exception as e:
        return jsonify({'message': f'Error signing transaction: {str(e)}'}), 400

    # Verify the transaction
    if not Wallet.verify_signature(
        transaction.public_key,
        transaction.signature,
        transaction.get_signing_data()
    ):
        return jsonify({'message': 'Invalid transaction signature'}), 400

    # Save the transaction
    db.session.add(transaction)
    db.session.commit()

    # If it's a form submission, render the response in HTML
    if request.headers.get('Content-Type') != 'application/json':
        return render_template('transaction_created.html', 
                             transaction=transaction.to_dict())

    return jsonify({
        'message': 'Transaction created successfully',
        'transaction': transaction.to_dict()
    }), 201

@app.route('/transaction/verify/<transaction_id>', methods=['GET'])
def verify_transaction(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({'message': 'Transaction not found'}), 404

    is_valid = Wallet.verify_signature(
        transaction.public_key,
        transaction.signature,
        transaction.get_signing_data()
    )

    return jsonify({
        'transaction': transaction.to_dict(),
        'is_valid': is_valid
    }), 200
