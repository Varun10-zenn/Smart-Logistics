import httpx, json

base = 'http://localhost:8000'

# Test 1: Login
r = httpx.post(f'{base}/api/v1/auth/login', json={'email': 'admin@smartlogistics.local', 'password': 'AdminPass123!'})
if r.status_code == 200:
    token = r.json()['access_token']
    print('LOGIN: 200 OK - token received')
    headers = {'Authorization': f'Bearer {token}'}

    r2 = httpx.get(f'{base}/api/v1/auth/me', headers=headers)
    role = r2.json().get('role')
    print(f'ME: {r2.status_code} role={role}')

    r3 = httpx.get(f'{base}/api/v1/warehouses', headers=headers)
    items = r3.json().get('items', [])
    print(f'WAREHOUSES: {r3.status_code} items={len(items)}')

    r4 = httpx.post(f'{base}/api/v1/intelligence/run', headers=headers,
                    json={'operation': 'warehouse_batch_recommendation', 'context': {'warehouse_id': 1}})
    fb = r4.json().get('fallback_used')
    print(f'INTELLIGENCE valid: {r4.status_code} fallback={fb}')

    r5 = httpx.post(f'{base}/api/v1/intelligence/run', headers=headers,
                    json={'operation': 'DROP TABLE users', 'context': {}})
    code = r5.json().get('error', {}).get('code')
    print(f'INTELLIGENCE invalid: {r5.status_code} code={code}')

    r6 = httpx.get(f'{base}/api/v1/dashboard/overview', headers=headers)
    print(f'DASHBOARD: {r6.status_code}')

    r7 = httpx.get(f'{base}/api/v1/audit/logs', headers=headers)
    audit_items = r7.json().get('items', [])
    print(f'AUDIT LOGS: {r7.status_code} items={len(audit_items)}')

    r8 = httpx.get(f'{base}/api/v1/warehouses/999999', headers=headers)
    err = r8.json()
    has_rid = 'request_id' in err.get('error', {})
    print(f'ERROR ENVELOPE: status={r8.status_code} has_request_id={has_rid}')

    # Test RBAC: driver token trying warehouses
    r_driver = httpx.post(f'{base}/api/v1/auth/login', json={'email': 'driver1@smartlogistics.local', 'password': 'DriverPass123!'})
    if r_driver.status_code == 200:
        driver_headers = {'Authorization': f'Bearer {r_driver.json()["access_token"]}'}
        r9 = httpx.get(f'{base}/api/v1/warehouses', headers=driver_headers)
        print(f'RBAC driver->warehouses: {r9.status_code}')

else:
    print(f'LOGIN FAILED: {r.status_code}')
    data = r.json()
    print('Response:', json.dumps(data, indent=2))
    print('NOTE: No seed data. Auth tests require seeded users.')

print('DONE')
