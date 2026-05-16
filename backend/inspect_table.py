import asyncio
import asyncpg

async def check():
    dsn = "postgresql://postgres.azjamwbxjrjgrobunodn:Support0825%24%23%40@aws-1-eu-north-1.pooler.supabase.com:5432/postgres"
    conn = await asyncpg.connect(dsn)
    rows = await conn.fetch("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'dh' AND table_name = 'sessions'
    """)
    print(f"Table dh.sessions columns:")
    for r in rows:
        print(f"  {r['column_name']} ({r['data_type']})")
    await conn.close()

asyncio.run(check())
