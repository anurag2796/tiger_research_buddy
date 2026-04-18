"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2, Trash2, StopCircle } from "lucide-react";

export interface Source {
  id: string;
  metadata: Record<string, any>;
  content: string;
  score: number;
}

const parseMarkdown = (text: string) => {
  if (!text) return "";
  let html = text.replace(/\n/g, "<br/>");
  // Bold: **text**
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  // Italic: *text*
  html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
  return html;
};

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

export default function ChatInterface({
  onSourcesChange,
}: {
  onSourcesChange: (sources: Source[]) => void;
}) {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hello! I'm TigerResearchBuddy v2. How can I help you find research opportunities today?" }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [persona, setPersona] = useState("tiger");
  const endRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const clearChat = () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    setMessages([{ role: "assistant", content: "Hello! I'm TigerResearchBuddy v2. How can I help you find research opportunities today?" }]);
    onSourcesChange([]);
  };

  const stopGenerating = () => {
    if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
        setLoading(false);
        setMessages((prev) => [...prev, { role: "assistant", content: "⚠️ Generation stopped by user." }]);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    // Create a new AbortController for this request
    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Add an empty assistant message that we'll stream tokens into
    setMessages((prev) => [...prev, { role: "assistant", content: "", sources: [] }]);

    try {
      const res = await fetch("http://localhost:8000/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMsg, use_cod: false, persona }),
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

        // Process complete SSE events (delimited by \n\n)
        const events = buffer.split("\n\n");
        buffer = events.pop() || ""; // Keep incomplete tail

        for (const event of events) {
          const line = event.trim();
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6); // strip "data: "

          if (payload === "[DONE]") {
            // Stream finished
            break;
          }

          if (payload.startsWith("[SOURCES]")) {
            // Parse sources event
            try {
              const sourceData = JSON.parse(payload.slice(9));
              const sources = sourceData.sources || [];
              // Update the last message with sources
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = { ...updated[updated.length - 1], sources };
                return updated;
              });
              if (sources.length > 0) onSourcesChange(sources);
            } catch { /* ignore parse errors */ }
            continue;
          }

          // Token event
          try {
            const { token } = JSON.parse(payload);
            if (token) {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                updated[updated.length - 1] = { ...last, content: last.content + token };
                return updated;
              });
            }
          } catch { /* ignore malformed events */ }
        }
      }
    } catch (error: any) {
      if (error.name === "AbortError") {
        console.log("Request canceled by user");
        // Message already in state from stopGenerating
      } else {
        console.error(error);
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: `Error: ${error.message || "Failed to fetch response from API. Please ensure the backend is running."}`,
          };
          return updated;
        });
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#111] border border-white/10 rounded-xl overflow-hidden shadow-2xl backdrop-blur-xl">
      <div className="flex items-center justify-between p-4 border-b border-white/10 bg-black/40">
        <div className="flex items-center gap-3">
            <Bot className="text-[#4ec5f1] w-6 h-6" />
            <h2 className="font-semibold text-white tracking-wide">TigerBrain Terminal</h2>
        </div>
        
        <div className="flex items-center gap-4">
           <select 
              value={persona} 
              onChange={(e) => setPersona(e.target.value)}
              className="bg-black/50 border border-white/20 text-[#ffe81f] text-xs px-3 py-1.5 rounded-md focus:outline-none focus:border-[#4ec5f1] transition-colors"
           >
              <option value="tiger">🐅 Tiger</option>
              <option value="analyzer">📊 Analyzer</option>
              <option value="critique">🔍 Critique</option>
           </select>
           
           <button onClick={clearChat} title="Clear Chat" className="text-white/40 hover:text-white transition-colors">
              <Trash2 className="w-4 h-4" />
           </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === "user" ? "bg-[#ffe81f]" : "bg-[#4ec5f1]"}`}>
              {msg.role === "user" ? <User className="w-5 h-5 text-black" /> : <Bot className="w-5 h-5 text-black" />}
            </div>
            <div className={`max-w-[85%] rounded-2xl p-4 ${msg.role === "user" ? "bg-white/10 text-white rounded-tr-sm" : "bg-black/40 border border-[#4ec5f1]/30 text-gray-200 rounded-tl-sm shadow-[0_0_15px_rgba(78,197,241,0.05)]"}`}>
              <div className="prose prose-invert max-w-none text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: parseMarkdown(msg.content) }} />
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-4">
            <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-[#4ec5f1]">
              <Bot className="w-5 h-5 text-black" />
            </div>
            <div className="bg-black/40 border border-[#4ec5f1]/30 rounded-2xl rounded-tl-sm p-4 flex items-center gap-3">
              <Loader2 className="w-4 h-4 text-[#4ec5f1] animate-spin" />
              <span className="text-xs text-[#4ec5f1] font-mono animate-pulse">Synthesizing...</span>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="p-4 bg-black/40 border-t border-white/10">
        <div className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Query the TigerBrain database..."
            className="w-full bg-[#1a1a1a] border border-white/20 rounded-full pl-5 pr-24 py-3 text-sm text-white focus:outline-none focus:border-[#4ec5f1] transition-colors focus:shadow-[0_0_10px_rgba(78,197,241,0.2)]"
          />
          <div className="absolute right-2 flex gap-2 items-center">
              {loading && (
                  <button
                    onClick={stopGenerating}
                    title="Stop Generating"
                    className="p-2 rounded-full bg-red-500/10 hover:bg-red-500/20 text-red-500 transition-colors"
                  >
                    <StopCircle className="w-4 h-4" />
                  </button>
              )}
              <button
                onClick={handleSend}
                disabled={loading || !input.trim()}
                className="p-2 rounded-full bg-[#4ec5f1]/10 hover:bg-[#4ec5f1]/20 text-[#4ec5f1] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
          </div>
        </div>
      </div>
    </div>
  );
}
