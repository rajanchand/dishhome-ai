import asyncio
import asyncpg
from app.security import verify_password

async def run():
    dsn = "postgresql://postgres.azjamwbxjrjgrobunodn:Support0825%24%23%40@aws-1-eu-north-1.pooler.supabase.com:5432/postgres"
    conn = await asyncpg.connect(dsn)
    row = await conn.fetchrow("SELECT password_hash FROM dh.users WHERE username='admin'")
    hash_val = row['password_hash']
    print("Hash from DB:", hash_val)
    print("Verify 'dishhome123':", verify_password(hash_val, 'dishhome123'))
    await conn.close()

asyncio.run(run())
