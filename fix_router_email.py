import re

router_file = 'src/contexts/document_intake_ocr/presentation/api/routers/batch_router.py'
with open(router_file, 'r', encoding='utf-8') as f:
    s_content = f.read()

s_content = s_content.replace(
    'user_email=current_user.email,',
    'user_email=current_user.email.value,'
)

with open(router_file, 'w', encoding='utf-8') as f:
    f.write(s_content)
