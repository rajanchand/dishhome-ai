import { useEffect, useState } from "react";
import { api, type Label, type SavedReply } from "../lib/api";
import {
  Button,
  Card,
  Input,
  PageBody,
  PageHeader,
} from "../components/ui";
import { Skeleton } from "../components/Skeleton";
import { useAsyncErrorToast, useToast } from "../components/Toast";

export default function SavedReplies() {
  const [replies, setReplies] = useState<SavedReply[] | null>(null);
  const [labels, setLabels] = useState<Label[] | null>(null);
  const errToast = useAsyncErrorToast();
  const toast = useToast();

  async function refresh() {
    try {
      const [r, l] = await Promise.all([
        api.get<SavedReply[]>("/saved-replies"),
        api.get<Label[]>("/labels"),
      ]);
      setReplies(r);
      setLabels(l);
    } catch (e) {
      errToast(e, "Could not load");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <PageHeader
        title="Saved Replies & Labels"
        subtitle="Pre-written responses for common situations, plus the label palette your team uses to organise contacts and conversations."
      />
      <PageBody>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="space-y-4">
            <AddReplyCard onAdded={refresh} />
            <Card title={`Saved replies (${replies?.length ?? 0})`}>
              {!replies ? (
                <Skeleton className="h-24" />
              ) : replies.length === 0 ? (
                <p className="text-sm text-dishhome-ink/50">
                  No saved replies yet.
                </p>
              ) : (
                <div className="space-y-2">
                  {replies.map((r) => (
                    <div
                      key={r.id}
                      className="rounded-lg border border-black/5 p-3"
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-medium text-dishhome-blue">
                          {r.title}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] uppercase tracking-widest text-dishhome-ink/50">
                            {r.language}
                          </span>
                          <button
                            onClick={async () => {
                              if (!confirm(`Delete "${r.title}"?`)) return;
                              try {
                                await api.delete(`/saved-replies/${r.id}`);
                                toast.success("Reply deleted");
                                refresh();
                              } catch (e) {
                                errToast(e, "Delete failed");
                              }
                            }}
                            className="text-[11px] text-rose-600 hover:underline"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                      <p className="text-xs text-dishhome-ink/70 mt-1.5">
                        {r.body}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          <div className="space-y-4">
            <AddLabelCard onAdded={refresh} />
            <Card title={`Labels (${labels?.length ?? 0})`}>
              {!labels ? (
                <Skeleton className="h-24" />
              ) : labels.length === 0 ? (
                <p className="text-sm text-dishhome-ink/50">No labels yet.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {labels.map((l) => (
                    <div
                      key={l.id}
                      className="group flex items-center gap-2 rounded-full px-3 py-1 text-sm text-white"
                      style={{ background: l.color }}
                    >
                      <span>{l.name}</span>
                      <button
                        onClick={async () => {
                          if (!confirm(`Delete label "${l.name}"?`)) return;
                          try {
                            await api.delete(`/labels/${l.id}`);
                            toast.success("Label deleted");
                            refresh();
                          } catch (e) {
                            errToast(e, "Delete failed");
                          }
                        }}
                        className="opacity-60 hover:opacity-100 text-xs"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>
      </PageBody>
    </>
  );
}

function AddReplyCard({ onAdded }: { onAdded: () => void }) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [language, setLanguage] = useState<"ne" | "en">("ne");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const errToast = useAsyncErrorToast();

  async function submit() {
    setBusy(true);
    try {
      await api.post<SavedReply>("/saved-replies", { title, body, language });
      toast.success("Reply saved");
      setTitle("");
      setBody("");
      onAdded();
    } catch (e) {
      errToast(e, "Could not save");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Add saved reply">
      <div className="space-y-3">
        <Input
          label="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Greeting (Nepali)"
        />
        <label className="block">
          <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
            Body
          </span>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={4}
            className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dishhome-blue/30"
            placeholder="Namaste, DishHome ma swagatam chha…"
          />
        </label>
        <label className="block">
          <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
            Language
          </span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as "ne" | "en")}
            className="rounded-lg border border-black/10 bg-white px-3 py-2 text-sm"
          >
            <option value="ne">Nepali</option>
            <option value="en">English</option>
          </select>
        </label>
        <Button onClick={submit} disabled={busy || !title.trim() || !body.trim()}>
          {busy ? "Saving…" : "Save reply"}
        </Button>
      </div>
    </Card>
  );
}

function AddLabelCard({ onAdded }: { onAdded: () => void }) {
  const [name, setName] = useState("");
  const [color, setColor] = useState("#0ea5e9");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const errToast = useAsyncErrorToast();

  async function submit() {
    setBusy(true);
    try {
      await api.post<Label>("/labels", { name, color });
      toast.success("Label added");
      setName("");
      onAdded();
    } catch (e) {
      errToast(e, "Could not save");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Add label">
      <div className="space-y-3">
        <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="High priority" />
        <label className="block">
          <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
            Color
          </span>
          <input
            type="color"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            className="h-10 w-20 rounded-md border border-black/10"
          />
        </label>
        <Button onClick={submit} disabled={busy || !name.trim()}>
          {busy ? "Saving…" : "Add label"}
        </Button>
      </div>
    </Card>
  );
}
