import asyncio
import os
import json
import logging
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_auth():
    from dotenv import load_dotenv
    load_dotenv()
    
    secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not secret:
        logger.error("GOOGLE_CLIENT_SECRET not found in environment.")
        return
        
    try:
        credentials_info = json.loads(secret)
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}")
        return
        
    logger.info(f"Loaded credentials for: {credentials_info.get('client_email')}")
    
    pk = credentials_info.get("private_key", "")
    
    try:
        private_key = serialization.load_pem_private_key(
            pk.encode("utf-8"),
            password=None,
            backend=default_backend()
        )
        logger.info("Private key loaded successfully! The key format is valid locally.")
    except Exception as e:
        logger.error(f"Failed to load private key locally: {e}")
        logger.info("This means the private key string is corrupted.")

if __name__ == "__main__":
    asyncio.run(test_auth())
