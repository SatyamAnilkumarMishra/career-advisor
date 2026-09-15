'use client';

import React, { useEffect, useRef, useState } from 'react';
import { ChatMessage } from '@/types';
import { Mascot } from './Mascot';
import { MarkdownRenderer } from './MarkdownRenderer';
import { Send, Sparkles, BookOpen, ChevronDown, ChevronUp, Bot, User } from 'lucide-react';

interface ChatViewProps {
  messages: ChatMessage[];
  onSendMessage: (text: string) => Promise<void>;
  isLoading: boolean;
  targetRole: string;
}

export const ChatView: React.FC<ChatViewProps> = ({
  messages,
  onSendMessage,
  isLoading,
  targetRole,
}) => {
  const [inputVal, setInputVal] = useState('');
  const [expandedSources, setExpandedSources] = useState<{ [key: number]: boolean }>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputVal.trim() || isLoading) return;
    const text = inputVal;
    setInputVal('');
    onSendMessage(text);
  };

  const toggleSource = (idx: number) => {
    setExpandedSources((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const quickActions = [
    {
      icon: '📄',
      title: 'Analyze my resume',
      desc: 'Extract key skills, strengths & growth areas',
      prompt: 'Analyze my resume and provide actionable career feedback.',
    },
    {
      icon: '🎯',
      title: 'Find my skill gaps',
      desc: `See what you're missing for ${targetRole}`,
      prompt: `Identify the critical skill gaps required to succeed as a ${targetRole}.`,
    },
    {
      icon: '🧭',
      title: 'Build my roadmap',
      desc: 'Create a structured 6-month learning curriculum',
      prompt: `Generate a structured, milestone-based learning roadmap for ${targetRole}.`,
    },
    {
      icon: '💼',
      title: 'Match me with jobs',
      desc: 'Discover live matching job openings',
      prompt: `What types of jobs and companies are best suited for an aspiring ${targetRole}?`,
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Quick Action Cards when empty */}
      {messages.length === 0 && (
        <div style={{ marginBottom: '24px' }}>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '14px',
              marginBottom: '20px',
            }}
          >
            {quickActions.map((qa, i) => (
              <div
                key={i}
                className="card"
                onClick={() => onSendMessage(qa.prompt)}
                style={{ cursor: 'pointer' }}
              >
                <div>
                  <span style={{ fontSize: '24px', display: 'block', marginBottom: '8px' }}>
                    {qa.icon}
                  </span>
                  <strong style={{ fontSize: '14px', color: '#ffffff', display: 'block', marginBottom: '4px' }}>
                    {qa.title}
                  </strong>
                  <p style={{ fontSize: '12px', color: 'var(--text-dim)', lineHeight: 1.4 }}>
                    {qa.desc}
                  </p>
                </div>
                <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'flex-end' }}>
                  <span
                    style={{
                      fontSize: '11.5px',
                      color: 'var(--neon-cyan)',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    Ask <Sparkles size={11} />
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Messages Feed */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '16px' }}>
        {messages.map((msg, idx) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={idx}
              style={{
                display: 'flex',
                gap: '12px',
                alignItems: 'flex-start',
                alignSelf: isUser ? 'flex-end' : 'flex-start',
                maxWidth: '85%',
              }}
            >
              {!isUser && (
                <div
                  style={{
                    width: '34px',
                    height: '34px',
                    borderRadius: '10px',
                    background: 'var(--grad-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    boxShadow: '0 4px 12px rgba(139, 92, 246, 0.3)',
                  }}
                >
                  <Bot size={18} color="#ffffff" />
                </div>
              )}

              <div
                style={{
                  backgroundColor: isUser ? 'rgba(139, 92, 246, 0.22)' : 'rgba(22, 18, 48, 0.85)',
                  border: isUser
                    ? '1px solid var(--border-violet-strong)'
                    : '1px solid var(--border-violet)',
                  borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                  padding: '14px 18px',
                  backdropFilter: 'blur(12px)',
                  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.2)',
                }}
              >
                <div
                  style={{
                    fontSize: '14px',
                    lineHeight: '1.6',
                    color: '#ffffff',
                  }}
                >
                  <MarkdownRenderer content={msg.content} />
                </div>

                {/* Sources Section if RAG retrieval was used */}
                {msg.sources && msg.sources.length > 0 && (
                  <div
                    style={{
                      marginTop: '12px',
                      paddingTop: '10px',
                      borderTop: '1px solid rgba(168, 85, 247, 0.15)',
                    }}
                  >
                    <button
                      onClick={() => toggleSource(idx)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--neon-cyan)',
                        fontSize: '12px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: 0,
                      }}
                    >
                      <BookOpen size={12} />
                      <span>{msg.sources.length} Verified Document Excerpt(s)</span>
                      {expandedSources[idx] ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                    </button>

                    {expandedSources[idx] && (
                      <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {msg.sources.map((s, sIdx) => (
                          <div
                            key={sIdx}
                            style={{
                              backgroundColor: 'rgba(10, 7, 20, 0.6)',
                              border: '1px solid rgba(34, 211, 238, 0.2)',
                              borderRadius: '8px',
                              padding: '8px 12px',
                              fontSize: '12px',
                            }}
                          >
                            <div
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                color: 'var(--neon-lavender)',
                                fontWeight: 600,
                                marginBottom: '4px',
                              }}
                            >
                              <span>{s.page !== undefined && s.page !== null ? `Page ${s.page}` : 'Document Excerpt'}</span>
                              <span style={{ color: 'var(--text-faint)', fontSize: '11px' }}>
                                Score: {s.relevance_score?.toFixed(2)}
                              </span>
                            </div>
                            <p style={{ color: 'var(--text-dim)', fontStyle: 'italic', margin: 0 }}>
                              &ldquo;{s.content}&rdquo;
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {msg.timestamp && (
                  <div
                    style={{
                      fontSize: '10.5px',
                      color: 'var(--text-faint)',
                      textAlign: 'right',
                      marginTop: '6px',
                    }}
                  >
                    {msg.timestamp}
                  </div>
                )}
              </div>

              {isUser && (
                <div
                  style={{
                    width: '34px',
                    height: '34px',
                    borderRadius: '10px',
                    background: 'rgba(255, 255, 255, 0.08)',
                    border: '1px solid var(--border-violet)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <User size={18} color="#ffffff" />
                </div>
              )}
            </div>
          );
        })}

        {isLoading && (
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '10px',
                background: 'var(--grad-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Bot size={18} color="#ffffff" />
            </div>
            <div
              style={{
                backgroundColor: 'rgba(22, 18, 48, 0.85)',
                border: '1px solid var(--border-violet)',
                borderRadius: '16px 16px 16px 4px',
                padding: '12px 18px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                color: 'var(--text-dim)',
                fontSize: '13.5px',
              }}
            >
              <span className="spinner" />
              <span>Generating response...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Animated Mascot is explicitly rendered in the Chat view */}
      <Mascot statusText={isLoading ? 'Generating response...' : 'Listening for your goal'} />

      {/* Input Bar */}
      <form onSubmit={handleSubmit} style={{ marginTop: 'auto', position: 'relative' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            backgroundColor: 'rgba(18, 14, 40, 0.95)',
            border: '1px solid var(--border-violet-strong)',
            borderRadius: '14px',
            padding: '6px 8px 6px 16px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
          }}
        >
          <input
            type="text"
            className="form-input"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="Ask me anything about your career..."
            style={{
              background: 'transparent',
              border: 'none',
              boxShadow: 'none',
              padding: '8px 0',
              fontSize: '14.5px',
            }}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!inputVal.trim() || isLoading}
            className="btn btn-primary"
            style={{ padding: '8px 16px', borderRadius: '10px' }}
          >
            <Send size={15} />
            <span>Send</span>
          </button>
        </div>
      </form>
    </div>
  );
};
