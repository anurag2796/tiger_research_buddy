"use client";

import { useState } from "react";
import ChatInterface, { Source } from "@/components/ChatInterface";
import CitationPanel from "@/components/CitationPanel";
import GraphViewer from "@/components/GraphViewer";
import CollaborationHub from "@/components/CollaborationHub";
import { MessageSquare, Network, Lightbulb } from "lucide-react";

export default function Home() {
  const [activeSources, setActiveSources] = useState<Source[]>([]);
  const [activeTab, setActiveTab] = useState<"chat" | "hub" | "graph">("chat");
  const [citationExpanded, setCitationExpanded] = useState(false);

  return (
    <main className="h-screen w-screen bg-[#050505] text-white p-4 overflow-hidden flex flex-col font-sans">
      <header className="mb-4 px-2 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-[#4ec5f1] to-[#ffe81f] text-transparent bg-clip-text">
            TigerResearchBuddy
          </h1>
        </div>
        
        {/* Navigation Tabs */}
        <div className="flex bg-black/50 border border-white/10 rounded-lg p-1">
            <button 
                onClick={() => setActiveTab("chat")}
                className={`flex items-center gap-2 px-4 py-2 rounded-md transition-all text-sm font-medium ${activeTab === "chat" ? "bg-[#4ec5f1]/20 text-[#4ec5f1]" : "text-white/50 hover:text-white"}`}
            >
                <MessageSquare className="w-4 h-4" /> Chat
            </button>
            <button 
                onClick={() => setActiveTab("hub")}
                className={`flex items-center gap-2 px-4 py-2 rounded-md transition-all text-sm font-medium ${activeTab === "hub" ? "bg-[#ffe81f]/20 text-[#ffe81f]" : "text-white/50 hover:text-white"}`}
            >
                <Lightbulb className="w-4 h-4" /> Collab Hub
            </button>
            <button 
                onClick={() => setActiveTab("graph")}
                className={`flex items-center gap-2 px-4 py-2 rounded-md transition-all text-sm font-medium ${activeTab === "graph" ? "bg-[#ff0055]/20 text-[#ff0055]" : "text-white/50 hover:text-white"}`}
            >
                <Network className="w-4 h-4" /> Prism View
            </button>
        </div>
      </header>

      <div className="flex-1 overflow-hidden min-h-0">
        {/* Chat Tab Layout */}
        {activeTab === "chat" && (
            <div className="flex h-full min-h-0 gap-4">
                <div className={`h-full min-h-0 overflow-hidden transition-all duration-300 ${citationExpanded ? "flex-1 lg:w-2/3" : "flex-1"}`}>
                    <ChatInterface onSourcesChange={setActiveSources} />
                </div>
                <div className={`h-full hidden lg:block min-h-0 overflow-hidden transition-all duration-300 ${citationExpanded ? "w-1/3" : "w-12"}`}>
                    <CitationPanel 
                       sources={activeSources} 
                       isExpanded={citationExpanded} 
                       onToggle={() => setCitationExpanded(!citationExpanded)} 
                    />
                </div>
            </div>
        )}
        
        {/* Collaboration Hub Layout */}
        {activeTab === "hub" && (
             <div className="h-full">
                 <CollaborationHub />
             </div>
        )}

        {/* Prism View Array */}
        {activeTab === "graph" && (
            <div className="h-full">
                 <GraphViewer />
            </div>
        )}
      </div>
    </main>
  );
}
