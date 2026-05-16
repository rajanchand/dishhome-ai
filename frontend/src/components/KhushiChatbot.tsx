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
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br/>');
}

// ── Khushi Avatar ──
function KhushiAvatar({ size = 40 }: { size?: number }) {
  return (
    <div
      className="rounded-full flex items-center justify-center flex-shrink-0 shadow-lg"
      style={{
        width: size,
        height: size,
        background: "linear-gradient(135deg, #003a70, #0066cc)",
      }}
    >
      <svg width={size * 0.55} height={size * 0.55} viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="8" r="4" fill="#f7941d" />
        <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" fill="white" opacity="0.9" />
        <circle cx="10" cy="7.5" r="0.7" fill="#003a70" />
        <circle cx="14" cy="7.5" r="0.7" fill="#003a70" />
        <path d="M10.5 9.5c0.8 0.8 2.2 0.8 3 0" stroke="#003a70" strokeWidth="0.6" fill="none" strokeLinecap="round" />
      </svg>
    </div>
  );
}

// ── Typing indicator ──
function TypingIndicator() {
  return (
    <div className="flex items-end gap-2 mb-3">
      <KhushiAvatar size={28} />
      <div className="bg-white rounded-2xl rounded-bl-md px-4 py-2.5 shadow-sm border border-gray-100">
        <div className="flex gap-1.5 items-center h-5">
          <span className="w-2 h-2 bg-dishhome-blue/40 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
          <span className="w-2 h-2 bg-dishhome-blue/40 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
          <span className="w-2 h-2 bg-dishhome-blue/40 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
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
    <div className={`flex items-end gap-2 mb-3 ${isUser ? "flex-row-reverse" : ""}`}>
      {!isUser && <KhushiAvatar size={28} />}
      <div className="max-w-[80%] flex flex-col gap-1.5">
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
            isUser
              ? "bg-dishhome-blue text-white rounded-br-md"
              : "bg-white text-gray-800 rounded-bl-md border border-gray-100"
          }`}
          dangerouslySetInnerHTML={
            isUser ? undefined : { __html: renderMarkdown(message.content) }
          }
        >
          {isUser ? message.content : undefined}
        </div>

        {/* Suggestion chips */}
        {!isUser && message.suggestions && message.suggestions.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1 pl-1">
            {message.suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => onSuggestionClick(s)}
                className="text-xs px-3 py-1.5 rounded-full border border-dishhome-blue/20 text-dishhome-blue
                  hover:bg-dishhome-blue hover:text-white transition-all duration-200
                  hover:shadow-md active:scale-95"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <span className={`text-[10px] text-gray-400 ${isUser ? "text-right" : ""}`}>
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

      // Add user message (skip for auto-greeting)
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

        // Simulate typing delay for natural feel
        const delay = Math.min(800 + res.reply.length * 5, 2000);
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
            className="fixed bottom-24 right-6 z-[9998] bg-white rounded-2xl rounded-br-md
              shadow-xl border border-gray-100 px-4 py-3 max-w-[260px]
              animate-fade-in-up cursor-pointer hover:shadow-2xl transition-shadow"
            onClick={toggleChat}
          >
            <p className="text-sm text-gray-700 leading-snug">
              नमस्ते! 👋 I'm <strong className="text-dishhome-blue">Khushi</strong>,
              your DishHome AI assistant. Need help?
            </p>
            <button
              onClick={(e) => { e.stopPropagation(); setShowBadge(false); }}
              className="absolute -top-2 -right-2 w-5 h-5 bg-gray-200 rounded-full
                text-gray-500 text-xs flex items-center justify-center hover:bg-gray-300 transition"
            >
              ✕
            </button>
          </div>
        )}

        {/* FAB */}
        <button
          onClick={toggleChat}
          className="fixed bottom-6 right-6 z-[9999] w-16 h-16 rounded-full
            shadow-2xl flex items-center justify-center
            hover:scale-110 active:scale-95 transition-all duration-300 group"
          style={{
            background: "linear-gradient(135deg, #003a70 0%, #0055a5 50%, #f7941d 100%)",
          }}
          aria-label="Open Khushi AI Chat"
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z" />
            <circle cx="8" cy="10" r="1.2" />
            <circle cx="12" cy="10" r="1.2" />
            <circle cx="16" cy="10" r="1.2" />
          </svg>

          {/* Pulse ring */}
          <span className="absolute inset-0 rounded-full animate-ping opacity-20 bg-dishhome-orange" />
        </button>
      </>
    );
  }

  // ── Chat Window ──
  return (
    <div
      className={`fixed bottom-6 right-6 z-[9999] flex flex-col
        bg-white rounded-2xl shadow-2xl border border-gray-200
        transition-all duration-300 overflow-hidden ${
          isMinimized
            ? "w-[340px] h-16"
            : "w-[380px] h-[600px] max-h-[calc(100vh-48px)]"
        }`}
      style={{
        animation: "slideUp 0.3s ease-out",
      }}
    >
      {/* ── Header ── */}
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer flex-shrink-0"
        style={{
          background: "linear-gradient(135deg, #003a70 0%, #004d99 100%)",
        }}
        onClick={() => setIsMinimized(!isMinimized)}
      >
        <div className="relative">
          <KhushiAvatar size={36} />
          <span
            className="absolute bottom-0 right-0 w-3 h-3 bg-green-400 rounded-full
              border-2 border-white"
          />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-semibold text-sm leading-tight">
            Khushi — DishHome AI
          </h3>
          <p className="text-white/70 text-xs flex items-center gap-1">
            <span className="w-1.5 h-1.5 bg-green-400 rounded-full inline-block" />
            Online • Replies instantly
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsMinimized(!isMinimized);
            }}
            className="w-7 h-7 flex items-center justify-center rounded-full
              text-white/60 hover:text-white hover:bg-white/10 transition"
          >
            {isMinimized ? "▲" : "▼"}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsOpen(false);
            }}
            className="w-7 h-7 flex items-center justify-center rounded-full
              text-white/60 hover:text-white hover:bg-white/10 transition"
          >
            ✕
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          {/* ── Messages ── */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto px-4 py-4"
            style={{
              background: "linear-gradient(180deg, #f8fafc 0%, #f0f4f8 100%)",
            }}
          >
            {/* Welcome card */}
            {messages.length === 0 && !isTyping && (
              <div className="text-center py-8">
                <KhushiAvatar size={64} />
                <h4 className="mt-4 text-lg font-semibold text-dishhome-blue">
                  Meet Khushi 🙏
                </h4>
                <p className="mt-2 text-sm text-gray-500 max-w-[240px] mx-auto">
                  Your 24/7 AI assistant for DishHome internet, TV, billing & support
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {["📦 Packages", "💳 Billing", "🔧 Troubleshoot", "📞 Contact"].map(
                    (s) => (
                      <button
                        key={s}
                        onClick={() => sendMessage(s.split(" ").slice(1).join(" "))}
                        className="text-xs px-3 py-1.5 rounded-full border border-dishhome-blue/20
                          text-dishhome-blue hover:bg-dishhome-blue hover:text-white
                          transition-all duration-200"
                      >
                        {s}
                      </button>
                    )
                  )}
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
            className="px-3 py-3 border-t border-gray-100 bg-white flex items-center gap-2 flex-shrink-0"
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 text-sm px-4 py-2.5 bg-gray-50 border border-gray-200
                rounded-full outline-none focus:border-dishhome-blue focus:bg-white
                focus:ring-2 focus:ring-dishhome-blue/10 transition-all
                placeholder:text-gray-400"
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
                  ? "linear-gradient(135deg, #003a70, #f7941d)"
                  : "#e5e7eb",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </form>

          {/* ── Footer ── */}
          <div className="px-4 py-1.5 text-center border-t border-gray-50 bg-gray-50/50 flex-shrink-0">
            <span className="text-[10px] text-gray-400">
              Powered by <strong className="text-dishhome-blue">DishHome AI</strong> •
              Toll-Free 16600122000
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
        .animate-fade-in-up { animation: fadeInUp 0.5s ease-out 2s both; }
      `}</style>
    </div>
  );
}
