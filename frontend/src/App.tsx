export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-dishhome-blue text-white shadow">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="inline-block w-3 h-3 rounded-full bg-dishhome-orange" />
            <h1 className="text-xl font-semibold tracking-tight">
              DishHome AI Call Center
            </h1>
          </div>
          <span className="text-xs uppercase tracking-widest text-white/70">
            Agent Panel
          </span>
        </div>
      </header>

      <main className="flex-1">
        <div className="max-w-6xl mx-auto px-6 py-10">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card title="Live Queue" value="0" hint="Calls waiting" />
            <Card title="Active AI Calls" value="0" hint="In progress" />
            <Card title="Today" value="0" hint="Handled" />
          </div>

          <section className="mt-10 rounded-2xl bg-white p-6 shadow-sm border border-black/5">
            <h2 className="text-lg font-semibold text-dishhome-blue">
              Scaffold ready
            </h2>
            <p className="mt-2 text-sm text-dishhome-ink/70">
              This is the starting point for the agent panel. The next milestone
              wires the live call queue, transcript view, and one-click
              takeover.
            </p>
          </section>
        </div>
      </main>

      <footer className="border-t border-black/5 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-4 text-xs text-dishhome-ink/60">
          Dish Media Network · AI Call Center · v0.0.1
        </div>
      </footer>
    </div>
  );
}

function Card({
  title,
  value,
  hint,
}: {
  title: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm border border-black/5">
      <div className="text-xs uppercase tracking-widest text-dishhome-ink/50">
        {title}
      </div>
      <div className="mt-2 text-3xl font-bold text-dishhome-blue">{value}</div>
      <div className="mt-1 text-xs text-dishhome-ink/60">{hint}</div>
    </div>
  );
}
