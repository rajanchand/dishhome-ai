"""Khushi AI Chatbot — DishHome's bilingual customer support agent.

Khushi is DishHome's AI assistant who handles:
- Package & pricing inquiries
- Bill balance & payment questions
- Internet troubleshooting (router reboot, speed issues)
- Service area coverage
- Ticket creation & tracking
- General ISP FAQs

In the mock phase, Khushi uses pattern-matching + pre-built knowledge base.
In production, wire to an LLM (Ollama / OpenAI / Claude) with RAG over
DishHome's real CRM, billing, and knowledge-base data.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.mock_data import CUSTOMERS, TICKETS

log = logging.getLogger("dishhome.chat")
router = APIRouter(prefix="/chat", tags=["chat"])

# ── Chat session store (in-memory; migrate to Redis/Supabase in prod) ──
_SESSIONS: dict[str, list[dict]] = {}
MAX_HISTORY = 50  # per session


# ── Request / Response models ──
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=2000)
    language: str = "auto"  # "ne", "en", or "auto"


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    language: str
    suggestions: list[str] = []
    metadata: dict = {}


# ── DishHome Knowledge Base ──
KNOWLEDGE_BASE = {
    "packages": {
        "FTTH 30 Mbps": {"speed": "30 Mbps", "price": "Rs. 899/month", "type": "Fiber", "data": "Unlimited"},
        "FTTH 60 Mbps": {"speed": "60 Mbps", "price": "Rs. 1,299/month", "type": "Fiber", "data": "Unlimited"},
        "FTTH 100 Mbps": {"speed": "100 Mbps", "price": "Rs. 1,799/month", "type": "Fiber", "data": "Unlimited"},
        "FTTH 150 Mbps": {"speed": "150 Mbps", "price": "Rs. 2,499/month", "type": "Fiber", "data": "Unlimited"},
        "FTTH 200 Mbps": {"speed": "200 Mbps", "price": "Rs. 3,499/month", "type": "Fiber", "data": "Unlimited"},
        "DishHome Go": {"speed": "Varies", "price": "Rs. 499/month", "type": "4G LTE", "data": "50GB"},
    },
    "tv_packages": {
        "DishHome Basic": {"channels": "80+", "price": "Rs. 300/month"},
        "DishHome Standard": {"channels": "120+", "price": "Rs. 500/month"},
        "DishHome Premium": {"channels": "160+", "price": "Rs. 800/month"},
        "DishHome Ultra": {"channels": "200+ (4K)", "price": "Rs. 1,200/month"},
    },
    "coverage": [
        "Kathmandu Valley", "Pokhara", "Biratnagar", "Birgunj", "Dharan",
        "Butwal", "Hetauda", "Itahari", "Nepalgunj", "Bharatpur",
        "Lalitpur", "Bhaktapur", "Dhangadhi", "Janakpur",
    ],
    "payment_methods": [
        "eSewa", "Khalti", "IME Pay", "ConnectIPS", "Bank Transfer",
        "DishHome App", "DishHome Website", "Nearest DishHome Franchise",
    ],
    "support": {
        "hotline": "16600122000 (Toll Free)",
        "email": "support@dishhome.com.np",
        "hours": "24/7 AI support, Human agents 7 AM – 10 PM",
        "website": "https://www.dishhome.com.np",
    },
    "troubleshooting": {
        "no_internet": [
            "Check if your router's power light is ON",
            "Look at the LOS light — if it's RED, there's a fiber issue",
            "Restart your router (unplug for 30 seconds, then plug back in)",
            "Check if other devices can connect",
            "If the issue persists, I can create a support ticket for you",
        ],
        "slow_internet": [
            "Run a speed test at speedtest.net",
            "Try connecting via Ethernet cable instead of Wi-Fi",
            "Check if someone is downloading large files",
            "Restart your router",
            "Move closer to the Wi-Fi router",
            "If speeds are consistently low, we may need a technician visit",
        ],
        "wifi_issues": [
            "Check if Wi-Fi light on router is blinking",
            "Try forgetting the network and reconnecting",
            "Change your Wi-Fi channel (5 GHz is usually less congested)",
            "Make sure you're not too far from the router",
            "Check if too many devices are connected",
        ],
    },
}

# Nepali language patterns
NEPALI_PATTERNS = [
    r"नमस्ते", r"कस्तो", r"धन्यवाद", r"कति", r"इन्टरनेट", r"समस्या",
    r"बिल", r"पैसा", r"प्याकेज", r"छ", r"छैन", r"गर्नुहोस्", r"मलाई",
    r"मेरो", r"कसरी", r"किन", r"राम्रो", r"खराब", r"slow", r"हुन्छ",
]

# ── Intent detection ──

# Exact-match aliases for suggestion chip labels — checked FIRST
# so clicking a chip always triggers the right intent.
EXACT_INTENTS: dict[str, str] = {
    # Packages
    "view packages": "packages",
    "packages": "packages",
    "internet packages": "packages",
    "show packages": "packages",
    "show me packages": "packages",
    "what packages": "packages",
    "what are the internet packages": "packages",
    "what are the packages": "packages",
    "pricing": "packages",
    "plans": "packages",
    "upgrade package": "packages",
    "how much": "packages",
    # TV
    "tv packages": "tv_packages",
    "tv channels": "tv_packages",
    "channels": "tv_packages",
    # Billing
    "check my bill": "billing",
    "check bill": "billing",
    "billing": "billing",
    "my bill": "billing",
    "pay bill": "billing",
    "how to pay": "billing",
    "how to pay?": "billing",
    "payment": "billing",
    "setup auto-pay": "billing",
    "how to subscribe": "billing",
    # Troubleshooting
    "internet issue": "troubleshoot_internet",
    "no internet": "troubleshoot_internet",
    "internet not working": "troubleshoot_internet",
    "reboot router": "troubleshoot_internet",
    "troubleshoot": "troubleshoot_internet",
    "run speed test": "troubleshoot_speed",
    "slow internet": "troubleshoot_speed",
    "change wi-fi password": "troubleshoot_wifi",
    # Coverage
    "check coverage": "coverage",
    "check my area": "coverage",
    "coverage": "coverage",
    "new connection": "coverage",
    "dishhome go (4g)": "coverage",
    # Tickets
    "create ticket": "ticket",
    "create new ticket": "ticket",
    "track ticket": "ticket",
    "report issue": "ticket",
    "schedule technician": "ticket",
    # Contact
    "contact support": "support_contact",
    "contact info": "support_contact",
    "call support": "support_contact",
    # Thanks & bye
    "thanks": "thanks",
    "thank you": "thanks",
    "goodbye": "goodbye",
    "bye": "goodbye",
    "another question": "greeting",
    "try again": "greeting",
}

INTENTS = {
    "greeting": [
        r"\b(hi|hello|hey|namaste|namaskar|हेलो|नमस्ते|नमस्कार)\b",
        r"^(yo|sup|good morning|good evening|शुभ)",
    ],
    "packages": [
        r"\b(package|plan|price|pricing|offer|mbps|speed|internet plan|प्याकेज|मूल्य|दर)\b",
        r"\b(ftth|fiber|broadband|ब्रोडब्यान्ड|फाइबर)\b",
        r"(show|view|list|what).*(package|plan|price)",
    ],
    "tv_packages": [
        r"\b(tv|television|channel|dish|dth|satellite|टिभी|च्यानल)\b",
    ],
    "billing": [
        r"\b(bill|balance|payment|pay|due|overdue|recharge|बिल|भुक्तानी|बाँकी)\b",
        r"\b(esewa|khalti|ime|connectips|bank|पैसा)\b",
    ],
    "troubleshoot_internet": [
        r"\b(no internet|not working|down|offline|disconnect|इन्टरनेट छैन|काम गरेन)\b",
        r"\b(outage|connection issue|can't connect|जोडिएन)\b",
        r"\b(reboot|restart)\b.*\b(router|ont)\b",
    ],
    "troubleshoot_speed": [
        r"\b(slow|buffering|lag|latency|ढिलो|बिस्तारै)\b",
        r"\bspeed\s*test\b",
    ],
    "troubleshoot_wifi": [
        r"\b(wifi|wi-fi|wireless|signal|वाइफाइ)\b",
    ],
    "coverage": [
        r"\b(coverage|area|location|city|service area|क्षेत्र|उपलब्ध)\b",
        r"\b(available|serve|where)\b.*\b(area|city|location)\b",
    ],
    "ticket": [
        r"\b(ticket|complaint|report|complain|उजुरी|टिकेट)\b",
        r"\b(technician|tech visit)\b",
    ],
    "customer_lookup": [
        r"\b(my account|account status|customer id|DH\d+|SC-\d+|smartcard|मेरो खाता)\b",
    ],
    "support_contact": [
        r"\b(contact|helpline|support number|customer care|सम्पर्क)\b",
    ],
    "thanks": [
        r"\b(thanks|thank you|dhanyabad|धन्यवाद|appreciated)\b",
    ],
    "goodbye": [
        r"\b(bye|goodbye|see you|alvida|अलविदा|बाई)\b",
    ],
}


def _detect_language(text: str) -> str:
    """Detect if the message is Nepali or English."""
    for pat in NEPALI_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return "ne"
    return "en"


def _detect_intent(text: str) -> str:
    """Detect user intent from message text.
    
    First checks exact-match aliases (for suggestion chip labels),
    then falls back to regex pattern matching.
    """
    text_lower = text.lower().strip()
    
    # 1. Exact match against known chip labels
    if text_lower in EXACT_INTENTS:
        return EXACT_INTENTS[text_lower]
    
    # 2. Regex pattern match
    for intent, patterns in INTENTS.items():
        for pat in patterns:
            if re.search(pat, text_lower, re.IGNORECASE):
                return intent
    return "general"


def _extract_customer_id(text: str) -> Optional[str]:
    """Extract DishHome customer ID from message."""
    match = re.search(r"DH\d+", text, re.IGNORECASE)
    if match:
        return match.group(0).upper()
    return None


def _extract_smartcard(text: str) -> Optional[str]:
    """Extract smartcard number from message."""
    match = re.search(r"SC-\d+", text, re.IGNORECASE)
    if match:
        return match.group(0).upper()
    return None


# ── Response generators ──
def _greeting_response(lang: str) -> tuple[str, list[str]]:
    if lang == "ne":
        return (
            "नमस्ते! 🙏 म **खुशी** हुँ, DishHome को AI सहायक। "
            "म तपाईंलाई इन्टरनेट प्याकेज, बिल, प्राविधिक समस्या, र अन्य कुरामा सहयोग गर्न सक्छु। "
            "तपाईंलाई आज कस्तो सहयोग चाहिएको छ?",
            ["प्याकेजहरू हेर्नुहोस्", "मेरो बिल जाँच", "इन्टरनेट समस्या", "सम्पर्क जानकारी"],
        )
    return (
        "Namaste! 🙏 I'm **Khushi**, DishHome's AI assistant. "
        "I can help you with internet packages, billing, troubleshooting, "
        "service coverage, and more. How can I assist you today?",
        ["View Packages", "Check My Bill", "Internet Issue", "Contact Support"],
    )


def _packages_response(lang: str) -> tuple[str, list[str]]:
    lines = ["**📦 DishHome Internet Packages:**\n"]
    for name, info in KNOWLEDGE_BASE["packages"].items():
        lines.append(f"• **{name}** — {info['speed']} | {info['price']} | {info['data']}")
    lines.append("\n*All fiber plans include unlimited data with no FUP!*")
    if lang == "ne":
        lines.insert(0, "यहाँ हाम्रा इन्टरनेट प्याकेजहरू छन्:\n")
    return "\n".join(lines), ["TV Packages", "Check Coverage", "How to Pay"]


def _tv_packages_response(lang: str) -> tuple[str, list[str]]:
    lines = ["**📺 DishHome TV Packages:**\n"]
    for name, info in KNOWLEDGE_BASE["tv_packages"].items():
        lines.append(f"• **{name}** — {info['channels']} channels | {info['price']}")
    lines.append("\n*Bundle TV + Internet for extra savings!*")
    return "\n".join(lines), ["Internet Packages", "How to Subscribe"]


def _billing_response(lang: str) -> tuple[str, list[str]]:
    methods = ", ".join(KNOWLEDGE_BASE["payment_methods"])
    if lang == "ne":
        return (
            "💳 **बिल र भुक्तानी:**\n\n"
            "तपाईंको बिल जाँच गर्न, कृपया तपाईंको Customer ID (जस्तै DH100234) वा "
            "Smartcard नम्बर (जस्तै SC-4429981) दिनुहोस्।\n\n"
            f"**भुक्तानी विधिहरू:** {methods}\n\n"
            "*DishHome App बाट सजिलै भुक्तानी गर्नुहोस्!*",
            ["मेरो ID: DH100234", "भुक्तानी कसरी गर्ने?", "Auto-Pay सेटअप"],
        )
    return (
        "💳 **Billing & Payments:**\n\n"
        "To check your bill, please provide your Customer ID (e.g., DH100234) or "
        "Smartcard number (e.g., SC-4429981).\n\n"
        f"**Payment Methods:** {methods}\n\n"
        "*Pay easily through the DishHome App!*",
        ["My ID: DH100234", "How to Pay?", "Setup Auto-Pay"],
    )


def _customer_lookup_response(text: str, lang: str) -> tuple[str, list[str]]:
    cid = _extract_customer_id(text)
    sc = _extract_smartcard(text)
    customer = None

    if cid:
        customer = CUSTOMERS.get(cid)
    elif sc:
        for c in CUSTOMERS.values():
            if c.get("smartcard") == sc:
                customer = c
                break

    if not customer:
        return (
            "❌ I couldn't find that account. Please double-check your Customer ID "
            "(format: DH followed by numbers, e.g., DH100234) or Smartcard number.",
            ["Try DH100234", "Contact Support"],
        )

    status_emoji = "✅" if customer["status"] == "active" else "⚠️"
    balance_info = f"Rs. {customer['balance_npr']}" if customer["balance_npr"] > 0 else "No dues"

    return (
        f"👤 **Account Details:**\n\n"
        f"• **Name:** {customer['name']}\n"
        f"• **Customer ID:** {customer['customer_id']}\n"
        f"• **Package:** {customer['package']}\n"
        f"• **Status:** {status_emoji} {customer['status'].title()}\n"
        f"• **Balance:** {balance_info}\n"
        f"• **Due Date:** {customer['due_date']}\n"
        f"• **ONT ID:** {customer['ont_id']}",
        ["Check Router Status", "Pay Bill", "Upgrade Package", "Report Issue"],
    )


def _troubleshoot_internet_response(lang: str) -> tuple[str, list[str]]:
    steps = KNOWLEDGE_BASE["troubleshooting"]["no_internet"]
    numbered = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
    if lang == "ne":
        return (
            "🔧 **इन्टरनेट काम गरिरहेको छैन? यी कदमहरू प्रयास गर्नुहोस्:**\n\n"
            f"{numbered}\n\n"
            "यदि समस्या जारी छ भने, म तपाईंको लागि सपोर्ट टिकेट बनाउन सक्छु।",
            ["टिकेट बनाउनुहोस्", "राउटर रिबुट", "फोन गर्नुहोस्"],
        )
    return (
        "🔧 **Internet not working? Try these steps:**\n\n"
        f"{numbered}\n\n"
        "If the issue persists, I can create a support ticket for you.",
        ["Create Ticket", "Reboot Router", "Call Support"],
    )


def _troubleshoot_speed_response(lang: str) -> tuple[str, list[str]]:
    steps = KNOWLEDGE_BASE["troubleshooting"]["slow_internet"]
    numbered = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
    return (
        "🐌 **Experiencing slow speeds? Here's what to try:**\n\n"
        f"{numbered}\n\n"
        "💡 *Tip: Connect via Ethernet for the most accurate speed test.*",
        ["Run Speed Test", "Create Ticket", "Upgrade Package"],
    )


def _troubleshoot_wifi_response(lang: str) -> tuple[str, list[str]]:
    steps = KNOWLEDGE_BASE["troubleshooting"]["wifi_issues"]
    numbered = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps))
    return (
        "📶 **Wi-Fi Troubleshooting:**\n\n"
        f"{numbered}\n\n"
        "If these don't help, a technician may need to check your setup.",
        ["Schedule Technician", "Change Wi-Fi Password", "Contact Support"],
    )


def _coverage_response(lang: str) -> tuple[str, list[str]]:
    cities = ", ".join(KNOWLEDGE_BASE["coverage"])
    return (
        "📍 **DishHome Service Coverage:**\n\n"
        f"We currently serve: **{cities}** and surrounding areas.\n\n"
        "Our fiber network is expanding rapidly across Nepal! "
        "For exact availability at your address, please share your location or ward number.",
        ["Check My Area", "New Connection", "DishHome Go (4G)"],
    )


def _ticket_response(lang: str) -> tuple[str, list[str]]:
    # Show existing tickets
    if TICKETS:
        ticket_lines = []
        for t in TICKETS[:3]:
            ticket_lines.append(
                f"• **{t['id']}** — {t['issue'][:50]}... | "
                f"Status: {t['status']} | Priority: {t['priority']}"
            )
        ticket_info = "\n".join(ticket_lines)
        return (
            "🎫 **Support Tickets:**\n\n"
            f"Recent tickets:\n{ticket_info}\n\n"
            "To create a new ticket, please describe your issue and I'll log it for you. "
            "Include your Customer ID for faster resolution.",
            ["Create New Ticket", "Track Ticket", "Call Support"],
        )
    return (
        "🎫 I can help you create a support ticket. Please describe your issue "
        "and include your Customer ID (e.g., DH100234) for faster resolution.",
        ["Internet Issue", "Billing Issue", "TV Issue"],
    )


def _support_contact_response(lang: str) -> tuple[str, list[str]]:
    info = KNOWLEDGE_BASE["support"]
    if lang == "ne":
        return (
            "📞 **सम्पर्क जानकारी:**\n\n"
            f"• **Toll-Free:** {info['hotline']}\n"
            f"• **Email:** {info['email']}\n"
            f"• **समय:** {info['hours']}\n"
            f"• **Website:** {info['website']}\n\n"
            "म २४/७ उपलब्ध छु! कुनै प्रश्न सोध्नुहोस्। 😊",
            ["प्याकेज हेर्नुहोस्", "बिल जाँच", "समस्या रिपोर्ट"],
        )
    return (
        "📞 **Contact Information:**\n\n"
        f"• **Toll-Free:** {info['hotline']}\n"
        f"• **Email:** {info['email']}\n"
        f"• **Hours:** {info['hours']}\n"
        f"• **Website:** {info['website']}\n\n"
        "I'm available 24/7! Feel free to ask me anything. 😊",
        ["View Packages", "Check Bill", "Report Issue"],
    )


def _thanks_response(lang: str) -> tuple[str, list[str]]:
    if lang == "ne":
        return (
            "धन्यवाद! 😊 तपाईंलाई सहयोग गर्न पाउँदा खुशी लाग्यो। "
            "अरू केही सहयोग चाहिए भने सोध्नुहोस्!",
            ["अरू प्रश्न", "बाई"],
        )
    return (
        "You're welcome! 😊 Happy to help. "
        "Let me know if there's anything else I can assist with!",
        ["Another Question", "Goodbye"],
    )


def _goodbye_response(lang: str) -> tuple[str, list[str]]:
    if lang == "ne":
        return (
            "अलविदा! 👋 DishHome रोज्नुभएकोमा धन्यवाद। "
            "फेरि कहिल्यै सहयोग चाहिँदा सम्झनुहोस्! 🙏",
            [],
        )
    return (
        "Goodbye! 👋 Thank you for choosing DishHome. "
        "Remember, I'm always here whenever you need help! 🙏",
        [],
    )


def _general_response(lang: str) -> tuple[str, list[str]]:
    if lang == "ne":
        return (
            "म तपाईंको प्रश्न पूर्ण रूपमा बुझ्न सकिनँ। 🤔 "
            "कृपया तल दिइएका विकल्पहरू मध्ये एउटा छान्नुहोस्, "
            "वा तपाईंको प्रश्न फरक तरिकाले सोध्नुहोस्।",
            ["प्याकेजहरू", "बिल जाँच", "इन्टरनेट समस्या", "सम्पर्क", "टिकेट"],
        )
    return (
        "I'm not quite sure I understood that. 🤔 "
        "Could you try rephrasing, or select one of the options below? "
        "I can help with packages, billing, troubleshooting, and more!",
        ["View Packages", "Check Bill", "Internet Issue", "Contact Info", "Create Ticket"],
    )


# ── Route: response dispatcher ──
RESPONSE_MAP = {
    "greeting": _greeting_response,
    "packages": _packages_response,
    "tv_packages": _tv_packages_response,
    "billing": _billing_response,
    "troubleshoot_internet": _troubleshoot_internet_response,
    "troubleshoot_speed": _troubleshoot_speed_response,
    "troubleshoot_wifi": _troubleshoot_wifi_response,
    "coverage": _coverage_response,
    "ticket": _ticket_response,
    "support_contact": _support_contact_response,
    "thanks": _thanks_response,
    "goodbye": _goodbye_response,
    "general": _general_response,
}


def _generate_reply(message: str, lang: str) -> tuple[str, list[str], dict]:
    """Generate a reply based on message intent."""
    intent = _detect_intent(message)

    # Special handler for customer lookup (needs the message for ID extraction)
    if intent == "customer_lookup":
        reply, suggestions = _customer_lookup_response(message, lang)
        return reply, suggestions, {"intent": intent}

    handler = RESPONSE_MAP.get(intent, _general_response)
    reply, suggestions = handler(lang)
    return reply, suggestions, {"intent": intent}


# ── API endpoints ──

@router.post("/message", response_model=ChatResponse)
async def chat_message(req: ChatRequest) -> ChatResponse:
    """Process a chat message from Khushi chatbot widget."""
    session_id = req.session_id or str(uuid.uuid4())

    # Detect language
    lang = req.language
    if lang == "auto":
        lang = _detect_language(req.message)

    # Generate reply
    reply, suggestions, metadata = _generate_reply(req.message, lang)

    # Store conversation history
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = []
    history = _SESSIONS[session_id]
    history.append({
        "role": "user",
        "content": req.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    history.append({
        "role": "assistant",
        "content": reply,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    # Trim history
    if len(history) > MAX_HISTORY * 2:
        _SESSIONS[session_id] = history[-MAX_HISTORY * 2:]

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        language=lang,
        suggestions=suggestions,
        metadata=metadata,
    )


@router.get("/history/{session_id}")
async def chat_history(session_id: str) -> dict:
    """Retrieve chat history for a session."""
    history = _SESSIONS.get(session_id, [])
    return {"session_id": session_id, "messages": history}


@router.post("/feedback")
async def chat_feedback(session_id: str, rating: int, comment: str = "") -> dict:
    """Submit feedback for a chat session."""
    log.info(f"Chat feedback: session={session_id} rating={rating} comment={comment}")
    return {"status": "ok", "message": "Thank you for your feedback!"}
