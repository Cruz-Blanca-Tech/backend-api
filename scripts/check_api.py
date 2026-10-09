import httpx
import jwt
from datetime import datetime, timedelta, timezone

now = datetime.now(timezone.utc)
claims = {
    'sub': 'f527fa45-90f2-42c3-ba3f-06879b9b1db3',
    'email': 'enzo.trujillo@cruz-blanca.org',
    'role': 'admin',
    'name': 'Enzo Trujillo',
    'exp': now + timedelta(hours=24),
    'iat': now
}
token = jwt.encode(claims, 'super-secret-key-change-in-production-1234567890', algorithm='HS256')
headers = {'Authorization': f'Bearer {token}'}

resp_sum = httpx.get('https://ca-cruzblanca-backend.happyforest-a0b724a4.centralus.azurecontainerapps.io/api/v1/intake/api/v1/batches/summary', headers=headers, timeout=30.0)
print('Summary:', resp_sum.status_code, resp_sum.json())

resp_list = httpx.get('https://ca-cruzblanca-backend.happyforest-a0b724a4.centralus.azurecontainerapps.io/api/v1/intake/api/v1/batches', headers=headers, timeout=30.0)
data = resp_list.json()
print('Batches list total:', data.get('total'))
for b in data.get('batches', []):
    print(f"ID: {b['id']} | Status: {b['status']} | Desc: {b['description']} | Total Docs: {b.get('total_documents_count')} | Triage: {b.get('triage_summary')}")
