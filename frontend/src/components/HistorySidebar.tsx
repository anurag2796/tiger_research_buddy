"use client";

import { useState, useEffect, useCallback } from "react";
import { MessageSquare, Lightbulb, Network, Trash2, RefreshCw, SquarePen, ChevronLeft, ChevronRight } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://192.168.0.8:8000";

interface Session {
  id: string;
  title: string;
  persona: string;
  created_at: string;
  updated_at: string;
}

interface Collaboration {
  id: number;
  title: string;
  college: string;
  tags: string;
  impact_score: number;
  impact_summary: string;
  collaborators_json: string;
  created_at: string;
}

interface Props {
  activeTab: "chat" | "hub" | "graph";
  onTabChange: (tab: "chat" | "hub" | "graph") => void;
  onLoadSession: (sessionId: string) => void;
  onLoadCollaboration: (collab: Collaboration) => void;
  onNewChat: () => void;
  refreshTrigger: number;
}

const NAV_TABS = [
  { id: "chat" as const, label: "Chat", icon: MessageSquare },
  { id: "hub" as const, label: "Collab Hub", icon: Lightbulb },
  { id: "graph" as const, label: "Prism View", icon: Network },
];

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function HistorySidebar({ activeTab, onTabChange, onLoadSession, onLoadCollaboration, onNewChat, refreshTrigger }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [collabs, setCollabs] = useState<Collaboration[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const [sessRes, collabRes] = await Promise.all([
        fetch(`${API_URL}/api/sessions?type=chat&limit=40`),
        fetch(`${API_URL}/api/collaborations?limit=30`),
      ]);
      if (sessRes.ok) setSessions(await sessRes.json());
      if (collabRes.ok) setCollabs(await collabRes.json());
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { fetchHistory(); }, [fetchHistory, refreshTrigger]);

  const deleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    await fetch(`${API_URL}/api/chat/${id}`, { method: "DELETE" });
    setSessions(prev => prev.filter(s => s.id !== id));
  };

  if (collapsed) {
    return (
      <div className="h-full flex flex-col items-center gap-2 py-4 w-14 bg-[#171717] border-r border-white/5 shrink-0">
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/5 transition-colors mb-2"
          title="Expand sidebar"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        {NAV_TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className={`p-2 rounded-lg transition-colors ${
              activeTab === id
                ? "text-[#F76902] bg-[#F76902]/10"
                : "text-white/40 hover:text-white hover:bg-white/5"
            }`}
            title={label}
          >
            <Icon className="w-4 h-4" />
          </button>
        ))}
        {activeTab === "chat" && (
          <button
            onClick={onNewChat}
            className="p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/5 transition-colors mt-1"
            title="New chat"
          >
            <SquarePen className="w-4 h-4" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col w-64 bg-[#171717] border-r border-white/5 shrink-0">
      {/* Brand header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[#F76902] flex items-center justify-center shrink-0">
            <span className="text-white font-black text-xs leading-none">T</span>
          </div>
          <span className="font-semibold text-sm text-white truncate">TigerResearch</span>
        </div>
        <button
          onClick={() => setCollapsed(true)}
          className="text-white/30 hover:text-white/70 transition-colors p-1 rounded"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* Nav tabs */}
      <div className="px-2 pb-2 space-y-0.5">
        {NAV_TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors text-left ${
              activeTab === id
                ? "bg-[#F76902]/15 text-[#F76902] font-medium"
                : "text-white/55 hover:bg-white/5 hover:text-white"
            }`}
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </button>
        ))}
      </div>

      <div className="mx-3 h-px bg-white/5 mb-2" />

      {/* New chat button */}
      {activeTab === "chat" && (
        <div className="px-2 pb-3">
          <button
            onClick={onNewChat}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-white/50 hover:text-white hover:bg-white/5 border border-white/8 transition-colors"
          >
            <SquarePen className="w-4 h-4 shrink-0" />
            New chat
          </button>
        </div>
      )}

      {/* History list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-4">
        {(activeTab === "chat" || activeTab === "graph") && (
          <div>
            <div className="flex items-center justify-between px-1 mb-1">
              <span className="text-[10px] font-semibold text-white/25 uppercase tracking-wider">Chats</span>
              <button onClick={fetchHistory} className="text-white/20 hover:text-white/50 transition-colors p-0.5">
                <RefreshCw className={`w-2.5 h-2.5 ${loading ? "animate-spin" : ""}`} />
              </button>
            </div>
            {sessions.length === 0 ? (
              <p className="text-xs text-white/20 px-1 py-1.5">No chats yet</p>
            ) : sessions.map(s => (
              <div
                key={s.id}
                onClick={() => onLoadSession(s.id)}
                className="group flex items-start justify-between px-2 py-1.5 rounded-lg hover:bg-white/5 cursor-pointer transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-white/65 truncate leading-snug">{s.title}</p>
                  <p className="text-[10px] text-white/25 mt-0.5">{relativeTime(s.updated_at)}</p>
                </div>
                <button
                  onClick={(e) => deleteSession(e, s.id)}
                  className="opacity-0 group-hover:opacity-100 text-white/25 hover:text-red-400 transition-all shrink-0 ml-1 mt-0.5"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        {(activeTab === "hub" || activeTab === "graph") && (
          <div>
            <div className="text-[10px] font-semibold text-white/25 uppercase tracking-wider px-1 mb-1">Past ideas</div>
            {collabs.length === 0 ? (
              <p className="text-xs text-white/20 px-1 py-1.5">No submissions yet</p>
            ) : collabs.map(c => (
              <button
                key={c.id}
                onClick={() => onLoadCollaboration(c)}
                className="w-full text-left px-2 py-1.5 rounded-lg hover:bg-white/5 transition-colors"
              >
                <p className="text-xs text-white/65 truncate leading-snug">{c.title}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-[#F76902]/60">{c.impact_score ? `${c.impact_score.toFixed(1)}/10` : "—"}</span>
                  <span className="text-[10px] text-white/25">{relativeTime(c.created_at)}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
