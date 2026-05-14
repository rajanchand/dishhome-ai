import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, type DemoCustomer } from "../lib/api";
import {
  Badge,
  Card,
  Input,
  PageBody,
  PageHeader,
  statusTone,
} from "../components/ui";
import { Skeleton } from "../components/Skeleton";
import { useAsyncErrorToast } from "../components/Toast";

const SCENARIOS: { key: string; label: string }[] = [
  { key: "all", label: "All" },
  { key: "healthy", label: "Healthy" },
  { key: "router_offline", label: "Router offline" },
  { key: "area_outage", label: "Area outage" },
  { key: "master_down", label: "OLT (master) down" },
  { key: "network_down", label: "Network down" },
  { key: "low_power", label: "Low RX power" },
  { key: "pppoe_disconnected", label: "PPPoE failed" },
  { key: "wifi_only_issue", label: "WiFi-only issue" },
];

export default function Customers() {
  const [list, setList] = useState<DemoCustomer[] | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [query, setQuery] = useState("");
  const errToast = useAsyncErrorToast();

  useEffect(() => {
    api
      .get<DemoCustomer[]>("/huawei/customers")
      .then(setList)
      .catch((e) => errToast(e, "Could not load customers"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(() => {
    if (!list) return [];
    let out = list;
    if (filter !== "all") out = out.filter((c) => c.scenario === filter);
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      out = out.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          c.mobile.includes(q) ||
          c.customer_id.toLowerCase().includes(q) ||
          c.address.toLowerCase().includes(q),
      );
    }
    return out;
  }, [list, filter, query]);

  return (
    <>
      <PageHeader
        title="Demo Customers"
        subtitle="Sample DishHome customers seeded across every common router / network scenario. Click one to open its DishHome integration view with the Huawei ONT diagnostics."
      />
      <PageBody>
        <Card>
          <div className="flex flex-col md:flex-row md:items-center gap-3">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by name, mobile, customer ID, address…"
              className="md:flex-1"
            />
            <div className="flex flex-wrap gap-1 bg-dishhome-mist rounded-lg p-1">
              {SCENARIOS.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setFilter(s.key)}
                  className={`px-3 py-1.5 text-xs uppercase tracking-widest rounded-md transition ${
                    filter === s.key
                      ? "bg-white text-dishhome-blue shadow-sm"
                      : "text-dishhome-ink/60 hover:text-dishhome-blue"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {!list ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 mt-5">
              {[...Array(6)].map((_, i) => (
                <Skeleton key={i} className="h-40" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <p className="mt-6 text-sm text-dishhome-ink/50">
              No customers match this filter.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 mt-5">
              {filtered.map((c) => (
                <CustomerCard key={c.customer_id} c={c} />
              ))}
            </div>
          )}
        </Card>
      </PageBody>
    </>
  );
}

function CustomerCard({ c }: { c: DemoCustomer }) {
  const tone = c.tone === "danger" ? "danger" : c.tone === "warn" ? "warn" : c.tone === "success" ? "success" : "info";
  return (
    <Link
      to={`/integrations?customer=${c.customer_id}`}
      className="block rounded-2xl bg-white border border-black/5 shadow-sm p-4 hover:border-dishhome-blue/30 transition"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold text-dishhome-blue">{c.name}</div>
          <div className="text-xs text-dishhome-ink/60 font-mono">
            {c.customer_id} · {c.mobile}
          </div>
        </div>
        <Badge tone={statusTone(c.online ? "active" : "failed")}>
          {c.online ? "Online" : "Offline"}
        </Badge>
      </div>
      <div className="mt-2 text-xs text-dishhome-ink/70">{c.address}</div>
      <div className="mt-1 text-xs text-dishhome-ink/60">{c.package}</div>

      <div className="mt-3 rounded-lg bg-dishhome-mist/60 px-3 py-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] uppercase tracking-widest text-dishhome-ink/50">
            Scenario
          </span>
          <Badge tone={tone}>{c.scenario.replace(/_/g, " ")}</Badge>
        </div>
        <div className="mt-1 text-sm text-dishhome-ink">{c.headline}</div>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-dishhome-ink/60">
        <span>
          <span className="opacity-60">Huawei </span>
          {c.device_model ?? "—"}
        </span>
        <span>
          {c.rx_power_dbm !== null ? `RX ${c.rx_power_dbm} dBm` : "RX —"}
        </span>
      </div>
    </Link>
  );
}
