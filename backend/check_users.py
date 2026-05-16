import asyncio
import asyncpg

async def check():
    dsn = "postgresql://postgres.azjamwbxjrjgrobunodn:Support0825%24%23%40@aws-1-eu-north-1.pooler.supabase.com:5432/postgres"
    conn = await asyncpg.connect(dsn)
    rows = await conn.fetch("SELECT username, password_hash FROM dh.users")
    for r in rows:
        print(r['username'], r['password_hash'])
    await conn.close()

asyncio.run(check())
