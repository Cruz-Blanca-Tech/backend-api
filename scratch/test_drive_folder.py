import asyncio
import os
import json
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_drive():
    from dotenv import load_dotenv
    load_dotenv()
    
    secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    folder_id = os.environ.get("GOOGLE_DRIVE_CONSOLIDATED_DOSSIERS_ID")
    
    if not secret or not folder_id:
        logger.error("Missing GOOGLE_CLIENT_SECRET or GOOGLE_DRIVE_CONSOLIDATED_DOSSIERS_ID")
        return
        
    credentials_info = json.loads(secret)
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_info(
        credentials_info, scopes=scopes
    )
    
    service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    
    try:
        # Check the base folder
        logger.info(f"Checking base folder {folder_id}...")
        folder = service.files().get(fileId=folder_id, supportsAllDrives=True).execute()
        logger.info(f"Found base folder: {folder.get('name')}")
        
        # List contents
        logger.info("Listing contents of the base folder...")
        query = f"'{folder_id}' in parents and trashed = false"
        response = service.files().list(q=query, spaces='drive', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        files = response.get('files', [])
        
        logger.info(f"Found {len(files)} items:")
        for f in files:
            logger.info(f"- {f.get('name')} (ID: {f.get('id')}, Type: {f.get('mimeType')})")
            
            # If it's a folder, list its contents too
            if f.get('mimeType') == 'application/vnd.google-apps.folder':
                sub_query = f"'{f.get('id')}' in parents and trashed = false"
                sub_resp = service.files().list(q=sub_query, spaces='drive', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
                for sf in sub_resp.get('files', []):
                    logger.info(f"  └─ {sf.get('name')} (ID: {sf.get('id')})")
                    
    except Exception as e:
        logger.error(f"Error accessing Drive: {e}")

if __name__ == "__main__":
    asyncio.run(test_drive())
