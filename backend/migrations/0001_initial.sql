-- DishHome AI Call Center — initial Supabase schema
--
-- Runs in its OWN schema (`dh`) so it doesn't collide with anything in
-- `public`. Idempotent — safe to re-run.
--
-- After applying this SQL:
--   Supabase Dashboard → Project Settings → API → Exposed schemas
--   add `dh` to the list so PostgREST can serve these tables.
--
-- What's persisted here (replaces in-memory state where wired):
--   • dh.users          — operator accounts (argon2-hashed passwords)
--   • dh.sessions       — live bearer tokens
--   • dh.login_events   — every login attempt (IP, UA, result)
--   • dh.audit_log      — every admin mutation

-- ─────────────────────────────────────────────────────────────
-- Schema
-- ─────────────────────────────────────────────────────────────
create schema if not exists dh;
-- Grant PostgREST's roles (used by Supabase's automatic API) the ability
-- to see + manipulate everything in dh.* — required even when we connect
-- with service_role because PostgREST checks role-scoped grants too.
grant usage on schema dh to anon, authenticated, service_role;
grant all   on all tables    in schema dh to anon, authenticated, service_role;
grant all   on all sequences in schema dh to anon, authenticated, service_role;
grant all   on all functions in schema dh to anon, authenticated, service_role;
alter default privileges in schema dh grant all on tables    to anon, authenticated, service_role;
alter default privileges in schema dh grant all on sequences to anon, authenticated, service_role;
alter default privileges in schema dh grant all on functions to anon, authenticated, service_role;

-- ─────────────────────────────────────────────────────────────
-- USERS
-- ─────────────────────────────────────────────────────────────
create table if not exists dh.users (
  username    text primary key check (username = lower(username) and username ~ '^[a-z0-9_.-]{3,40}$'),
  password    text not null,                  -- argon2 hash, never plaintext
  name        text not null,
  email       text not null,
  role        text not null check (role in ('super_admin','admin','supervisor','agent')),
  created_at  timestamptz not null default now(),
  created_by  text references dh.users(username) on delete set null,
  updated_at  timestamptz not null default now()
);

create index if not exists users_role_idx  on dh.users (role);
create index if not exists users_email_idx on dh.users (lower(email));

-- updated_at trigger
create or replace function dh.set_updated_at() returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

drop trigger if exists users_set_updated_at on dh.users;
create trigger users_set_updated_at before update on dh.users
  for each row execute function dh.set_updated_at();

-- ─────────────────────────────────────────────────────────────
-- SESSIONS
-- ─────────────────────────────────────────────────────────────
create table if not exists dh.sessions (
  token         text primary key,
  token_prefix  text generated always as (substr(token, 1, 8)) stored,
  username      text not null references dh.users(username) on delete cascade,
  issued_at     timestamptz not null default now(),
  expires_at    timestamptz not null,
  last_seen     timestamptz not null default now(),
  issued_ip     inet,
  last_ip       inet,
  user_agent    text default ''
);

create index if not exists sessions_username_idx     on dh.sessions (username);
create index if not exists sessions_expires_idx      on dh.sessions (expires_at);
create index if not exists sessions_token_prefix_idx on dh.sessions (token_prefix);

-- ─────────────────────────────────────────────────────────────
-- LOGIN_EVENTS
-- ─────────────────────────────────────────────────────────────
create table if not exists dh.login_events (
  id              bigserial primary key,
  at              timestamptz not null default now(),
  username        text not null,
  ip              inet,
  user_agent      text default '',
  device          text default '',
  result          text not null check (result in ('success','failure')),
  reason          text default '',
  session_prefix  text default ''
);

create index if not exists login_events_at_idx       on dh.login_events (at desc);
create index if not exists login_events_username_idx on dh.login_events (username);
create index if not exists login_events_result_idx   on dh.login_events (result);

-- ─────────────────────────────────────────────────────────────
-- AUDIT_LOG
-- ─────────────────────────────────────────────────────────────
create table if not exists dh.audit_log (
  id      bigserial primary key,
  at      timestamptz not null default now(),
  actor   text not null,
  action  text not null,
  target  text not null default '',
  detail  text not null default ''
);

create index if not exists audit_log_at_idx     on dh.audit_log (at desc);
create index if not exists audit_log_actor_idx  on dh.audit_log (actor);
create index if not exists audit_log_action_idx on dh.audit_log (action);

-- ─────────────────────────────────────────────────────────────
-- Row-level security
-- ─────────────────────────────────────────────────────────────
-- Enabled but no policies → only service_role can read/write (which is
-- exactly the access pattern we want). Add per-user policies later if
-- you decide to call PostgREST from the browser with end-user JWTs.
alter table dh.users        enable row level security;
alter table dh.sessions     enable row level security;
alter table dh.login_events enable row level security;
alter table dh.audit_log    enable row level security;
