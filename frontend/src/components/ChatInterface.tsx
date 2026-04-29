"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://192.168.0.8:8000";
import { Bot, User, Trash2, StopCircle, History, ArrowUp, ChevronDown, ChevronRight, Search, Brain } from "lucide-react";

export interface Source {
  id: string;
  metadata: Record<string, any>;
  content: string;
  score: number;
}

interface Step {
  step: string;
  label: string;
  details: string;
  count?: number;
}


interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  steps?: Step[];
  ts?: number;
}

const STORAGE_KEY = "tiger_chat_messages";
const SESSION_KEY = "tiger_session_id";
const MAX_STORED_MESSAGES = 60;

const MODELS = [
  { id: "auto", label: "Auto", short: "Auto" },
  { id: "qwen3:14b", label: "Fast · qwen3:14b", short: "Fast" },
  { id: "gemma4:26b", label: "Deep · gemma4:26b", short: "Deep" },
];

const STEP_ICONS: Record<string, React.ReactNode> = {
  retrieval: <Search className="w-3 h-3" />,
  generate: <Brain className="w-3 h-3" />,
};

// ── Thinking block (collapsible, does NOT trigger parent scroll) ─────────────
function ThinkingBlock({ steps, sources }: { steps: Step[]; sources?: Source[] }) {
  const [open, setOpen] = useState(false);
  const summary = steps.map(s => s.label).join(" · ");

  const toggle = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setOpen(v => !v);
  }, []);

  return (
    <div className="mb-3">
      <button
        onClick={toggle}
        className="flex items-center gap-1.5 text-xs text-white/35 hover:text-white/55 transition-colors group select-none"
      >
        {open
          ? <ChevronDown className="w-3 h-3 text-white/25 group-hover:text-white/45" />
          : <ChevronRight className="w-3 h-3 text-white/25 group-hover:text-white/45" />
        }
        <span className="italic">{summary}</span>
      </button>

      {open && (
        <div className="mt-2 ml-4 border-l border-white/8 pl-3 space-y-2">
          {steps.map((s, i) => (
            <div key={i} className="flex items-start gap-2">
              <span className="text-white/25 mt-0.5 shrink-0">
                {STEP_ICONS[s.step] ?? <Brain className="w-3 h-3" />}
              </span>
              <div>
                <p className="text-xs text-white/50 font-medium">{s.label}</p>
                <p className="text-[11px] text-white/30">{s.details}</p>
              </div>
            </div>
          ))}

          {sources && sources.length > 0 && (
            <div className="pt-1">
              <p className="text-[10px] text-white/25 uppercase tracking-wider mb-1.5">Context used</p>
              <div className="space-y-1">
                {sources.slice(0, 5).map((src, i) => (
                  <div key={i} className="flex items-baseline gap-2">
                    <span className="text-[10px] text-[#F76902]/50 font-mono shrink-0">[{i + 1}]</span>
                    <p className="text-[11px] text-white/40 truncate">
                      {src.metadata?.name || src.metadata?.title || src.id}
                      <span className="text-white/20 ml-1.5">{src.metadata?.doc_type}</span>
                    </p>
                  </div>
                ))}
                {sources.length > 5 && (
                  <p className="text-[10px] text-white/20">+{sources.length - 5} more</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Live status indicator shown inside a streaming message ───────────────────
function StreamStatus({ steps, hasContent }: { steps: Step[]; hasContent: boolean }) {
  // Once content is flowing we only show the cursor — handled in parent
  if (hasContent) return null;

  if (steps.length === 0) {
    return (
      <div className="flex items-center gap-2 mb-2">
        <div className="flex gap-1">
          {[0, 1, 2].map(n => (
            <span
              key={n}
              className="inline-block w-1.5 h-1.5 rounded-full bg-white/30"
              style={{ animation: `pulse-dot 1.2s ease-in-out ${n * 0.2}s infinite` }}
            />
          ))}
        </div>
        <span className="text-xs text-white/30 italic">Connecting...</span>
      </div>
    );
  }

  const last = steps[steps.length - 1];

  // Map step type to a friendlier verb
  const verb: Record<string, string> = {
    retrieval: "Searching knowledge base",
    generate: "Generating response",
  };
  const label = verb[last.step] ?? last.label;

  return (
    <div className="flex items-center gap-2 mb-2">
      {/* Spinning ring */}
      <span
        className="inline-block w-3 h-3 rounded-full border border-[#F76902]/50 border-t-transparent shrink-0"
        style={{ animation: "spin 0.8s linear infinite" }}
      />
      <span className="text-xs text-white/40 italic">{label}...</span>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function ChatInterface({
  onSourcesChange,
  loadSessionId,
  onSessionSaved,
}: {
  onSourcesChange: (sources: Source[]) => void;
  loadSessionId?: string | null;
  onSessionSaved?: () => void;
}) {
  const WELCOME: Message = {
    role: "assistant",
    content: "Hello! I'm TigerResearchBuddy. Ask me anything about RIT research, faculty, or find collaboration opportunities.",
    ts: 0,
  };
  const [messages, setMessages] = useState<Message[]>([WELCOME]);

  const sessionIdRef = useRef<string>("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [persona, setPersona] = useState("tiger");
  const [selectedModel, setSelectedModel] = useState("auto");
  const [showTimestamps, setShowTimestamps] = useState(false);
  const [sessionActive, setSessionActive] = useState(false);

  const endRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  // true = auto-scroll to bottom; flips to false when user scrolls up
  const shouldAutoScrollRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ── Scroll tracking ──
  const handleContainerScroll = useCallback(() => {
    const el = messagesContainerRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    // Re-enable auto-scroll when user scrolls back near bottom
    shouldAutoScrollRef.current = distFromBottom < 150;
  }, []);

  // ── Auto-scroll: only when user hasn't scrolled up ──
  useEffect(() => {
    if (shouldAutoScrollRef.current) {
      endRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading]);

  // ── Persist / restore ──
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) setMessages(JSON.parse(stored));
    } catch { /* ignore */ }
    const sid = localStorage.getItem(SESSION_KEY) || "";
    if (sid) {
      sessionIdRef.current = sid;
      setSessionActive(true);
    }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-MAX_STORED_MESSAGES)));
    } catch { /* ignore */ }
  }, [messages]);

  // ── Load session from sidebar ──
  useEffect(() => {
    if (!loadSessionId) return;
    if (loadSessionId === "__new__") {
      setMessages([WELCOME]);
      sessionIdRef.current = "";
      setSessionActive(false);
      onSourcesChange([]);
      localStorage.removeItem(SESSION_KEY);
      shouldAutoScrollRef.current = true;
      return;
    }
    fetch(`${API_URL}/api/sessions/${loadSessionId}/messages`)
      .then(r => r.json())
      .then((msgs: { role: string; content: string; ts: number }[]) => {
        if (!msgs.length) return;
        const loaded = msgs.map(m => ({ role: m.role as "user" | "assistant", content: m.content, ts: m.ts }));
        setMessages(loaded);
        sessionIdRef.current = loadSessionId;
        setSessionActive(true);
        onSourcesChange([]);
        shouldAutoScrollRef.current = true;
      })
      .catch(() => {});
  }, [loadSessionId]);

  const clearChat = () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    setMessages([WELCOME]);
    onSourcesChange([]);
    sessionIdRef.current = "";
    setSessionActive(false);
    localStorage.removeItem(SESSION_KEY);
    localStorage.setItem(STORAGE_KEY, JSON.stringify([WELCOME]));
    shouldAutoScrollRef.current = true;
  };

  const stopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setLoading(false);
      setMessages(prev => [...prev, { role: "assistant", content: "Generation stopped.", ts: Date.now() }]);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    // Always scroll to bottom on new send
    shouldAutoScrollRef.current = true;

    setMessages(prev => [...prev, { role: "user", content: userMsg, ts: Date.now() }]);
    setLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;
    setMessages(prev => [...prev, { role: "assistant", content: "", sources: [], steps: [], ts: Date.now() }]);

    try {
      const res = await fetch(`${API_URL}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: userMsg,
          use_cod: false,
          persona,
          model: selectedModel,
          session_id: sessionIdRef.current || undefined,
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No response body");

      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          const line = event.trim();
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);

          if (payload === "[DONE]") break;

          if (payload.startsWith("[STEP]")) {
            try {
              const step: Step = JSON.parse(payload.slice(6));
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                updated[updated.length - 1] = { ...last, steps: [...(last.steps || []), step] };
                return updated;
              });
            } catch { /* ignore */ }
            continue;
          }

          if (payload.startsWith("[SOURCES]")) {
            try {
              const sourceData = JSON.parse(payload.slice(9));
              const sources = sourceData.sources || [];
              if (sourceData.session_id && !sessionIdRef.current) {
                sessionIdRef.current = sourceData.session_id;
                setSessionActive(true);
                localStorage.setItem(SESSION_KEY, sourceData.session_id);
              }
              setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = { ...updated[updated.length - 1], sources };
                return updated;
              });
              if (sources.length > 0) onSourcesChange(sources);
            } catch { /* ignore */ }
            continue;
          }

          try {
            const { token } = JSON.parse(payload);
            if (token) {
              let loopDetected = false;
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                const newContent = last.content + token;
                const tail = newContent.slice(-400);
                const phrase = newContent.slice(-20, -5);
                if (phrase.trim().length > 10 && tail.split(phrase).length > 6) {
                  loopDetected = true;
                  updated[updated.length - 1] = {
                    ...last,
                    content: last.content + "\n\n⚠️ *Response truncated — repetition loop detected.*",
                  };
                } else {
                  updated[updated.length - 1] = { ...last, content: newContent };
                }
                return updated;
              });
              if (loopDetected && abortControllerRef.current) {
                abortControllerRef.current.abort();
                abortControllerRef.current = null;
                setLoading(false);
                return;
              }
            }
          } catch { /* ignore */ }
        }
      }
    } catch (error: any) {
      if (error.name !== "AbortError") {
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: `Error: ${error.message || "Failed to connect to backend."}`,
            ts: Date.now(),
          };
          return updated;
        });
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
      onSessionSaved?.();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
  };

  const formatTime = (ts?: number) => {
    if (!ts) return "";
    return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const messageCount = messages.filter(m => m.role === "user").length;

  return (
    <div className="flex flex-col h-full bg-[#212121]">
      {/* Top bar */}
      <div className="flex items-center justify-between px-5 py-2.5 border-b border-white/5 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white/70">TigerBrain</span>
          {sessionActive && (
            <span className="text-[10px] text-white/30 font-mono">
              · {messageCount} {messageCount === 1 ? "turn" : "turns"}{messageCount > 6 ? " · 6-turn memory" : ""}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowTimestamps(v => !v)}
            className={`p-1.5 rounded-md transition-colors ${showTimestamps ? "text-[#F76902]" : "text-white/25 hover:text-white/50"}`}
            title="Toggle timestamps"
          >
            <History className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={clearChat}
            className="p-1.5 rounded-md text-white/25 hover:text-white/60 transition-colors"
            title="New session"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Messages — attach scroll listener here */}
      <div
        ref={messagesContainerRef}
        onScroll={handleContainerScroll}
        className="flex-1 overflow-y-auto"
      >
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
          {messages.map((msg, i) => {
            const isStreamingThis = loading && i === messages.length - 1 && msg.role === "assistant";

            return (
              <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "items-start"}`}>
                {msg.role === "assistant" && (
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${isStreamingThis ? "bg-[#F76902]" : "bg-[#F76902]/80"}`}>
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}

                <div className={`flex flex-col gap-1 ${msg.role === "user" ? "items-end max-w-[78%]" : "flex-1 min-w-0"}`}>
                  {msg.role === "user" ? (
                    <div className="bg-[#2f2f2f] text-[#ececec] rounded-2xl rounded-br-sm px-4 py-3">
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  ) : (
                    <div className="text-[#ececec]">
                      {/* Live status while streaming (no content yet) */}
                      {isStreamingThis && (
                        <StreamStatus steps={msg.steps ?? []} hasContent={msg.content.length > 0} />
                      )}

                      {/* Thinking block — only once steps exist */}
                      {(msg.steps?.length ?? 0) > 0 && (
                        <ThinkingBlock steps={msg.steps!} sources={msg.sources} />
                      )}

                      {/* Response text */}
                      {msg.content ? (
                        <div className="prose prose-invert prose-sm max-w-none text-[#ececec]
                          prose-headings:text-[#F76902] prose-headings:font-semibold
                          prose-strong:text-[#F76902]
                          prose-a:text-[#F76902] prose-a:underline
                          prose-code:bg-[#1a1a1a] prose-code:text-[#F76902] prose-code:px-1 prose-code:rounded
                          prose-pre:bg-[#1a1a1a] prose-pre:rounded-lg
                          prose-li:marker:text-[#F76902]
                          prose-ol:text-[#ececec] prose-ul:text-[#ececec]">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                          </ReactMarkdown>
                          {/* Blinking cursor while tokens stream */}
                          {isStreamingThis && (
                            <span
                              className="inline-block w-0.5 h-3.5 bg-[#F76902]/70 ml-0.5 align-middle rounded-sm"
                              style={{ animation: "blink 1s step-end infinite" }}
                            />
                          )}
                        </div>
                      ) : null}
                    </div>
                  )}

                  {showTimestamps && msg.ts ? (
                    <span className="text-[10px] text-white/20 font-mono px-1">{formatTime(msg.ts)}</span>
                  ) : null}
                </div>

                {msg.role === "user" && (
                  <div className="w-8 h-8 rounded-full bg-[#2f2f2f] border border-white/10 flex items-center justify-center shrink-0 mt-0.5">
                    <User className="w-4 h-4 text-white/60" />
                  </div>
                )}
              </div>
            );
          })}
          <div ref={endRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="px-4 pb-5 pt-2 shrink-0">
        <div className="max-w-3xl mx-auto">
          <div className="relative flex flex-col bg-[#2f2f2f] rounded-2xl border border-white/10 focus-within:border-[#F76902]/40 transition-colors">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              placeholder="Message TigerBrain..."
              rows={1}
              className="flex-1 bg-transparent resize-none px-4 pt-3.5 pb-2 text-sm text-[#ececec] placeholder-white/30 focus:outline-none max-h-40 leading-relaxed"
            />

            <div className="flex items-center justify-between px-3 pb-2.5">
              <div className="flex items-center gap-2">
                <select
                  value={selectedModel}
                  onChange={e => setSelectedModel(e.target.value)}
                  className="bg-[#212121] border border-white/10 text-white/55 text-xs px-2.5 py-1.5 rounded-lg focus:outline-none focus:border-[#F76902]/40 transition-colors cursor-pointer"
                  title="Model"
                >
                  {MODELS.map(m => (
                    <option key={m.id} value={m.id}>{m.label}</option>
                  ))}
                </select>

                <select
                  value={persona}
                  onChange={e => setPersona(e.target.value)}
                  className="bg-[#212121] border border-white/10 text-white/55 text-xs px-2.5 py-1.5 rounded-lg focus:outline-none focus:border-[#F76902]/40 transition-colors cursor-pointer"
                  title="Persona"
                >
                  <option value="tiger">🐅 Tiger</option>
                  <option value="analyzer">📊 Analyzer</option>
                  <option value="critique">🔍 Critique</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5">
                {loading ? (
                  <button
                    onClick={stopGenerating}
                    className="p-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-white/60 transition-colors"
                    title="Stop"
                  >
                    <StopCircle className="w-4 h-4" />
                  </button>
                ) : (
                  <button
                    onClick={handleSend}
                    disabled={!input.trim()}
                    className="p-1.5 rounded-lg bg-[#F76902] hover:bg-[#e55f00] text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ArrowUp className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
          <p className="text-center text-[10px] text-white/20 mt-2">
            Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>

      <style>{`
        @keyframes pulse-dot {
          0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}
