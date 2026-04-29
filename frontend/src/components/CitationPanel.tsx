"use client";

import { Source } from "./ChatInterface";
import { BookOpen, ChevronRight, ChevronLeft } from "lucide-react";

export default function CitationPanel({
  sources,
  isExpanded = true,
  onToggle,
}: {
  sources: Source[];
  isExpanded?: boolean;
  onToggle?: () => void;
}) {
  if (!sources || sources.length === 0) {
    return (
      <div className="h-full bg-[#1a1a1a] border-l border-white/5 flex flex-col items-center justify-center text-center p-6">
        <BookOpen className="w-10 h-10 text-white/8 mb-3" />
        <p className="text-xs text-white/25">Citations will appear here after a response.</p>
      </div>
    );
  }

  if (!isExpanded) {
    return (
      <div
        className="h-full bg-[#1a1a1a] border-l border-white/5 flex flex-col items-center py-4 cursor-pointer hover:bg-[#1f1f1f] transition-colors"
        onClick={onToggle}
      >
        <button className="text-white/40 hover:text-white mb-4 transition-colors">
          <ChevronLeft className="w-4 h-4" />
        </button>
        <div className="writing-vertical-rl transform rotate-180 flex items-center gap-2 text-white/35 tracking-widest text-xs uppercase whitespace-nowrap">
          <BookOpen className="w-3.5 h-3.5 transform -rotate-90" />
          Citations ({sources.length})
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-[#1a1a1a] border-l border-white/5">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-[#F76902]" />
          <span className="text-sm font-medium text-white/80">Citations ({sources.length})</span>
        </div>
        <button onClick={onToggle} className="text-white/30 hover:text-white/70 transition-colors">
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {sources.map((src, i) => (
          <div
            key={i}
            className="bg-[#212121] border border-white/5 rounded-xl p-3 hover:border-white/10 transition-colors cursor-default"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono bg-[#F76902]/10 text-[#F76902] px-2 py-0.5 rounded-full border border-[#F76902]/20">
                [{i + 1}]
              </span>
              <span className="text-[10px] text-white/30 uppercase tracking-wide">
                {src.metadata?.doc_type || "doc"}
              </span>
            </div>
            <h4 className="text-xs text-white/80 font-medium mb-1.5 leading-snug">
              {src.metadata?.name || src.metadata?.title || src.id}
            </h4>
            <p className="text-[11px] text-white/45 line-clamp-3 leading-relaxed">{src.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
