# MARC Comparator Client

React frontend for the MARC Comparator application, built with Vite, TypeScript, and Tailwind CSS.

## Development

```bash
# From the repository root:
make up-infra     # Start backend services (API, worker, DB, Redis)
make dev-client   # Start Vite dev server with HMR
```

The dev server proxies API requests to the backend at `localhost:8000`.

## Production Build

The `Containerfile` builds a multi-stage image: Vite builds the static assets, then Nginx serves them with SPA routing and API proxying configured in `nginx.conf`.

```bash
# From the repository root:
make build   # Builds all images including the client
```
