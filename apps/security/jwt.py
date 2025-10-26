"""
TOM v3.0 - JWT Validator mit Replay-Schutz
"""

import hashlib
import logging
import os
import time
from typing import Optional

import jwt
import redis

logger = logging.getLogger(__name__)


class JWTValidator:
    """JWT-Validator mit Replay-Schutz via Redis"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.secret = os.getenv('JWT_SECRET', 'dev-secret-key')
        self.algorithm = os.getenv('JWT_ALGORITHM', 'HS256')
        self.public_key_path = os.getenv('JWT_PUBLIC_KEY_PATH')
        
    def validate_jwt(self, token: str, call_id: str) -> bool:
        """Validiert JWT mit Replay-Schutz"""
        try:
            # JWT dekodieren
            if self.algorithm.startswith('RS'):
                # RS256/RS512
                with open(self.public_key_path, 'r') as f:
                    public_key = f.read()
                payload = jwt.decode(token, public_key, algorithms=[self.algorithm])
            else:
                # HS256/HS384/HS512
                payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            
            # Basis-Validierung
            if payload.get('sub') != 'realtime_user':
                logger.warning("Invalid JWT subject")
                return False
                
            if payload.get('call_id') != call_id:
                logger.warning(f"JWT call_id mismatch: {payload.get('call_id')} != {call_id}")
                return False
                
            # Expiry prüfen
            exp = payload.get('exp', 0)
            if exp < time.time():
                logger.warning("JWT expired")
                return False
            
            # Replay-Schutz via Redis Nonce
            nonce = payload.get('nonce')
            if not nonce:
                logger.warning("JWT missing nonce")
                return False
            
            # Redis SETNX für atomare Operation
            key = f"jwt_nonce:{nonce}"
            if not self.redis_client.set(key, "1", nx=True, ex=300):  # 5min TTL
                logger.warning(f"JWT Replay detected: {nonce}")
                return False
            
            logger.info(f"JWT validated successfully for call {call_id}")
            return True
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            return False
    
    def hash_phone_number(self, phone_number: str) -> str:
        """Hasht Telefonnummer für anonyme Metriken"""
        salt = os.getenv('PHONE_HASH_SALT', 'CHANGE_ME')
        
        # Hash mit Salt
        hash_input = f"{phone_number}{salt}"
        hash_bytes = hashlib.sha256(hash_input.encode()).digest()
        
        # Hex-String (erste 12 Zeichen)
        return hash_bytes.hex()[:12]

