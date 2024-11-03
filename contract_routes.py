from flask import request, jsonify, render_template
from app import app, db
from models import SmartContract, ContractCall, Transaction
from smart_contracts import SmartContractEngine
from wallet import Wallet
import json

contract_engine = SmartContractEngine()

@app.route('/contracts/deploy', methods=['GET', 'POST'])
def deploy_contract():
    if request.method == 'POST':
        try:
            if request.headers.get('Content-Type') == 'application/json':
                data = request.get_json()
            else:
                data = request.form

            creator = data.get('creator')
            code = data.get('code')
            private_key = data.get('private_key')

            if not all([creator, code, private_key]):
                return jsonify({'error': 'Missing required fields'}), 400

            # Verify creator's identity
            wallet = Wallet()
            if not wallet.import_private_key(private_key):
                return jsonify({'error': 'Invalid private key'}), 400

            # Deploy contract
            contract = contract_engine.deploy_contract(creator, code)

            if request.headers.get('Content-Type') == 'application/json':
                return jsonify(contract.to_dict()), 201
            else:
                return render_template('contract_deployed.html', contract=contract)

        except ValueError as e:
            return jsonify({'error': str(e)}), 400

    return render_template('deploy_contract.html')

@app.route('/contracts/<address>/call', methods=['POST'])
def call_contract(address):
    try:
        if request.headers.get('Content-Type') == 'application/json':
            data = request.get_json()
        else:
            data = request.form

        function_name = data.get('function')
        arguments = json.loads(data.get('arguments', '[]'))
        sender = data.get('sender')
        private_key = data.get('private_key')

        if not all([function_name, sender, private_key]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Verify sender's identity
        wallet = Wallet()
        if not wallet.import_private_key(private_key):
            return jsonify({'error': 'Invalid private key'}), 400

        # Create transaction for contract call
        transaction = Transaction(
            sender=sender,
            recipient=address,
            amount=0,  # Contract calls don't require transfer
            public_key=wallet.get_public_key_string()
        )
        transaction.signature = wallet.sign_transaction(transaction.get_signing_data())

        # Execute contract call
        result = contract_engine.call_contract(address, function_name, arguments, transaction)

        if request.headers.get('Content-Type') == 'application/json':
            return jsonify({'result': result}), 200
        else:
            return render_template('contract_call_result.html', 
                                result=result, 
                                function=function_name, 
                                contract_address=address)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/contracts/<address>')
def get_contract(address):
    contract = SmartContract.query.filter_by(address=address).first()
    if not contract:
        return jsonify({'error': 'Contract not found'}), 404

    state = contract_engine.get_contract_state(address)
    calls = ContractCall.query.filter_by(contract_id=contract.id).order_by(ContractCall.timestamp.desc()).all()

    return render_template('contract_detail.html', 
                         contract=contract,
                         state=state,
                         calls=calls)

@app.route('/contracts')
def list_contracts():
    contracts = SmartContract.query.order_by(SmartContract.created_at.desc()).all()
    return render_template('contracts.html', contracts=contracts)
