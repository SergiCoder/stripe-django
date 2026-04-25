# Changelog

All notable user-facing and contract changes to `saasmint-core`. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
the project adheres to [Semantic Versioning](https://semver.org/).

From `v0.7.0` onward, `saasmint-core` (root), `saasmint-core-lib` (`core/`),
and the frontend `saasmint-app` ship in lockstep — a `v<X.Y.Z>` tag is
only valid if all three repos already match `<X.Y.Z>` on `main`.

## [0.7.2] - 2026-04-25

### Fixed

- **Microsoft OAuth login signs verified-tenant users in directly.**
  The Microsoft callback now parses and validates the OIDC `id_token`
  returned alongside the access token (signature verified against
  Microsoft's JWKS at `login.microsoftonline.com/common/discovery/v2.0/keys`,
  audience pinned to `OAUTH_MICROSOFT_CLIENT_ID`, issuer prefix-checked
  against `https://login.microsoftonline.com/{tid}/v2.0`). When the
  token's `xms_edov` claim is `true` — Microsoft's attestation that the
  email's domain belongs to the user's tenant — the user is signed in
  with `is_verified=True`, mirroring the Google/GitHub UX. Otherwise
  (no `id_token`, signature/audience failure, or `xms_edov` absent /
  false) the flow falls back to the existing unverified path and the
  user is bounced to `/auth/error?error=email_not_verified`.

### Security

- **Microsoft Graph `/me` is no longer treated as proof of email
  ownership.** A tenant admin can set a user's `mail` attribute to any
  string (including a third-party domain) without verifying the
  destination mailbox; combined with the email-match auto-link in
  `resolve_oauth_user`, naïvely trusting `/me.mail` would have enabled
  account takeover of an existing password-registered user. Trust now
  flows from the signed `id_token`'s `xms_edov` claim, not Graph.

## [0.7.1] - 2026-04-25

### Fixed

- **Hijack release no longer 405s on the admin re-login bounce.**
  `HijackReleaseView` is no longer wrapped in `staff_member_required`
  (during impersonation `request.user` is the impersonated non-staff
  user, so the gate would 302 the release POST to the admin login page
  with a stale `next=/hijack/release/`, which then returned 405 on the
  follow-up GET). The parent `UserPassesTestMixin.test_func` already
  gates POST on `session["hijack_history"]`, which is the correct
  invariant. GETs to `/hijack/release/` now 302 to the admin home as a
  no-op instead of 405. Stop-impersonating from the admin toolbar now
  lands on `/admin/` (admin index) rather than the users changelist.

## [0.7.0] - 2026-04-25

### Changed (breaking)

- **`Subscription` is now a pure Stripe mirror.** Every persisted row
  has a `stripe_id`; the free tier is the *absence* of a Subscription
  row. The dual-shape `stripe_id IS NULL` placeholder is gone. (#46)
- **`GET /api/v1/billing/subscriptions/me/`** returns **404** for users
  on the free tier (previously a synthetic 200 with `stripe_id: null`,
  `current_period_end: 9999-12-31`, `plan.tier: "free"`). The 404 is
  now declared in `schema.yml`. (#46)
- **`GET /api/v1/billing/plans/`** no longer includes the `Personal
  Free` plan row. (#46)
- **Signup paths** (`/auth/register/`, `/auth/register/org-owner/`,
  OAuth callback) no longer create any Subscription. The user only
  gets one once they pay. (#46)
- The `customer.subscription.deleted` webhook flips status to `CANCELED`
  and **no longer creates a fallback free Subscription** for personal
  users. Subsequent reads observe the absence as 404. (#46)

### Removed

- `Subscription.is_free`, `FREE_SUBSCRIPTION_PERIOD_END` sentinel,
  `assign_free_plan`, `_lock_user`, `Plan.free_plans()`,
  `delete_free_for_user`, `get_free_plan`. (#46)
- The "Personal Free" entry from `seed_catalog`. The `PlanTier.FREE = 1`
  enum value is preserved for legacy data but is no longer seeded. (#46)
- The `uniq_free_subscription_per_user` partial unique constraint on
  `Subscription` (no rows match the predicate any more). (#46)

### Performance

- Migration `0014` deletes free Subscriptions in 1000-row batches to
  keep transaction size bounded — the migration runs on every deploy
  via the entrypoint and the table can be the largest in the schema.
  (#46)
- One fewer query per `customer.subscription.created` / `.updated`
  webhook (the prune-free-sub block is gone). (#46)
- One fewer SELECT FOR UPDATE per signup (the `_lock_user` row lock
  that guarded `assign_free_plan` race is gone). (#46)

### Documentation

- CLAUDE.md "Versioning" rule added: every PR bumps both
  `pyproject.toml` files together; `saasmint-core` and `saasmint-app`
  ship in lockstep. (#46)
- README plan list dropped the unseeded "free" tier. (#46)

### Maintenance

- `uv.lock` re-resolved so the editable entries match the bumped
  `pyproject.toml` versions. (#47)

## Deprecated tags (pre-lockstep)

These tags shipped with divergent versions across `saasmint-core` and
`saasmint-core-lib`. Kept for deploy-forensics; do not use as a basis
for new work. From `v0.7.0` onward all packages ship in lockstep.

- `v0.5.0` — `saasmint-core` 0.5.0, `saasmint-core-lib` 0.4.0.
- `v0.5.1` — `saasmint-core` 0.5.1, `saasmint-core-lib` 0.4.0.
- `v0.6.0` — `saasmint-core` 0.6.0, `saasmint-core-lib` 0.5.0.
