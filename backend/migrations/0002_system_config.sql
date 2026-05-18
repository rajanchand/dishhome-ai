-- DishHome AI — runtime configuration overrides
--
-- Lets super_admin operators paste credentials (SIP, Twilio, ElevenLabs,
-- Ollama, Sentry) from the Settings UI without redeploying.
--
-- Precedence rule: a row here OVERRIDES the equivalent env var. Empty
-- string means "no override" (env wins). Bootstrap secrets (APP_SECRET_KEY,
-- DATABASE_URL, Supabase keys) are intentionally never stored here — they
-- must come from the platform.
--
-- Idempotent. Safe to re-run.

create table if not exists dh.system_config (
  key         text primary key check (key ~ '^[a-z][a-z0-9_]{2,63}$'),
  value       text not null default '',
  is_secret   boolean not null default false,
  updated_at  timestamptz not null default now(),
  updated_by  text references dh.users(username) on delete set null
);

-- Reuse the trigger function from 0001_initial.sql.
drop trigger if exists system_config_set_updated_at on dh.system_config;
create trigger system_config_set_updated_at before update on dh.system_config
  for each row execute function dh.set_updated_at();

create index if not exists system_config_updated_at_idx
  on dh.system_config (updated_at desc);
