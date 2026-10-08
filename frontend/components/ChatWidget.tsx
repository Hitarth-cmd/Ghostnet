"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { postChat, type ChatResponse, type UserLocation } from "@/lib/chatApi";
import ReactMarkdown from "react-markdown";

/* ── Session ID (stable per browser tab) ─────────────────────────────────── */
function useSessionId() {
  const [sid] = useState(
    () => `vessel-${Math.random().toString(36).slice(2, 10)}`
  );
  return sid;
}

/* ── Suggestion chips ────────────────────────────────────────────────────── */
const SUGGESTIONS = [
  "Leaving Mundra tomorrow heading west 40 km — any debris?",
  "Ghost nets near Okha heading south 25 nautical miles today",
  "Marine debris 30 km southwest of Kandla this weekend",
];

/* ── Types ───────────────────────────────────────────────────────────────── */
type MessageRole = "user" | "assistant" | "error";

interface Message {
  id: string;
  role: MessageRole;
  text: string;
  response?: ChatResponse;
}

/* ── Props ───────────────────────────────────────────────────────────────── */
interface ChatWidgetProps {
  onRouteDrawn?: (geojson: GeoJSON.FeatureCollection | null) => void;
}

/* ─────────────────────────────────────────────────────────────────────────── */

export default function ChatWidget({ onRouteDrawn }: ChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      text:
        "👋 I'm the **OceanGuard Debris Assistant**.\n\n" +
        "Tell me your planned route and I'll show you how much marine debris " +
        "and ghost nets lie along the way — using real detection data.\n\n" +
        "Try one of the examples below ↓",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [userLocation, setUserLocation] = useState<UserLocation | null>(null);

  const sessionId = useSessionId();
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  /* ── Scroll to bottom on new messages ─────────────────────────────────── */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isOpen]);

  /* ── Try to get GPS position ──────────────────────────────────────────── */
  useEffect(() => {
    if (typeof navigator !== "undefined" && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) =>
          setUserLocation({
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
          }),
        () => {} // silently fail
      );
    }
  }, []);

  /* ── Auto-focus input on open ─────────────────────────────────────────── */
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading) return;

      const userMsg: Message = {
        id: Date.now().toString(),
        role: "user",
        text: trimmed,
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsLoading(true);

      try {
        const resp = await postChat({
          message: trimmed,
          session_id: sessionId,
          user_location: userLocation,
        });

        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          text: resp.reply,
          response: resp,
        };
        setMessages((prev) => [...prev, assistantMsg]);

        // Push GeoJSON overlay to the map
        if (resp.geojson && onRouteDrawn) {
          onRouteDrawn(resp.geojson);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        setMessages((prev) => [
          ...prev,
          { id: Date.now().toString(), role: "error", text: `⚠️ ${msg}` },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading, sessionId, userLocation, onRouteDrawn]
  );

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  /* ── "Understood as" card ─────────────────────────────────────────────── */
  function ParsedCard({ resp }: { resp: ChatResponse }) {
    const q = resp.parsed_query;
    if (q.intent === "off_topic" || q.needs_clarification) return null;
    const parts: string[] = [];
    if (q.origin_name) parts.push(`📍 ${q.origin_name}`);
    if (q.bearing_label) parts.push(`🧭 ${q.bearing_label}`);
    if (q.distance_km) parts.push(`📏 ${q.distance_km.toFixed(0)} km`);
    if (q.date_label || q.date)
      parts.push(`📅 ${q.date_label || q.date}`);
    if (!parts.length) return null;
    return (
      <div className="mt-2 rounded-lg border border-sky-500/20 bg-sky-950/40 px-3 py-2 text-[10px] text-sky-300">
        <div className="mb-1 font-bold uppercase tracking-wider text-sky-400/70">
          Understood as
        </div>
        <div className="flex flex-wrap gap-2">
          {parts.map((p) => (
            <span
              key={p}
              className="rounded bg-sky-900/60 px-1.5 py-0.5 text-sky-200"
            >
              {p}
            </span>
          ))}
        </div>
        {resp.summary && (
          <div className="mt-1.5 font-semibold text-sky-300">
            {resp.summary.total_debris} detection(s) found · {resp.summary.ghost_nets} ghost net(s)
          </div>
        )}
      </div>
    );
  }

  /* ── Render ─────────────────────────────────────────────────────────────── */
  return (
    <>
      {/* Floating toggle button */}
      <button
        id="chat-widget-toggle"
        onClick={() => setIsOpen((v) => !v)}
        className={`
          fixed bottom-6 right-[430px] z-40 flex h-14 w-14 items-center justify-center
          rounded-full shadow-2xl ring-2 transition-all duration-300
          ${isOpen
            ? "bg-slate-800 ring-slate-600 hover:bg-slate-700"
            : "bg-gradient-to-br from-sky-500 to-teal-400 ring-sky-400/60 hover:scale-110"
          }
        `}
        title={isOpen ? "Close debris assistant" : "Open debris assistant"}
        aria-label="Toggle chat widget"
      >
        {isOpen ? (
          <svg className="h-6 w-6 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="h-7 w-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
        )}
        {/* Unread dot */}
        {!isOpen && (
          <span className="absolute -right-0.5 -top-0.5 flex h-3.5 w-3.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-teal-400 opacity-75" />
            <span className="relative inline-flex h-3.5 w-3.5 rounded-full bg-teal-500" />
          </span>
        )}
      </button>

      {/* Chat panel */}
      {isOpen && (
        <div
          id="chat-widget-panel"
          className="
            fixed bottom-24 right-[430px] z-40 flex h-[540px] w-[380px]
            flex-col overflow-hidden rounded-2xl border border-slate-700/80
            bg-slate-950/98 shadow-2xl backdrop-blur-xl
          "
          style={{ boxShadow: "0 0 60px rgba(14,165,233,0.15), 0 25px 60px rgba(0,0,0,0.6)" }}
        >
          {/* Header */}
          <div className="flex items-center gap-3 border-b border-slate-800 bg-gradient-to-r from-sky-950/80 to-teal-950/50 px-4 py-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-sky-500 to-teal-400">
              <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <div>
              <div className="text-sm font-bold text-slate-100">Debris Route Assistant</div>
              <div className="text-[10px] text-slate-400">
                {userLocation ? "📡 GPS location available" : "Route query · Real detection data"}
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="ml-auto text-slate-500 transition hover:text-slate-300"
              aria-label="Close chat"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 scrollbar-thin scrollbar-thumb-slate-700">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`
                    max-w-[90%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed
                    ${msg.role === "user"
                      ? "rounded-br-sm bg-sky-600 text-white"
                      : msg.role === "error"
                      ? "rounded-bl-sm border border-red-500/40 bg-red-950/60 text-red-300"
                      : "rounded-bl-sm border border-slate-700/60 bg-slate-800/80 text-slate-200"
                    }
                  `}
                >
                  <div className="prose prose-invert prose-sm max-w-none prose-p:my-0.5 prose-ul:my-0.5 prose-li:my-0">
                    <ReactMarkdown>{msg.text}</ReactMarkdown>
                  </div>
                  {msg.response && <ParsedCard resp={msg.response} />}
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-bl-sm border border-slate-700/60 bg-slate-800/80 px-4 py-3">
                  <div className="flex gap-1.5 items-center">
                    <span className="text-[11px] text-slate-400 mr-1">Querying debris data</span>
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className="inline-block h-1.5 w-1.5 rounded-full bg-sky-400"
                        style={{
                          animation: `bounce 1.2s ${i * 0.2}s infinite`,
                        }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Suggestion chips (only when no user messages yet) */}
            {messages.length === 1 && (
              <div className="space-y-1.5 pt-1">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => sendMessage(s)}
                    className="
                      w-full rounded-xl border border-sky-600/30 bg-sky-950/40 px-3 py-2
                      text-left text-[11px] text-sky-300 transition
                      hover:border-sky-500/60 hover:bg-sky-900/40
                    "
                  >
                    💬 {s}
                  </button>
                ))}
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input area */}
          <div className="border-t border-slate-800 bg-slate-900/60 px-3 py-2.5">
            <div className="flex items-end gap-2 rounded-xl border border-slate-700 bg-slate-800/80 px-3 py-2 focus-within:border-sky-500/60 focus-within:ring-1 focus-within:ring-sky-500/30 transition">
              <textarea
                ref={inputRef}
                id="chat-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Describe your route… e.g. 'Leaving Mundra tomorrow, heading west 40 km'"
                rows={2}
                className="flex-1 resize-none bg-transparent text-[13px] text-slate-200 placeholder-slate-500 outline-none scrollbar-none"
                disabled={isLoading}
                aria-label="Chat message input"
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || isLoading}
                className="
                  mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center
                  rounded-lg bg-sky-600 text-white transition
                  hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-40
                "
                aria-label="Send message"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
              </button>
            </div>
            <div className="mt-1.5 text-center text-[9px] text-slate-600">
              Real detection data · No AI fabrication · Press Enter to send
            </div>
          </div>
        </div>
      )}

      {/* Bounce keyframe */}
      <style jsx global>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-5px); }
        }
      `}</style>
    </>
  );
}
