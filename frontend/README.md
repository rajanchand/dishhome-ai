# Frontend — DishHome AI Agent Panel

React + Vite + TypeScript + Tailwind. Brand palette wired into `tailwind.config.js` as `dishhome-blue` (`#003a70`) and `dishhome-orange` (`#f7941d`).

## Run

```sh
npm install
npm run dev
```

Open the URL Vite prints. This project pins Vite to `http://localhost:3000`
and proxies API routes to FastAPI on `http://127.0.0.1:8000`.

## Layout

```
src/
├── main.tsx       App bootstrap
├── App.tsx        Protected routes
├── components/    Layout, UI primitives, toast, chatbot
├── lib/           API client and auth provider
├── pages/         Dashboard, calls, inbox, contacts, admin, voice, campaigns
└── index.css      Tailwind directives + base styles
```

## Next steps

- Replace remaining symbol nav icons with `lucide-react`.
- Add real-time call transcript updates over WebSocket.
- Add i18n for Nepali/English UI strings.
- Add automated browser smoke tests for the protected routes.

## Production build

The production Docker target builds static assets and serves them with nginx:

```sh
docker build --target production --build-arg VITE_API_BASE=https://api.example.com -t dishhome-ai-frontend .
```

Set `VITE_API_BASE` at build time to the public backend origin.
