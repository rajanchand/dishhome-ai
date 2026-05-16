import asyncio
import asyncpg
import sys

async def run():
    dsn = "postgresql://postgres.azjamwbxjrjgrobunodn:Support0825%24%23%40@aws-1-eu-north-1.pooler.supabase.com:5432/postgres"
    conn = await asyncpg.connect(dsn)
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS dh.sessions (
        token VARCHAR(100) PRIMARY KEY,
        username VARCHAR(50) REFERENCES dh.users(username),
        issued_at DOUBLE PRECISION,
        expires_at DOUBLE PRECISION,
        last_seen DOUBLE PRECISION,
        issued_ip VARCHAR(50),
        user_agent TEXT,
        last_ip VARCHAR(50)
    );
    """)
    await conn.close()
    print("Sessions table created.")

if __name__ == "__main__":
    asyncio.run(run())
