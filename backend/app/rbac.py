"""Role-based access control (RBAC).

Permissions are coarse-grained verbs over a resource ("calls.read",
"campaigns.write"). Roles map to a set of permissions. We keep this in code
rather than a DB so that the surface stays auditable.

Hierarchy: super_admin > admin > supervisor > agent.
"""

ALL_PERMISSIONS: tuple[str, ...] = (
    # Read
    "calls.read",
    "campaigns.read",
    "customers.read",
    "contacts.read",
    "inbox.read",
    "faqs.read",
    "voice.read",
    "metrics.read",
    "telephony.read",
    # Write (mutations)
    "campaigns.write",
    "contacts.write",
    "faqs.write",
    "inbox.write",
    "voice.upload",
    "voice.clone",
    "telephony.originate",
    # Admin-only
    "users.manage",
    "roles.manage",
    "integrations.manage",
    # Super-admin only: write runtime config overrides (SIP creds, API keys).
    "system.write",
)


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "super_admin": set(ALL_PERMISSIONS),
    # admin: everything except `roles.manage` and `system.write` — the latter
    # gates writing runtime credentials (SIP / Twilio / API keys), which we
    # restrict to super_admin so credentials never silently rotate.
    "admin": set(ALL_PERMISSIONS) - {"roles.manage", "system.write"},
    "supervisor": {
        "calls.read",
        "campaigns.read",
        "campaigns.write",
        "customers.read",
        "contacts.read",
        "contacts.write",
        "inbox.read",
        "inbox.write",
        "faqs.read",
        "faqs.write",
        "voice.read",
        "voice.upload",
        "voice.clone",
        "metrics.read",
        "telephony.read",
        "telephony.originate",
    },
    "agent": {
        "calls.read",
        "campaigns.read",
        "customers.read",
        "contacts.read",
        "inbox.read",
        "inbox.write",
        "faqs.read",
        "voice.read",
        "telephony.read",
    },
}

ROLE_ORDER: tuple[str, ...] = ("super_admin", "admin", "supervisor", "agent")


def permissions_for(role: str) -> list[str]:
    return sorted(ROLE_PERMISSIONS.get(role, set()))


def has_permission(role: str, perm: str) -> bool:
    return perm in ROLE_PERMISSIONS.get(role, set())
