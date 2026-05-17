# Supabase integration

The backend can persist users, sessions, login events, and the audit log to
Supabase. When the env vars are unset everything stays in memory — same
behaviour as before — so this is opt-in.

## 1. Set the env

Get the values from **Supabase Dashboard → Project Settings → API**, then
add to `backend/.env` (gitignored):

```ini
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=<eyJ…>          # public, browser-safe
SUPABASE_SERVICE_ROLE_KEY=<eyJ…>  # secret — server-side only, bypasses RLS
SUPABASE_SCHEMA=dh
```

Restart the backend.

## 2. Apply the migration

Open **Supabase Dashboard → SQL Editor → New query**, paste the contents
of [`backend/migrations/0001_initial.sql`](../backend/migrations/0001_initial.sql),
and Run. The script is idempotent (`create table if not exists`), so
re-running is safe.

This creates:

| Table | What lives there |
|---|---|
| `users` | operator accounts (argon2-hashed passwords) |
| `sessions` | live bearer tokens — one row per browser |
| `login_events` | every login attempt (IP, UA, result, geo enriched on read) |
| `audit_log` | every admin mutation (user.create, session.revoke, …) |

RLS is enabled on every table. The server always talks to PostgREST with
the `service_role` key, which bypasses RLS — that's why the tables work
without policies. **Never expose `SUPABASE_SERVICE_ROLE_KEY` to the
browser.**

## 3. Verify

Hit `/admin/db/health` as an admin:

```sh
curl -H "authorization: Bearer $TOK" http://localhost:8000/admin/db/health
```

Expected response:

```json
{
  "enabled": true,
  "reachable": true,
  "url": "https://<project>.supabase.co",
  "schema": "dh",
  "tables": { "users": true, "sessions": true, "login_events": true, "audit_log": true },
  "migration_applied": true
}
```

If a table is `false`, re-run the migration. If `reachable` is `false`,
check the URL and key.

## 4. Security notes

- The `service_role` key bypasses RLS — treat it like a root password.
  Rotate it in **Settings → API → Reset service_role key** if it leaks.
- The `anon` key is safe to ship to browsers but the current backend
  doesn't use it.
- Sessions store the *full* bearer token as the primary key. PostgREST
  exposes a generated `token_prefix` column (first 8 chars) so the
  admin UI can identify sessions without the full token ever leaving
  the server.
- Schema bumps: add new files as `migrations/0002_*.sql`,
  `0003_*.sql`, … and run them in order in the SQL Editor. No tooling
  enforces this yet — keep them in lockstep with code by hand.

## 5. Falling back to in-memory

Unset `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` and restart. The
app reverts to the in-memory store; existing rows in Supabase are
untouched.
