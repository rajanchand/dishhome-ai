"""In-memory mock data for the DishHome AI Call Center scaffold.

In production replace these with adapters to the real DishHome systems:
  - billing/CRM (Freeside / Splynx / in-house)
  - Huawei OLT + iManager U2000 (ONT diagnostics, remote reboot)
  - RADIUS / PPPoE for session state
  - NMS (Zabbix / LibreNMS) for outage flags
  - Ticketing + SMS gateway (Sparrow / Sociair / NT BulkSMS)

Every dict here has a single owner and matches the shape returned by the
public API. The frontend reads from those endpoints — never from this module
directly — so swapping mocks for real adapters is a one-file change.
"""

from datetime import datetime, timedelta, timezone


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(delta_minutes: int = 0) -> str:
    return (_now() - timedelta(minutes=delta_minutes)).isoformat()


# ============================================================
# Customers — covers every common ISP support scenario
# ============================================================
# Huawei ONT models used by DishHome in the field:
#   - EG8145V5  (GPON, 4 GE + 2 POTS + WiFi)
#   - HG8145V5  (GPON, 4 GE + 2 POTS + WiFi)
#   - EG8245H5  (GPON, 4 GE + 2 POTS + WiFi 5)
#   - HN8145V6  (XGS-PON dual-band WiFi 6)
CUSTOMERS: dict[str, dict] = {
    "DH100234": {
        "customer_id": "DH100234",
        "name": "Suresh Shrestha",
        "mobile": "9841234567",
        "smartcard": "SC-4429981",
        "address": "Baluwatar, Kathmandu",
        "ward": "Kathmandu-4",
        "package": "FTTH 60 Mbps Unlimited",
        "balance_npr": 0,
        "due_date": "2026-05-22",
        "status": "active",
        "ont_id": "ONT-KTM-882441",
        "scenario": "healthy",
    },
    "DH100997": {
        "customer_id": "DH100997",
        "name": "Aarati Khadka",
        "mobile": "9802112233",
        "smartcard": "SC-4429120",
        "address": "Pokhara-15, Lakeside",
        "ward": "Pokhara-15",
        "package": "FTTH 100 Mbps Unlimited",
        "balance_npr": 1499,
        "due_date": "2026-05-10",
        "status": "overdue",
        "ont_id": "ONT-PKR-110028",
        "scenario": "area_outage",
    },
    "DH101452": {
        "customer_id": "DH101452",
        "name": "Bikash Tamang",
        "mobile": "9818776655",
        "smartcard": "SC-4430018",
        "address": "Itahari-7, Sunsari",
        "ward": "Itahari-7",
        "package": "FTTH 40 Mbps + DTH Combo",
        "balance_npr": 0,
        "due_date": "2026-06-01",
        "status": "active",
        "ont_id": "ONT-ITH-330091",
        "scenario": "healthy",
    },
    "DH102881": {
        "customer_id": "DH102881",
        "name": "Sita Adhikari",
        "mobile": "9843022119",
        "smartcard": "SC-4430887",
        "address": "Naxal, Kathmandu",
        "ward": "Kathmandu-1",
        "package": "FTTH 100 Mbps Unlimited",
        "balance_npr": 0,
        "due_date": "2026-05-30",
        "status": "active",
        "ont_id": "ONT-KTM-901221",
        "scenario": "router_offline",
    },
    "DH103992": {
        "customer_id": "DH103992",
        "name": "Pradeep Maharjan",
        "mobile": "9851011234",
        "smartcard": "SC-4431002",
        "address": "Lalitpur-3, Jhamsikhel",
        "ward": "Lalitpur-3",
        "package": "FTTH 200 Mbps Business",
        "balance_npr": 0,
        "due_date": "2026-06-12",
        "status": "active",
        "ont_id": "ONT-LTP-440018",
        "scenario": "low_power",
    },
    "DH104550": {
        "customer_id": "DH104550",
        "name": "Manju Karki",
        "mobile": "9809887766",
        "smartcard": "SC-4431229",
        "address": "Biratnagar-12",
        "ward": "Biratnagar-12",
        "package": "FTTH 60 Mbps Unlimited",
        "balance_npr": 0,
        "due_date": "2026-06-04",
        "status": "active",
        "ont_id": "ONT-BRT-220019",
        "scenario": "master_down",
    },
    "DH105113": {
        "customer_id": "DH105113",
        "name": "Roshan Lama",
        "mobile": "9860112299",
        "smartcard": "SC-4431667",
        "address": "Butwal-10",
        "ward": "Butwal-10",
        "package": "FTTH 100 Mbps Unlimited",
        "balance_npr": 2998,
        "due_date": "2026-04-28",
        "status": "overdue",
        "ont_id": "ONT-BTW-110078",
        "scenario": "network_down",
    },
    "DH106002": {
        "customer_id": "DH106002",
        "name": "Anjali Bhandari",
        "mobile": "9863442211",
        "smartcard": "SC-4432019",
        "address": "Hetauda-4",
        "ward": "Hetauda-4",
        "package": "FTTH 40 Mbps Unlimited",
        "balance_npr": 0,
        "due_date": "2026-06-09",
        "status": "active",
        "ont_id": "ONT-HTD-560029",
        "scenario": "pppoe_disconnected",
    },
    "DH106877": {
        "customer_id": "DH106877",
        "name": "Krishna Pandey",
        "mobile": "9841559900",
        "smartcard": "SC-4432441",
        "address": "Kirtipur, Kathmandu",
        "ward": "Kirtipur-5",
        "package": "FTTH 100 Mbps Unlimited",
        "balance_npr": 0,
        "due_date": "2026-05-25",
        "status": "active",
        "ont_id": "ONT-KTM-998812",
        "scenario": "wifi_only_issue",
    },
    "DH107311": {
        "customer_id": "DH107311",
        "name": "Sunita Rai",
        "mobile": "9866220011",
        "smartcard": "SC-4432809",
        "address": "Dharan-15",
        "ward": "Dharan-15",
        "package": "FTTH 200 Mbps Business",
        "balance_npr": 0,
        "due_date": "2026-06-15",
        "status": "active",
        "ont_id": "ONT-DHR-440091",
        "scenario": "healthy",
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


# ============================================================
# Huawei ONT diagnostics (per customer, modeled on iManager U2000)
# ============================================================
# Realistic Huawei fields:
#   - device_model (EG8145V5 / HG8145V5 / HN8145V6 / EG8245H5)
#   - serial_number, firmware_version, hardware_version
#   - rx_power_dbm  (good: -8..-28; warn: -28..-30; bad: <-30 or null)
#   - tx_power_dbm  (typical 1.5..3.5)
#   - line_attenuation_db
#   - olt_id, olt_port, ont_index   (uplink path)
#   - pppoe_session ("active" | "disconnected" | "auth_failed")
#   - uptime_hours
#   - wifi_radio_2g / wifi_radio_5g booleans
#   - error_state (None or "los"=loss of signal, "lof"=loss of frame, "dying_gasp")

ONT_STATUS: dict[str, dict] = {
    "ONT-KTM-882441": {
        "ont_id": "ONT-KTM-882441",
        "device_model": "HN8145V6",
        "serial_number": "HWTC8C8E1D44",
        "firmware_version": "V5R020C00S280",
        "hardware_version": "HN8145V6.A",
        "olt_id": "OLT-KTM-CORE-01",
        "olt_port": "0/3/12",
        "ont_index": 18,
        "online": True,
        "rx_power_dbm": -22.4,
        "tx_power_dbm": 2.1,
        "line_attenuation_db": 18.6,
        "uptime_hours": 142,
        "last_reboot": _iso(142 * 60),
        "pppoe_session": "active",
        "wifi_radio_2g": True,
        "wifi_radio_5g": True,
        "error_state": None,
        "area_outage": False,
        "scenario": "healthy",
    },
    "ONT-PKR-110028": {
        "ont_id": "ONT-PKR-110028",
        "device_model": "EG8145V5",
        "serial_number": "HWTC1C2A9B07",
        "firmware_version": "V5R019C00S160",
        "hardware_version": "EG8145V5.A",
        "olt_id": "OLT-PKR-LAKESIDE-02",
        "olt_port": "0/2/04",
        "ont_index": 9,
        "online": False,
        "rx_power_dbm": None,
        "tx_power_dbm": None,
        "line_attenuation_db": None,
        "uptime_hours": 0,
        "last_reboot": _iso(8 * 60),
        "pppoe_session": "disconnected",
        "wifi_radio_2g": False,
        "wifi_radio_5g": False,
        "error_state": "los",
        "area_outage": True,
        "scenario": "area_outage",
    },
    "ONT-ITH-330091": {
        "ont_id": "ONT-ITH-330091",
        "device_model": "HG8145V5",
        "serial_number": "HWTC4D1E2F88",
        "firmware_version": "V5R019C10S110",
        "hardware_version": "HG8145V5.A",
        "olt_id": "OLT-ITH-CORE-01",
        "olt_port": "0/4/06",
        "ont_index": 22,
        "online": True,
        "rx_power_dbm": -25.8,
        "tx_power_dbm": 1.9,
        "line_attenuation_db": 21.0,
        "uptime_hours": 17,
        "last_reboot": _iso(17 * 60),
        "pppoe_session": "active",
        "wifi_radio_2g": True,
        "wifi_radio_5g": True,
        "error_state": None,
        "area_outage": False,
        "scenario": "healthy",
    },
    "ONT-KTM-901221": {
        "ont_id": "ONT-KTM-901221",
        "device_model": "EG8245H5",
        "serial_number": "HWTC6A2B71C2",
        "firmware_version": "V5R019C10S190",
        "hardware_version": "EG8245H5.A",
        "olt_id": "OLT-KTM-CORE-01",
        "olt_port": "0/3/16",
        "ont_index": 3,
        "online": False,
        "rx_power_dbm": None,
        "tx_power_dbm": None,
        "line_attenuation_db": None,
        "uptime_hours": 0,
        "last_reboot": _iso(3 * 60),
        "pppoe_session": "disconnected",
        "wifi_radio_2g": False,
        "wifi_radio_5g": False,
        "error_state": "dying_gasp",
        "area_outage": False,
        "scenario": "router_offline",
    },
    "ONT-LTP-440018": {
        "ont_id": "ONT-LTP-440018",
        "device_model": "HN8145V6",
        "serial_number": "HWTCAA1144EE",
        "firmware_version": "V5R020C00S260",
        "hardware_version": "HN8145V6.A",
        "olt_id": "OLT-LTP-CORE-01",
        "olt_port": "0/1/02",
        "ont_index": 14,
        "online": True,
        "rx_power_dbm": -31.4,   # low power — fiber attenuation issue
        "tx_power_dbm": 2.7,
        "line_attenuation_db": 28.9,
        "uptime_hours": 412,
        "last_reboot": _iso(412 * 60),
        "pppoe_session": "active",
        "wifi_radio_2g": True,
        "wifi_radio_5g": True,
        "error_state": "low_rx_power",
        "area_outage": False,
        "scenario": "low_power",
    },
    "ONT-BRT-220019": {
        "ont_id": "ONT-BRT-220019",
        "device_model": "EG8145V5",
        "serial_number": "HWTC22002211",
        "firmware_version": "V5R019C00S160",
        "hardware_version": "EG8145V5.A",
        "olt_id": "OLT-BRT-CORE-01",  # ← THIS OLT is down
        "olt_port": "0/2/11",
        "ont_index": 6,
        "online": False,
        "rx_power_dbm": None,
        "tx_power_dbm": None,
        "line_attenuation_db": None,
        "uptime_hours": 0,
        "last_reboot": _iso(35),
        "pppoe_session": "disconnected",
        "wifi_radio_2g": False,
        "wifi_radio_5g": False,
        "error_state": "olt_unreachable",
        "area_outage": True,
        "scenario": "master_down",
    },
    "ONT-BTW-110078": {
        "ont_id": "ONT-BTW-110078",
        "device_model": "HG8145V5",
        "serial_number": "HWTC78001100",
        "firmware_version": "V5R019C10S100",
        "hardware_version": "HG8145V5.A",
        "olt_id": "OLT-BTW-CORE-01",
        "olt_port": "0/3/09",
        "ont_index": 11,
        "online": False,
        "rx_power_dbm": None,
        "tx_power_dbm": None,
        "line_attenuation_db": None,
        "uptime_hours": 0,
        "last_reboot": _iso(120),
        "pppoe_session": "disconnected",
        "wifi_radio_2g": False,
        "wifi_radio_5g": False,
        "error_state": "uplink_down",
        "area_outage": True,
        "scenario": "network_down",
    },
    "ONT-HTD-560029": {
        "ont_id": "ONT-HTD-560029",
        "device_model": "EG8145V5",
        "serial_number": "HWTC56002900",
        "firmware_version": "V5R019C00S160",
        "hardware_version": "EG8145V5.A",
        "olt_id": "OLT-HTD-CORE-01",
        "olt_port": "0/1/04",
        "ont_index": 19,
        "online": True,
        "rx_power_dbm": -24.1,
        "tx_power_dbm": 2.3,
        "line_attenuation_db": 20.5,
        "uptime_hours": 89,
        "last_reboot": _iso(89 * 60),
        "pppoe_session": "auth_failed",   # PPPoE credentials issue
        "wifi_radio_2g": True,
        "wifi_radio_5g": True,
        "error_state": None,
        "area_outage": False,
        "scenario": "pppoe_disconnected",
    },
    "ONT-KTM-998812": {
        "ont_id": "ONT-KTM-998812",
        "device_model": "HN8145V6",
        "serial_number": "HWTC99881200",
        "firmware_version": "V5R020C00S280",
        "hardware_version": "HN8145V6.A",
        "olt_id": "OLT-KTM-CORE-02",
        "olt_port": "0/2/07",
        "ont_index": 8,
        "online": True,
        "rx_power_dbm": -21.0,
        "tx_power_dbm": 2.0,
        "line_attenuation_db": 17.8,
        "uptime_hours": 240,
        "last_reboot": _iso(240 * 60),
        "pppoe_session": "active",
        "wifi_radio_2g": True,    # WiFi 2.4 working
        "wifi_radio_5g": False,   # WiFi 5G off — customer WiFi-only issue
        "error_state": None,
        "area_outage": False,
        "scenario": "wifi_only_issue",
    },
    "ONT-DHR-440091": {
        "ont_id": "ONT-DHR-440091",
        "device_model": "HN8145V6",
        "serial_number": "HWTC44009100",
        "firmware_version": "V5R020C00S280",
        "hardware_version": "HN8145V6.A",
        "olt_id": "OLT-DHR-CORE-01",
        "olt_port": "0/1/12",
        "ont_index": 5,
        "online": True,
        "rx_power_dbm": -19.6,
        "tx_power_dbm": 2.4,
        "line_attenuation_db": 16.0,
        "uptime_hours": 720,
        "last_reboot": _iso(720 * 60),
        "pppoe_session": "active",
        "wifi_radio_2g": True,
        "wifi_radio_5g": True,
        "error_state": None,
        "area_outage": False,
        "scenario": "healthy",
    },
}


# OLT (master device) status — when an OLT is down, every ONT under it goes dark.
OLT_STATUS: dict[str, dict] = {
    "OLT-KTM-CORE-01": {"olt_id": "OLT-KTM-CORE-01", "site": "Kathmandu Core", "online": True, "active_onts": 248, "uptime_hours": 4400},
    "OLT-KTM-CORE-02": {"olt_id": "OLT-KTM-CORE-02", "site": "Kathmandu Core 2", "online": True, "active_onts": 191, "uptime_hours": 3120},
    "OLT-PKR-LAKESIDE-02": {"olt_id": "OLT-PKR-LAKESIDE-02", "site": "Pokhara Lakeside", "online": True, "active_onts": 142, "uptime_hours": 1800, "degraded": True},
    "OLT-ITH-CORE-01": {"olt_id": "OLT-ITH-CORE-01", "site": "Itahari Core", "online": True, "active_onts": 96, "uptime_hours": 5600},
    "OLT-LTP-CORE-01": {"olt_id": "OLT-LTP-CORE-01", "site": "Lalitpur Core", "online": True, "active_onts": 188, "uptime_hours": 2900},
    "OLT-BRT-CORE-01": {"olt_id": "OLT-BRT-CORE-01", "site": "Biratnagar Core", "online": False, "active_onts": 0, "uptime_hours": 0},
    "OLT-BTW-CORE-01": {"olt_id": "OLT-BTW-CORE-01", "site": "Butwal Core", "online": True, "active_onts": 124, "uptime_hours": 1100, "degraded": True},
    "OLT-HTD-CORE-01": {"olt_id": "OLT-HTD-CORE-01", "site": "Hetauda Core", "online": True, "active_onts": 78, "uptime_hours": 4100},
    "OLT-DHR-CORE-01": {"olt_id": "OLT-DHR-CORE-01", "site": "Dharan Core", "online": True, "active_onts": 64, "uptime_hours": 6200},
}


# Diagnostic narratives — what to tell the customer for each scenario
SCENARIO_BLURBS: dict[str, dict] = {
    "healthy": {
        "headline": "All systems normal",
        "tone": "info",
        "advice": "Service is healthy. If the customer reports issues, check WiFi config and connected devices.",
    },
    "router_offline": {
        "headline": "ONT is offline (dying-gasp signal seen)",
        "tone": "danger",
        "advice": "Last signal from the ONT was a 'dying gasp' (power loss). Ask the customer to check the power adapter and the LED status. If power LED is dead, dispatch field team.",
    },
    "area_outage": {
        "headline": "Area outage active",
        "tone": "danger",
        "advice": "NMS reports an outage in this area. Inform the customer of the outage and ETA. Do NOT dispatch field team — wait for area restoration.",
    },
    "master_down": {
        "headline": "Upstream OLT is down",
        "tone": "danger",
        "advice": "The OLT serving this customer is offline. All customers on that OLT are affected. Escalate to NOC immediately — this is a P1 incident.",
    },
    "network_down": {
        "headline": "OLT uplink degraded",
        "tone": "warn",
        "advice": "OLT is up but uplink is unstable. Service may be intermittent. NOC is aware.",
    },
    "low_power": {
        "headline": "Low RX power (below threshold)",
        "tone": "warn",
        "advice": "RX power is below -30 dBm. Likely dirty / bent fiber or a bad splice. Dispatch field team for fiber inspection.",
    },
    "pppoe_disconnected": {
        "headline": "PPPoE authentication failed",
        "tone": "warn",
        "advice": "Hardware is online but PPPoE auth is failing. Trigger a session reset from RADIUS. If it persists, check credentials in CRM.",
    },
    "wifi_only_issue": {
        "headline": "WiFi 5G radio is off",
        "tone": "info",
        "advice": "Internet is reaching the ONT but the 5GHz radio is disabled. Guide the customer through enabling it, or remotely re-enable via TR-069.",
    },
}


# ============================================================
# Calls (in-memory log) — already shaped for the conversation pane
# ============================================================
CALLS: list[dict] = [
    {
        "id": "call_01HZX7A",
        "caller_number": "9841234567",
        "called_number": "16600122000",
        "customer_id": "DH100234",
        "customer_name": "Suresh Shrestha",
        "language": "ne",
        "started_at": _iso(18),
        "ended_at": _iso(15),
        "duration_sec": 138,
        "status": "resolved",
        "resolution": "remote_reboot",
        "intent": "router_offline",
        "ai_confidence": 0.94,
        "sentiment": "positive",
        "labels": ["resolved-by-ai", "router"],
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
        "started_at": _iso(9),
        "ended_at": _iso(5),
        "duration_sec": 228,
        "status": "ticket_created",
        "resolution": "field_team_dispatched",
        "intent": "router_offline",
        "ai_confidence": 0.88,
        "sentiment": "neutral",
        "labels": ["outage", "pokhara"],
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
        "started_at": _iso(2),
        "ended_at": None,
        "duration_sec": 124,
        "status": "in_progress",
        "resolution": None,
        "intent": "billing_inquiry",
        "ai_confidence": 0.91,
        "sentiment": "positive",
        "labels": ["billing"],
        "transcript": [
            {"role": "ai", "text": "Hello, welcome to DishHome. How can I help you?"},
            {"role": "customer", "text": "I want to check my next bill date."},
            {"role": "ai", "text": "Sure, may I have your customer ID?"},
            {"role": "customer", "text": "DH 1 0 1 4 5 2."},
            {"role": "ai", "text": "Bikash ji, your next bill is due on June 1. Anything else?"},
        ],
    },
    {
        "id": "call_01HZXB5",
        "caller_number": "9851011234",
        "called_number": "16600122000",
        "customer_id": "DH103992",
        "customer_name": "Pradeep Maharjan",
        "language": "ne",
        "started_at": _iso(33),
        "ended_at": _iso(30),
        "duration_sec": 192,
        "status": "ticket_created",
        "resolution": "field_team_dispatched",
        "intent": "slow_internet",
        "ai_confidence": 0.83,
        "sentiment": "negative",
        "labels": ["fiber-attenuation", "field-dispatch"],
        "transcript": [
            {"role": "customer", "text": "Net dherai dhilo bhayo aaja."},
            {"role": "ai", "text": "Tapainko ONT ko RX power check gardai chu… RX -31 dBm cha, fiber bhitra problem cha."},
            {"role": "ai", "text": "Field team aune ho. Ticket banauchu."},
        ],
    },
]


# ============================================================
# Tickets, labels, saved replies, contacts, conversations, FAQs, campaigns
# ============================================================
LABELS: list[dict] = [
    {"id": "lbl_router", "name": "Router", "color": "#2563eb"},
    {"id": "lbl_billing", "name": "Billing", "color": "#f59e0b"},
    {"id": "lbl_outage", "name": "Outage", "color": "#dc2626"},
    {"id": "lbl_vip", "name": "VIP", "color": "#8b5cf6"},
    {"id": "lbl_new_install", "name": "New install", "color": "#10b981"},
    {"id": "lbl_followup", "name": "Follow-up", "color": "#0ea5e9"},
    {"id": "lbl_complaint", "name": "Complaint", "color": "#e11d48"},
    {"id": "lbl_resolved_ai", "name": "Resolved by AI", "color": "#14b8a6"},
]


SAVED_REPLIES: list[dict] = [
    {
        "id": "rep_greeting_ne",
        "title": "Greeting (Nepali)",
        "body": "Namaste, DishHome customer care ma swagatam chha. Ma tapainlai kasari sahayog garna saktinchu?",
        "language": "ne",
    },
    {
        "id": "rep_greeting_en",
        "title": "Greeting (English)",
        "body": "Hello, welcome to DishHome customer care. How may I help you today?",
        "language": "en",
    },
    {
        "id": "rep_reboot",
        "title": "Remote reboot scheduled",
        "body": "Tapainko router malai remote bata reboot garchu — 2 minute bhitra phir try garnuhos.",
        "language": "ne",
    },
    {
        "id": "rep_ticket",
        "title": "Ticket created",
        "body": "Ticket {ticket_id} banaiyo. Field team {eta} minute bhitra aainchhan. Update SMS bata pathaune chau.",
        "language": "ne",
    },
    {
        "id": "rep_outage",
        "title": "Area outage notice",
        "body": "Hami {area} ma area outage report gareko chau. Restoration ETA {eta}. Dhanyabad tapainko sahayog ko lagi.",
        "language": "ne",
    },
    {
        "id": "rep_billing_due",
        "title": "Billing reminder",
        "body": "Tapainko {package} ko bill NPR {amount} due cha mati {due_date}. eSewa, Khalti, IME Pay bata payment garna sakincha.",
        "language": "ne",
    },
]


CONTACTS: list[dict] = [
    {
        "id": "ct_001",
        "name": "Suresh Shrestha",
        "mobile": "9841234567",
        "email": "suresh@example.com",
        "customer_id": "DH100234",
        "labels": ["lbl_router", "lbl_resolved_ai"],
        "last_contacted_at": _iso(18),
        "notes": "Reliable customer. Prefers Nepali. WhatsApp friendly.",
    },
    {
        "id": "ct_002",
        "name": "Aarati Khadka",
        "mobile": "9802112233",
        "email": "aarati.k@example.com",
        "customer_id": "DH100997",
        "labels": ["lbl_outage", "lbl_billing"],
        "last_contacted_at": _iso(9),
        "notes": "Pokhara Lakeside. Had outage 2026-05-14.",
    },
    {
        "id": "ct_003",
        "name": "Bikash Tamang",
        "mobile": "9818776655",
        "email": None,
        "customer_id": "DH101452",
        "labels": ["lbl_billing"],
        "last_contacted_at": _iso(2),
        "notes": "Combo package. Business hours preferred.",
    },
    {
        "id": "ct_004",
        "name": "Pradeep Maharjan",
        "mobile": "9851011234",
        "email": "pradeep.m@example.com",
        "customer_id": "DH103992",
        "labels": ["lbl_complaint", "lbl_followup", "lbl_vip"],
        "last_contacted_at": _iso(33),
        "notes": "Business plan. Sensitive to outages.",
    },
    {
        "id": "ct_005",
        "name": "Roshan Lama",
        "mobile": "9860112299",
        "email": None,
        "customer_id": "DH105113",
        "labels": ["lbl_outage", "lbl_followup"],
        "last_contacted_at": _iso(45),
        "notes": "Overdue balance. Send reminder.",
    },
    {
        "id": "ct_006",
        "name": "Sita Adhikari",
        "mobile": "9843022119",
        "email": None,
        "customer_id": "DH102881",
        "labels": ["lbl_router"],
        "last_contacted_at": None,
        "notes": "New customer (installed last month).",
    },
]


CONVERSATIONS: list[dict] = [
    {
        "id": "conv_001",
        "channel": "voice",
        "contact_id": "ct_001",
        "subject": "Router offline (resolved by AI)",
        "labels": ["lbl_router", "lbl_resolved_ai"],
        "status": "closed",
        "last_message_at": _iso(15),
        "messages": [
            {"author": "customer", "at": _iso(18), "body": "Internet chhaina."},
            {"author": "ai", "at": _iso(17), "body": "Customer ID dinuhos."},
            {"author": "customer", "at": _iso(17), "body": "DH 1 0 0 2 3 4."},
            {"author": "ai", "at": _iso(16), "body": "Remote reboot garchu."},
            {"author": "ai", "at": _iso(15), "body": "Bhayo. Aaba chalcha."},
        ],
    },
    {
        "id": "conv_002",
        "channel": "voice",
        "contact_id": "ct_002",
        "subject": "Area outage — field dispatched",
        "labels": ["lbl_outage"],
        "status": "open",
        "last_message_at": _iso(5),
        "messages": [
            {"author": "customer", "at": _iso(9), "body": "WiFi chhaina."},
            {"author": "ai", "at": _iso(8), "body": "Lakeside ma outage cha."},
            {"author": "ai", "at": _iso(7), "body": "Ticket DH-T-44219 banaiyo."},
            {"author": "agent", "at": _iso(5), "body": "Field team dispatched. ETA 90m."},
        ],
    },
    {
        "id": "conv_003",
        "channel": "sms",
        "contact_id": "ct_004",
        "subject": "Slow internet complaint",
        "labels": ["lbl_complaint", "lbl_vip"],
        "status": "open",
        "last_message_at": _iso(30),
        "messages": [
            {"author": "customer", "at": _iso(35), "body": "Net dherai slow. Business affect bhayo."},
            {"author": "ai", "at": _iso(33), "body": "RX power low cha. Field team dispatch garchu."},
            {"author": "agent", "at": _iso(30), "body": "Pradeep ji, namaste — Bishnu (field eng) 2pm bhitra aainchhan."},
        ],
    },
]


FAQS: list[dict] = [
    {
        "id": "faq_001",
        "question_en": "What is DishHome's monthly internet package price?",
        "question_ne": "DishHome ko monthly internet package ko mulya kati ho?",
        "answer_en": "Our FTTH packages start at NPR 999 (40 Mbps), NPR 1499 (60 Mbps), NPR 1999 (100 Mbps), and NPR 3499 (200 Mbps Business). Prices include 13% VAT.",
        "answer_ne": "Hamro FTTH package NPR 999 dekhi suru hunchha (40 Mbps), NPR 1499 (60 Mbps), NPR 1999 (100 Mbps), ra NPR 3499 (200 Mbps Business). 13% VAT include cha.",
        "category": "billing",
        "tags": ["pricing", "package"],
    },
    {
        "id": "faq_002",
        "question_en": "How do I reset my WiFi password?",
        "question_ne": "WiFi password kasari change garne?",
        "answer_en": "Open the router admin page at 192.168.1.1, log in with username 'telecomadmin' and the default password printed on the back of your ONT. Go to WLAN settings and change the WPA key.",
        "answer_ne": "Browser ma 192.168.1.1 type garnuhos, 'telecomadmin' username ra ONT ko pachadi lekheko default password le login garnuhos. WLAN ma gayera password change garnuhos.",
        "category": "router",
        "tags": ["wifi", "password"],
    },
    {
        "id": "faq_003",
        "question_en": "My internet is not working — what should I do first?",
        "question_ne": "Internet chaldaina — ke garne pahile?",
        "answer_en": "Check the LED on your ONT. If the LOS LED is red, fiber is disconnected — contact support. If only the PON LED is blinking, restart the router by unplugging power for 30 seconds.",
        "answer_ne": "ONT ko LED check garnuhos. LOS LED rato cha bhane fiber disconnect chha — support lai call garnuhos. PON LED matra blink cha bhane router ko power 30 second ko lagi off-on garnuhos.",
        "category": "troubleshooting",
        "tags": ["offline", "led"],
    },
    {
        "id": "faq_004",
        "question_en": "How do I pay my DishHome bill online?",
        "question_ne": "DishHome ko bill online kasari tirne?",
        "answer_en": "You can pay via eSewa, Khalti, IME Pay, ConnectIPS, or any commercial bank's mobile app — search for 'DishHome' and enter your customer ID.",
        "answer_ne": "eSewa, Khalti, IME Pay, ConnectIPS ya kunai pani bank ko mobile app bata payment garna sakincha — 'DishHome' search garera customer ID enter garnuhos.",
        "category": "billing",
        "tags": ["payment", "esewa", "khalti"],
    },
    {
        "id": "faq_005",
        "question_en": "What does the LOS red light on my router mean?",
        "question_ne": "Router ma LOS rato batti ko matlab ke?",
        "answer_en": "LOS = Loss of Signal. The fiber cable to your home is disconnected, damaged, or there is an area outage. Please call 16600122000.",
        "answer_ne": "LOS = Loss of Signal. Tapaiko gharma fiber cable disconnect bhayeko, damage bhayeko, ya area outage cha. 16600122000 ma call garnuhos.",
        "category": "troubleshooting",
        "tags": ["led", "fiber", "los"],
    },
    {
        "id": "faq_006",
        "question_en": "How long does new fiber installation take?",
        "question_ne": "Naya fiber installation kati samaya lagcha?",
        "answer_en": "Within Kathmandu Valley, installation usually completes within 48 hours of payment. Outside the valley, allow 3–7 business days.",
        "answer_ne": "Kathmandu Valley bhitra payment paachi 48 ghanta bhitra installation hunchha. Valley bahira 3–7 business day lagcha.",
        "category": "new-install",
        "tags": ["installation", "fiber"],
    },
    {
        "id": "faq_007",
        "question_en": "Can I upgrade my internet package mid-month?",
        "question_ne": "Bicha mahina ma package upgrade garna sakincha?",
        "answer_en": "Yes — call 16600122000 or upgrade from the customer portal. Pro-rated charges apply for the remaining days of your current billing cycle.",
        "answer_ne": "Hunchha — 16600122000 ma call garnuhos ya customer portal bata upgrade garnuhos. Baki dinharu ko lagi pro-rated charge lagcha.",
        "category": "billing",
        "tags": ["upgrade", "package"],
    },
    {
        "id": "faq_008",
        "question_en": "Why is my WiFi slow but ONT shows online?",
        "question_ne": "Internet aairaheko cha tara WiFi slow chha — kina?",
        "answer_en": "WiFi range or interference. Try (1) moving closer to the router, (2) switching to 5GHz band, (3) restarting the router. If multiple devices are connected, bandwidth is shared.",
        "answer_ne": "WiFi range ya interference. (1) Router najik jaanuhos, (2) 5GHz band ma switch garnuhos, (3) router restart garnuhos. Dherai device connect cha bhane bandwidth share hunchha.",
        "category": "troubleshooting",
        "tags": ["wifi", "slow"],
    },
]


CAMPAIGNS: list[dict] = [
    {
        "id": "camp_001",
        "name": "Overdue payment reminder — May 2026",
        "language": "ne",
        "voice_id": "dishhome-ne-female-v1",
        "script": "Namaste, DishHome bata. Tapainko bill {amount} rupaiya due cha. Krapaya eSewa, Khalti, ya IME Pay bata payment garidinuhos. Dhanyabad.",
        "status": "draft",
        "contacts_count": 0,
        "created_at": _iso(60 * 24 * 2),
        "started_at": None,
        "completed_at": None,
        "stats": {"dialed": 0, "connected": 0, "completed": 0, "failed": 0},
    },
    {
        "id": "camp_002",
        "name": "Customer satisfaction survey — Q2",
        "language": "ne",
        "voice_id": "dishhome-ne-male-v1",
        "script": "Namaste, DishHome ko taraf bata ek chhoto survey. Tapainko service ko ratings 1 dekhi 5 sammama kati dinuhuncha?",
        "status": "running",
        "contacts_count": 1200,
        "created_at": _iso(60 * 24 * 5),
        "started_at": _iso(120),
        "completed_at": None,
        "stats": {"dialed": 642, "connected": 488, "completed": 312, "failed": 154},
    },
    {
        "id": "camp_003",
        "name": "WiFi 5G upgrade outreach",
        "language": "en",
        "voice_id": "dishhome-en-female-v1",
        "script": "Hello, this is DishHome. You can now upgrade your home to dual-band WiFi 5GHz at no extra cost. Press 1 to schedule a visit.",
        "status": "completed",
        "contacts_count": 580,
        "created_at": _iso(60 * 24 * 12),
        "started_at": _iso(60 * 24 * 10),
        "completed_at": _iso(60 * 24 * 8),
        "stats": {"dialed": 580, "connected": 519, "completed": 401, "failed": 61},
    },
]


# campaign_id -> list of contacts (id, name, mobile, status, attempts, last_dialed_at)
CAMPAIGN_CONTACTS: dict[str, list[dict]] = {
    "camp_001": [],
    "camp_002": [
        {"id": "cc_001", "name": "Suresh Shrestha", "mobile": "9841234567", "status": "completed", "attempts": 1, "outcome": "rating_5"},
        {"id": "cc_002", "name": "Bikash Tamang", "mobile": "9818776655", "status": "completed", "attempts": 1, "outcome": "rating_4"},
        {"id": "cc_003", "name": "Pradeep Maharjan", "mobile": "9851011234", "status": "no_answer", "attempts": 2, "outcome": None},
        {"id": "cc_004", "name": "Manju Karki", "mobile": "9809887766", "status": "queued", "attempts": 0, "outcome": None},
        {"id": "cc_005", "name": "Sunita Rai", "mobile": "9866220011", "status": "queued", "attempts": 0, "outcome": None},
    ],
    "camp_003": [
        {"id": "cc_101", "name": "Krishna Pandey", "mobile": "9841559900", "status": "completed", "attempts": 1, "outcome": "scheduled"},
    ],
}


# ============================================================
# AI voices, users
# ============================================================
VOICES: list[dict] = [
    {"id": "dishhome-ne-female-v1", "name": "Anjali", "language": "ne", "gender": "female", "tone": "warm, professional"},
    {"id": "dishhome-ne-male-v1", "name": "Bibek", "language": "ne", "gender": "male", "tone": "confident, polite"},
    {"id": "dishhome-en-female-v1", "name": "Priya", "language": "en", "gender": "female", "tone": "friendly, clear"},
    {"id": "dishhome-en-male-v1", "name": "Arjun", "language": "en", "gender": "male", "tone": "calm, professional"},
]


USERS = {
    "admin": {
        "username": "admin",
        "password": "dishhome123",  # hashed in-place on first import (see _migrate_seed_passwords)
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


def _migrate_seed_passwords() -> None:
    """Hash any plaintext seed passwords on first import."""
    # Imported here to avoid a circular dep at module import time.
    from app.security import hash_password, is_hashed

    for u in USERS.values():
        pw = u.get("password")
        if pw and not is_hashed(pw):
            u["password"] = hash_password(pw)


_migrate_seed_passwords()


# ============================================================
# Tickets (initial seed; new ones appended at runtime)
# ============================================================
TICKETS: list[dict] = [
    {
        "id": "DH-T-44219",
        "customer_id": "DH100997",
        "issue": "Router offline — Lakeside area outage",
        "priority": "high",
        "status": "dispatched",
        "assigned_team": "Pokhara Field Team A",
        "eta_minutes": 90,
        "created_at": _iso(7),
        "labels": ["lbl_outage"],
    },
    {
        "id": "DH-T-44220",
        "customer_id": "DH103992",
        "issue": "Slow internet — low RX power on fiber",
        "priority": "high",
        "status": "dispatched",
        "assigned_team": "Lalitpur Field Team",
        "eta_minutes": 60,
        "created_at": _iso(30),
        "labels": ["lbl_complaint", "lbl_vip"],
    },
    {
        "id": "DH-T-44221",
        "customer_id": "DH104550",
        "issue": "OLT-BRT-CORE-01 down — multiple customers affected",
        "priority": "critical",
        "status": "noc_engaged",
        "assigned_team": "NOC + Biratnagar Tower Team",
        "eta_minutes": 120,
        "created_at": _iso(35),
        "labels": ["lbl_outage"],
    },
]
