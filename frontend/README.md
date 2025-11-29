# Neumann Frontend Scaffold

Next.js 14 App Router + TypeScript with Tailwind. This is the starting point for the Neumann hybrid-search UI.

## Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
```

Update `NEXT_PUBLIC_API_BASE_URL` in `.env.local` if your backend is not running on `http://127.0.0.1:8001`.

> CORS: ensure the FastAPI backend `API_CORS_ORIGINS` includes `http://localhost:3000` for local dev.

## Scripts

- `npm run dev` – start the dev server on port 3000
- `npm run build` – production build
- `npm run lint` – Next.js lint

App shell lives in `src/app/` and currently renders a placeholder status page; replace it with the real UI as features land.
