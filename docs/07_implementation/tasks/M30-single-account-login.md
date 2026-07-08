# M30: Single-Account Deployment Login

## Goal

Add a simple deployment login so private deployments can restrict application
and API access to one configured account.

## Scope

- Single configured username.
- Bcrypt password hash stored in environment configuration.
- JWT-style bearer token signed with `APP_AUTH_JWT_SECRET`.
- No account creation, no user table, no multi-user roles.

## Configuration

```env
APP_AUTH_ENABLED=true
APP_AUTH_USERNAME=admin
APP_AUTH_PASSWORD_HASH=<bcrypt-hash>
APP_AUTH_JWT_SECRET=<long-random-secret>
APP_AUTH_TOKEN_EXPIRE_MINUTES=720
```

Generate the password hash with:

```bash
cd backend
uv run python scripts/hash_password.py
```

## Acceptance Criteria

- Auth is disabled by default for local development and tests.
- When enabled, all `/api/v1` application endpoints except `/health`,
  `/auth/login`, and `/auth/me` require a valid bearer token.
- The frontend shows a login page and protects application routes.
- Real `.env` files and secrets remain ignored by Git.

