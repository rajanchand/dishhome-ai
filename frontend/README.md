# Frontend — DishHome AI Agent Panel

React + Vite + TypeScript + Tailwind. Brand palette wired into `tailwind.config.js` as `dishhome-blue` (`#003a70`) and `dishhome-orange` (`#f7941d`).

## Run

```sh
npm install
npm run dev
```

Open the URL Vite prints (defaults to `http://localhost:5173`).

## Layout

```
src/
├── main.tsx      App bootstrap
├── App.tsx       Placeholder dashboard
└── index.css     Tailwind directives + base styles
```

## Next steps

- Agent live queue + transcript view + one-click takeover.
- Supervisor panel.
- Super admin panel (model + voice management, RAG ingest, analytics).
