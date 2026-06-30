import asyncio
import os
import json
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def find_all():
    from dotenv import load_dotenv
    load_dotenv()
    
    secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    credentials_info = json.loads(secret)
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_info(
        credentials_info, scopes=scopes
    )
    
    service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    
    # Just list the most recent files created by this service account
    response = service.files().list(
        q="trashed = false", 
        orderBy="createdTime desc", 
        pageSize=10,
        fields="files(id, name, mimeType, parents, webViewLink)",
        supportsAllDrives=True, 
        includeItemsFromAllDrives=True
    ).execute()
    
    files = response.get('files', [])
    logger.info(f"Most recently created files across the entire Service Account:")
    for f in files:
        logger.info(f"- {f.get('name')} (ID: {f.get('id')}, Parents: {f.get('parents')})")
        logger.info(f"  Link: {f.get('webViewLink')}")

if __name__ == "__main__":
    asyncio.run(find_all())
