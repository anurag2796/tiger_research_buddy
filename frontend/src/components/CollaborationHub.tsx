"use client";

import { useState } from "react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://192.168.0.8:8000";
import { Rocket, Target, Users, Loader2 } from "lucide-react";

interface Collaborator {
  id: string;
  score: number;
  metadata: Record<string, any>;
  content: string;
}

export default function CollaborationHub() {
  const [formData, setFormData] = useState({
    title: "",
    college: "Computing",
    tags: "",
    description: ""
  });
  
  const [loading, setLoading] = useState(false);
  const [impact, setImpact] = useState<any>(null);
  const [collaborators, setCollaborators] = useState<Collaborator[]>([]);

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
    <div className="h-full bg-[#111] border border-white/10 rounded-xl overflow-hidden shadow-2xl backdrop-blur-xl flex flex-col md:flex-row">
      <div className="w-full md:w-1/2 p-6 border-r border-white/10 overflow-y-auto">
        <div className="flex items-center gap-3 mb-6">
          <Rocket className="w-6 h-6 text-[#4ec5f1]" />
          <h2 className="text-xl font-bold text-white tracking-wide">💡 Post an Idea</h2>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-white/60 uppercase tracking-widest mb-1 block">Title</label>
            <input 
              type="text"
              value={formData.title}
              onChange={e => setFormData({...formData, title: e.target.value})}
              placeholder="e.g. AI for Sustainable Farming"
              className="w-full bg-black/50 border border-white/20 rounded-md p-3 text-sm text-white focus:outline-none focus:border-[#4ec5f1]"
              required
            />
          </div>
          
          <div className="flex gap-4">
              <div className="flex-1">
                <label className="text-xs text-white/60 uppercase tracking-widest mb-1 block">College</label>
                <select 
                  value={formData.college}
                  onChange={e => setFormData({...formData, college: e.target.value})}
                  className="w-full bg-black/50 border border-white/20 rounded-md p-3 text-sm text-white focus:outline-none focus:border-[#4ec5f1]"
                >
                    {["Computing", "Science", "Engineering", "Liberal Arts", "Business", "Technology"].map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="flex-1">
                <label className="text-xs text-white/60 uppercase tracking-widest mb-1 block">Tags</label>
                <input 
                  type="text"
                  value={formData.tags}
                  onChange={e => setFormData({...formData, tags: e.target.value})}
                  placeholder="ai, sustainability"
                  className="w-full bg-black/50 border border-white/20 rounded-md p-3 text-sm text-white focus:outline-none focus:border-[#4ec5f1]"
                />
              </div>
          </div>
          
          <div>
            <label className="text-xs text-white/60 uppercase tracking-widest mb-1 block">Description</label>
            <textarea 
              value={formData.description}
              onChange={e => setFormData({...formData, description: e.target.value})}
              placeholder="Describe your research idea in detail..."
              rows={4}
              className="w-full bg-black/50 border border-white/20 rounded-md p-3 text-sm text-white focus:outline-none focus:border-[#4ec5f1] resize-none"
              required
            />
          </div>
          
          <button 
            type="submit" 
            disabled={loading}
            className="w-full bg-[#4ec5f1]/10 border border-[#4ec5f1]/50 text-[#4ec5f1] hover:bg-[#4ec5f1] hover:text-black font-bold uppercase tracking-widest py-3 rounded-sm transition-all flex justify-center items-center gap-2"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : < Rocket className="w-5 h-5" />}
            {loading ? "Analyzing Matrix..." : "Find Collaborators"}
          </button>
        </form>
      </div>
      
      <div className="w-full md:w-1/2 p-6 bg-black/30 overflow-y-auto">
        <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2"><Target className="w-5 h-5 text-[#ffe81f]" /> Analysis Results</h3>
        
        {!impact && !loading && (
            <div className="h-48 flex flex-col items-center justify-center text-white/30 border border-dashed border-white/10 rounded-lg">
                <Users className="w-8 h-8 mb-2" />
                <p>Submit an idea to discover faculty matches.</p>
            </div>
        )}
        
        {loading && (
             <div className="h-48 flex flex-col items-center justify-center text-[#4ec5f1] border border-dashed border-[#4ec5f1]/30 rounded-lg">
                <Loader2 className="w-8 h-8 mb-4 animate-spin" />
                <p className="font-mono text-sm animate-pulse">Running semantic graph fusion...</p>
            </div>
        )}
        
        {impact && !loading && (
            <div className="space-y-6">
                <div className="bg-[#4ec5f1]/5 border border-[#4ec5f1]/30 rounded-lg p-5">
                    <div className="flex justify-between items-center mb-3">
                        <span className="text-[#4ec5f1] font-bold text-sm uppercase tracking-widest">Impact Score</span>
                        <span className="text-2xl font-black text-white">{impact.score}/10</span>
                    </div>
                    <p className="text-sm text-white/80 italic">"{impact.summary}"</p>
                    
                    {impact.sdgs && impact.sdgs.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-[#4ec5f1]/20">
                            <span className="text-xs text-[#4ec5f1]/80 uppercase block mb-2">Sustainable Development Goals</span>
                            <div className="flex flex-wrap gap-2">
                                {impact.sdgs.map((sdg: string) => (
                                    <span key={sdg} className="bg-[#4ec5f1]/20 text-[#4ec5f1] text-[10px] px-2 py-1 rounded-full">{sdg}</span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
                
                <div>
                     <h4 className="text-sm font-bold text-white uppercase tracking-widest mb-4 flex items-center gap-2"><Users className="w-4 h-4 text-[#ffe81f]" /> Top Faculty Matches</h4>
                     <div className="space-y-4">
                         {collaborators.map((c, i) => {
                             const relevance = Math.min(0.99, Math.max(0.50, c.score * 25 + 0.45));
                             return (
                                 <div key={i} className="bg-black/60 border border-white/10 rounded-lg p-4 hover:border-white/30 transition-colors">
                                     <div className="flex justify-between items-start mb-2">
                                         <span className="font-bold text-[#ffe81f]">{c.metadata?.name || 'Unknown'}</span>
                                         <span className="text-xs font-mono text-white/50 bg-white/10 px-2 py-0.5 rounded">Relevance: {(relevance * 100).toFixed(0)}%</span>
                                     </div>
                                     {c.metadata?.college && (
                                         <span className="text-[10px] text-white/40 uppercase tracking-widest block mb-3">College: {c.metadata.college}</span>
                                     )}
                                     <p className="text-xs text-white/70 leading-relaxed line-clamp-3">{c.content}</p>
                                 </div>
                             )
                         })}
                         {collaborators.length === 0 && (
                             <p className="text-sm text-white/40 italic">No direct faculty matches found yet.</p>
                         )}
                     </div>
                </div>
            </div>
        )}
      </div>
    </div>
  );
}
