# Environment Variable Management for Atlas IDE Frontend

This document outlines the strategy for managing environment variables within the Atlas IDE Next.js application (`atlas-ide-shell`).

## Overview

We will leverage Next.js's built-in support for environment variables using `.env` files. This approach allows for different configurations across various environments (local development, testing, production) without hardcoding sensitive information or environment-specific settings into the codebase.

## `.env` Files

The following `.env` files will be used, following Next.js conventions:

*   `.env.local`: For local development. This file is not committed to version control and is intended for user-specific settings or secrets.
*   `.env.development`: Default development variables. Committed to version control.
*   `.env.production`: Default production variables. Committed to version control.
*   `.env.test`: Default testing variables. Committed to version control.

Next.js automatically loads these files based on the current environment (`NODE_ENV`). `.env.local` always overrides defaults set in other files for local development.

## Accessing Environment Variables

### Server-Side

Environment variables can be accessed directly on the server-side (e.g., in API routes, `getServerSideProps`) via `process.env.VARIABLE_NAME`.

### Client-Side

To expose an environment variable to the browser (client-side JavaScript), it **must** be prefixed with `NEXT_PUBLIC_`.

For example, `NEXT_PUBLIC_API_URL` will be available as `process.env.NEXT_PUBLIC_API_URL` in your client-side code.

**Important Security Note:** Variables without the `NEXT_PUBLIC_` prefix are only available on the server-side. Do not prefix sensitive information that should not be exposed to the client with `NEXT_PUBLIC_`.

## Example `.env.development`

```env
# Backend API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# Code Server Configuration
NEXT_PUBLIC_CODESERVER_URL=http://localhost:8080

# Other application-specific variables
# EXAMPLE_SETTING=some_value
```

## Example `.env.local` (Gitignored)

This file can be created locally to override defaults for development, for example:

```env
# Override for local FastAPI instance if different
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001/api/v1

# Override for local code-server instance if different
NEXT_PUBLIC_CODESERVER_URL=http://127.0.0.1:8888
```

## Loading Order

Next.js loads environment variables in the following order (later files override earlier ones for the specific environment):

1.  `.env` (global defaults, rarely used if environment-specific files exist)
2.  `.env.development` / `.env.production` / `.env.test` (environment-specific defaults)
3.  `.env.local` (local overrides, gitignored)

## Best Practices

*   **Never commit `.env.local` to version control.** Ensure it's listed in your `.gitignore` file.
*   Use descriptive names for your environment variables.
*   Only expose variables to the client-side if absolutely necessary, and always use the `NEXT_PUBLIC_` prefix for them.
*   Provide sensible defaults in `.env.development` and `.env.production` to ensure the application can run out-of-the-box in those environments with minimal setup.
