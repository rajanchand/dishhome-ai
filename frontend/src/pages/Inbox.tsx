import { useEffect, useMemo, useState } from "react";
import {
  api,
  type Contact,
  type Conversation,
  type Label,
  type SavedReply,
} from "../lib/api";
import {
  Badge,
  Button,
  Card,
  PageBody,
  PageHeader,
} from "../components/ui";
import { Skeleton } from "../components/Skeleton";
import { useAsyncErrorToast, useToast } from "../components/Toast";

export default function Inbox() {
  const [list, setList] = useState<Conversation[] | null>(null);
  const [contacts, setContacts] = useState<Record<string, Contact>>({});
  const [labels, setLabels] = useState<Record<string, Label>>({});
  const [savedReplies, setSavedReplies] = useState<SavedReply[]>([]);
  const [filter, setFilter] = useState<"all" | "open" | "closed">("all");
  const [activeId, setActiveId] = useState<string | null>(null);
  const errToast = useAsyncErrorToast();
  const toast = useToast();

  async function refresh() {
    try {
      const qs = filter === "all" ? "" : `?status=${filter}`;
      const [cs, ct, lb, sr] = await Promise.all([
        api.get<Conversation[]>(`/conversations${qs}`),
        api.get<Contact[]>("/contacts"),
        api.get<Label[]>("/labels"),
        api.get<SavedReply[]>("/saved-replies"),
      ]);
      setList(cs);
      setContacts(Object.fromEntries(ct.map((c) => [c.id, c])));
      setLabels(Object.fromEntries(lb.map((l) => [l.id, l])));
      setSavedReplies(sr);
      if (!activeId && cs[0]) setActiveId(cs[0].id);
    } catch (e) {
      errToast(e, "Could not load inbox");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const active = useMemo(
    () => list?.find((c) => c.id === activeId) ?? null,
    [list, activeId],
  );

  async function send(body: string) {
    if (!active) return;
    try {
      const c = await api.post<Conversation>(
        `/conversations/${active.id}/reply`,
        { body, author: "agent" },
      );
      setList((cur) => (cur ? cur.map((x) => (x.id === c.id ? c : x)) : cur));
      toast.success("Message sent");
    } catch (e) {
      errToast(e, "Send failed");
    }
  }

  async function close() {
    if (!active) return;
    try {
      const c = await api.post<Conversation>(
        `/conversations/${active.id}/close`,
      );
      setList((cur) => (cur ? cur.map((x) => (x.id === c.id ? c : x)) : cur));
      toast.success("Conversation closed");
    } catch (e) {
      errToast(e, "Could not close");
    }
  }

  return (
    <>
      <PageHeader
        title="Inbox"
        subtitle="Unified view of voice, SMS, WhatsApp, and web conversations. Reply with saved replies, apply labels, close when done."
        actions={
          <div className="flex items-center gap-1 bg-dishhome-mist rounded-lg p-1">
            {(["all", "open", "closed"] as const).map((s) => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={`px-3 py-1.5 text-xs uppercase tracking-widest rounded-md ${
                  filter === s
                    ? "bg-white text-dishhome-blue shadow-sm"
                    : "text-dishhome-ink/60"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        }
      />
      <PageBody>
        <div className="grid grid-cols-12 gap-4 min-h-[60vh]">
          <Card className="col-span-12 md:col-span-4 lg:col-span-3">
            {!list ? (
              <Skeleton className="h-72" />
            ) : list.length === 0 ? (
              <p className="text-sm text-dishhome-ink/50">No conversations.</p>
            ) : (
              <div className="-m-5">
                {list.map((c) => {
                  const ct = contacts[c.contact_id];
                  return (
                    <button
                      key={c.id}
                      onClick={() => setActiveId(c.id)}
                      className={`w-full text-left px-4 py-3 border-b border-black/5 transition ${
                        activeId === c.id
                          ? "bg-dishhome-blue/5"
                          : "hover:bg-black/5"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-dishhome-blue text-sm">
                          {ct?.name ?? c.contact_id}
                        </span>
                        <Badge
                          tone={c.status === "open" ? "info" : "neutral"}
                        >
                          {c.status}
                        </Badge>
                      </div>
                      <div className="text-xs text-dishhome-ink/60 mt-0.5">
                        [{c.channel}] {c.subject}
                      </div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {c.labels.map((lid) => {
                          const l = labels[lid];
                          return l ? (
                            <span
                              key={lid}
                              className="text-[9px] px-1.5 py-0.5 rounded-full text-white"
                              style={{ background: l.color }}
                            >
                              {l.name}
                            </span>
                          ) : null;
                        })}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </Card>

          <Card className="col-span-12 md:col-span-8 lg:col-span-9 flex flex-col">
            {!active ? (
              <p className="text-sm text-dishhome-ink/50">
                Select a conversation.
              </p>
            ) : (
              <>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="font-semibold text-dishhome-blue">
                      {contacts[active.contact_id]?.name ?? active.contact_id}
                    </div>
                    <div className="text-xs text-dishhome-ink/60">
                      [{active.channel}] {active.subject}
                    </div>
                  </div>
                  {active.status === "open" && (
                    <Button variant="ghost" onClick={close}>
                      Close
                    </Button>
                  )}
                </div>
                <div className="flex-1 overflow-y-auto space-y-3 pb-4 max-h-[55vh] pr-2">
                  {active.messages.map((m, i) => (
                    <MessageBubble key={i} m={m} />
                  ))}
                </div>
                <ReplyBox replies={savedReplies} onSend={send} />
              </>
            )}
          </Card>
        </div>
      </PageBody>
    </>
  );
}

function MessageBubble({
  m,
}: {
  m: Conversation["messages"][number];
}) {
  const isCustomer = m.author === "customer";
  return (
    <div className={`flex ${isCustomer ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-sm ${
          isCustomer
            ? "bg-dishhome-mist border border-black/5 text-dishhome-ink"
            : m.author === "ai"
              ? "bg-dishhome-blue text-white"
              : "bg-dishhome-orange/10 border border-dishhome-orange/30 text-dishhome-ink"
        }`}
      >
        <div
          className={`text-[10px] uppercase tracking-widest mb-1 ${
            isCustomer ? "text-dishhome-ink/50" : m.author === "ai" ? "text-white/60" : "text-dishhome-orange"
          }`}
        >
          {m.author} · {new Date(m.at).toLocaleTimeString()}
        </div>
        {m.body}
      </div>
    </div>
  );
}

function ReplyBox({
  replies,
  onSend,
}: {
  replies: SavedReply[];
  onSend: (body: string) => void;
}) {
  const [body, setBody] = useState("");
  return (
    <div className="border-t border-black/5 pt-3">
      <div className="flex flex-wrap gap-1.5 mb-2 max-h-20 overflow-y-auto">
        {replies.map((r) => (
          <button
            key={r.id}
            onClick={() => setBody(r.body)}
            className="text-[11px] px-2.5 py-1 rounded-full bg-dishhome-mist hover:bg-dishhome-blue/10 text-dishhome-ink/70 hover:text-dishhome-blue transition"
            title={r.body}
          >
            ↪ {r.title}
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={2}
          placeholder="Type a reply, or pick a saved reply…"
          className="flex-1 rounded-lg border border-black/10 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dishhome-blue/30"
        />
        <Button
          onClick={() => {
            if (body.trim()) {
              onSend(body.trim());
              setBody("");
            }
          }}
          disabled={!body.trim()}
        >
          Send
        </Button>
      </div>
    </div>
  );
}
