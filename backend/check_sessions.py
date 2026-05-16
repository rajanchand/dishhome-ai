import asyncio
import asyncpg
from datetime import datetime

async def check():
    dsn = "postgresql://postgres.azjamwbxjrjgrobunodn:Support0825%24%23%40@aws-1-eu-north-1.pooler.supabase.com:5432/postgres"
    conn = await asyncpg.connect(dsn)
    rows = await conn.fetch("SELECT id, username, expires_at FROM dh.sessions")
    print(f"Found {len(rows)} sessions")
    for r in rows:
        print(f"Token: {r['id'][:8]}... User: {r['username']} Expires: {r['expires_at']}")
    await conn.close()

asyncio.run(check())
