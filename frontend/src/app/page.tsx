"use client";

import { useState, useCallback } from "react";
import ChatInterface, { Source } from "@/components/ChatInterface";
import CitationPanel from "@/components/CitationPanel";
import GraphViewer from "@/components/GraphViewer";
import CollaborationHub from "@/components/CollaborationHub";
import HistorySidebar from "@/components/HistorySidebar";

export default function Home() {
  const [activeSources, setActiveSources] = useState<Source[]>([]);
  const [activeTab, setActiveTab] = useState<"chat" | "hub" | "graph">("chat");
  const [citationExpanded, setCitationExpanded] = useState(false);
  const [loadSessionId, setLoadSessionId] = useState<string | null>(null);
  const [historyRefresh, setHistoryRefresh] = useState(0);
  const [pendingCollab, setPendingCollab] = useState<any>(null);
  const [graphEverVisited, setGraphEverVisited] = useState(false);

  const handleLoadSession = useCallback((id: string) => {
    setActiveTab("chat");
    setLoadSessionId(id);
  }, []);

  const handleLoadCollaboration = useCallback((collab: any) => {
    setActiveTab("hub");
    setPendingCollab(collab);
  }, []);

  const handleSessionSaved = useCallback(() => {
    setHistoryRefresh(n => n + 1);
  }, []);

  const handleNewChat = useCallback(() => {
    setLoadSessionId("__new__");
    setTimeout(() => setLoadSessionId(null), 0);
  }, []);

  const handleTabChange = useCallback((tab: "chat" | "hub" | "graph") => {
    if (tab === "graph") setGraphEverVisited(true);
    setActiveTab(tab);
  }, []);

  return (
    <main className="h-screen w-screen bg-[#212121] text-[#ececec] overflow-hidden flex font-sans">
      {/* Unified sidebar: logo + nav + history */}
      <HistorySidebar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        onLoadSession={handleLoadSession}
        onLoadCollaboration={handleLoadCollaboration}
        onNewChat={handleNewChat}
        refreshTrigger={historyRefresh}
      />

      {/* Main content area — all three views stay mounted; CSS hides inactive ones */}
      <div className="flex-1 overflow-hidden min-h-0">
        {/* Chat */}
        <div className={`flex h-full min-h-0 ${activeTab === "chat" ? "" : "hidden"}`}>
          <div className="flex-1 h-full min-h-0 overflow-hidden">
            <ChatInterface
              onSourcesChange={setActiveSources}
              loadSessionId={loadSessionId}
              onSessionSaved={handleSessionSaved}
            />
          </div>
          <div className={`h-full hidden lg:flex min-h-0 overflow-hidden transition-all duration-300 ${citationExpanded ? "w-80" : "w-12"}`}>
            <CitationPanel
              sources={activeSources}
              isExpanded={citationExpanded}
              onToggle={() => setCitationExpanded(!citationExpanded)}
            />
          </div>
        </div>

        {/* Collab Hub */}
        <div className={`h-full p-4 ${activeTab === "hub" ? "" : "hidden"}`}>
          <CollaborationHub pendingLoad={pendingCollab} onLoaded={() => setPendingCollab(null)} />
        </div>

        {/* Prism View — only mount once first visited to avoid upfront graph fetch */}
        {(activeTab === "graph" || graphEverVisited) && (
          <div className={`h-full ${activeTab === "graph" ? "" : "hidden"}`}>
            <GraphViewer />
          </div>
        )}
      </div>
    </main>
  );
}
