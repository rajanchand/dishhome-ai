"""In-memory mock data. Replace with real DB + DishHome system integration in production."""

from datetime import datetime, timedelta, timezone


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------- Customers (DishHome subscribers) ----------------
CUSTOMERS: dict[str, dict] = {
    "DH100234": {
        "customer_id": "DH100234",
        "name": "Suresh Shrestha",
        "mobile": "9841234567",
        "smartcard": "SC-4429981",
        "address": "Baluwatar, Kathmandu",
        "package": "FTTH 60 Mbps Unlimited",
        "balance_npr": 0,
        "due_date": "2026-05-22",
        "status": "active",
        "ont_id": "ONT-KTM-882441",
    },
    "DH100997": {
        "customer_id": "DH100997",
        "name": "Aarati Khadka",
        "mobile": "9802112233",
        "smartcard": "SC-4429120",
        "address": "Pokhara-15, Lakeside",
        "package": "FTTH 100 Mbps Unlimited",
        "balance_npr": 1499,
        "due_date": "2026-05-10",
        "status": "overdue",
        "ont_id": "ONT-PKR-110028",
    },
    "DH101452": {
        "customer_id": "DH101452",
        "name": "Bikash Tamang",
        "mobile": "9818776655",
        "smartcard": "SC-4430018",
        "address": "Itahari-7, Sunsari",
        "package": "FTTH 40 Mbps + DTH Combo",
        "balance_npr": 0,
        "due_date": "2026-06-01",
        "status": "active",
        "ont_id": "ONT-ITH-330091",
    },
}


def find_customer(query: str) -> dict | None:
    q = (query or "").strip()
    if not q:
        return None
    if q in CUSTOMERS:
        return CUSTOMERS[q]
    for cust in CUSTOMERS.values():
        if cust["mobile"] == q or cust["smartcard"] == q:
            return cust
    return None


# ---------------- ONT / network status ----------------
ONT_STATUS: dict[str, dict] = {
    "ONT-KTM-882441": {
        "ont_id": "ONT-KTM-882441",
        "online": True,
        "rx_power_dbm": -22.4,
        "tx_power_dbm": 2.1,
        "uptime_hours": 142,
        "last_reboot": (_now() - timedelta(hours=142)).isoformat(),
        "pppoe_session": "active",
        "area_outage": False,
    },
    "ONT-PKR-110028": {
        "ont_id": "ONT-PKR-110028",
        "online": False,
        "rx_power_dbm": None,
        "tx_power_dbm": None,
        "uptime_hours": 0,
        "last_reboot": (_now() - timedelta(hours=8)).isoformat(),
        "pppoe_session": "disconnected",
        "area_outage": True,
    },
    "ONT-ITH-330091": {
        "ont_id": "ONT-ITH-330091",
        "online": True,
        "rx_power_dbm": -25.8,
        "tx_power_dbm": 1.9,
        "uptime_hours": 17,
        "last_reboot": (_now() - timedelta(hours=17)).isoformat(),
        "pppoe_session": "active",
        "area_outage": False,
    },
}


# ---------------- Calls (in-memory log) ----------------
CALLS: list[dict] = [
    {
        "id": "call_01HZX7A",
        "caller_number": "9841234567",
        "called_number": "16600122000",
        "customer_id": "DH100234",
        "customer_name": "Suresh Shrestha",
        "language": "ne",
        "started_at": (_now() - timedelta(minutes=18)).isoformat(),
        "ended_at": (_now() - timedelta(minutes=15, seconds=42)).isoformat(),
        "duration_sec": 138,
        "status": "resolved",
        "resolution": "remote_reboot",
        "intent": "router_offline",
        "ai_confidence": 0.94,
        "transcript": [
            {"role": "ai", "text": "Namaste, DishHome ma swagatam chha. Ma tapailai kasari sahayog garna saktinchu?"},
            {"role": "customer", "text": "Mero internet chaldaina aja bata."},
            {"role": "ai", "text": "Tapainko customer ID dinuhos hai."},
            {"role": "customer", "text": "DH 1 0 0 2 3 4."},
            {"role": "ai", "text": "Suresh ji, malai ek chhin dinuhos — ma tapainko router check gardai chhu."},
            {"role": "ai", "text": "Router online dekhincha. Ma remote reboot garchu — 2 minute pakhanus."},
            {"role": "customer", "text": "Hunchha, dhanyabad."},
            {"role": "ai", "text": "Reboot bhayo. Ahile chalcha ki check garnuhos."},
            {"role": "customer", "text": "Ho chalyo. Dhanyabad."},
            {"role": "ai", "text": "Tapainko samasya samadhan bhayo. Aaba phone rakhdai chhu. Namaste."},
        ],
    },
    {
        "id": "call_01HZX91",
        "caller_number": "9802112233",
        "called_number": "16600122000",
        "customer_id": "DH100997",
        "customer_name": "Aarati Khadka",
        "language": "ne",
        "started_at": (_now() - timedelta(minutes=9)).isoformat(),
        "ended_at": (_now() - timedelta(minutes=5, seconds=12)).isoformat(),
        "duration_sec": 228,
        "status": "ticket_created",
        "resolution": "field_team_dispatched",
        "intent": "router_offline",
        "ai_confidence": 0.88,
        "transcript": [
            {"role": "ai", "text": "Namaste, DishHome support ma swagatam."},
            {"role": "customer", "text": "Wifi chhaina."},
            {"role": "ai", "text": "Customer ID ya mobile number dinuhos hai."},
            {"role": "customer", "text": "9 8 0 2 1 1 2 2 3 3."},
            {"role": "ai", "text": "Aarati ji, Pokhara Lakeside ma sano area outage cha. Ma ticket banauchu, field team 90 minute bhitra aainchhan."},
            {"role": "customer", "text": "Hunchha."},
            {"role": "ai", "text": "Ticket DH-T-44219 banaiyo. SMS pathayo. Dhanyabad."},
        ],
    },
    {
        "id": "call_01HZXA3",
        "caller_number": "9818776655",
        "called_number": "16600122000",
        "customer_id": "DH101452",
        "customer_name": "Bikash Tamang",
        "language": "en",
        "started_at": (_now() - timedelta(minutes=2, seconds=4)).isoformat(),
        "ended_at": None,
        "duration_sec": 124,
        "status": "in_progress",
        "resolution": None,
        "intent": "billing_inquiry",
        "ai_confidence": 0.91,
        "transcript": [
            {"role": "ai", "text": "Hello, welcome to DishHome. How can I help you?"},
            {"role": "customer", "text": "I want to check my next bill date."},
            {"role": "ai", "text": "Sure, may I have your customer ID?"},
            {"role": "customer", "text": "DH 1 0 1 4 5 2."},
            {"role": "ai", "text": "Bikash ji, your next bill is due on June 1. Anything else?"},
        ],
    },
]


# ---------------- Tickets ----------------
TICKETS: list[dict] = [
    {
        "id": "DH-T-44219",
        "customer_id": "DH100997",
        "issue": "Router offline — Lakeside area outage",
        "priority": "high",
        "status": "dispatched",
        "assigned_team": "Pokhara Field Team A",
        "eta_minutes": 90,
        "created_at": (_now() - timedelta(minutes=7)).isoformat(),
    },
]


# ---------------- AI voices ----------------
VOICES: list[dict] = [
    {"id": "dishhome-ne-female-v1", "name": "Anjali", "language": "ne", "gender": "female", "tone": "warm, professional"},
    {"id": "dishhome-ne-male-v1", "name": "Bibek", "language": "ne", "gender": "male", "tone": "confident, polite"},
    {"id": "dishhome-en-female-v1", "name": "Priya", "language": "en", "gender": "female", "tone": "friendly, clear"},
    {"id": "dishhome-en-male-v1", "name": "Arjun", "language": "en", "gender": "male", "tone": "calm, professional"},
]


# ---------------- Users (mock) ----------------
USERS = {
    "admin": {
        "username": "admin",
        "password": "dishhome123",
        "name": "Rajan Chand",
        "email": "rajanchand48@gmail.com",
        "role": "super_admin",
    },
    "supervisor": {
        "username": "supervisor",
        "password": "dishhome123",
        "name": "Sita Pandey",
        "email": "sita@dishhome.com.np",
        "role": "supervisor",
    },
    "agent": {
        "username": "agent",
        "password": "dishhome123",
        "name": "Rohan KC",
        "email": "rohan@dishhome.com.np",
        "role": "agent",
    },
}
