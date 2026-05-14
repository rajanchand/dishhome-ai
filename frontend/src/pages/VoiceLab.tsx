import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  fetchAudioBlobUrl,
  type Voice,
  type VoicePreviewResponse,
} from "../lib/api";
import { Badge, Button, Card, Input, PageBody, PageHeader } from "../components/ui";
import { Skeleton } from "../components/Skeleton";
import { useAsyncErrorToast, useToast } from "../components/Toast";

const PRESETS = [
  {
    label: "Greeting (Nepali)",
    text: "Namaste, DishHome customer care ma swagatam chha. Ma tapainlai kasari sahayog garna saktinchu?",
  },
  {
    label: "Greeting (English)",
    text: "Hello, welcome to DishHome customer care. How may I help you today?",
  },
  {
    label: "Router reboot (Nepali)",
    text: "Tapainko router malai check garna dinuhos. Ma remote reboot garchu — 2 minute pakhanus.",
  },
  {
    label: "Ticket created (Nepali)",
    text: "Tapainko samasya samadhan ka lagi ticket banaiyo. Hamro field team 90 minute bhitra aainchhan.",
  },
];

export default function VoiceLab() {
  const [voices, setVoices] = useState<Voice[] | null>(null);
  const [selected, setSelected] = useState<string>("");
  const [text, setText] = useState(PRESETS[0].text);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const toast = useToast();
  const errToast = useAsyncErrorToast();

  async function refresh() {
    try {
      const v = await api.get<Voice[]>("/voice/voices");
      setVoices(v);
      if (!selected && v[0]) setSelected(v[0].id);
    } catch (e) {
      errToast(e, "Could not load voices");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const currentVoice = useMemo(
    () => voices?.find((v) => v.id === selected),
    [voices, selected],
  );

  function stop() {
    window.speechSynthesis?.cancel();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setPlaying(false);
  }

  async function play() {
    if (!selected || !text.trim() || !currentVoice) return;
    stop();
    setPlaying(true);
    try {
      // If voice has an uploaded sample, play that first (preview the cloned voice itself)
      if (currentVoice.source === "uploaded" && currentVoice.sample_url) {
        const url = await fetchAudioBlobUrl(currentVoice.sample_url);
        const a = new Audio(url);
        audioRef.current = a;
        a.onended = () => {
          setPlaying(false);
          URL.revokeObjectURL(url);
        };
        a.onerror = () => setPlaying(false);
        await a.play();
        return;
      }
      const spec = await api.post<VoicePreviewResponse>("/voice/preview", {
        voice_id: selected,
        text,
      });
      speak(spec);
    } catch (e) {
      setPlaying(false);
      errToast(e, "Preview failed");
    }
  }

  function speak(spec: VoicePreviewResponse) {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      toast.warn("Web Speech API not available in this browser");
      setPlaying(false);
      return;
    }
    const u = new SpeechSynthesisUtterance(spec.text);
    u.lang = spec.language;
    u.rate = spec.rate;
    u.pitch = spec.pitch;
    const sysVoices = window.speechSynthesis.getVoices();
    const match = sysVoices.find(
      (v) =>
        v.lang.startsWith(spec.language.split("-")[0]) &&
        (spec.gender === "female"
          ? /female|samantha|priya|kalpana|veena/i.test(v.name)
          : /male|daniel|rishi|alex/i.test(v.name)),
    );
    if (match) u.voice = match;
    u.onend = () => setPlaying(false);
    u.onerror = () => setPlaying(false);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  }

  return (
    <>
      <PageHeader
        title="Voice Lab"
        subtitle="Preview, upload, and clone the AI's voice. Upload a 5–60 second clean sample of any voice to train a custom voice clone (in production, this trains a Piper/Coqui model)."
      />
      <PageBody>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-1 space-y-4">
            <Card title="Voice library">
              {!voices ? (
                <div className="space-y-2">
                  {[...Array(4)].map((_, i) => (
                    <Skeleton key={i} className="h-16" />
                  ))}
                </div>
              ) : (
                <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
                  {voices.map((v) => (
                    <VoiceCard
                      key={v.id}
                      voice={v}
                      selected={selected === v.id}
                      onSelect={() => setSelected(v.id)}
                      onDelete={async () => {
                        try {
                          await api.delete(`/voice/voices/${v.id}`);
                          toast.success("Voice deleted", v.name);
                          refresh();
                        } catch (e) {
                          errToast(e, "Delete failed");
                        }
                      }}
                    />
                  ))}
                </div>
              )}
            </Card>

            <UploadCard onUploaded={refresh} />
          </div>

          <Card
            title={currentVoice ? `Preview · ${currentVoice.name}` : "Preview"}
            className="lg:col-span-2"
          >
            <div className="flex flex-wrap gap-2 mb-3">
              {PRESETS.map((p) => (
                <button
                  key={p.label}
                  onClick={() => setText(p.text)}
                  className="text-xs px-3 py-1.5 rounded-full bg-dishhome-mist hover:bg-dishhome-blue/10 text-dishhome-ink/70 hover:text-dishhome-blue transition"
                >
                  {p.label}
                </button>
              ))}
            </div>

            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={6}
              maxLength={400}
              className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dishhome-blue/30"
              placeholder="Type a Nepali or English line for the AI to say…"
            />
            <div className="text-xs text-dishhome-ink/40 mt-1">
              {text.length} / 400 characters
            </div>

            <div className="mt-4 flex items-center gap-3 flex-wrap">
              {playing ? (
                <Button variant="danger" onClick={stop}>
                  ■ Stop
                </Button>
              ) : (
                <Button onClick={play} disabled={!text.trim() || !currentVoice}>
                  ▶ Play sample
                </Button>
              )}
              {currentVoice?.source === "uploaded" && (
                <span className="text-xs text-dishhome-ink/60">
                  Playing the original upload (clone training queued — uses
                  Web Speech fallback for new synthesis in this scaffold).
                </span>
              )}
              {currentVoice?.source === "builtin" && (
                <span className="text-xs text-dishhome-ink/50">
                  Tip: Nepali voices fall back to the closest available system
                  voice if Nepali isn't installed on your OS.
                </span>
              )}
            </div>
          </Card>
        </div>
      </PageBody>
    </>
  );
}

function VoiceCard({
  voice,
  selected,
  onSelect,
  onDelete,
}: {
  voice: Voice;
  selected: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      className={`rounded-lg border transition ${
        selected
          ? "border-dishhome-blue bg-dishhome-blue/5"
          : "border-black/5 hover:border-dishhome-blue/30"
      }`}
    >
      <button
        onClick={onSelect}
        className="w-full text-left p-3"
      >
        <div className="flex items-center justify-between">
          <span className="font-medium text-dishhome-blue">{voice.name}</span>
          <Badge tone={voice.source === "uploaded" ? "warn" : "info"}>
            {voice.source === "uploaded" ? "Custom" : "Built-in"}
          </Badge>
        </div>
        <div className="text-[10px] uppercase tracking-widest text-dishhome-ink/50 mt-1">
          {voice.language === "ne" ? "Nepali" : "English"} · {voice.gender}
        </div>
        <div className="text-xs text-dishhome-ink/60 mt-1">{voice.tone}</div>
      </button>
      {voice.source === "uploaded" && (
        <div className="px-3 pb-2 -mt-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (confirm(`Delete voice "${voice.name}"?`)) onDelete();
            }}
            className="text-[11px] text-rose-600 hover:underline"
          >
            Delete
          </button>
        </div>
      )}
    </div>
  );
}

function UploadCard({ onUploaded }: { onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [language, setLanguage] = useState<"ne" | "en">("ne");
  const [gender, setGender] = useState<"female" | "male">("female");
  const [tone, setTone] = useState("warm, professional");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const toast = useToast();
  const errToast = useAsyncErrorToast();

  function pick(f: File | null) {
    if (!f) return setFile(null);
    if (f.size > 10 * 1024 * 1024) {
      toast.warn("File too large", "Max 10 MB");
      return;
    }
    setFile(f);
    if (!name) setName(f.name.replace(/\.[^.]+$/, ""));
  }

  async function submit() {
    if (!file || !name.trim()) {
      toast.warn("Add a file and a voice name");
      return;
    }
    setBusy(true);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", name.trim());
    fd.append("language", language);
    fd.append("gender", gender);
    fd.append("tone", tone);
    try {
      const v = await api.upload<Voice>("/voice/upload", fd);
      toast.success("Voice uploaded", v.name);
      setFile(null);
      setName("");
      if (inputRef.current) inputRef.current.value = "";
      onUploaded();
    } catch (e) {
      errToast(e, "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Upload your own voice">
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          pick(e.dataTransfer.files?.[0] ?? null);
        }}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-4 text-center transition ${
          file
            ? "border-dishhome-blue/40 bg-dishhome-blue/5"
            : "border-black/10 hover:border-dishhome-blue/40 hover:bg-dishhome-blue/5"
        }`}
      >
        <div className="text-2xl">♪</div>
        {file ? (
          <div className="mt-1 text-sm font-medium text-dishhome-blue">
            {file.name}
          </div>
        ) : (
          <div className="mt-1 text-sm text-dishhome-ink/70">
            Drop an audio file here or click to choose
          </div>
        )}
        <div className="text-[11px] text-dishhome-ink/50 mt-1">
          WAV · MP3 · M4A · OGG · FLAC · WebM · max 10 MB
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="audio/*"
          className="hidden"
          onChange={(e) => pick(e.target.files?.[0] ?? null)}
        />
      </div>

      <div className="mt-3 space-y-2">
        <Input
          label="Voice name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Anjali (DishHome female)"
        />
        <div className="grid grid-cols-2 gap-2">
          <label className="block">
            <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
              Language
            </span>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value as "ne" | "en")}
              className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm"
            >
              <option value="ne">Nepali</option>
              <option value="en">English</option>
            </select>
          </label>
          <label className="block">
            <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
              Gender
            </span>
            <select
              value={gender}
              onChange={(e) => setGender(e.target.value as "female" | "male")}
              className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm"
            >
              <option value="female">Female</option>
              <option value="male">Male</option>
            </select>
          </label>
        </div>
        <Input
          label="Tone description"
          value={tone}
          onChange={(e) => setTone(e.target.value)}
          placeholder="warm, professional, confident…"
        />
      </div>

      <Button
        onClick={submit}
        disabled={busy || !file || !name.trim()}
        className="w-full mt-3"
      >
        {busy ? "Uploading…" : "Train custom voice"}
      </Button>
      <div className="text-[11px] text-dishhome-ink/50 mt-2">
        Production: the sample is sent to the Piper/Coqui training pipeline.
        In this scaffold we store the file and expose it for direct playback.
      </div>
    </Card>
  );
}
