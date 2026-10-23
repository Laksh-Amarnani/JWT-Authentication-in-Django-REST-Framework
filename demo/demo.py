"""Full JWT demo. Start the server first (python manage.py runserver), then run: python demo/demo.py"""
import base64
import json
import time

import requests

# 127.0.0.1 instead of "localhost": on Windows, localhost tries IPv6 first and adds ~2s to every request.
BASE_URL = 'http://127.0.0.1:8000/api'
USERNAME = 'demo_user'
PASSWORD = 'Demo-Pass-2026!'


def step(title):
    print(f'\n=== {title} ===')


def check(response, expected_status, expected_code=None):
    body = response.json()
    ok = response.status_code == expected_status
    if expected_code:
        ok = ok and body.get('code') == expected_code
    print(f'Status: {response.status_code}')
    print(f'Body: {json.dumps(body)[:200]}')
    print('PASS' if ok else 'FAIL')


def call_protected(token):
    # Timeout is longer than the server's 10s Random User timeout.
    return requests.get(f'{BASE_URL}/protected/', headers={'Authorization': f'Bearer {token}'}, timeout=15)


def b64url_decode(text):
    # JWTs drop the "=" padding at the end, so add it back before decoding.
    return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))


def b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


step('1. Register (201, or 400 if the user already exists)')
response = requests.post(f'{BASE_URL}/register/', data={'username': USERNAME, 'password': PASSWORD}, timeout=10)
print(f'Status: {response.status_code}  Body: {response.json()}')

step('2. Login (expect 200) and decode the access token')
response = requests.post(f'{BASE_URL}/login/', data={'username': USERNAME, 'password': PASSWORD}, timeout=10)
check(response, 200)
access = response.json()['access']
refresh = response.json()['refresh']

header_b64, payload_b64, signature_b64 = access.split('.')
payload = json.loads(b64url_decode(payload_b64))
print(f'Header:    {json.loads(b64url_decode(header_b64))}')
print(f'Payload:   {payload}')
print(f'Signature: {signature_b64}  (HMAC-SHA256 of header.payload with SECRET_KEY, not JSON)')

step('3. Call /api/protected/ with the valid token (expect 200)')
check(call_protected(access), 200)

step('4. Change one character of the signature (expect 401)')
# Change the first character: the last one partly holds padding bits, so changing it may not change the signature.
new_char = 'A' if signature_b64[0] != 'A' else 'B'
check(call_protected(f'{header_b64}.{payload_b64}.{new_char + signature_b64[1:]}'), 401)

step('5. Change user_id in the payload, keep the old signature (expect 401)')
fake_payload = dict(payload, user_id=str(int(payload['user_id']) + 1))
print(f'Fake payload: {fake_payload}')
fake_payload_b64 = b64url_encode(json.dumps(fake_payload).encode())
check(call_protected(f'{header_b64}.{fake_payload_b64}.{signature_b64}'), 401)

step('6. Wait 31 seconds so the access token expires (expect 401 token_not_valid)')
time.sleep(31)
check(call_protected(access), 401, 'token_not_valid')

step('7. Use the refresh token to get a new access token (expect 200), then call again (expect 200)')
response = requests.post(f'{BASE_URL}/token/refresh/', data={'refresh': refresh}, timeout=10)
check(response, 200)
check(call_protected(response.json()['access']), 200)
