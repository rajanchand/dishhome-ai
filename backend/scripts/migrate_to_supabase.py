import asyncio
import os
import sys
from datetime import datetime

import asyncpg

# Add the parent directory to sys.path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import settings
from app.mock_data import CUSTOMERS, ONT_STATUS, TICKETS, USERS, CALLS


async def migrate():
    print("Connecting to Supabase (Direct Connection) for migration...")
    try:
        conn = await asyncpg.connect(
            host="aws-1-eu-north-1.pooler.supabase.com",
            port=5432,
            user="postgres.azjamwbxjrjgrobunodn",
            password="Support0825$#@",
            database="postgres"
        )
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return

    try:
        # 1. Apply Schema
        print("Applying schema.sql...")
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        await conn.execute(schema_sql)
        print("Schema applied successfully.")

        # Set search path for inserts
        await conn.execute("SET search_path TO dh, public;")

        # 2. Insert Users
        print("Inserting users...")
        for u in USERS.values():
            await conn.execute(
                """
                INSERT INTO users (username, password_hash, name, email, role)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (username) DO NOTHING
                """,
                u["username"], u["password"], u["name"], u["email"], u["role"]
            )

        # 3. Insert Customers
        print("Inserting customers...")
        for c in CUSTOMERS.values():
            due_date = datetime.strptime(c["due_date"], "%Y-%m-%d").date() if c["due_date"] else None
            await conn.execute(
                """
                INSERT INTO customers (
                    customer_id, name, mobile, smartcard, address, ward, package, 
                    balance_npr, due_date, status, ont_id, scenario
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (customer_id) DO NOTHING
                """,
                c["customer_id"], c["name"], c["mobile"], c["smartcard"], c["address"],
                c["ward"], c["package"], c["balance_npr"], due_date, c["status"],
                c["ont_id"], c["scenario"]
            )

        # 4. Insert ONT Status
        print("Inserting ONT statuses...")
        for o in ONT_STATUS.values():
            last_reboot = datetime.fromisoformat(o["last_reboot"].replace("Z", "+00:00")) if o["last_reboot"] else None
            await conn.execute(
                """
                INSERT INTO ont_status (
                    ont_id, device_model, serial_number, firmware_version, hardware_version,
                    olt_id, olt_port, ont_index, online, rx_power_dbm, tx_power_dbm, 
                    line_attenuation_db, uptime_hours, last_reboot, pppoe_session,
                    wifi_radio_2g, wifi_radio_5g, error_state, area_outage, scenario
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
                ON CONFLICT (ont_id) DO NOTHING
                """,
                o["ont_id"], o.get("device_model"), o.get("serial_number"), o.get("firmware_version"),
                o.get("hardware_version"), o.get("olt_id"), o.get("olt_port"), o.get("ont_index"),
                o.get("online", True), o.get("rx_power_dbm"), o.get("tx_power_dbm"),
                o.get("line_attenuation_db"), o.get("uptime_hours", 0), last_reboot, o.get("pppoe_session"),
                o.get("wifi_radio_2g", True), o.get("wifi_radio_5g", True), o.get("error_state"),
                o.get("area_outage", False), o.get("scenario")
            )

        # 5. Insert Tickets
        print("Inserting tickets...")
        for t in TICKETS:
            created_at = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) if t["created_at"] else None
            await conn.execute(
                """
                INSERT INTO tickets (
                    id, customer_id, issue, priority, status, assigned_team, eta_minutes, created_at, labels
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (id) DO NOTHING
                """,
                t["id"], t["customer_id"], t["issue"], t["priority"], t["status"], 
                t["assigned_team"], t["eta_minutes"], created_at, t.get("labels", [])
            )
            
        import json
        
        # 6. Insert Calls
        print("Inserting calls...")
        for c in CALLS:
            started_at = datetime.fromisoformat(c["started_at"].replace("Z", "+00:00")) if c["started_at"] else None
            ended_at = datetime.fromisoformat(c["ended_at"].replace("Z", "+00:00")) if c["ended_at"] else None
            await conn.execute(
                """
                INSERT INTO calls (
                    id, caller_number, called_number, customer_id, customer_name, language,
                    started_at, ended_at, duration_sec, status, resolution, intent,
                    ai_confidence, sentiment, labels, transcript
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16::jsonb)
                ON CONFLICT (id) DO NOTHING
                """,
                c["id"], c["caller_number"], c["called_number"], c["customer_id"], c["customer_name"],
                c["language"], started_at, ended_at, c.get("duration_sec"), c["status"],
                c.get("resolution"), c.get("intent"), c.get("ai_confidence"), c.get("sentiment"),
                c.get("labels", []), json.dumps(c.get("transcript", []))
            )

        print("Migration complete! All mock data inserted into Supabase Postgres.")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
