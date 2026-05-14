import { useEffect, useMemo, useState } from "react";
import { api, type Voice, type VoicePreviewResponse } from "../lib/api";
import { Button, Card, PageBody, PageHeader } from "../components/ui";

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
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [text, setText] = useState(PRESETS[0].text);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    api.get<Voice[]>("/voice/voices").then((v) => {
      setVoices(v);
      setSelected(v[0]?.id ?? "");
    });
  }, []);

  const currentVoice = useMemo(
    () => voices.find((v) => v.id === selected),
    [voices, selected],
  );

  async function play() {
    if (!selected || !text.trim()) return;
    setPlaying(true);
    try {
      const spec = await api.post<VoicePreviewResponse>("/voice/preview", {
        voice_id: selected,
        text,
      });
      speak(spec);
    } catch (e) {
      console.error(e);
      setPlaying(false);
    }
  }

  function speak(spec: VoicePreviewResponse) {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      alert("Web Speech API not available in this browser.");
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

  function stop() {
    window.speechSynthesis?.cancel();
    setPlaying(false);
  }

  return (
    <>
      <PageHeader
        title="Voice Lab"
        subtitle="Preview the AI's voice with any script. In production this calls Piper TTS with the DishHome-branded voice clone; the demo uses the browser's Web Speech API so you can hear it now."
      />
      <PageBody>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card title="Voice catalog" className="lg:col-span-1">
            <div className="space-y-2">
              {voices.map((v) => (
                <button
                  key={v.id}
                  onClick={() => setSelected(v.id)}
                  className={`w-full text-left rounded-lg p-3 border transition ${
                    selected === v.id
                      ? "border-dishhome-blue bg-dishhome-blue/5"
                      : "border-black/5 hover:border-dishhome-blue/30"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-dishhome-blue">
                      {v.name}
                    </span>
                    <span className="text-[10px] uppercase tracking-widest text-dishhome-ink/50">
                      {v.language === "ne" ? "Nepali" : "English"} · {v.gender}
                    </span>
                  </div>
                  <div className="text-xs text-dishhome-ink/60 mt-1">
                    {v.tone}
                  </div>
                </button>
              ))}
            </div>
          </Card>

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
              className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dishhome-blue/30"
              placeholder="Type a Nepali or English line for the AI to say…"
            />

            <div className="mt-4 flex items-center gap-3">
              {playing ? (
                <Button variant="danger" onClick={stop}>
                  ■ Stop
                </Button>
              ) : (
                <Button onClick={play} disabled={!text.trim()}>
                  ▶ Play sample
                </Button>
              )}
              <span className="text-xs text-dishhome-ink/50">
                Tip: Nepali voices fall back to the closest available system
                voice if Nepali isn't installed on your OS.
              </span>
            </div>
          </Card>
        </div>
      </PageBody>
    </>
  );
}
