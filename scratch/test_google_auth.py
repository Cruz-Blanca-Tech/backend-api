import asyncio
import os
import json
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_auth():
    # Attempt to load credentials from .env or just use the system ones
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
    
    try:
        # Check if private key contains literal '\n' instead of actual newlines
        pk = credentials_info.get("private_key", "")
        if "\\n" in pk:
            logger.warning("Private key contains literal '\\n'. Fixing it...")
            credentials_info["private_key"] = pk.replace("\\n", "\n")
            
        scopes = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_info(
            credentials_info, scopes=scopes
        )
        
        # Build service, this doesn't immediately fetch a token unless cache_discovery=False tries to
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        
        # Try to execute a simple API call to force token fetch
        logger.info("Attempting to list files to force authentication...")
        results = service.files().list(pageSize=1, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        logger.info(f"Success! Found {len(items)} files.")
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_auth())
