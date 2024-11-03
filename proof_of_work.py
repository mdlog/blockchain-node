import hashlib

class ProofOfWork:
    def __init__(self, difficulty=4):
        self.difficulty = difficulty
        self.target = "0" * difficulty

    def find_nonce(self, previous_hash, transactions):
        nonce = 0
        while True:
            if self.is_valid_proof(nonce, previous_hash, transactions):
                return nonce
            nonce += 1

    def is_valid_proof(self, nonce, previous_hash, transactions):
        guess = f"{previous_hash}{transactions}{nonce}".encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:self.difficulty] == self.target
