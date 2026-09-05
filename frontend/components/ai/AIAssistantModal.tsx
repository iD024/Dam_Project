"use client";

import React, { useState } from "react";
import { MessageSquare, Sparkles, Send, X, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";

interface AIAssistantProps {
  isOpen: boolean;
  onClose: () => void;
  simulationId?: string;
}

export default function AIAssistantModal({ isOpen, onClose, simulationId }: AIAssistantProps) {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Array<{ role: "user" | "assistant"; text: string; grounding?: any }>>([
    {
      role: "assistant",
      text: "I am the AI Hydroinformatics Assistant. My answers are strictly grounded in physical hydrodynamic simulation outputs and PostGIS impact analytics. What would you like to know about the dam-break scenario?",
    },
  ]);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const quickPrompts = [
    "Which villages flood within 30 minutes?",
    "What is the maximum water depth?",
    "How many kilometers of roads are inundated?",
    "What is the earliest flood arrival time?",
  ];

  const handleSend = async (textToSend?: string) => {
    const q = textToSend || query;
    if (!q.trim() || !simulationId) return;

    const userMsg = { role: "user" as const, text: q };
    setMessages((prev) => [...prev, userMsg]);
    setQuery("");
    setLoading(true);

    try {
      const res = await api.interpretResult(simulationId, q);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: res.answer,
          grounding: res.grounding_data,
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "Simulation data is currently being solved or unavailable. Please run the hydrodynamic model first.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-xl shadow-2xl flex flex-col h-[580px] overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-violet-600/20 text-violet-400 border border-violet-500/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">AI Decision-Support Assistant</h3>
              <p className="text-xs text-slate-400 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Deterministic Hydrodynamic Grounding
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Quick Prompts */}
        <div className="px-5 py-2.5 bg-slate-850 border-b border-slate-800/80 flex items-center gap-2 overflow-x-auto no-scrollbar">
          {quickPrompts.map((qp, i) => (
            <button
              key={i}
              onClick={() => handleSend(qp)}
              className="text-[11px] px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 whitespace-nowrap transition"
            >
              {qp}
            </button>
          ))}
        </div>

        {/* Messages Scroll Area */}
        <div className="flex-1 p-5 overflow-y-auto space-y-3.5 text-xs">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 leading-relaxed ${
                  m.role === "user"
                    ? "bg-sky-600 text-white rounded-br-none"
                    : "bg-slate-800 border border-slate-700/80 text-slate-200 rounded-bl-none shadow-md"
                }`}
              >
                {m.text}
              </div>

              {m.grounding && Object.keys(m.grounding).length > 0 && (
                <div className="mt-1.5 p-2 rounded-lg bg-slate-950 border border-slate-800 text-[10px] text-slate-400 max-w-[85%] font-mono">
                  <div className="font-bold text-sky-400 mb-0.5">Physical Verification Evidence:</div>
                  <pre className="overflow-x-auto whitespace-pre-wrap">{JSON.stringify(m.grounding, null, 2)}</pre>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-2 text-slate-400 text-xs italic">
              <Sparkles className="w-4 h-4 animate-spin text-violet-400" />
              Querying simulation database & PostGIS spatial assets...
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="p-3.5 border-t border-slate-800 bg-slate-950/60 flex items-center gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask anything about the flood wave, villages, or velocity..."
            className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
          <button
            onClick={() => handleSend()}
            disabled={!query.trim() || loading}
            className="p-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white transition disabled:opacity-40"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
