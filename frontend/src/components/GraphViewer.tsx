"use client";

import { useEffect, useState, useRef } from "react";
import dynamic from "next/dynamic";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://192.168.0.8:8000";
import { Network } from "lucide-react";

// Safe dynamic import for browser-only react-force-graph
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

export default function GraphViewer() {
  const [data, setData] = useState<{ nodes: any[]; links: any[] }>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>();
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/graph`);
        setData(res.data);
        
        // Auto-center after load
        setTimeout(() => {
          graphRef.current?.zoomToFit(400, 20);
        }, 500);
      } catch (err) {
        console.error("Failed to load graph", err);
      } finally {
        setLoading(false);
      }
    };
    fetchGraph();
  }, []);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      if (entries[0]) {
        setDimensions({
          width: entries[0].contentRect.width,
          height: entries[0].contentRect.height,
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="h-full bg-[#0a0a0a] rounded-xl overflow-hidden relative border border-white/5 shadow-inner" ref={containerRef}>
      <div className="absolute top-4 left-4 z-10 bg-black/60 border border-white/10 px-3 py-1.5 rounded-full flex items-center gap-2 backdrop-blur-md">
         <Network className="w-4 h-4 text-[#4ec5f1]" />
         <span className="text-xs font-mono text-white/80">Knowledge Graph View</span>
      </div>
      
      {loading ? (
        <div className="w-full h-full flex items-center justify-center">
            <span className="text-white/30 text-sm animate-pulse flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-[#4ec5f1] border-t-transparent rounded-full animate-spin" />
                Initializing Matrix...
            </span>
        </div>
      ) : (
        <div className="w-full h-full">
            <ForceGraph2D
            ref={graphRef}
            width={dimensions.width}
            height={dimensions.height}
            graphData={data}
            nodeLabel={(node: any) => node?.name || node?.label || node?.id || "Unknown"}
            nodeColor={(node: any) => {
                const t = node.type?.toLowerCase() || "";
                if (t.includes("faculty")) return "#4ec5f1"; // Neon blue
                if (t.includes("paper")) return "#ffe81f"; // Neon yellow
                if (t.includes("topic")) return "#ff0055"; // Neon Red/Pink
                return "#ffffff";
            }}
            nodeRelSize={6}
            linkColor={() => "rgba(255,255,255,0.15)"}
            backgroundColor="#0a0a0a"
            enableNodeDrag={true}
            enablePanInteraction={true}
            enableZoomInteraction={true}
            />
        </div>
      )}
    </div>
  );
}
