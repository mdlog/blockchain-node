from ecdsa import SigningKey, VerifyingKey, SECP256k1
from ecdsa.util import sigencode_string, sigdecode_string
import hashlib
import json
import binascii
import os

class Wallet:
    def __init__(self):
        self.private_key = None
        self.public_key = None

    def _hash_public_key(self, public_key_bytes):
        """Hash the public key to 20 bytes (40 hex chars)"""
        sha256_hash = hashlib.sha256(public_key_bytes).digest()
        ripemd160_hash = hashlib.new('ripemd160')
        ripemd160_hash.update(sha256_hash)
        return ripemd160_hash.digest()

    def generate_keys(self):
        """Generate a new key pair using secp256k1"""
        self.private_key = SigningKey.generate(curve=SECP256k1)
        self.public_key = self.private_key.get_verifying_key()
        
        # Get the raw public key bytes (uncompressed format)
        pub_key_bytes = self.public_key.to_string()
        
        # Hash to get 20-byte address (40 hex chars)
        hashed_key = self._hash_public_key(pub_key_bytes)
        return '0x' + binascii.hexlify(hashed_key).decode('ascii')

    def get_public_key_string(self):
        """Get public key in hex format (40 characters) with 0x prefix"""
        if not self.public_key:
            return None
            
        pub_key_bytes = self.public_key.to_string()
        return '0x' + binascii.hexlify(pub_key_bytes).decode('ascii')

    def sign_transaction(self, transaction_data):
        """Sign a transaction with the private key"""
        if not self.private_key:
            raise ValueError("No private key available")

        # Convert transaction data to canonical string representation
        message = json.dumps(transaction_data, sort_keys=True).encode()
        message_hash = hashlib.sha256(message).digest()
        
        # Sign the hash with the 32-byte private key
        signature = self.private_key.sign(
            message_hash,
            sigencode=sigencode_string
        )
        
        # Return hex-encoded signature
        return binascii.hexlify(signature).decode('ascii')

    @staticmethod
    def verify_signature(public_key_str, signature_str, transaction_data):
        """Verify a transaction signature"""
        try:
            # Remove '0x' prefix if present
            if public_key_str.startswith('0x'):
                public_key_str = public_key_str[2:]

            # Convert hex signature back to bytes
            signature = binascii.unhexlify(signature_str)
            
            # Convert transaction data to canonical string representation
            message = json.dumps(transaction_data, sort_keys=True).encode()
            message_hash = hashlib.sha256(message).digest()

            # Convert public key from hex to bytes (expect 64 bytes for uncompressed key)
            public_key_bytes = binascii.unhexlify(public_key_str)
            
            # Create verifying key from the public key bytes
            public_key = VerifyingKey.from_string(
                public_key_bytes,
                curve=SECP256k1
            )

            # Verify the signature
            return public_key.verify(
                signature,
                message_hash,
                sigdecode=sigdecode_string
            )
        except Exception as e:
            print(f"Signature verification failed: {str(e)}")
            return False

    def export_private_key(self):
        """Export private key in hex format (exactly 64 characters)"""
        if not self.private_key:
            return None
        
        private_bytes = self.private_key.to_string()
        return binascii.hexlify(private_bytes).decode('ascii')

    def import_private_key(self, private_key_str):
        """Import private key from hex format (exactly 64 characters)"""
        try:
            # Verify length (64 hex chars = 32 bytes)
            if len(private_key_str) != 64:
                return False
                
            private_key_bytes = binascii.unhexlify(private_key_str)
            if len(private_key_bytes) != 32:
                return False
                
            self.private_key = SigningKey.from_string(private_key_bytes, curve=SECP256k1)
            self.public_key = self.private_key.get_verifying_key()
            return True
        except Exception:
            return False
