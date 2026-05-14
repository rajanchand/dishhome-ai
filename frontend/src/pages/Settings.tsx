import { Card, Input, PageBody, PageHeader } from "../components/ui";
import { useAuth } from "../lib/auth";

export default function Settings() {
  const { user } = useAuth();
  return (
    <>
      <PageHeader
        title="Settings"
        subtitle="System configuration. In production these values come from environment variables and are read-only here."
      />
      <PageBody>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card title="AI engine">
            <div className="space-y-3">
              <Input label="LLM (Ollama model)" defaultValue="llama3.1:70b" />
              <Input label="STT model" defaultValue="faster-whisper large-v3" />
              <Input label="TTS voice (default)" defaultValue="dishhome-ne-female-v1 (Anjali)" />
              <Input label="VAD" defaultValue="Silero v4" />
            </div>
          </Card>

          <Card title="Telephony">
            <div className="space-y-3">
              <Input label="SIP trunk" defaultValue="sip.provider.com.np" />
              <Input label="Toll-free DID" defaultValue="16600122000" />
              <Input label="AudioSocket host" defaultValue="0.0.0.0:4000" />
              <Input label="Codec" defaultValue="PCMU / PCMA" />
            </div>
          </Card>

          <Card title="DishHome system endpoints">
            <div className="space-y-3">
              <Input label="Billing / CRM API" placeholder="https://billing.dishhome.com.np" />
              <Input label="Network OSS API" placeholder="https://oss.dishhome.com.np" />
              <Input label="Ticketing API" placeholder="https://tickets.dishhome.com.np" />
              <Input label="SMS gateway" placeholder="https://sms.dishhome.com.np" />
            </div>
          </Card>

          <Card title="Profile">
            <dl className="text-sm space-y-2">
              <Row label="Name">{user?.name}</Row>
              <Row label="Username"><code>{user?.username}</code></Row>
              <Row label="Email">{user?.email}</Row>
              <Row label="Role">{user?.role}</Row>
            </dl>
          </Card>
        </div>
      </PageBody>
    </>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-xs uppercase tracking-widest text-dishhome-ink/50">
        {label}
      </dt>
      <dd>{children}</dd>
    </div>
  );
}
