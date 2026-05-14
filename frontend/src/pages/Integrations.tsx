import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  api,
  ApiError,
  type Customer,
  type RouterStatus,
  type Ticket,
} from "../lib/api";
import { Badge, Button, Card, Input, PageBody, PageHeader, statusTone } from "../components/ui";

export default function Integrations() {
  const [params] = useSearchParams();
  const [query, setQuery] = useState(params.get("customer") ?? "DH100234");
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [router, setRouter] = useState<RouterStatus | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, string>>({});

  useEffect(() => {
    if (params.get("customer")) lookup(params.get("customer")!);
    api.get<Ticket[]>("/integrations/dishhome/tickets").then(setTickets);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function lookup(q: string) {
    setErr(null);
    setCustomer(null);
    setRouter(null);
    setBusy(true);
    try {
      const c = await api.get<Customer>(
        `/integrations/dishhome/customer/${encodeURIComponent(q)}`,
      );
      setCustomer(c);
      const r = await api.get<RouterStatus>(
        `/integrations/dishhome/router-status/${c.ont_id}`,
      );
      setRouter(r);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Lookup failed");
    } finally {
      setBusy(false);
    }
  }

  async function reboot() {
    if (!router) return;
    setBusy(true);
    try {
      await api.post(
        `/integrations/dishhome/router-reboot/${router.ont_id}`,
      );
      alert(`Reboot command sent to ${router.ont_id}.`);
    } finally {
      setBusy(false);
    }
  }

  async function createTicket() {
    if (!customer) return;
    setBusy(true);
    try {
      const t = await api.post<Ticket>("/integrations/dishhome/ticket", {
        customer_id: customer.customer_id,
        issue: "Customer reported connectivity issue (via portal)",
        priority: "high",
      });
      setTickets((cur) => [t, ...cur]);
      alert(`Ticket ${t.id} created.`);
    } finally {
      setBusy(false);
    }
  }

  async function testSystem(system: string) {
    setTestResults((r) => ({ ...r, [system]: "Testing…" }));
    try {
      const res = await api.post<{ ok: boolean; latency_ms: number; message: string }>(
        "/integrations/test",
        { system },
      );
      setTestResults((r) => ({
        ...r,
        [system]: `${res.ok ? "✓" : "✗"} ${res.latency_ms}ms — ${res.message}`,
      }));
    } catch (e) {
      setTestResults((r) => ({
        ...r,
        [system]: `✗ ${e instanceof Error ? e.message : "failed"}`,
      }));
    }
  }

  return (
    <>
      <PageHeader
        title="DishHome System Integration"
        subtitle="Look up customers, diagnose ONT devices, create tickets, and test connectivity to billing/OSS/SMS systems."
      />
      <PageBody>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card title="Customer lookup" className="lg:col-span-2">
            <div className="flex gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Customer ID, mobile, or smartcard…"
                onKeyDown={(e) => e.key === "Enter" && lookup(query)}
              />
              <Button onClick={() => lookup(query)} disabled={busy}>
                Search
              </Button>
            </div>
            <div className="text-xs text-dishhome-ink/50 mt-1.5">
              Try: <code>DH100234</code>, <code>9841234567</code>, <code>SC-4429981</code>, <code>DH100997</code>
            </div>

            {err && (
              <div className="mt-3 text-sm text-rose-600 bg-rose-50 border border-rose-200 rounded-md px-3 py-2">
                {err}
              </div>
            )}

            {customer && (
              <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h3 className="text-xs uppercase tracking-widest text-dishhome-ink/50 mb-2">
                    Account
                  </h3>
                  <dl className="text-sm space-y-2">
                    <Field label="Name">{customer.name}</Field>
                    <Field label="Customer ID">
                      <code>{customer.customer_id}</code>
                    </Field>
                    <Field label="Mobile">
                      <code>{customer.mobile}</code>
                    </Field>
                    <Field label="Smartcard">
                      <code>{customer.smartcard}</code>
                    </Field>
                    <Field label="Package">{customer.package}</Field>
                    <Field label="Address">{customer.address}</Field>
                    <Field label="Balance (NPR)">
                      <span
                        className={
                          customer.balance_npr > 0
                            ? "text-rose-600 font-semibold"
                            : "text-emerald-600 font-semibold"
                        }
                      >
                        {customer.balance_npr.toLocaleString()}
                      </span>
                    </Field>
                    <Field label="Due date">{customer.due_date}</Field>
                    <Field label="Status">
                      <Badge tone={statusTone(customer.status)}>
                        {customer.status}
                      </Badge>
                    </Field>
                  </dl>
                </div>
                <div>
                  <h3 className="text-xs uppercase tracking-widest text-dishhome-ink/50 mb-2">
                    Router (ONT) diagnostics
                  </h3>
                  {router && (
                    <dl className="text-sm space-y-2">
                      <Field label="ONT ID">
                        <code>{router.ont_id}</code>
                      </Field>
                      <Field label="Online">
                        <Badge tone={router.online ? "success" : "danger"}>
                          {router.online ? "Yes" : "No"}
                        </Badge>
                      </Field>
                      <Field label="RX power">
                        {router.rx_power_dbm ?? "—"} dBm
                      </Field>
                      <Field label="TX power">
                        {router.tx_power_dbm ?? "—"} dBm
                      </Field>
                      <Field label="PPPoE">{router.pppoe_session}</Field>
                      <Field label="Uptime">{router.uptime_hours}h</Field>
                      <Field label="Area outage">
                        <Badge tone={router.area_outage ? "danger" : "success"}>
                          {router.area_outage ? "Yes" : "No"}
                        </Badge>
                      </Field>
                    </dl>
                  )}
                  <div className="mt-4 flex gap-2">
                    <Button onClick={reboot} disabled={busy} variant="secondary">
                      Remote reboot
                    </Button>
                    <Button
                      onClick={createTicket}
                      disabled={busy}
                      variant="ghost"
                    >
                      Create ticket
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </Card>

          <Card title="System health probes">
            <div className="space-y-2">
              {(["billing", "oss", "ticketing", "sms"] as const).map((s) => (
                <div
                  key={s}
                  className="flex items-center justify-between text-sm border-b border-black/5 pb-2 last:border-0"
                >
                  <span className="capitalize">{s}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-dishhome-ink/60">
                      {testResults[s] ?? "not tested"}
                    </span>
                    <button
                      onClick={() => testSystem(s)}
                      className="text-xs px-2 py-1 rounded-md bg-dishhome-mist hover:bg-dishhome-blue/10 text-dishhome-blue"
                    >
                      Test
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <Card title="Recent tickets" className="mt-4">
          {tickets.length === 0 ? (
            <p className="text-sm text-dishhome-ink/50">No tickets yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-widest text-dishhome-ink/50 border-b border-black/5">
                  <th className="py-2">Ticket</th>
                  <th>Customer</th>
                  <th>Issue</th>
                  <th>Priority</th>
                  <th>Team</th>
                  <th>ETA</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {tickets.map((t) => (
                  <tr key={t.id} className="border-b border-black/5 last:border-0">
                    <td className="py-2 font-mono text-xs">{t.id}</td>
                    <td className="font-mono text-xs">{t.customer_id}</td>
                    <td>{t.issue}</td>
                    <td>
                      <Badge
                        tone={
                          t.priority === "critical" || t.priority === "high"
                            ? "danger"
                            : "info"
                        }
                      >
                        {t.priority}
                      </Badge>
                    </td>
                    <td>{t.assigned_team}</td>
                    <td>{t.eta_minutes}m</td>
                    <td>
                      <Badge tone={statusTone(t.status)}>{t.status}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </PageBody>
    </>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-xs uppercase tracking-widest text-dishhome-ink/50">
        {label}
      </dt>
      <dd className="text-dishhome-ink text-right">{children}</dd>
    </div>
  );
}
