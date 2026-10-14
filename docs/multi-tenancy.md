# Multi-tenancy security model

This document is the source of truth for *what is and isn't isolated* between
tenants in this codebase. If you find a path that doesn't match this model,
it's a bug.

## Three GUC states

The Postgres session variable `app.tenant_id` has exactly three meaningful values:

| GUC value           | Set by                          | RLS behavior                                |
| ------------------- | ------------------------------- | ------------------------------------------- |
| `<a tenant UUID>`   | `set_tenant_guc(s, tenant_id)`  | Only rows where `tenant_id` matches are visible/writable. |
| `""` (empty)        | `set_tenant_guc(s, None)` or unset | **Zero rows visible. Fail-closed.**     |
| `"__bootstrap__"`   | `set_admin_guc(s)`              | Bypass: all rows visible/writable.          |

The first two states are the default. The third is reserved for cross-tenant
bootstrap operations and requires an explicit, intentional call.

## What's NOT row-level-secured

The `tenants` table itself is intentionally outside RLS. It's the directory.
Lookups by `slug`, `public_key`, or `id` need cross-row visibility — and the
table contains no per-tenant data (no documents, no conversations) so RLS
adds no value.

Tables that ARE row-level-secured:

- `users`
- `documents`
- `chunks`
- `conversations`
- `messages`
- `usage_events`
- `subscriptions`

## Where the bootstrap bypass is used (audit list)

Grep for `set_admin_guc` to verify. As of the last audit, only these call
sites legitimately use it:

1. **`auth/dev.py:signup`** — duplicate-email check across all tenants + INSERT
   of the first user row + subscription row before any tenant scope exists.
2. **`auth/dev.py:login`** — lookup user by email before knowing their tenant.
   The password check is the actual authorization gate; the cross-tenant read
   is unavoidable.
3. **`auth/clerk.py:verify_token`** — same pattern: maps a Clerk identity to
   a local tenant+user, creating both on first sight.

Anything outside this list that calls `set_admin_guc` is a code smell — every
other path should either:

- Use `set_tenant_guc(s, tenant_id)` with a verified tenant ID (the normal case);
- Or touch only the unprotected `tenants` table with no GUC set.

## Why fail-closed matters

The previous policy `tenant_id::text = current_setting(...) OR current_setting(...) = ''`
treated an unset GUC as "no filter" — meaning any handler that forgot to call
`set_tenant_guc` would read across all tenants. That's the failure mode RLS
exists to prevent.

Fail-closed (`""` matches zero rows) means a handler that forgets to set the
GUC returns empty results — visibly broken, easy to detect in development,
not a silent data leak.

## How to verify isolation

Run the integration test (requires a running Postgres):

```bash
make up && make migrate
docker compose exec backend pytest -v tests/test_tenant_isolation.py
```

The test creates two tenants, inserts a document for each, and asserts:
- Tenant A's session sees only A's doc.
- Tenant B's session sees only B's doc.
- An unscoped session (GUC unset) sees zero docs.
- The bootstrap-scoped session sees both.

If any of these fail, the RLS policy is broken — escalate immediately.

## What this model does NOT protect

- **Logic-level mistakes outside RLS-protected tables.** If a handler reads
  the `tenants` table by primary key with no other check, it can return any
  tenant's metadata. The RLS policy can't help there; authorization at the
  handler level must.
- **The `tenants.public_key` field.** Widget endpoints authenticate by this
  field — exposing it on a client page is intentional and safe (it only
  authorizes the widget chat surface). Treat it like a Stripe `pk_` key, not
  a secret.
- **Cross-tenant queries from outside the application.** A direct `psql`
  connection as the `saas` user has no GUC set; reads return empty (fail-closed),
  but a SUPERUSER role of course bypasses RLS entirely. Lock down DB roles
  in production.
