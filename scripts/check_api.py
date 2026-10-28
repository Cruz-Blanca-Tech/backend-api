import os
import sys
import httpx
import jwt
from datetime import datetime, timedelta, timezone

secret_key = os.getenv("SECRET_KEY", "REDACTED_DEV_SECRET_KEY")
api_base_url = os.getenv("API_BASE_URL", "https://ca-cruzblanca-backend.happyforest-a0b724a4.centralus.azurecontainerapps.io")

now = datetime.now(timezone.utc)
claims = {
    'sub': os.getenv("TEST_USER_ID", 'f527fa45-90f2-42c3-ba3f-06879b9b1db3'),
    'email': os.getenv("TEST_USER_EMAIL", 'test.admin@cruz-blanca.org'),
    'role': 'admin',
    'name': 'Test Admin',
    'exp': now + timedelta(hours=24),
    'iat': now
}
token = jwt.encode(claims, secret_key, algorithm='HS256')
headers = {'Authorization': f'Bearer {token}'}

resp_sum = httpx.get(f'{api_base_url.rstrip("/")}/api/v1/intake/api/v1/batches/summary', headers=headers, timeout=30.0)
print('Summary:', resp_sum.status_code, resp_sum.json() if resp_sum.status_code == 200 else resp_sum.text)

resp_list = httpx.get(f'{api_base_url.rstrip("/")}/api/v1/intake/api/v1/batches', headers=headers, timeout=30.0)
if resp_list.status_code == 200:
    data = resp_list.json()
    print('Batches list total:', data.get('total'))
    for b in data.get('batches', []):
        print(f"ID: {b['id']} | Status: {b['status']} | Desc: {b['description']} | Total Docs: {b.get('total_documents_count')} | Triage: {b.get('triage_summary')}")
else:
    print('Batches list error:', resp_list.status_code, resp_list.text)
