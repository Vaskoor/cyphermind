'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import { Bot, Loader2, Send, Trash2, User } from 'lucide-react';
import { chatApi, getErrorMessage } from '@/lib/api';
import type { ChatMessage } from '@/lib/types';

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Hello! I\'m CypherMind AI. I can help with threat modeling, vulnerability analysis, security best practices, and interpreting findings. How can I assist you today?',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError('');

    try {
      const { reply, toolCalls, citations } = await chatApi.send(userMessage.content, messages.map(m => ({ role: m.role, content: m.content })));
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: reply,
          timestamp: new Date().toISOString(),
          toolCalls,
          citations,
        },
      ]);
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'system',
          content: `Error: ${msg}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content: 'Chat cleared. How can I help you?',
        timestamp: new Date().toISOString(),
      },
    ]);
    setError('');
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">AI Security Chat</h1>
          <p className="mt-1 text-sm text-muted">
            Tool-augmented copilot — web search, CVE lookup, HTTP probe, knowledge base
          </p>
        </div>
        <button
          onClick={clearChat}
          className="flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-muted transition-colors hover:border-danger/30 hover:text-danger"
        >
          <Trash2 className="h-4 w-4" />
          Clear
        </button>
      </div>

      <div className="flex flex-1 flex-col overflow-hidden rounded-xl border border-border bg-surface">
        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
            >
              <div
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-accent/20'
                    : msg.role === 'system'
                      ? 'bg-danger/20'
                      : 'bg-success/20'
                }`}
              >
                {msg.role === 'user' ? (
                  <User className="h-4 w-4 text-accent" />
                ) : (
                  <Bot className={`h-4 w-4 ${msg.role === 'system' ? 'text-danger' : 'text-success'}`} />
                )}
              </div>
              <div
                className={`max-w-[75%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-accent text-white'
                    : msg.role === 'system'
                      ? 'border border-danger/30 bg-danger/10 text-danger'
                      : 'border border-border bg-background text-white'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.toolCalls && msg.toolCalls.length > 0 && (
                  <details className="mt-2 text-xs opacity-80">
                    <summary>{msg.toolCalls.length} tool call(s)</summary>
                    <pre className="mt-1 max-h-32 overflow-auto text-[10px]">{JSON.stringify(msg.toolCalls, null, 2)}</pre>
                  </details>
                )}
                <p className="mt-1.5 text-xs opacity-50">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-success/20">
                <Bot className="h-4 w-4 text-success" />
              </div>
              <div className="flex items-center gap-2 rounded-xl border border-border bg-background px-4 py-3">
                <Loader2 className="h-4 w-4 animate-spin text-accent" />
                <span className="text-sm text-muted">Thinking...</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {error && (
          <div className="border-t border-border px-5 py-2 text-xs text-danger">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="border-t border-border p-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about security vulnerabilities, CWEs, remediation..."
              className="flex-1"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-accent-hover"
            >
              <Send className="h-4 w-4" />
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
