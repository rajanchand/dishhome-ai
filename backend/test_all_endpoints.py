import asyncio
import os
import sys

# Setup paths
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)
if os.path.join(_here, "backend") not in sys.path:
    sys.path.insert(0, os.path.join(_here, "backend"))

# Load dotenv BEFORE importing app
from dotenv import load_dotenv
load_dotenv(os.path.join(_here, ".env"))

# Make sure we use capitalized password
if "DATABASE_URL" in os.environ:
    dsn = os.environ["DATABASE_URL"]
    if "support0825" in dsn:
        os.environ["DATABASE_URL"] = dsn.replace("support0825", "Support0825")

from httpx import AsyncClient
from app.main import app

# Correct list of endpoints to test
ENDPOINTS = [
    ("GET", "/calls/stats"),
    ("GET", "/calls"),
    ("GET", "/metrics"),
    ("GET", "/admin/users"),
    ("GET", "/admin/roles"),
    ("GET", "/admin/audit-log"),
    ("GET", "/admin/login-activity"),
    ("GET", "/admin/active-sessions"),
    ("GET", "/huawei/customers"),
    ("GET", "/huawei/onts/ONT-KTM-882441"),
    ("GET", "/conversations"),
    ("GET", "/labels"),
    ("GET", "/contacts"),
    ("GET", "/saved-replies"),
    ("GET", "/integrations/dishhome/customer/DH100234"),
    ("GET", "/integrations/dishhome/router-status/ONT-KTM-882441"),
    ("GET", "/integrations/dishhome/tickets"),
    ("GET", "/faqs"),
    ("GET", "/voice/voices"),
    ("GET", "/campaigns"),
    ("GET", "/telephony/health"),
    ("GET", "/telephony/sessions"),
]

async def run():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Login to get a valid token
        print("Logging in...")
        login_res = await client.post("/auth/login", json={"username": "admin", "password": "dishhome123"})
        if login_res.status_code != 200:
            print("Login failed:", login_res.text)
            return
            
        token = login_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print("\n=== QA AUDIT CORRECTED ENDPOINTS RUN ===")
        for method, path in ENDPOINTS:
            try:
                if method == "GET":
                    res = await client.get(path, headers=headers)
                else:
                    res = await client.post(path, headers=headers)
                print(f"[{res.status_code}] {method} {path}")
                if res.status_code == 500:
                    print(f"  ERROR: {res.text}")
            except Exception as e:
                print(f"[EXC] {method} {path} - Exception: {e}")

if __name__ == "__main__":
    async def main():
        async with app.router.lifespan_context(app):
            await run()
    asyncio.run(main())
