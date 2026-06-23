import json
with open('accounts/virtual_2026_account.json') as f:
    acc = json.load(f)
print('Position stock_codes:', [p['stock_code'] for p in acc['positions']])
