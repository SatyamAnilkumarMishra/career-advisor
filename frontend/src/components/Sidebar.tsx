'use client';

import React from 'react';
import { HistoryItem } from '@/types';
import {
  Compass,
  MessageCircle,
  FileText,
  Target,
  Map,
  Briefcase,
  Trash2,
  X,
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  activeView: 'chat' | 'resume' | 'skillgap' | 'roadmap' | 'matcher';
  onSelectView: (view: 'chat' | 'resume' | 'skillgap' | 'roadmap' | 'matcher') => void;
  searchHistory: HistoryItem[];
  onSelectHistory: (query: string) => void;
  onDeleteHistory: (e: React.MouseEvent, id: string) => void;
  onClearConversation: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  activeView,
  onSelectView,
  searchHistory,
  onSelectHistory,
  onDeleteHistory,
  onClearConversation,
}) => {
  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && <div className="sidebar-backdrop" onClick={onClose} aria-hidden="true" />}

      <aside className={`app-sidebar ${isOpen ? 'open' : ''}`}>
        {/* Brand Header */}
        <div className="sidebar-brand-header">
          <div className="brand-logo-container">
            <div className="brand-logo-gold">
              <Compass size={22} color="#080808" strokeWidth={2.2} />
            </div>
            <h1 className="brand-logo-text">Career Advisor</h1>
          </div>
          <button className="sidebar-close-btn" onClick={onClose} aria-label="Close sidebar">
            <X size={18} />
          </button>
        </div>

        {/* Section 1: WORKSPACE */}
        <div className="sidebar-section">
          <div className="sidebar-section-title">WORKSPACE</div>
          <div className="sidebar-nav-items">
            <button
              className={`sidebar-nav-item ${activeView === 'chat' ? 'active' : ''}`}
              onClick={() => {
                onSelectView('chat');
                onClose();
              }}
            >
              <MessageCircle size={18} className="nav-icon" />
              <span>Chat</span>
            </button>
          </div>
        </div>

        {/* Section 2: CAREER TOOLS */}
        <div className="sidebar-section">
          <div className="sidebar-section-title">CAREER TOOLS</div>
          <div className="sidebar-nav-items">
            <button
              className={`sidebar-nav-item ${activeView === 'resume' ? 'active' : ''}`}
              onClick={() => {
                onSelectView('resume');
                onClose();
              }}
            >
              <FileText size={18} className="nav-icon" />
              <span>Resume Analyzer</span>
            </button>
            <button
              className={`sidebar-nav-item ${activeView === 'skillgap' ? 'active' : ''}`}
              onClick={() => {
                onSelectView('skillgap');
                onClose();
              }}
            >
              <Target size={18} className="nav-icon" />
              <span>Skill Gap Analyzer</span>
            </button>
            <button
              className={`sidebar-nav-item ${activeView === 'roadmap' ? 'active' : ''}`}
              onClick={() => {
                onSelectView('roadmap');
                onClose();
              }}
            >
              <Map size={18} className="nav-icon" />
              <span>Learning Roadmap</span>
            </button>
            <button
              className={`sidebar-nav-item ${activeView === 'matcher' ? 'active' : ''}`}
              onClick={() => {
                onSelectView('matcher');
                onClose();
              }}
            >
              <Briefcase size={18} className="nav-icon" />
              <span>Job Matcher</span>
            </button>
          </div>
        </div>

        <div className="sidebar-hairline-divider" />

        {/* Section 3: SEARCH HISTORY - No default mock values */}
        <div className="sidebar-section search-history-section">
          <div className="sidebar-section-title">SEARCH HISTORY</div>
          <div className="history-list-container">
            {searchHistory && searchHistory.length > 0 ? (
              searchHistory.map((item) => (
                <div
                  key={item.id}
                  className="history-list-item"
                  onClick={() => {
                    onSelectHistory(item.query);
                    onClose();
                  }}
                  title={item.query}
                >
                  <span className="history-gold-dot" />
                  <span className="history-query-text">{item.query}</span>

                  <button
                    className="history-delete-btn"
                    onClick={(e) => onDeleteHistory(e, item.id)}
                    title="Delete chat"
                    aria-label="Delete chat"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            ) : (
              <div className="history-empty-message">
                No recent searches
              </div>
            )}
          </div>
        </div>

        <div className="sidebar-hairline-divider" />

        {/* Footer: Clear conversation */}
        <div className="sidebar-footer-area">
          <button className="clear-conversation-btn" onClick={onClearConversation}>
            <Trash2 size={16} />
            <span>Clear conversation</span>
          </button>
        </div>
      </aside>
    </>
  );
};
