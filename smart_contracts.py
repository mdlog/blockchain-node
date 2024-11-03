import hashlib
import json
import ast
from datetime import datetime
from app import db
from models import SmartContract, ContractCall
from wallet import Wallet

class SmartContractEngine:
    def __init__(self):
        self.supported_operations = {
            'add': lambda x, y: x + y,
            'subtract': lambda x, y: x - y,
            'multiply': lambda x, y: x * y,
            'divide': lambda x, y: x / y if y != 0 else None,
            'get': lambda x: x,
            'set': lambda x: x
        }
    
    def _generate_contract_address(self, creator, code, timestamp):
        """Generate a unique contract address"""
        data = f"{creator}{code}{timestamp}".encode()
        return hashlib.sha256(data).hexdigest()
    
    def _validate_contract_code(self, code):
        """Validate contract code for security"""
        try:
            # Parse the code to check for syntax errors
            ast.parse(code)
            
            # Check for forbidden operations
            forbidden = ['import', 'exec', 'eval', 'open', '__import__']
            for op in forbidden:
                if op in code:
                    raise ValueError(f"Forbidden operation: {op}")
            
            return True
        except SyntaxError:
            raise ValueError("Invalid contract code syntax")
    
    def _generate_contract_abi(self, code):
        """Generate ABI from contract code"""
        try:
            tree = ast.parse(code)
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    args = [arg.arg for arg in node.args.args]
                    functions.append({
                        'name': node.name,
                        'inputs': args,
                        'outputs': ['any']  # Simplified output type
                    })
            
            return json.dumps(functions)
        except Exception as e:
            raise ValueError(f"Error generating ABI: {str(e)}")
    
    def deploy_contract(self, creator, code):
        """Deploy a new smart contract"""
        # Validate contract code
        self._validate_contract_code(code)
        
        # Generate contract address and ABI
        timestamp = datetime.utcnow()
        address = self._generate_contract_address(creator, code, timestamp)
        abi = self._generate_contract_abi(code)
        
        # Create new contract
        contract = SmartContract(
            address=address,
            creator=creator,
            code=code,
            abi=abi,
            created_at=timestamp
        )
        
        db.session.add(contract)
        db.session.commit()
        return contract
    
    def _execute_contract_function(self, contract, function_name, args):
        """Execute a contract function"""
        # Create a safe execution environment
        local_env = self.supported_operations.copy()
        local_env.update(contract.get_state())
        
        try:
            # Execute the function
            exec(contract.code, {'__builtins__': {}}, local_env)
            if function_name not in local_env:
                raise ValueError(f"Function {function_name} not found in contract")
            
            result = local_env[function_name](*args)
            
            # Update contract state
            new_state = {k: v for k, v in local_env.items() 
                        if k not in self.supported_operations and not k.startswith('__')}
            contract.set_state(new_state)
            
            return result
        except Exception as e:
            raise ValueError(f"Error executing contract function: {str(e)}")
    
    def call_contract(self, contract_address, function_name, args, transaction=None):
        """Call a contract function"""
        contract = SmartContract.query.filter_by(address=contract_address).first()
        if not contract:
            raise ValueError("Contract not found")
        
        # Create contract call record
        call = ContractCall(
            contract=contract,
            function_name=function_name,
            transaction=transaction
        )
        call.set_arguments(args)
        
        # Execute function and store result
        result = self._execute_contract_function(contract, function_name, args)
        call.set_result(result)
        
        db.session.add(call)
        db.session.commit()
        
        return result
    
    def get_contract_state(self, contract_address):
        """Get current state of a contract"""
        contract = SmartContract.query.filter_by(address=contract_address).first()
        if not contract:
            raise ValueError("Contract not found")
        return contract.get_state()
