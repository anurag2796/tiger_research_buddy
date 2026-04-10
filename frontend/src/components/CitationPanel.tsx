"use client";

import { Source } from "./ChatInterface";
import { BookOpen, ChevronRight, ChevronLeft } from "lucide-react";
import { useState } from "react";

export default function CitationPanel({ 
  sources, 
  isExpanded = true, 
  onToggle 
}: { 
  sources: Source[];
  isExpanded?: boolean;
  onToggle?: () => void;
}) {
  if (!sources || sources.length === 0) {
    return (
      <div className="h-full bg-[#111] border border-white/10 rounded-xl p-6 flex flex-col items-center justify-center text-center backdrop-blur-xl shadow-2xl">
        <BookOpen className="w-12 h-12 text-white/10 mb-4" />
        <h3 className="text-white/50 font-medium">No References Active</h3>
        <p className="text-xs text-white/30 mt-2">Query the chat to visualize document citations.</p>
      </div>
    );
  }

  if (!isExpanded) {
    return (
      <div className="h-full bg-[#111] border border-white/10 rounded-xl flex flex-col items-center py-4 backdrop-blur-xl shadow-2xl transition-all cursor-pointer hover:bg-black/50" onClick={onToggle}>
          <button className="text-white/50 hover:text-white mb-4">
              <ChevronLeft className="w-5 h-5" />
          </button>
          <div className="writing-vertical-rl transform rotate-180 flex items-center gap-2 text-white/50 tracking-widest text-sm uppercase whitespace-nowrap">
              <BookOpen className="w-4 h-4 transform -rotate-90" />
              Citations ({sources.length})
          </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full bg-[#111] border border-white/10 rounded-xl flex flex-col overflow-hidden backdrop-blur-xl shadow-2xl transition-all">
      <div className="p-4 border-b border-white/10 bg-black/40 flex items-center justify-between">
        <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-[#ffe81f]" />
            <h3 className="font-semibold text-white tracking-wide text-sm whitespace-nowrap">Active Citations ({sources.length})</h3>
        </div>
        <button onClick={onToggle} className="text-white/50 hover:text-white transition-colors">
            <ChevronRight className="w-5 h-5" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {sources.map((src, i) => (
          <div key={i} className="bg-black/30 border border-white/5 rounded-lg p-3 hover:border-white/20 hover:bg-black/50 transition-all cursor-default">
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs font-mono bg-[#ffe81f]/10 text-[#ffe81f] px-2 py-0.5 rounded-full border border-[#ffe81f]/20">
                Source [{i + 1}]
              </span>
              <span className="text-[10px] text-white/40 uppercase tracking-widest">
                {src.metadata?.doc_type || 'Document'}
              </span>
            </div>
            <h4 className="text-sm text-white font-medium mb-2 leading-tight">
              {src.metadata?.name || src.metadata?.title || src.id}
            </h4>
            <p className="text-xs text-white/60 line-clamp-4 leading-relaxed">
              {src.content}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
