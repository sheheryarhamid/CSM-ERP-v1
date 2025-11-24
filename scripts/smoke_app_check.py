import sys
from pathlib import Path

# ensure repo root is on sys.path so `hub` package can be imported
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from hub.main import app


def run_smoke():
    client = TestClient(app)
    print('GET /health ->', client.get('/health').status_code, client.get('/health').json())

    print('\nGET /api/health/clients ->')
    r = client.get('/api/health/clients')
    print(r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)

    print('\nPOST /api/clients/create ->')
    r = client.post('/api/clients/create', params={'user': 'smoke-test', 'role': 'Tester'})
    print(r.status_code)
    info = {}
    try:
        info = r.json()
        print(info)
    except Exception:
        print(r.text)

    sid = info.get('session_id')
    if sid:
        print(f"\nPOST /api/clients/{sid}/terminate ->")
        r2 = client.post(f"/api/clients/{sid}/terminate")
        print(r2.status_code)
        try:
            print(r2.json())
        except Exception:
            print(r2.text)

    print('\nGET /metrics ->', client.get('/metrics').status_code)

    print('\nGET /api/ops/audit ->')
    r3 = client.get('/api/ops/audit')
    print(r3.status_code)
    try:
        print(r3.json())
    except Exception:
        print(r3.text)


if __name__ == '__main__':
    run_smoke()
