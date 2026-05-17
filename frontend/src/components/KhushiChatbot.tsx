import { useState, useRef, useEffect, useCallback } from "react";
import { api } from "../lib/api";

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
    sendMessage(text);
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
          <div className="flex items-center gap-0.5">
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
          {/* ── Messages ── */}
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
                      onClick={() => sendMessage(label)}
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

      <style>{`
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px) scale(0.95); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
