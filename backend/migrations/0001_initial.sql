-- DishHome AI Call Center — initial Supabase schema
--
-- Run this once in the Supabase SQL Editor (or via psql with the connection
-- string from Settings → Database). Idempotent: safe to re-run.
--
-- What's persisted here (replaces in-memory state):
--   • users           — operator accounts (argon2-hashed passwords)
--   • sessions        — live bearer tokens (one row per logged-in browser)
--   • login_events    — every login attempt with IP + UA + result
--   • audit_log       — every admin mutation (user.create / user.update / …)
--
-- What's NOT moved (yet, intentionally — seed/demo data):
--   • customers, OLT/ONT telemetry, FAQs, contacts, conversations,
--     campaigns, voices. Those stay in mock_data.py until you decide
--     to migrate them.

-- ─────────────────────────────────────────────────────────────
-- USERS
-- ─────────────────────────────────────────────────────────────
create table if not exists public.users (
  username    text primary key check (username = lower(username) and username ~ '^[a-z0-9_.-]{3,40}$'),
  password    text not null,                  -- argon2 hash, never plaintext
  name        text not null,
  email       text not null,
  role        text not null check (role in ('super_admin','admin','supervisor','agent')),
  created_at  timestamptz not null default now(),
  created_by  text references public.users(username) on delete set null,
  updated_at  timestamptz not null default now()
);

create index if not exists users_role_idx on public.users (role);
create index if not exists users_email_idx on public.users (lower(email));

-- Trigger to keep updated_at fresh on every UPDATE.
create or replace function public.set_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

drop trigger if exists users_set_updated_at on public.users;
create trigger users_set_updated_at before update on public.users
  for each row execute function public.set_updated_at();

-- ─────────────────────────────────────────────────────────────
-- SESSIONS
-- ─────────────────────────────────────────────────────────────
-- token is the actual bearer; token_prefix is the 8-char identifier we show
-- in the admin UI (so we never have to send the full token over the wire).
create table if not exists public.sessions (
  token         text primary key,
  token_prefix  text generated always as (substr(token, 1, 8)) stored,
  username      text not null references public.users(username) on delete cascade,
  issued_at     timestamptz not null default now(),
  expires_at    timestamptz not null,
  last_seen     timestamptz not null default now(),
  issued_ip     inet,
  last_ip       inet,
  user_agent    text default ''
);

create index if not exists sessions_username_idx on public.sessions (username);
create index if not exists sessions_expires_idx on public.sessions (expires_at);
create index if not exists sessions_token_prefix_idx on public.sessions (token_prefix);

-- ─────────────────────────────────────────────────────────────
-- LOGIN_EVENTS
-- ─────────────────────────────────────────────────────────────
create table if not exists public.login_events (
  id              bigserial primary key,
  at              timestamptz not null default now(),
  username        text not null,                       -- not FK: failed logins for unknown users still recorded
  ip              inet,
  user_agent      text default '',
  device          text default '',                     -- "Chrome on macOS"
  result          text not null check (result in ('success','failure')),
  reason          text default '',                     -- "bad_credentials" / "rate_limited" / ""
  session_prefix  text default ''                      -- 8 chars; links to sessions.token_prefix
);

create index if not exists login_events_at_idx on public.login_events (at desc);
create index if not exists login_events_username_idx on public.login_events (username);
create index if not exists login_events_result_idx on public.login_events (result);

-- ─────────────────────────────────────────────────────────────
-- AUDIT_LOG
-- ─────────────────────────────────────────────────────────────
create table if not exists public.audit_log (
  id      bigserial primary key,
  at      timestamptz not null default now(),
  actor   text not null,
  action  text not null,        -- 'user.create' / 'user.update' / 'session.revoke' / 'login' / 'logout' / ...
  target  text not null default '',
  detail  text not null default ''
);

create index if not exists audit_log_at_idx on public.audit_log (at desc);
create index if not exists audit_log_actor_idx on public.audit_log (actor);
create index if not exists audit_log_action_idx on public.audit_log (action);

-- ─────────────────────────────────────────────────────────────
-- ROW LEVEL SECURITY
-- ─────────────────────────────────────────────────────────────
-- We always talk to PostgREST with the service_role key (bypasses RLS), so
-- enabling RLS without policies is fine — it just locks out the anon role,
-- which is what we want for now.
alter table public.users         enable row level security;
alter table public.sessions      enable row level security;
alter table public.login_events  enable row level security;
alter table public.audit_log     enable row level security;
