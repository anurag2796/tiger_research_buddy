"use client";

import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import axios from "axios";
import { Network, Search, X, Users, FileText, Tag, ChevronRight, Eye, EyeOff, ZoomIn, RefreshCw } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://192.168.0.8:8000";

const CosmographWrapper = dynamic(
  () => import("@cosmograph/react").then((mod) => mod.Cosmograph),
  { ssr: false }
);

type NodeType = "faculty" | "paper" | "concept" | string;

interface GraphNode {
  [key: string]: any;
  id: string;
  type?: NodeType;
  label?: string;
  name?: string;
  dept?: string;
  email?: string;
  url?: string;
  year?: string;
  degree?: number;
  x?: number;
  y?: number;
}

interface GraphLink {
  [key: string]: any;
  source: string | GraphNode;
  target: string | GraphNode;
  type?: string;
  weight?: number;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

type ViewMode = "all" | "faculty-network" | "papers" | "concepts";

// Edge colors by relationship type
const LINK_COLORS: Record<string, string> = {
  AUTHORED:        "rgba(78, 197, 241, 0.4)",  // Cyan (matches paper)
  COAUTHORED_WITH: "rgba(236, 72, 153, 0.8)",  // Pink (distinct for faculty-faculty)
  MENTIONS:        "rgba(167, 139, 250, 0.3)", // Purple (matches concept)
  HAS_TOPIC:       "rgba(167, 139, 250, 0.3)",
  RELATED_TO:      "rgba(255, 255, 255, 0.15)",
};
const LINK_COLOR_DEFAULT = "rgba(255,255,255,0.06)";

const NODE_COLORS: Record<string, string> = {
  faculty: "#F76902",   // RIT orange
  paper:   "#4ec5f1",   // cyan
  concept: "#a78bfa",   // purple
};
const NODE_COLOR_DIM = "rgba(255,255,255,0.07)";

export default function GraphViewer() {
  const [rawData, setRawData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>("all");
  const [search, setSearch] = useState("");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [highlightIds, setHighlightIds] = useState<Set<string>>(new Set());
  const [highlightLinks, setHighlightLinks] = useState<Set<string>>(new Set());
  const [showLabels, setShowLabels] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);

  useEffect(() => {
    axios.get(`${API_URL}/api/graph`).then(res => {
      setRawData(res.data);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  // Cosmograph automatically handles layout spreading via simulationRepulsion

  const degreeMap = useMemo(() => {
    const map: Record<string, number> = {};
    rawData.links.forEach(l => {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      map[s] = (map[s] || 0) + 1;
      map[t] = (map[t] || 0) + 1;
    });
    return map;
  }, [rawData]);

  const neighborMap = useMemo(() => {
    const map: Record<string, string[]> = {};
    rawData.links.forEach(l => {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      if (!map[s]) map[s] = [];
      if (!map[t]) map[t] = [];
      map[s].push(t);
      map[t].push(s);
    });
    return map;
  }, [rawData]);

  // Link key helper for highlight set
  const linkKey = (l: GraphLink) => {
    const s = typeof l.source === "object" ? l.source.id : l.source;
    const t = typeof l.target === "object" ? l.target.id : l.target;
    return `${s}|${t}`;
  };

  // Filtered graph data based on view mode
  const graphData = useMemo(() => {
    // Filter out bare URL stub nodes (no type) — these are raw crawler artifacts, not semantic nodes
    let nodes = rawData.nodes
      .filter(n => n.type)
      .map((n, idx) => {
        const deg = degreeMap[n.id] || 0;
        const mappedNode = { ...n, degree: deg, color: "", size: 1, index: idx };
        
        // Calculate size (tuned down for Cosmograph WebGL renderer)
        const type = (n.type || "").toLowerCase();
        if (type === "faculty") mappedNode.size = Math.min(2 + deg * 0.4, 8);
        else if (type === "paper") mappedNode.size = Math.min(1 + deg * 0.1, 4);
        else mappedNode.size = Math.min(0.5 + deg * 0.05, 2);

        // Calculate color (base color, dimming handled natively or via search)
        mappedNode.color = NODE_COLORS[type || "concept"] || "#ffffff";
        
        // Calculate label
        mappedNode.label = n.label || n.name || String(n.id ?? "");
        
        return mappedNode;
      });
      
    // Create a Set of valid node IDs so we can remove orphaned links
    const validNodeIds = new Set(nodes.map(n => n.id));
    
    const validLinks = rawData.links.filter(l => {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      return validNodeIds.has(s) && validNodeIds.has(t);
    });

    const nodeIdToIndex = new Map<string, number>();
    nodes.forEach(n => nodeIdToIndex.set(n.id, n.index));

    let links = validLinks.map(l => {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      const mappedLink = { 
        ...l, 
        source: s, 
        target: t, 
        sourceIndex: nodeIdToIndex.get(s),
        targetIndex: nodeIdToIndex.get(t),
        color: LINK_COLOR_DEFAULT, 
        width: 0.5 
      };
      const ltype = (l.type || "").toUpperCase();
      mappedLink.color = LINK_COLORS[ltype] || LINK_COLOR_DEFAULT;
      
      if (ltype === "COAUTHORED_WITH") mappedLink.width = Math.min((l.weight || 1) * 0.8, 4);
      else if (ltype === "AUTHORED") mappedLink.width = 1.2;
      
      return mappedLink;
    });

    if (viewMode === "faculty-network") {
      // Only faculty nodes + their coauthor edges
      nodes = nodes.filter(n => (n.type || "").toLowerCase() === "faculty");
      const nodeIds = new Set(nodes.map(n => n.id));
      links = links.filter(l => {
        return nodeIds.has(l.source as string) && nodeIds.has(l.target as string);
      });
    } else if (viewMode === "papers") {
      nodes = nodes.filter(n => {
        const t = (n.type || "").toLowerCase();
        return t === "faculty" || t === "paper";
      });
      const nodeIds = new Set(nodes.map(n => n.id));
      links = links.filter(l => {
        return nodeIds.has(l.source as string) && nodeIds.has(l.target as string);
      });
    } else if (viewMode === "concepts") {
      nodes = nodes.filter(n => {
        const t = (n.type || "").toLowerCase();
        return t === "concept" || t === "paper";
      });
      const nodeIds = new Set(nodes.map(n => n.id));
      links = links.filter(l => {
        return nodeIds.has(l.source as string) && nodeIds.has(l.target as string);
      });
    }

    return { nodes, links };
  }, [rawData, viewMode, degreeMap]);

  const searchResults = useMemo(() => {
    if (!search.trim()) return [];
    const q = search.toLowerCase();
    return rawData.nodes.filter(n =>
      ((n.label || n.name || n.id || "").toLowerCase().includes(q))
    );
  }, [search, rawData]);

  useEffect(() => {
    if (searchResults.length > 0) {
      const ids = new Set<string>();
      const lks = new Set<string>();
      searchResults.forEach(n => {
        ids.add(n.id);
        (neighborMap[n.id] || []).forEach(nb => ids.add(nb));
      });
      rawData.links.forEach(l => {
        const s = typeof l.source === "object" ? l.source.id : l.source;
        const t = typeof l.target === "object" ? l.target.id : l.target;
        if (ids.has(s) && ids.has(t)) lks.add(linkKey(l));
      });
      setHighlightIds(ids);
      setHighlightLinks(lks);
    } else if (!selectedNode) {
      setHighlightIds(new Set());
      setHighlightLinks(new Set());
    }
  }, [searchResults, neighborMap, rawData.links, selectedNode]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    const nodeId = String(node.id ?? "");
    setSelectedNode(prev => prev?.id === nodeId ? null : { ...node, id: nodeId });

    // Fallback for search/highlight mapping
    const ids = new Set<string>([nodeId]);
    const lks = new Set<string>();
    (neighborMap[nodeId] || []).forEach(nb => ids.add(nb));

    rawData.links.forEach(l => {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      if ((s === nodeId || t === nodeId) && (ids.has(s) && ids.has(t))) {
        lks.add(linkKey(l));
      }
    });

    setHighlightIds(ids);
    setHighlightLinks(lks);

    if (graphRef.current?.selectNodeById) {
       graphRef.current.selectNodeById(nodeId, true);
    }
  }, [neighborMap, rawData.links]);

  const clearSelection = useCallback(() => {
    setSelectedNode(null);
    setHighlightIds(new Set());
    setHighlightLinks(new Set());
    setSearch("");
    if (graphRef.current?.fitView) {
      graphRef.current.fitView(500);
    }
  }, []);

  const nodeLabel = useCallback((node: GraphNode) => {
    return node.label || node.name || String(node.id ?? "");
  }, []);

  const stats = useMemo(() => ({
    faculty:  rawData.nodes.filter(n => (n.type||"").toLowerCase() === "faculty").length,
    papers:   rawData.nodes.filter(n => (n.type||"").toLowerCase() === "paper").length,
    concepts: rawData.nodes.filter(n => (n.type||"").toLowerCase() === "concept").length,
    edges:    rawData.links.length,
  }), [rawData]);

  const selectedNeighbors = useMemo(() => {
    if (!selectedNode) return { faculty: [], papers: [], concepts: [], links: [] };
    const neighborIds = Array.from(new Set(neighborMap[selectedNode.id] || []));
    const nodeById = Object.fromEntries(rawData.nodes.map(n => [n.id, n]));
    const neighbors = neighborIds.map(id => nodeById[id]).filter(Boolean);
    const relLinks = rawData.links.filter(l => {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      return s === selectedNode.id || t === selectedNode.id;
    });
    return {
      faculty:  neighbors.filter(n => (n.type||"").toLowerCase() === "faculty"),
      papers:   neighbors.filter(n => (n.type||"").toLowerCase() === "paper"),
      concepts: neighbors.filter(n => (n.type||"").toLowerCase() === "concept"),
      links:    relLinks,
    };
  }, [selectedNode, neighborMap, rawData]);

  const viewModes: { key: ViewMode; label: string; icon: React.ReactNode }[] = [
    { key: "all",             label: "All",           icon: <Network className="w-3 h-3" /> },
    { key: "faculty-network", label: "Collaboration", icon: <Users className="w-3 h-3" /> },
    { key: "papers",          label: "Faculty+Papers", icon: <FileText className="w-3 h-3" /> },
    { key: "concepts",        label: "Concepts",      icon: <Tag className="w-3 h-3" /> },
  ];

  const panelWidth = selectedNode ? 280 : 0;

  return (
    <div className="h-full bg-[#080808] rounded-xl overflow-hidden relative border border-white/5 flex" ref={containerRef}>

      {/* Canvas area */}
      <div className="flex-1 relative min-w-0">

        {/* Top controls */}
        <div className="absolute top-3 left-3 right-3 z-10 flex items-center gap-2 flex-wrap">
          {/* Title pill */}
          <div className="bg-black/80 border border-white/10 px-3 py-1.5 rounded-full flex items-center gap-2 backdrop-blur-md shrink-0">
            <Network className="w-4 h-4 text-[#F76902]" />
            <span className="text-xs font-mono text-white/70">Prism View</span>
          </div>

          {/* View mode tabs */}
          <div className="flex gap-0.5 bg-black/80 border border-white/10 p-1 rounded-full backdrop-blur-md">
            {viewModes.map(m => (
              <button
                key={m.key}
                onClick={() => { setViewMode(m.key); clearSelection(); }}
                className="text-[10px] px-2.5 py-1 rounded-full font-mono flex items-center gap-1 transition-all"
                style={{
                  backgroundColor: viewMode === m.key ? "#F76902" : "transparent",
                  color: viewMode === m.key ? "#000" : "rgba(255,255,255,0.5)",
                }}
              >
                {m.icon}
                <span className="hidden sm:inline">{m.label}</span>
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative bg-black/80 border border-white/10 rounded-full px-3 py-1 flex items-center gap-2 backdrop-blur-md">
            <Search className="w-3 h-3 text-white/40 shrink-0" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search nodes..."
              className="bg-transparent text-xs text-white/80 placeholder-white/30 focus:outline-none w-28"
            />
            {search && (
              <button onClick={() => { setSearch(""); setHighlightIds(new Set()); setHighlightLinks(new Set()); }}>
                <X className="w-3 h-3 text-white/40 hover:text-white" />
              </button>
            )}
          </div>

          {/* Toggle labels */}
          <button
            onClick={() => setShowLabels(v => !v)}
            className="bg-black/80 border border-white/10 text-white/40 hover:text-white text-[10px] px-2.5 py-1.5 rounded-full backdrop-blur-md transition-colors flex items-center gap-1"
            title="Toggle labels"
          >
            {showLabels ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
            <span className="hidden sm:inline font-mono">Labels</span>
          </button>

          {/* Zoom to fit */}
          <button
            onClick={() => graphRef.current?.fitView && graphRef.current.fitView(500)}
            className="bg-black/80 border border-white/10 text-white/40 hover:text-white text-[10px] px-2.5 py-1.5 rounded-full backdrop-blur-md transition-colors flex items-center gap-1"
          >
            <ZoomIn className="w-3 h-3" />
          </button>

          {(selectedNode || highlightIds.size > 0) && (
            <button
              onClick={clearSelection}
              className="bg-[#F76902]/20 border border-[#F76902]/30 text-[#F76902] hover:bg-[#F76902]/30 text-[10px] px-3 py-1.5 rounded-full backdrop-blur-md transition-colors font-mono"
            >
              Reset
            </button>
          )}
        </div>

        {/* Legend */}
        <div className="absolute bottom-3 left-3 z-10 flex flex-col gap-1.5">
          <div className="bg-black/80 border border-white/10 p-2.5 rounded-xl backdrop-blur-md flex flex-col gap-1.5">
            {[
              { color: "#F76902", label: `Faculty (${stats.faculty})`,  dot: true },
              { color: "#4ec5f1", label: `Papers (${stats.papers})`,    dot: true },
              { color: "#a78bfa", label: `Concepts (${stats.concepts})`,dot: true },
            ].map(s => (
              <div key={s.label} className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: s.color }} />
                <span className="text-[10px] font-mono text-white/50">{s.label}</span>
              </div>
            ))}
            <div className="border-t border-white/10 pt-1 mt-0.5 flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <div className="h-0.5 w-6 rounded shrink-0" style={{ backgroundColor: "rgba(236, 72, 153, 0.8)" }} />
                <span className="text-[10px] font-mono text-white/40">Co-authored</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-0.5 w-6 rounded shrink-0" style={{ backgroundColor: "rgba(78, 197, 241, 0.4)" }} />
                <span className="text-[10px] font-mono text-white/40">Authored</span>
              </div>
            </div>
            <div className="border-t border-white/10 pt-1 text-[10px] font-mono text-white/30">
              {stats.edges} connections
            </div>
          </div>
        </div>

        {loading ? (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-white/30 text-sm flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-[#F76902] border-t-transparent rounded-full animate-spin" />
              Building graph...
            </span>
          </div>
        ) : (
          <CosmographWrapper
            ref={graphRef}
            className="w-full h-full"
            points={graphData.nodes}
            links={graphData.links}
            pointIdBy="id"
            pointIndexBy="index"
            linkSourceBy="source"
            linkTargetBy="target"
            linkSourceIndexBy={"sourceIndex" as any}
            linkTargetIndexBy={"targetIndex" as any}
            pointLabelBy="label"
            pointColorBy="color"
            pointSizeBy="size"
            linkColorBy="color"
            linkWidthBy="width"
            showDynamicLabels={showLabels}
            onClick={(index: number | undefined) => {
              if (index !== undefined && graphData.nodes[index]) {
                handleNodeClick(graphData.nodes[index]);
              } else {
                clearSelection();
              }
            }}
            simulationRepulsion={2}
            simulationLinkDistance={5}
            simulationFriction={0.5}
            fitViewOnInit={true}
          />
        )}
      </div>

      {/* Detail panel */}
      {selectedNode && (
        <div
          className="border-l border-white/10 bg-[#0e0e0e] overflow-y-auto shrink-0 flex flex-col"
          style={{ width: panelWidth }}
        >
          {/* Header */}
          <div className="p-4 border-b border-white/10 flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: NODE_COLORS[(selectedNode.type||"").toLowerCase()] || "#fff" }}
                />
                <span className="text-[10px] uppercase tracking-widest font-mono text-white/40">
                  {selectedNode.type}
                </span>
              </div>
              <p className="text-sm font-bold text-white leading-tight break-words">
                {selectedNode.label || selectedNode.name || selectedNode.id}
              </p>
              {selectedNode.dept && (
                <p className="text-[10px] text-[#F76902]/70 mt-1">{selectedNode.dept}</p>
              )}
              {selectedNode.year && (
                <p className="text-[10px] text-white/30 mt-1">Year: {selectedNode.year}</p>
              )}
            </div>
            <button onClick={clearSelection} className="text-white/30 hover:text-white shrink-0 mt-0.5">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-4 space-y-4 text-xs">
            {/* Connections summary */}
            <div className="bg-white/5 rounded-lg p-2.5 flex flex-wrap gap-3">
              {selectedNeighbors.faculty.length > 0 && (
                <div className="text-center">
                  <div className="text-lg font-bold text-[#F76902]">{selectedNeighbors.faculty.length}</div>
                  <div className="text-[10px] text-white/40 font-mono">faculty</div>
                </div>
              )}
              {selectedNeighbors.papers.length > 0 && (
                <div className="text-center">
                  <div className="text-lg font-bold text-[#4ec5f1]">{selectedNeighbors.papers.length}</div>
                  <div className="text-[10px] text-white/40 font-mono">papers</div>
                </div>
              )}
              {selectedNeighbors.concepts.length > 0 && (
                <div className="text-center">
                  <div className="text-lg font-bold text-[#a78bfa]">{selectedNeighbors.concepts.length}</div>
                  <div className="text-[10px] text-white/40 font-mono">concepts</div>
                </div>
              )}
            </div>

            {/* Relationship types */}
            {selectedNeighbors.links.length > 0 && (
              <div>
                <p className="text-[10px] text-white/30 uppercase tracking-widest mb-1.5 font-mono">Relationships</p>
                <div className="flex flex-wrap gap-1">
                  {Array.from(new Set(selectedNeighbors.links.map(l => l.type || "RELATED"))).map(t => (
                    <span key={t} className="text-[10px] px-2 py-0.5 rounded-full font-mono border"
                      style={{ borderColor: LINK_COLORS[t.toUpperCase()]?.replace(/[\d.]+\)$/, "0.5)") || "rgba(255,255,255,0.2)", color: LINK_COLORS[t.toUpperCase()]?.replace(/[\d.]+\)$/, "0.8)") || "rgba(255,255,255,0.6)" }}>
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Faculty neighbors */}
            {selectedNeighbors.faculty.length > 0 && (
              <div>
                <p className="text-[#F76902] uppercase tracking-widest text-[10px] mb-2 flex items-center gap-1 font-mono">
                  <Users className="w-3 h-3" /> Faculty
                </p>
                <ul className="space-y-1">
                  {selectedNeighbors.faculty.slice(0, 10).map(n => (
                    <li
                      key={n.id}
                      className="text-white/60 flex items-center gap-1.5 cursor-pointer hover:text-white transition-colors text-[11px]"
                      onClick={() => handleNodeClick(n)}
                    >
                      <ChevronRight className="w-3 h-3 shrink-0 text-[#F76902]/40" />
                      <span className="truncate">{n.label || n.name || n.id}</span>
                    </li>
                  ))}
                  {selectedNeighbors.faculty.length > 10 && (
                    <li className="text-white/25 text-[10px]">+{selectedNeighbors.faculty.length - 10} more</li>
                  )}
                </ul>
              </div>
            )}

            {/* Paper neighbors */}
            {selectedNeighbors.papers.length > 0 && (
              <div>
                <p className="text-[#4ec5f1] uppercase tracking-widest text-[10px] mb-2 flex items-center gap-1 font-mono">
                  <FileText className="w-3 h-3" /> Papers
                </p>
                <ul className="space-y-1">
                  {selectedNeighbors.papers.slice(0, 8).map(n => (
                    <li
                      key={n.id}
                      className="text-white/60 flex items-center gap-1.5 cursor-pointer hover:text-white transition-colors text-[11px]"
                      onClick={() => handleNodeClick(n)}
                    >
                      <ChevronRight className="w-3 h-3 shrink-0 text-[#4ec5f1]/40" />
                      <span className="truncate">{n.label || n.name || n.id}</span>
                    </li>
                  ))}
                  {selectedNeighbors.papers.length > 8 && (
                    <li className="text-white/25 text-[10px]">+{selectedNeighbors.papers.length - 8} more</li>
                  )}
                </ul>
              </div>
            )}

            {/* Concept neighbors */}
            {selectedNeighbors.concepts.length > 0 && (
              <div>
                <p className="text-[#a78bfa] uppercase tracking-widest text-[10px] mb-2 flex items-center gap-1 font-mono">
                  <Tag className="w-3 h-3" /> Concepts
                </p>
                <div className="flex flex-wrap gap-1">
                  {selectedNeighbors.concepts.slice(0, 15).map(n => (
                    <span
                      key={n.id}
                      className="bg-[#a78bfa]/10 border border-[#a78bfa]/25 text-[#a78bfa]/80 px-2 py-0.5 rounded-full text-[10px] truncate max-w-[120px] cursor-pointer hover:bg-[#a78bfa]/20 transition-colors"
                      onClick={() => handleNodeClick(n)}
                    >
                      {n.label || n.name || n.id}
                    </span>
                  ))}
                  {selectedNeighbors.concepts.length > 15 && (
                    <span className="text-white/25 text-[10px] self-center">+{selectedNeighbors.concepts.length - 15}</span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
