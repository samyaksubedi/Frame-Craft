# Framecraft frontend

A client-side thumbnail studio built with Vite, React, and TypeScript. It connects to the Framecraft FastAPI backend for portrait uploads, generation jobs, job polling, thumbnail variants, previews, and downloads.

## Requirements

- Node.js `>=22.13.0`
- Backend running at the URL configured in `VITE_API_URL`

## Local development

```bash
npm install
npm run dev
```

The application runs at `http://localhost:5173`.

## Environment

Copy `.env.example` to `.env` and set the public backend URL:

```env
VITE_API_URL=http://127.0.0.1:8000
```

## Commands

- `npm run dev` — start the Vite development server
- `npm run build` — type-check and create the production build
- `npm run preview` — preview the production build locally
- `npm run lint` — lint the React and TypeScript source

## Vercel

Set the Vercel project root directory to `frontend` and add `VITE_API_URL` with the deployed backend URL. The included `vercel.json` uses the Vite preset, publishes `dist`, and preserves client-side routes on direct navigation.
