import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Contact, type Label } from "../lib/api";
import {
  Button,
  Card,
  Input,
  PageBody,
  PageHeader,
} from "../components/ui";
import { Skeleton } from "../components/Skeleton";
import { useAsyncErrorToast, useToast } from "../components/Toast";

export default function Contacts() {
  const [list, setList] = useState<Contact[] | null>(null);
  const [labels, setLabels] = useState<Label[]>([]);
  const [activeLabel, setActiveLabel] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const errToast = useAsyncErrorToast();
  const toast = useToast();

  async function refresh() {
    try {
      const params = new URLSearchParams();
      if (activeLabel !== "all") params.set("label", activeLabel);
      if (search.trim()) params.set("q", search.trim());
      const [contacts, lbls] = await Promise.all([
        api.get<Contact[]>(`/contacts${params.toString() ? `?${params}` : ""}`),
        api.get<Label[]>("/labels"),
      ]);
      setList(contacts);
      setLabels(lbls);
    } catch (e) {
      errToast(e, "Could not load contacts");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeLabel, search]);

  async function remove(id: string) {
    try {
      await api.delete(`/contacts/${id}`);
      toast.success("Contact removed");
      refresh();
    } catch (e) {
      errToast(e, "Delete failed");
    }
  }

  const labelMap = Object.fromEntries(labels.map((l) => [l.id, l]));

  return (
    <>
      <PageHeader
        title="Contacts"
        subtitle="People your AI agents interact with — DishHome customers and outreach leads. Filter by label, search by name / mobile / customer ID."
        actions={<Button onClick={() => setCreating(true)}>+ New contact</Button>}
      />
      <PageBody>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <Card title="Labels" className="lg:col-span-1">
            <button
              onClick={() => setActiveLabel("all")}
              className={`w-full text-left text-sm rounded-md px-3 py-1.5 mb-1 transition ${
                activeLabel === "all"
                  ? "bg-dishhome-blue/10 text-dishhome-blue font-semibold"
                  : "text-dishhome-ink/70 hover:bg-black/5"
              }`}
            >
              All contacts
            </button>
            {labels.map((l) => (
              <button
                key={l.id}
                onClick={() => setActiveLabel(l.id)}
                className={`w-full text-left text-sm rounded-md px-3 py-1.5 mb-1 flex items-center gap-2 transition ${
                  activeLabel === l.id
                    ? "bg-dishhome-blue/10 text-dishhome-blue font-semibold"
                    : "text-dishhome-ink/70 hover:bg-black/5"
                }`}
              >
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ background: l.color }}
                />
                {l.name}
              </button>
            ))}
            <Link
              to="/saved-replies"
              className="block mt-3 text-xs text-dishhome-blue hover:underline"
            >
              Manage labels & saved replies →
            </Link>
          </Card>

          <Card title={`${list?.length ?? 0} contacts`} className="lg:col-span-3">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, mobile, email, customer ID…"
              className="mb-3"
            />
            {!list ? (
              <div className="space-y-2">
                {[...Array(4)].map((_, i) => (
                  <Skeleton key={i} className="h-12" />
                ))}
              </div>
            ) : list.length === 0 ? (
              <p className="text-sm text-dishhome-ink/50">
                No contacts match this view.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-widest text-dishhome-ink/50 border-b border-black/5">
                    <th className="py-2">Name</th>
                    <th>Mobile</th>
                    <th>Customer</th>
                    <th>Labels</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((c) => (
                    <tr key={c.id} className="border-b border-black/5 last:border-0">
                      <td className="py-2.5">
                        <div className="font-medium">{c.name}</div>
                        {c.email && (
                          <div className="text-xs text-dishhome-ink/60">
                            {c.email}
                          </div>
                        )}
                      </td>
                      <td className="font-mono text-xs">{c.mobile}</td>
                      <td>
                        {c.customer_id ? (
                          <Link
                            to={`/integrations?customer=${c.customer_id}`}
                            className="text-xs font-mono text-dishhome-blue hover:underline"
                          >
                            {c.customer_id}
                          </Link>
                        ) : (
                          <span className="text-xs text-dishhome-ink/40">—</span>
                        )}
                      </td>
                      <td>
                        <div className="flex flex-wrap gap-1">
                          {c.labels.map((lid) => {
                            const l = labelMap[lid];
                            return l ? (
                              <span
                                key={lid}
                                className="text-[10px] px-2 py-0.5 rounded-full text-white"
                                style={{ background: l.color }}
                              >
                                {l.name}
                              </span>
                            ) : null;
                          })}
                        </div>
                      </td>
                      <td className="text-right">
                        <button
                          onClick={() => {
                            if (confirm(`Remove ${c.name}?`)) remove(c.id);
                          }}
                          className="text-[11px] text-rose-600 hover:underline"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>

        {creating && (
          <CreateContactModal
            labels={labels}
            onClose={() => setCreating(false)}
            onCreated={() => {
              setCreating(false);
              refresh();
            }}
          />
        )}
      </PageBody>
    </>
  );
}

function CreateContactModal({
  labels,
  onClose,
  onCreated,
}: {
  labels: Label[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [mobile, setMobile] = useState("");
  const [email, setEmail] = useState("");
  const [customerId, setCustomerId] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const errToast = useAsyncErrorToast();

  async function submit() {
    setBusy(true);
    try {
      await api.post<Contact>("/contacts", {
        name,
        mobile,
        email: email || null,
        customer_id: customerId || null,
        labels: selected,
        notes: notes || null,
      });
      toast.success("Contact added");
      onCreated();
    } catch (e) {
      errToast(e, "Could not add contact");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 bg-black/40 z-40 flex items-center justify-center p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-2xl bg-white shadow-xl p-6"
      >
        <h2 className="text-lg font-semibold text-dishhome-blue">New contact</h2>
        <div className="mt-4 space-y-3">
          <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <Input label="Mobile" value={mobile} onChange={(e) => setMobile(e.target.value)} />
          <Input label="Email (optional)" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Input label="Customer ID (optional)" value={customerId} onChange={(e) => setCustomerId(e.target.value)} />
          <label className="block">
            <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
              Labels
            </span>
            <div className="flex flex-wrap gap-2">
              {labels.map((l) => {
                const on = selected.includes(l.id);
                return (
                  <button
                    key={l.id}
                    onClick={() =>
                      setSelected((s) =>
                        on ? s.filter((x) => x !== l.id) : [...s, l.id],
                      )
                    }
                    className={`text-xs rounded-full px-2.5 py-0.5 transition ${
                      on
                        ? "text-white"
                        : "text-dishhome-ink/60 border border-black/10"
                    }`}
                    style={on ? { background: l.color } : undefined}
                  >
                    {l.name}
                  </button>
                );
              })}
            </div>
          </label>
          <label className="block">
            <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
              Notes
            </span>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm"
            />
          </label>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={busy || !name.trim() || !mobile.trim()}
          >
            {busy ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>
    </div>
  );
}
