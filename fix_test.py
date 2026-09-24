with open('test_e2e_reprocess.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace("WHERE status IN ('FAILED', 'SUCCESS') ", "")
with open('test_e2e_reprocess.py', 'w', encoding='utf-8') as f:
    f.write(c)
