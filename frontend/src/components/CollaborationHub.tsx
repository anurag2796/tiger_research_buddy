"use client";

import { useState, useEffect } from "react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://192.168.0.8:8000";
import { Rocket, Target, Users, Loader2 } from "lucide-react";

interface Collaborator {
  id: string;
  score: number;
  metadata: Record<string, any>;
  content: string;
}

export default function CollaborationHub({
  pendingLoad,
  onLoaded,
}: {
  pendingLoad?: any;
  onLoaded?: () => void;
}) {
  const [formData, setFormData] = useState({
    title: "",
    college: "Computing",
    tags: "",
    description: ""
  });

  const [loading, setLoading] = useState(false);
  const [impact, setImpact] = useState<any>(null);
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);

  // Load a past submission from history sidebar
  useEffect(() => {
    if (!pendingLoad) return;
    setFormData({
      title: pendingLoad.title || "",
      college: pendingLoad.college || "Computing",
      tags: pendingLoad.tags || "",
      description: pendingLoad.description || "",
    });
    if (pendingLoad.impact_summary) {
      setImpact({ score: pendingLoad.impact_score, summary: pendingLoad.impact_summary });
    }
    if (pendingLoad.collaborators_json) {
      try { setCollaborators(JSON.parse(pendingLoad.collaborators_json)); } catch { /* ignore */ }
    }
    onLoaded?.();
  }, [pendingLoad]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title || !formData.description) return;
    
    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/api/idea`, formData);
      setImpact(res.data.impact);
      setCollaborators(res.data.collaborators);
    } catch (err) {
      console.error(err);
      alert("Failed to analyze idea. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full bg-[#1a1a1a] border border-white/5 rounded-xl overflow-hidden flex flex-col md:flex-row">
      <div className="w-full md:w-1/2 p-6 border-r border-white/5 overflow-y-auto">
        <div className="flex items-center gap-3 mb-6">
          <Rocket className="w-5 h-5 text-[#F76902]" />
          <h2 className="text-lg font-semibold text-white">Post an Idea</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-white/45 uppercase tracking-wider mb-1.5 block">Title</label>
            <input
              type="text"
              value={formData.title}
              onChange={e => setFormData({...formData, title: e.target.value})}
              placeholder="e.g. AI for Sustainable Farming"
              className="w-full bg-[#212121] border border-white/10 rounded-xl p-3 text-sm text-white placeholder-white/25 focus:outline-none focus:border-[#F76902]/40 transition-colors"
              required
            />
          </div>

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs text-white/45 uppercase tracking-wider mb-1.5 block">College</label>
              <select
                value={formData.college}
                onChange={e => setFormData({...formData, college: e.target.value})}
                className="w-full bg-[#212121] border border-white/10 rounded-xl p-3 text-sm text-white focus:outline-none focus:border-[#F76902]/40 transition-colors"
              >
                {["Computing", "Science", "Engineering", "Liberal Arts", "Business", "Technology"].map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="text-xs text-white/45 uppercase tracking-wider mb-1.5 block">Tags</label>
              <input
                type="text"
                value={formData.tags}
                onChange={e => setFormData({...formData, tags: e.target.value})}
                placeholder="ai, sustainability"
                className="w-full bg-[#212121] border border-white/10 rounded-xl p-3 text-sm text-white placeholder-white/25 focus:outline-none focus:border-[#F76902]/40 transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-white/45 uppercase tracking-wider mb-1.5 block">Description</label>
            <textarea
              value={formData.description}
              onChange={e => setFormData({...formData, description: e.target.value})}
              placeholder="Describe your research idea in detail..."
              rows={5}
              className="w-full bg-[#212121] border border-white/10 rounded-xl p-3 text-sm text-white placeholder-white/25 focus:outline-none focus:border-[#F76902]/40 transition-colors resize-none"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#F76902] hover:bg-[#e55f00] text-white font-semibold py-3 rounded-xl transition-colors flex justify-center items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Rocket className="w-4 h-4" />}
            {loading ? "Analyzing..." : "Find Collaborators"}
          </button>
        </form>
      </div>

      <div className="w-full md:w-1/2 p-6 overflow-y-auto">
        <h3 className="text-base font-semibold text-white mb-5 flex items-center gap-2">
          <Target className="w-4 h-4 text-[#F76902]" />
          Analysis Results
        </h3>

        {!impact && !loading && (
          <div className="h-40 flex flex-col items-center justify-center text-white/25 border border-dashed border-white/8 rounded-xl">
            <Users className="w-7 h-7 mb-2" />
            <p className="text-sm">Submit an idea to discover faculty matches.</p>
          </div>
        )}

        {loading && (
          <div className="h-40 flex flex-col items-center justify-center border border-dashed border-[#F76902]/20 rounded-xl">
            <Loader2 className="w-7 h-7 mb-3 animate-spin text-[#F76902]" />
            <p className="text-sm text-white/40 animate-pulse">Running semantic graph fusion...</p>
          </div>
        )}

        {impact && !loading && (
          <div className="space-y-5">
            <div className="bg-[#F76902]/8 border border-[#F76902]/25 rounded-xl p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-[#F76902] font-semibold uppercase tracking-wider">Impact Score</span>
                <span className="text-2xl font-bold text-white">{impact.score}<span className="text-sm text-white/40">/10</span></span>
              </div>
              <p className="text-sm text-white/65 italic leading-relaxed">"{impact.summary}"</p>

              {impact.sdgs && impact.sdgs.length > 0 && (
                <div className="mt-3 pt-3 border-t border-[#F76902]/15">
                  <span className="text-[10px] text-white/35 uppercase tracking-wider block mb-2">SDG Alignment</span>
                  <div className="flex flex-wrap gap-1.5">
                    {impact.sdgs.map((sdg: string) => (
                      <span key={sdg} className="bg-[#F76902]/15 text-[#F76902] text-[10px] px-2.5 py-1 rounded-full border border-[#F76902]/20">{sdg}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div>
              <h4 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5" />
                Top Faculty Matches
              </h4>
              <div className="space-y-3">
                {collaborators.map((c, i) => {
                  const relevance = Math.min(0.99, Math.max(0.50, c.score * 25 + 0.45));
                  return (
                    <div key={i} className="bg-[#212121] border border-white/8 rounded-xl p-4 hover:border-white/15 transition-colors">
                      <div className="flex justify-between items-start mb-1.5">
                        <span className="font-semibold text-[#F76902] text-sm">{c.metadata?.name || "Unknown"}</span>
                        <span className="text-[10px] font-mono text-white/40 bg-white/5 px-2 py-0.5 rounded-full">
                          {(relevance * 100).toFixed(0)}% match
                        </span>
                      </div>
                      {c.metadata?.college && (
                        <span className="text-[10px] text-white/35 block mb-2">{c.metadata.college}</span>
                      )}
                      <p className="text-xs text-white/55 leading-relaxed line-clamp-3">{c.content}</p>
                    </div>
                  );
                })}
                {collaborators.length === 0 && (
                  <p className="text-sm text-white/30 italic">No direct faculty matches found.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
