import { useState, useRef, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import { Phone, PhoneOff, Mic, MicOff, Play, Pause, Headphones } from "lucide-react";
import { useAuth } from "../lib/auth";

// ── Types ──
interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  suggestions?: string[];
}

interface ChatResponse {
  session_id: string;
  reply: string;
  language: string;
  suggestions: string[];
  metadata: Record<string, string>;
}

// ── Markdown-lite renderer ──
function renderMarkdown(text: string): string {
  const escaped = text.replace(/[&<>"']/g, (char) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[char];
  });

  return escaped
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br/>');
}

// ── Khushi Avatar — DishHome branded ──
function KhushiAvatar({ size = 40 }: { size?: number }) {
  return (
    <div
      className="rounded-full flex items-center justify-center flex-shrink-0"
      style={{
        width: size,
        height: size,
        background: "linear-gradient(135deg, #003a70 0%, #005baa 100%)",
        boxShadow: "0 2px 8px rgba(0,58,112,0.3)",
      }}
    >
      {/* Khushi "K" monogram with headset */}
      <svg width={size * 0.6} height={size * 0.6} viewBox="0 0 28 28" fill="none">
        {/* Headset band */}
        <path d="M5 14C5 8.5 9 4.5 14 4.5C19 4.5 23 8.5 23 14" stroke="#f7941d" strokeWidth="2" strokeLinecap="round" fill="none"/>
        {/* Left ear */}
        <rect x="3" y="12" width="4" height="7" rx="2" fill="#f7941d"/>
        {/* Right ear */}
        <rect x="21" y="12" width="4" height="7" rx="2" fill="#f7941d"/>
        {/* Mic arm */}
        <path d="M5 19C5 21 7 23 10 23" stroke="#f7941d" strokeWidth="1.5" strokeLinecap="round" fill="none"/>
        <circle cx="10" cy="23" r="1.5" fill="#f7941d"/>
        {/* K letter */}
        <text x="14" y="18" textAnchor="middle" fill="white" fontSize="11" fontWeight="bold" fontFamily="Inter,sans-serif">K</text>
      </svg>
    </div>
  );
}

// ── Typing indicator ──
function TypingIndicator() {
  return (
    <div className="flex items-end gap-2.5 mb-3">
      <KhushiAvatar size={30} />
      <div
        className="rounded-2xl rounded-bl-md px-4 py-3"
        style={{
          background: "linear-gradient(135deg, #f0f4f8, #e8edf3)",
          border: "1px solid #e2e8f0",
        }}
      >
        <div className="flex gap-1.5 items-center h-4">
          <span className="w-2 h-2 rounded-full animate-bounce" style={{ background: "#f7941d", animationDelay: "0ms" }} />
          <span className="w-2 h-2 rounded-full animate-bounce" style={{ background: "#003a70", animationDelay: "150ms" }} />
          <span className="w-2 h-2 rounded-full animate-bounce" style={{ background: "#f7941d", animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  );
}

// ── Message Bubble ──
function MessageBubble({
  message,
  onSuggestionClick,
}: {
  message: ChatMessage;
  onSuggestionClick: (text: string) => void;
}) {
  const isUser = message.role === "user";

  return (
    <div className={`flex items-end gap-2.5 mb-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {!isUser && <KhushiAvatar size={30} />}
      <div className="max-w-[82%] flex flex-col gap-1.5">
        <div
          className={`rounded-2xl px-4 py-2.5 text-[13px] leading-relaxed ${
            isUser
              ? "rounded-br-md text-white"
              : "rounded-bl-md text-gray-800"
          }`}
          style={
            isUser
              ? { background: "linear-gradient(135deg, #003a70 0%, #005baa 100%)" }
              : {
                  background: "linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)",
                  border: "1px solid #e2e8f0",
                }
          }
          dangerouslySetInnerHTML={
            isUser ? undefined : { __html: renderMarkdown(message.content) }
          }
        >
          {isUser ? message.content : undefined}
        </div>

        {/* Suggestion chips — DishHome themed */}
        {!isUser && message.suggestions && message.suggestions.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1 pl-1">
            {message.suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => onSuggestionClick(s)}
                className="text-[11px] font-medium px-3 py-1.5 rounded-full
                  transition-all duration-200 active:scale-95"
                style={{
                  background: "linear-gradient(135deg, #fff7ed, #fff)",
                  border: "1.5px solid #f7941d",
                  color: "#c2700c",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "linear-gradient(135deg, #f7941d, #e8850d)";
                  e.currentTarget.style.color = "white";
                  e.currentTarget.style.borderColor = "#e8850d";
                  e.currentTarget.style.boxShadow = "0 2px 8px rgba(247,148,29,0.3)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "linear-gradient(135deg, #fff7ed, #fff)";
                  e.currentTarget.style.color = "#c2700c";
                  e.currentTarget.style.borderColor = "#f7941d";
                  e.currentTarget.style.boxShadow = "none";
                }}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <span className={`text-[10px] text-gray-400 ${isUser ? "text-right pr-1" : "pl-1"}`}>
          {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
    </div>
  );
}

// ── Main Widget ──
export default function KhushiChatbot() {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [hasGreeted, setHasGreeted] = useState(false);
  const [showBadge, setShowBadge] = useState(true);
  const [isMinimized, setIsMinimized] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // ── Let's Talk State ──
  const [showLetsTalk, setShowLetsTalk] = useState(false);
  const [letsTalkName, setLetsTalkName] = useState("");
  const [letsTalkPhone, setLetsTalkPhone] = useState("");
  const [letsTalkCustomerId, setLetsTalkCustomerId] = useState("");
  const [letsTalkIssue, setLetsTalkIssue] = useState("router_offline");
  const [letsTalkMode, setLetsTalkMode] = useState<"browser" | "callback">("browser");
  const [isCallActive, setIsCallActive] = useState(false);
  const [callStatus, setCallStatus] = useState<"connecting" | "ringing" | "connected" | "ended">("connecting");
  const [callId, setCallId] = useState<string | null>(null);
  const [isCallMuted, setIsCallMuted] = useState(false);
  const [isCallOnHold, setIsCallOnHold] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [activeSpeechUrl, setActiveSpeechUrl] = useState<string | null>(null);
  const [welcomeText, setWelcomeText] = useState("");

  const audioCtxRef = useRef<AudioContext | null>(null);
  const ringIntervalRef = useRef<number | null>(null);
  const durationIntervalRef = useRef<number | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  // Auto-prefill name if logged in
  useEffect(() => {
    if (user) {
      setLetsTalkName(user.name || user.username);
      // Suresh Shrestha's mock mobile for demo
      if (user.username === "admin" || user.username === "agent") {
        setLetsTalkPhone("9841234567");
        setLetsTalkCustomerId("DH100234");
      }
    }
  }, [user]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [isOpen]);

  // Send greeting on first open
  useEffect(() => {
    if (isOpen && !hasGreeted) {
      setHasGreeted(true);
      sendMessage("hi", true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const sendMessage = useCallback(
    async (text: string, isGreeting = false) => {
      const trimmed = text.trim();
      if (!trimmed) return;

      // Dynamic harvesting of Customer ID and Phone Number from user inputs
      const cidMatch = trimmed.match(/DH\d+/i);
      if (cidMatch) {
        setLetsTalkCustomerId(cidMatch[0].toUpperCase());
      }
      const phMatch = trimmed.match(/(98\d{8}|97\d{8})/);
      if (phMatch) {
        setLetsTalkPhone(phMatch[0]);
      }

      // Intercept "Let's Talk" messages to open the overlay form instantly
      if (trimmed.toLowerCase().includes("let's talk") || trimmed.toLowerCase().includes("lets talk")) {
        setShowLetsTalk(true);
        return;
      }

      if (!isGreeting) {
        const userMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "user",
          content: trimmed,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, userMsg]);
      }
      setInput("");
      setIsTyping(true);
      setShowBadge(false);

      try {
        const res = await api.post<ChatResponse>("/chat/message", {
          session_id: sessionId,
          message: trimmed,
          language: "auto",
        });
        setSessionId(res.session_id);

        const delay = Math.min(600 + res.reply.length * 4, 1800);
        await new Promise((r) => setTimeout(r, delay));

        const botMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.reply,
          timestamp: new Date(),
          suggestions: res.suggestions,
        };
        setMessages((prev) => [...prev, botMsg]);
      } catch {
        const errorMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content:
            "I'm having trouble connecting right now. Please try again or call us at **16600122000** for immediate assistance.",
          timestamp: new Date(),
          suggestions: ["Try Again", "Contact Support"],
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsTyping(false);
      }
    },
    [sessionId]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleSuggestionClick = (text: string) => {
    if (text.toLowerCase().includes("let's talk") || text.toLowerCase().includes("lets talk")) {
      setShowLetsTalk(true);
    } else {
      sendMessage(text);
    }
  };

  // ── Browser Audio & Synthesis helpers ──
  const getAudioContext = () => {
    if (!audioCtxRef.current) {
      // @ts-ignore
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      audioCtxRef.current = new AudioContextClass();
    }
    return audioCtxRef.current;
  };

  const startRingtone = () => {
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      
      let ringCount = 0;
      const playSingleRing = () => {
        if (ringCount >= 2) {
          if (ringIntervalRef.current) clearInterval(ringIntervalRef.current);
          setCallStatus("connected");
          playConnectChime();
          startActiveSpeech();
          return;
        }
        ringCount++;
        
        const osc1 = ctx.createOscillator();
        const osc2 = ctx.createOscillator();
        const gainNode = ctx.createGain();
        
        osc1.type = "sine";
        osc2.type = "sine";
        osc1.frequency.setValueAtTime(440, ctx.currentTime);
        osc2.frequency.setValueAtTime(480, ctx.currentTime);
        
        gainNode.gain.setValueAtTime(0, ctx.currentTime);
        gainNode.gain.linearRampToValueAtTime(0.06, ctx.currentTime + 0.1);
        gainNode.gain.setValueAtTime(0.06, ctx.currentTime + 1.8);
        gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + 1.9);
        
        osc1.connect(gainNode);
        osc2.connect(gainNode);
        gainNode.connect(ctx.destination);
        
        osc1.start();
        osc2.start();
        
        setTimeout(() => {
          try {
            osc1.stop();
            osc2.stop();
          } catch {}
        }, 2100);
      };
      
      playSingleRing();
      ringIntervalRef.current = window.setInterval(playSingleRing, 4000);
    } catch (e) {
      console.warn("Ringtone synthesis failed:", e);
    }
  };

  const playConnectChime = () => {
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(600, ctx.currentTime);
      osc.frequency.setValueAtTime(800, ctx.currentTime + 0.12);
      
      gain.gain.setValueAtTime(0.04, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.3);
    } catch {}
  };

  const playDisconnectChime = () => {
    try {
      const ctx = getAudioContext();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(800, ctx.currentTime);
      osc.frequency.setValueAtTime(500, ctx.currentTime + 0.15);
      
      gain.gain.setValueAtTime(0.04, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
      
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.35);
    } catch {}
  };

  const startActiveSpeech = () => {
    if (activeSpeechUrl && audioPlayerRef.current) {
      audioPlayerRef.current.src = activeSpeechUrl;
      audioPlayerRef.current.play().catch(err => {
        console.warn("Synthesis player blocked, falling back to Web Speech:", err);
        fallbackSpeechSynthesis();
      });
    } else {
      fallbackSpeechSynthesis();
    }
  };

  const fallbackSpeechSynthesis = () => {
    try {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(welcomeText || "नमस्ते! डिशहोमको लेट्स टक सेवामा स्वागत छ।");
        utterance.lang = "ne-NP";
        utterance.rate = 0.92;
        window.speechSynthesis.speak(utterance);
      }
    } catch (e) {
      console.warn("Speech synthesis failed:", e);
    }
  };

  const endCall = () => {
    setIsCallActive(false);
    setCallStatus("ended");
    playDisconnectChime();
    
    if (ringIntervalRef.current) clearInterval(ringIntervalRef.current);
    if (durationIntervalRef.current) clearInterval(durationIntervalRef.current);
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current.src = "";
    }
    try {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    } catch {}
    
    // Append the call summary turn in message log
    const summaryMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: `📞 **Let's Talk Session Logged!**\n\n` + 
               `• **Call ID:** \`${callId || "call_mocked"}\`\n` +
               `• **Subject:** \`${letsTalkIssue.replace("_", " ").toUpperCase()}\`\n` +
               `• **Contact:** ${letsTalkName} (${letsTalkPhone})\n` +
               `• **Duration:** ${callDuration}s (Browser Voice AI)\n` +
               `• **Resolution:** Ticket created and transferred to NOC Team.\n\n` +
               `Thank you for using DishHome Let's Talk!`,
      timestamp: new Date()
    };
    setMessages((prev) => [...prev, summaryMsg]);
    setShowLetsTalk(false);
  };

  const handleLetsTalkSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!letsTalkName.trim() || !letsTalkPhone.trim()) {
      alert("Please fill in your name and phone number.");
      return;
    }
    
    setIsCallActive(true);
    setCallStatus("connecting");
    setCallDuration(0);
    
    try {
      const res = await api.post<{
        status: string;
        call_id: string;
        message: string;
        mode: string;
        speech_text: string;
        audio_url: string | null;
      }>("/chat/lets-talk", {
        name: letsTalkName,
        phone: letsTalkPhone,
        issue: letsTalkIssue,
        customer_id: letsTalkCustomerId || null,
        mode: letsTalkMode
      });
      
      setCallId(res.call_id);
      setWelcomeText(res.speech_text);
      setActiveSpeechUrl(res.audio_url);
      
      if (letsTalkMode === "callback") {
        setCallStatus("connected");
        setTimeout(() => {
          setIsCallActive(false);
          setShowLetsTalk(false);
          const callbackMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: `📞 **Telephone Callback Scheduled!**\n\n` +
                     `We are dialing your phone at **${letsTalkPhone}** right now! ` +
                     `Our voice agent **Jessica** is calling to troubleshoot your **${letsTalkIssue.replace("_", " ").toUpperCase()}** issue.\n\n` +
                     `Please answer your phone! Call ID: \`${res.call_id}\`.`,
            timestamp: new Date()
          };
          setMessages((prev) => [...prev, callbackMsg]);
        }, 4000);
      } else {
        setCallStatus("ringing");
        startRingtone();
        
        durationIntervalRef.current = window.setInterval(() => {
          setCallDuration((prev) => prev + 1);
        }, 1000);
      }
    } catch (err) {
      console.error(err);
      setIsCallActive(false);
      alert("Failed to connect to Let's Talk server. Please try again.");
    }
  };

  const toggleChat = () => {
    if (isMinimized) {
      setIsMinimized(false);
      return;
    }
    setIsOpen(!isOpen);
  };

  // ── Floating Action Button ──
  if (!isOpen) {
    return (
      <>
        {/* Proactive bubble */}
        {showBadge && (
          <div
            className="fixed bottom-24 right-6 z-[9998] rounded-2xl rounded-br-md
              px-4 py-3 max-w-[280px] cursor-pointer"
            style={{
              background: "linear-gradient(135deg, #ffffff, #f8fafc)",
              border: "1px solid #e2e8f0",
              boxShadow: "0 8px 32px rgba(0,58,112,0.15), 0 2px 8px rgba(0,0,0,0.08)",
              animation: "fadeInUp 0.5s ease-out 2s both",
            }}
            onClick={toggleChat}
          >
            <div className="flex items-start gap-2.5">
              <KhushiAvatar size={32} />
              <div>
                <p className="text-[13px] text-gray-700 leading-snug">
                  नमस्ते! 👋 I'm <strong style={{ color: "#003a70" }}>Khushi</strong>,
                  your DishHome AI assistant.
                </p>
                <p className="text-[11px] mt-1 font-medium" style={{ color: "#f7941d" }}>
                  Ask me about packages, billing & more →
                </p>
              </div>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); setShowBadge(false); }}
              className="absolute -top-2 -right-2 w-5 h-5 rounded-full
                text-gray-500 text-xs flex items-center justify-center transition"
              style={{
                background: "#f1f5f9",
                border: "1px solid #e2e8f0",
              }}
            >
              ✕
            </button>
          </div>
        )}

        {/* FAB — DishHome blue with orange ring */}
        <button
          onClick={toggleChat}
          className="fixed bottom-6 right-6 z-[9999] w-[60px] h-[60px] rounded-full
            flex items-center justify-center
            hover:scale-110 active:scale-95 transition-all duration-300"
          style={{
            background: "linear-gradient(135deg, #003a70 0%, #005baa 100%)",
            boxShadow: "0 4px 20px rgba(0,58,112,0.4), 0 0 0 3px rgba(247,148,29,0.5)",
          }}
          aria-label="Open Khushi AI Chat"
        >
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" fill="white"/>
            <circle cx="8" cy="10" r="1.2" fill="#003a70"/>
            <circle cx="12" cy="10" r="1.2" fill="#f7941d"/>
            <circle cx="16" cy="10" r="1.2" fill="#003a70"/>
          </svg>
          {/* Pulse ring */}
          <span
            className="absolute inset-0 rounded-full animate-ping"
            style={{ background: "rgba(247,148,29,0.2)" }}
          />
        </button>
      </>
    );
  }

  // ── Chat Window ──
  return (
    <div
      className={`fixed bottom-6 right-6 z-[9999] flex flex-col
        rounded-2xl overflow-hidden transition-all duration-300 ${
          isMinimized
            ? "w-[360px] h-[56px]"
            : "w-[390px] h-[620px] max-h-[calc(100vh-48px)]"
        }`}
      style={{
        boxShadow: "0 12px 48px rgba(0,58,112,0.25), 0 4px 16px rgba(0,0,0,0.1)",
        border: "1px solid rgba(0,58,112,0.1)",
        animation: "slideUp 0.3s ease-out",
      }}
    >
      {/* ── Header — DishHome gradient with orange accent bar ── */}
      <div
        className="flex-shrink-0 cursor-pointer"
        onClick={() => setIsMinimized(!isMinimized)}
      >
        {/* Orange accent bar */}
        <div style={{ height: 3, background: "linear-gradient(90deg, #f7941d, #ffb347, #f7941d)" }} />

        <div
          className="flex items-center gap-3 px-4 py-3"
          style={{
            background: "linear-gradient(135deg, #003a70 0%, #004d99 50%, #003060 100%)",
          }}
        >
          <div className="relative">
            <KhushiAvatar size={38} />
            <span
              className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full"
              style={{
                background: "#22c55e",
                border: "2px solid #003a70",
                boxShadow: "0 0 6px rgba(34,197,94,0.5)",
              }}
            />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-white font-semibold text-sm leading-tight flex items-center gap-1.5">
              Khushi
              <span className="text-[10px] font-normal px-1.5 py-0.5 rounded-full"
                style={{ background: "rgba(247,148,29,0.25)", color: "#ffb347" }}>
                AI
              </span>
            </h3>
            <p className="text-white/60 text-[11px] flex items-center gap-1">
              DishHome Support • Always online
            </p>
          </div>
          <div className="flex items-center gap-1">
            {/* Let's Talk Header Action Button */}
            {!isCallActive && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowLetsTalk(!showLetsTalk);
                }}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-full text-[10px] font-bold
                  text-white transition-all active:scale-95 duration-200 border mr-1 relative overflow-hidden"
                style={{
                  background: showLetsTalk
                    ? "rgba(255, 255, 255, 0.15)"
                    : "linear-gradient(135deg, #f7941d, #e8850d)",
                  borderColor: showLetsTalk ? "rgba(255,255,255,0.3)" : "#ffb347",
                  boxShadow: showLetsTalk ? "none" : "0 0 8px rgba(247,148,29,0.5)"
                }}
              >
                <Phone size={10} className={showLetsTalk ? "" : "animate-bounce"} />
                Let's Talk
                {!showLetsTalk && (
                  <span className="absolute top-0 right-0 w-1.5 h-1.5 bg-green-400 rounded-full animate-ping" />
                )}
              </button>
            )}

            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsMinimized(!isMinimized);
              }}
              className="w-7 h-7 flex items-center justify-center rounded-full
                text-white/50 hover:text-white hover:bg-white/10 transition text-sm"
            >
              {isMinimized ? "▲" : "▼"}
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsOpen(false);
              }}
              className="w-7 h-7 flex items-center justify-center rounded-full
                text-white/50 hover:text-white hover:bg-white/10 transition text-sm"
            >
              ✕
            </button>
          </div>
        </div>
      </div>

      {!isMinimized && (
        <>
          {showLetsTalk ? (
            isCallActive ? (
              // ── Active Voice Call Interface ──
              <div 
                className="flex-1 flex flex-col items-center justify-between p-6 relative overflow-hidden"
                style={{
                  background: "radial-gradient(circle, #003a70 0%, #001224 100%)",
                }}
              >
                {/* Decorative glowing lines */}
                <div className="absolute inset-0 opacity-10 pointer-events-none">
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full border border-white animate-ping" style={{ animationDuration: '3.5s' }} />
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-72 h-72 rounded-full border border-white animate-ping" style={{ animationDuration: '5s' }} />
                </div>

                {/* Status Bar */}
                <div className="text-center mt-2 z-10">
                  <span className="text-[9px] uppercase tracking-wider font-extrabold text-orange-400 bg-orange-400/10 px-3 py-1 rounded-full border border-orange-400/20">
                    Voice AI Assistant
                  </span>
                  <h4 className="text-white text-base font-bold mt-2">
                    Jessica (Khushi Voice)
                  </h4>
                  <div className="text-white/60 text-[10px] mt-1 font-semibold flex items-center justify-center gap-1.5">
                    {callStatus === "connecting" && "Initiating connection..."}
                    {callStatus === "ringing" && (
                      <>
                        <span className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-ping" />
                        Ringing Line...
                      </>
                    )}
                    {callStatus === "connected" && (
                      <>
                        <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                        Live Call • {Math.floor(callDuration / 60).toString().padStart(2, '0')}:{(callDuration % 60).toString().padStart(2, '0')}
                      </>
                    )}
                  </div>
                </div>

                {/* Avatar Frame */}
                <div className="relative my-4 flex items-center justify-center z-10">
                  <div className={`absolute w-28 h-28 rounded-full bg-orange-500/15 blur-xl transition-all duration-1000 ${callStatus === 'connected' ? 'scale-125' : 'scale-90'}`} />
                  
                  <div 
                    className={`w-24 h-24 rounded-full flex items-center justify-center border-4 transition-all duration-300 ${
                      callStatus === 'connected' ? 'border-green-400 animate-pulse' : 'border-orange-400'
                    }`}
                    style={{
                      background: "linear-gradient(135deg, #003a70 0%, #005baa 100%)",
                      boxShadow: "0 6px 20px rgba(0,58,112,0.4)"
                    }}
                  >
                    <Headphones size={36} className="text-white animate-pulse" />
                  </div>
                  
                  {callStatus === 'connected' && (
                    <div className="absolute inset-0 rounded-full border-2 border-green-400/40 animate-ping" style={{ animationDuration: '2.5s' }} />
                  )}
                </div>

                {/* CSS Audio Waveform Visualizer */}
                {callStatus === "connected" && !isCallOnHold && (
                  <div className="flex items-end justify-center gap-1 h-7 my-1.5 z-10">
                    {[1, 2, 3, 4, 5, 4, 3, 2, 1].map((val, i) => (
                      <span
                        key={i}
                        className="w-1 bg-green-400 rounded-full"
                        style={{
                          height: `${20 + val * 16}%`,
                          animation: `voiceBar 0.8s ease-in-out infinite alternate`,
                          animationDelay: `${i * 90}ms`,
                        }}
                      />
                    ))}
                  </div>
                )}

                {/* Interactive Subtitles Box */}
                <div className="w-full bg-black/40 border border-white/5 rounded-xl p-3 min-h-[90px] max-h-[105px] overflow-y-auto mb-3.5 z-10">
                  <p className="text-[9px] font-bold text-white/30 uppercase tracking-wider">Subtitles Transcript</p>
                  <p className="text-white/90 text-xs leading-relaxed mt-1 font-medium italic">
                    {callStatus === "connecting" && "... Contacting NOC database, allocating voice port ..."}
                    {callStatus === "ringing" && "... Dialtone active, waiting for response ..."}
                    {callStatus === "connected" && (
                      <>
                        <strong className="text-orange-400 not-italic">Jessica: </strong> 
                        "{welcomeText || "नमस्ते! डिशहोमको lets talk सेवामा स्वागत छ।"}"
                      </>
                    )}
                  </p>
                </div>

                {/* Call Action Panel */}
                <div className="w-full flex items-center justify-around mb-2.5 z-10 px-4">
                  <button
                    onClick={() => setIsCallMuted(!isCallMuted)}
                    className={`w-10 h-10 rounded-full flex items-center justify-center border transition-all ${
                      isCallMuted 
                        ? 'bg-red-500/20 border-red-500 text-red-400' 
                        : 'bg-white/5 border-white/10 text-white hover:bg-white/10'
                    }`}
                  >
                    {isCallMuted ? <MicOff size={16} /> : <Mic size={16} />}
                  </button>

                  <button
                    onClick={() => endCall()}
                    className="w-14 h-14 rounded-full bg-red-600 hover:bg-red-700 text-white flex items-center justify-center shadow-lg hover:scale-105 active:scale-95 transition-all"
                  >
                    <PhoneOff size={20} />
                  </button>

                  <button
                    onClick={() => setIsCallOnHold(!isCallOnHold)}
                    className={`w-10 h-10 rounded-full flex items-center justify-center border transition-all ${
                      isCallOnHold 
                        ? 'bg-orange-500/20 border-orange-500 text-orange-400' 
                        : 'bg-white/5 border-white/10 text-white hover:bg-white/10'
                    }`}
                  >
                    {isCallOnHold ? <Play size={16} /> : <Pause size={16} />}
                  </button>
                </div>

                <audio ref={audioPlayerRef} className="hidden" />
              </div>
            ) : (
              // ── Premium Let's Talk Request Form ──
              <div 
                className="flex-1 overflow-y-auto px-4.5 py-4.5 flex flex-col justify-between"
                style={{
                  background: "linear-gradient(180deg, #ffffff 0%, #f8fafc 100%)",
                }}
              >
                <div className="space-y-3.5">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-9 h-9 rounded-full flex items-center justify-center border"
                      style={{
                        background: "linear-gradient(135deg, #fff7ed, #fff)",
                        borderColor: "#f7941d"
                      }}
                    >
                      <Headphones className="text-orange-600" size={18} />
                    </div>
                    <div>
                      <h4 className="text-xs font-extrabold text-slate-800 tracking-tight">
                        Let's Talk — Escalation Form
                      </h4>
                      <p className="text-[10px] text-gray-500 leading-normal">
                        Bypasses all routing lines. Talk instantly or get callback.
                      </p>
                    </div>
                  </div>

                  <form onSubmit={handleLetsTalkSubmit} className="space-y-3">
                    <div>
                      <label className="block text-[10px] font-bold text-gray-500 uppercase mb-0.5">
                        Full Name
                      </label>
                      <input
                        type="text"
                        required
                        value={letsTalkName}
                        onChange={(e) => setLetsTalkName(e.target.value)}
                        placeholder="e.g. Suresh Shrestha"
                        className="w-full text-xs px-3 py-2 rounded-lg border border-gray-200 bg-slate-50 outline-none focus:border-orange-400 focus:bg-white transition-colors"
                      />
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold text-gray-500 uppercase mb-0.5">
                        Phone Number
                      </label>
                      <input
                        type="tel"
                        required
                        pattern="(98\d{8}|97\d{8})"
                        title="Nepali mobile must start with 98 or 97 and be 10 digits"
                        value={letsTalkPhone}
                        onChange={(e) => setLetsTalkPhone(e.target.value)}
                        placeholder="9841XXXXXX"
                        className="w-full text-xs px-3 py-2 rounded-lg border border-gray-200 bg-slate-50 outline-none focus:border-orange-400 focus:bg-white transition-colors"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="block text-[10px] font-bold text-gray-500 uppercase mb-0.5">
                          Customer ID
                        </label>
                        <input
                          type="text"
                          value={letsTalkCustomerId}
                          onChange={(e) => setLetsTalkCustomerId(e.target.value)}
                          placeholder="DH100234"
                          className="w-full text-xs px-3 py-2 rounded-lg border border-gray-200 bg-slate-50 outline-none focus:border-orange-400 focus:bg-white transition-colors"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-gray-500 uppercase mb-0.5">
                          Issue Topic
                        </label>
                        <select
                          value={letsTalkIssue}
                          onChange={(e) => setLetsTalkIssue(e.target.value)}
                          className="w-full text-xs px-2 py-2 rounded-lg border border-gray-200 bg-slate-50 outline-none focus:border-orange-400 focus:bg-white transition-colors"
                        >
                          <option value="router_offline">Router Offline</option>
                          <option value="slow_internet">Slow Internet</option>
                          <option value="wifi_only_issue">Wi-Fi Range</option>
                          <option value="billing_inquiry">Billing Dispute</option>
                          <option value="package_upgrade">Upgrade Plan</option>
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-[10px] font-bold text-gray-500 uppercase mb-1">
                        Escalation Mode
                      </label>
                      <div className="grid grid-cols-2 gap-2.5">
                        <div
                          onClick={() => setLetsTalkMode("browser")}
                          className={`border rounded-lg p-2.5 cursor-pointer transition-all flex flex-col items-center justify-center text-center ${
                            letsTalkMode === "browser"
                              ? "border-orange-400 bg-orange-500/5 ring-1 ring-orange-400"
                              : "border-gray-200 bg-slate-50 hover:bg-slate-100"
                          }`}
                        >
                          <span className="text-sm">🌐</span>
                          <span className="text-[10px] font-bold text-slate-800 mt-0.5">Browser Audio</span>
                          <span className="text-[8px] text-gray-400">Microphone in-browser</span>
                        </div>

                        <div
                          onClick={() => setLetsTalkMode("callback")}
                          className={`border rounded-lg p-2.5 cursor-pointer transition-all flex flex-col items-center justify-center text-center ${
                            letsTalkMode === "callback"
                              ? "border-orange-400 bg-orange-500/5 ring-1 ring-orange-400"
                              : "border-gray-200 bg-slate-50 hover:bg-slate-100"
                          }`}
                        >
                          <span className="text-sm">📞</span>
                          <span className="text-[10px] font-bold text-slate-800 mt-0.5">Phone Call</span>
                          <span className="text-[8px] text-gray-400">Instant outbound call</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex gap-2 pt-2.5">
                      <button
                        type="button"
                        onClick={() => setShowLetsTalk(false)}
                        className="flex-1 py-2 rounded-lg border border-gray-200 text-xs font-semibold text-gray-500 bg-white hover:bg-gray-50 active:scale-95 transition-all"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="flex-1 py-2 rounded-lg text-xs font-bold text-white active:scale-95 transition-all shadow-sm"
                        style={{
                          background: "linear-gradient(135deg, #f7941d 0%, #e8850d 100%)",
                        }}
                      >
                        Let's Talk
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )
          ) : (
            // ── Messages, Input Form, and Support Footer ──
            <>
              <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto px-4 py-4"
                style={{
                  background: "linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)",
                }}
              >
                {/* Welcome card */}
            {messages.length === 0 && !isTyping && (
              <div className="text-center py-6">
                <div className="flex justify-center">
                  <KhushiAvatar size={56} />
                </div>
                <h4 className="mt-3 text-base font-bold" style={{ color: "#003a70" }}>
                  Meet Khushi 🙏
                </h4>
                <p className="mt-1.5 text-xs text-gray-500 max-w-[220px] mx-auto leading-relaxed">
                  Your 24/7 AI assistant for DishHome<br/>
                  internet, TV, billing & support
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {[
                    { emoji: "📦", label: "Packages" },
                    { emoji: "💳", label: "Billing" },
                    { emoji: "🔧", label: "Troubleshoot" },
                    { emoji: "📞", label: "Contact Support" },
                  ].map(({ emoji, label }) => (
                    <button
                      key={label}
                      onClick={() => handleSuggestionClick(label)}
                      className="text-[11px] font-medium px-3 py-1.5 rounded-full
                        transition-all duration-200 active:scale-95"
                      style={{
                        background: "linear-gradient(135deg, #fff7ed, #fff)",
                        border: "1.5px solid #f7941d",
                        color: "#c2700c",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = "linear-gradient(135deg, #f7941d, #e8850d)";
                        e.currentTarget.style.color = "white";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "linear-gradient(135deg, #fff7ed, #fff)";
                        e.currentTarget.style.color = "#c2700c";
                      }}
                    >
                      {emoji} {label}
                    </button>
                  ))}
                </div>

                {/* Let's Talk CTA Banner on welcome screen */}
                <div className="mt-4 w-full px-2">
                  <button
                    onClick={() => setShowLetsTalk(true)}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-extrabold text-xs text-white transition-all duration-300 hover:scale-105 active:scale-95 border"
                    style={{
                      background: "linear-gradient(135deg, #003a70 0%, #005baa 100%)",
                      borderColor: "#f7941d",
                      boxShadow: "0 4px 14px rgba(0,58,112,0.3)"
                    }}
                  >
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-green-400"></span>
                    </span>
                    📞 Let's Talk — Voice AI Callback
                  </button>
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                onSuggestionClick={handleSuggestionClick}
              />
            ))}

            {isTyping && <TypingIndicator />}
          </div>

          {/* ── Input ── */}
          <form
            onSubmit={handleSubmit}
            className="px-3 py-3 flex items-center gap-2 flex-shrink-0"
            style={{
              background: "white",
              borderTop: "1px solid #e2e8f0",
            }}
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Message Khushi..."
              className="flex-1 text-sm px-4 py-2.5 rounded-full outline-none
                transition-all placeholder:text-gray-400"
              style={{
                background: "#f1f5f9",
                border: "1.5px solid #e2e8f0",
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = "#f7941d";
                e.currentTarget.style.background = "white";
                e.currentTarget.style.boxShadow = "0 0 0 3px rgba(247,148,29,0.1)";
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = "#e2e8f0";
                e.currentTarget.style.background = "#f1f5f9";
                e.currentTarget.style.boxShadow = "none";
              }}
              disabled={isTyping}
              maxLength={500}
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="w-10 h-10 rounded-full flex items-center justify-center
                disabled:opacity-30 disabled:cursor-not-allowed
                hover:scale-105 active:scale-95 transition-all duration-200"
              style={{
                background: input.trim()
                  ? "linear-gradient(135deg, #f7941d, #e8850d)"
                  : "#e2e8f0",
                boxShadow: input.trim() ? "0 2px 8px rgba(247,148,29,0.3)" : "none",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </form>

          {/* ── Footer — DishHome branded ── */}
          <div
            className="px-4 py-1.5 text-center flex-shrink-0 flex items-center justify-center gap-2"
            style={{
              background: "linear-gradient(135deg, #003a70, #004d99)",
            }}
          >
            <span className="text-[10px] text-white/60">
              Powered by
            </span>
            <span className="text-[10px] font-semibold" style={{ color: "#f7941d" }}>
              DishHome AI
            </span>
            <span className="text-[10px] text-white/40">•</span>
            <span className="text-[10px] text-white/60">
              16600122000
            </span>
          </div>
        </>
      )}

      {showLetsTalk && !isMinimized && (
        <div 
          className="px-4 py-1.5 text-center flex-shrink-0 flex items-center justify-center gap-1.5"
          style={{
            background: "linear-gradient(135deg, #0f172a, #1e293b)",
          }}
        >
          <span className="text-[9px] text-white/50">
            Secure VoIP Link
          </span>
          <span className="text-[9px] font-bold text-orange-400">
            DishHome Voice Core
          </span>
        </div>
      )}
    </>
  )}

      <style>{`
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px) scale(0.95); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes voiceBar {
          from { height: 20%; }
          to { height: 100%; }
        }
      `}</style>
    </div>
  );
}
