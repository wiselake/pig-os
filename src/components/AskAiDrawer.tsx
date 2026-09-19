"use client";

import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslations, useLocale } from "next-intl";
import { Sparkles, X, Pin } from "lucide-react";
import { chatApi } from "@/lib/api/endpoints/chat";
import { useAuthStore } from "@/store/auth.store";
import type { ChatQuery, ChatResponse } from "@/types/api.types";
import type { Locale } from "@/i18n/config";

interface AskAiDrawerProps {
  open: boolean;
  onClose: () => void;
  context?: string | null;
  lang?: Locale;   // 하위호환용(라벨·응답 로케일은 next-intl 사용, 파일 단일소스)
}

// 라벨은 messages/*.json 의 askAi 네임스페이스(파일 단일소스, 인라인 제거).
type Msg = { role: "user"; text: string } | { role: "ai"; response: ChatResponse };

export function AskAiDrawer({ open, onClose, context }: AskAiDrawerProps) {
  const t = useTranslations("askAi");
  const locale = useLocale();
  const farmId = useAuthStore((s) => s.activeFarmId);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  const mutation = useMutation({
    // 백엔드 챗은 8개 로케일(ru 포함) 모두 지원 → UI 로케일 그대로 전송.
    mutationFn: (q: string) =>
      chatApi.query(farmId!, { question: q, locale: locale as ChatQuery["locale"] }),
    onSuccess: (data) => setMessages((p) => [...p, { role: "ai", response: data }]),
    onError: () => setMessages((p) => [...p, {
      role: "ai",
      response: { intent: "error", severity: "CRITICAL", answer: t("errorMsg"), findings: [], farm_id: farmId ?? "", as_of: "", renderer: "template" },
    }]),
  });

  const send = (text: string) => {
    if (!text.trim() || !farmId || mutation.isPending) return;
    setMessages((p) => [...p, { role: "user", text }]);
    setInput("");
    mutation.mutate(text);
  };

  const header = t("header"), subtitle = t("subtitle"), placeholder = t("placeholder");
  const suggested = t.raw("suggested") as string[];

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div className="fixed inset-0 bg-black/20 z-[90] md:bg-transparent" onClick={onClose} />
      )}

      {/* Drawer */}
      <div
        className={`fixed top-0 right-0 h-full w-full md:w-[380px] bg-surface border-l border-border z-[100] flex flex-col shadow-2xl transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center text-white"
              style={{ background: "linear-gradient(135deg,#123A2A,#178A5A)" }}>
              <Sparkles size={14} />
            </div>
            <div>
              <div className="text-sm font-bold text-text">{header}</div>
              <div className="text-[10px] text-muted">{subtitle}</div>
            </div>
          </div>
          <button onClick={onClose} className="w-7 h-7 rounded-full bg-bg2 flex items-center justify-center text-muted hover:text-text transition">
            <X size={14} aria-hidden />
          </button>
        </div>

        {/* Context chip */}
        {context && (
          <div className="px-4 pt-3">
            <span className="inline-flex items-center gap-1.5 text-[11px] bg-primary-soft text-primary px-2.5 py-1 rounded-full font-medium">
              <Pin size={12} aria-hidden />{context}
            </span>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
          {messages.length === 0 && (
            <div className="space-y-2 mt-2">
              <p className="text-xs text-muted font-medium">{t("suggestedLabel")}</p>
              {suggested.map((q) => (
                <button
                  key={q}
                  onClick={() => send(q)}
                  className="w-full text-left px-3 py-2 rounded-lg border border-border bg-bg text-xs text-text2 hover:bg-bg2 hover:border-primary transition"
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {messages.map((msg, i) =>
            msg.role === "user" ? (
              <div key={i} className="flex justify-end">
                <div className="bg-navy text-white rounded-2xl rounded-tr-sm px-3 py-2 text-xs max-w-[80%]">
                  {msg.text}
                </div>
              </div>
            ) : (
              <div key={i} className="flex justify-start">
                <div className="bg-bg2 border border-border rounded-2xl rounded-tl-sm px-3 py-2.5 text-xs max-w-[90%]">
                  <p className="text-text leading-relaxed">{msg.response.answer}</p>
                  {msg.response.findings.slice(0, 2).map((f, j) => (
                    <div key={j} className="mt-2 pt-2 border-t border-border">
                      <span className="font-mono font-bold text-primary">{f.kpi}</span>
                      {f.current_value != null && (
                        <span className="text-muted ml-1">{f.current_value.toFixed(1)} / {f.target_value?.toFixed(1) ?? "-"}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )
          )}

          {mutation.isPending && (
            <div className="flex gap-1 items-center text-muted text-xs">
              <span className="w-1.5 h-1.5 bg-muted rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-1.5 h-1.5 bg-muted rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-1.5 h-1.5 bg-muted rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-3 border-t border-border flex-shrink-0">
          <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={placeholder}
              disabled={mutation.isPending}
              className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 text-xs outline-none focus:border-primary transition"
            />
            <button
              type="submit"
              disabled={!input.trim() || mutation.isPending || !farmId}
              className="bg-navy text-white px-3 py-2 rounded-lg text-xs font-semibold disabled:opacity-40 hover:bg-primary transition"
            >
              ↑
            </button>
          </form>
        </div>
      </div>
    </>
  );
}
