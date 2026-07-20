"""
blockchain.py
--------------
A minimal, dependency-free blockchain used to anchor image-recognition
results. This is a *permissioned, educational* chain (not a cryptocurrency):
its only job is to give every recognition event a tamper-evident,
chronologically ordered record.

Each block stores:
    - index            : position in the chain
    - timestamp         : when the block was created
    - image_hash        : SHA-256 hash of the uploaded image bytes
    - filename          : original filename (for human reference only)
    - prediction         : top label returned by the recognition model
    - confidence         : model confidence for that label (0-1)
    - previous_hash      : hash of the prior block (the "link")
    - nonce              : proof-of-work nonce
    - hash               : this block's own hash (computed after mining)

Chain integrity is verified by recomputing hashes and checking the
previous_hash links -- if any block's stored data is altered, every
hash after it will fail to recompute, exposing the tampering.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional


# Difficulty controls how many leading zeros a valid block hash must have.
# Kept low (2) so mining stays instant for a classroom demo; a production
# chain would tune this against desired block time.
MINING_DIFFICULTY = 2


@dataclass
class Block:
    index: int
    timestamp: float
    image_hash: str
    filename: str
    prediction: str
    confidence: float
    previous_hash: str
    nonce: int = 0
    hash: str = field(default="")

    def compute_hash(self) -> str:
        """Hash every field except the stored hash itself."""
        block_body = {
            "index": self.index,
            "timestamp": self.timestamp,
            "image_hash": self.image_hash,
            "filename": self.filename,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        payload = json.dumps(block_body, sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)


class Blockchain:
    def __init__(self, storage_path: str = "data/chain.json"):
        self.storage_path = storage_path
        self.chain: List[Block] = []
        self._load()
        if not self.chain:
            self._add_genesis_block()

    # ------------------------------------------------------------------
    # Core chain operations
    # ------------------------------------------------------------------
    def _add_genesis_block(self):
        genesis = Block(
            index=0,
            timestamp=time.time(),
            image_hash="0" * 64,
            filename="genesis",
            prediction="N/A",
            confidence=0.0,
            previous_hash="0" * 64,
        )
        genesis.hash = self._mine(genesis)
        self.chain.append(genesis)
        self._save()

    def _mine(self, block: Block) -> str:
        """Simple proof-of-work: increment nonce until the hash has the
        required number of leading zeros. Demonstrates the concept without
        the computational cost of a real network."""
        target = "0" * MINING_DIFFICULTY
        block.nonce = 0
        computed = block.compute_hash()
        while not computed.startswith(target):
            block.nonce += 1
            computed = block.compute_hash()
        return computed

    def add_block(self, image_hash: str, filename: str, prediction: str,
                  confidence: float) -> Block:
        previous_block = self.chain[-1]
        new_block = Block(
            index=previous_block.index + 1,
            timestamp=time.time(),
            image_hash=image_hash,
            filename=filename,
            prediction=prediction,
            confidence=confidence,
            previous_hash=previous_block.hash,
        )
        new_block.hash = self._mine(new_block)
        self.chain.append(new_block)
        self._save()
        return new_block

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------
    def is_valid(self) -> tuple[bool, Optional[str]]:
        """Walk the chain and confirm every hash and link is intact.
        Returns (True, None) if valid, or (False, reason) on the first
        broken block found."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prior = self.chain[i - 1]

            if current.hash != current.compute_hash():
                return False, f"Block {current.index} data does not match its stored hash."
            if current.previous_hash != prior.hash:
                return False, f"Block {current.index} is not correctly linked to block {prior.index}."
        return True, None

    def find_by_image_hash(self, image_hash: str) -> Optional[Block]:
        for block in self.chain:
            if block.image_hash == image_hash:
                return block
        return None

    # ------------------------------------------------------------------
    # Persistence (JSON file stands in for a distributed ledger/DB)
    # ------------------------------------------------------------------
    def _save(self):
        with open(self.storage_path, "w") as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=2)

    def _load(self):
        try:
            with open(self.storage_path) as f:
                raw = json.load(f)
            self.chain = [Block(**b) for b in raw]
        except (FileNotFoundError, json.JSONDecodeError):
            self.chain = []

    def as_list(self) -> List[dict]:
        return [b.to_dict() for b in self.chain]
