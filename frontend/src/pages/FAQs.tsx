import { useEffect, useRef, useState } from "react";
import { api, type Faq, type FaqAskResponse } from "../lib/api";
import {
  Badge,
  Button,
  Card,
  Input,
  PageBody,
  PageHeader,
} from "../components/ui";
import { Skeleton } from "../components/Skeleton";
import { useAsyncErrorToast, useToast } from "../components/Toast";

export default function FAQs() {
  const [faqs, setFaqs] = useState<Faq[] | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const toast = useToast();
  const errToast = useAsyncErrorToast();

  async function refresh() {
    try {
      const [list, cats] = await Promise.all([
        api.get<Faq[]>("/faqs"),
        api.get<string[]>("/faqs/categories"),
      ]);
      setFaqs(list);
      setCategories(cats);
    } catch (e) {
      errToast(e, "Could not load FAQs");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = (faqs ?? []).filter((f) => {
    if (filter !== "all" && f.category !== filter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const blob = `${f.question_en} ${f.question_ne} ${f.answer_en} ${f.answer_ne} ${(f.tags || []).join(" ")}`.toLowerCase();
      if (!blob.includes(q)) return false;
    }
    return true;
  });

  async function deleteFaq(id: string) {
    try {
      await api.delete(`/faqs/${id}`);
      toast.success("FAQ removed");
      refresh();
    } catch (e) {
      errToast(e, "Delete failed");
    }
  }

  return (
    <>
      <PageHeader
        title="FAQ Knowledge Base"
        subtitle="The AI agent uses these Q/A pairs to answer customer questions. Admin uploads, edits, and bulk-imports here. Test how the AI matches a question against the knowledge base in the panel on the right."
      />
      <PageBody>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <AddFaqCard onAdded={refresh} />

            <Card
              title={`Knowledge base · ${faqs?.length ?? 0} items`}
              actions={
                <div className="flex items-center gap-2">
                  <select
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    className="text-xs rounded-md border border-black/10 px-2 py-1"
                  >
                    <option value="all">All categories</option>
                    {categories.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
              }
            >
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search FAQs…"
                className="mb-3"
              />
              {!faqs ? (
                <div className="space-y-2">
                  {[...Array(4)].map((_, i) => (
                    <Skeleton key={i} className="h-16" />
                  ))}
                </div>
              ) : filtered.length === 0 ? (
                <p className="text-sm text-dishhome-ink/50">
                  No FAQs match.
                </p>
              ) : (
                <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
                  {filtered.map((f) => (
                    <FaqItem key={f.id} faq={f} onDelete={() => deleteFaq(f.id)} />
                  ))}
                </div>
              )}
            </Card>
          </div>

          <div className="space-y-4">
            <AskCard />
            <BulkImportCard onImported={refresh} />
          </div>
        </div>
      </PageBody>
    </>
  );
}

function FaqItem({ faq, onDelete }: { faq: Faq; onDelete: () => void }) {
  return (
    <div className="rounded-lg border border-black/5 bg-dishhome-mist/30 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {faq.category && (
              <Badge tone="info">{faq.category}</Badge>
            )}
            {(faq.tags || []).slice(0, 4).map((t) => (
              <span
                key={t}
                className="text-[10px] uppercase tracking-widest text-dishhome-ink/40"
              >
                #{t}
              </span>
            ))}
          </div>
          {faq.question_en && (
            <div className="text-sm font-medium text-dishhome-blue">
              EN: {faq.question_en}
            </div>
          )}
          {faq.question_ne && (
            <div className="text-sm font-medium text-dishhome-blue">
              NE: {faq.question_ne}
            </div>
          )}
          {(faq.answer_en || faq.answer_ne) && (
            <div className="mt-1 text-xs text-dishhome-ink/70">
              {faq.answer_ne || faq.answer_en}
            </div>
          )}
        </div>
        <button
          onClick={() => {
            if (confirm("Delete this FAQ?")) onDelete();
          }}
          className="text-[11px] text-rose-600 hover:underline shrink-0"
        >
          Delete
        </button>
      </div>
    </div>
  );
}

function AddFaqCard({ onAdded }: { onAdded: () => void }) {
  const [qEn, setQEn] = useState("");
  const [qNe, setQNe] = useState("");
  const [aEn, setAEn] = useState("");
  const [aNe, setANe] = useState("");
  const [category, setCategory] = useState("general");
  const [tags, setTags] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const errToast = useAsyncErrorToast();

  async function submit() {
    setBusy(true);
    try {
      await api.post<Faq>("/faqs", {
        question_en: qEn || null,
        question_ne: qNe || null,
        answer_en: aEn || null,
        answer_ne: aNe || null,
        category,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      toast.success("FAQ added");
      setQEn("");
      setQNe("");
      setAEn("");
      setANe("");
      setTags("");
      onAdded();
    } catch (e) {
      errToast(e, "Failed to add FAQ");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Add FAQ">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Input
          label="Question (English)"
          value={qEn}
          onChange={(e) => setQEn(e.target.value)}
          placeholder="How do I reset my WiFi password?"
        />
        <Input
          label="Question (Nepali)"
          value={qNe}
          onChange={(e) => setQNe(e.target.value)}
          placeholder="WiFi password kasari change garne?"
        />
        <label className="block md:col-span-1">
          <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
            Answer (English)
          </span>
          <textarea
            value={aEn}
            onChange={(e) => setAEn(e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dishhome-blue/30"
          />
        </label>
        <label className="block">
          <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
            Answer (Nepali)
          </span>
          <textarea
            value={aNe}
            onChange={(e) => setANe(e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dishhome-blue/30"
          />
        </label>
        <Input
          label="Category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        />
        <Input
          label="Tags (comma separated)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="wifi, password"
        />
      </div>
      <Button onClick={submit} disabled={busy} className="mt-4">
        {busy ? "Saving…" : "Add to knowledge base"}
      </Button>
      <p className="text-[11px] text-dishhome-ink/50 mt-2">
        At minimum, give one question and one answer (English or Nepali).
      </p>
    </Card>
  );
}

function AskCard() {
  const [q, setQ] = useState("WiFi password kasari change garne?");
  const [lang, setLang] = useState<"ne" | "en">("ne");
  const [result, setResult] = useState<FaqAskResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const errToast = useAsyncErrorToast();

  async function ask() {
    setBusy(true);
    try {
      const r = await api.post<FaqAskResponse>("/faqs/ask", {
        query: q,
        language: lang,
        top_k: 3,
      });
      setResult(r);
    } catch (e) {
      errToast(e, "Ask failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Test the AI matcher">
      <textarea
        value={q}
        onChange={(e) => setQ(e.target.value)}
        rows={3}
        className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dishhome-blue/30"
        placeholder="Ask a question like a customer would…"
      />
      <div className="mt-3 flex items-center gap-2">
        <select
          value={lang}
          onChange={(e) => setLang(e.target.value as "ne" | "en")}
          className="text-sm rounded-md border border-black/10 px-2 py-1.5"
        >
          <option value="ne">Nepali</option>
          <option value="en">English</option>
        </select>
        <Button onClick={ask} disabled={busy || !q.trim()}>
          {busy ? "Searching…" : "Ask AI"}
        </Button>
      </div>
      {result && (
        <div className="mt-4 space-y-3">
          {result.answer ? (
            <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3">
              <div className="text-[10px] uppercase tracking-widest text-emerald-700 font-semibold">
                AI answer
              </div>
              <div className="mt-1 text-sm text-emerald-900">
                {result.answer}
              </div>
            </div>
          ) : (
            <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900">
              No confident match. AI would fall back to live LLM generation.
            </div>
          )}
          <div className="text-xs text-dishhome-ink/50 uppercase tracking-widest">
            Top matches
          </div>
          {result.matched.length === 0 && (
            <p className="text-xs text-dishhome-ink/50">No matches.</p>
          )}
          {result.matched.map((m) => (
            <div
              key={m.faq.id}
              className="rounded-lg border border-black/5 px-3 py-2 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-dishhome-ink/60">
                  score {m.score}
                </span>
                {m.faq.category && (
                  <Badge tone="info">{m.faq.category}</Badge>
                )}
              </div>
              <div className="mt-1 text-dishhome-ink">
                {m.faq.question_ne || m.faq.question_en}
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function BulkImportCard({ onImported }: { onImported: () => void }) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const errToast = useAsyncErrorToast();

  async function handle(file: File) {
    if (file.size > 2 * 1024 * 1024) {
      toast.warn("File too large", "Max 2 MB");
      return;
    }
    setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await api.upload<{ added: number; skipped: number; total: number }>(
        "/faqs/import",
        fd,
      );
      toast.success(
        "Import complete",
        `${res.added} added, ${res.skipped} skipped`,
      );
      onImported();
    } catch (e) {
      errToast(e, "Import failed");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <Card title="Bulk import">
      <p className="text-xs text-dishhome-ink/60">
        JSON or JSONL file. Each item needs at least one question + one answer.
      </p>
      <input
        ref={inputRef}
        type="file"
        accept=".json,.jsonl,application/json"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handle(f);
        }}
      />
      <Button
        variant="ghost"
        className="mt-3 w-full"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
      >
        {busy ? "Importing…" : "Choose JSON file"}
      </Button>
      <pre className="mt-3 text-[10px] bg-dishhome-mist/70 rounded-md p-2 overflow-x-auto">
{`[
  {
    "question_en": "How do I pay my bill?",
    "answer_en": "Use eSewa or Khalti…",
    "category": "billing",
    "tags": ["payment"]
  }
]`}
      </pre>
    </Card>
  );
}
