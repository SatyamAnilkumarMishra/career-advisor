'use client';

import React from 'react';
import { Brain, Menu } from 'lucide-react';

interface HeaderProps {
  onOpenSidebar: () => void;
  statusText?: string;
}

export const Header: React.FC<HeaderProps> = ({ onOpenSidebar, statusText = 'Online' }) => {
  return (
    <header className="main-header">
      <div className="header-left">
        <button
          className="sidebar-mobile-toggle"
          onClick={onOpenSidebar}
          aria-label="Open navigation menu"
        >
          <Menu size={20} />
        </button>

        <div className="agent-status-indicator">
          <span className="gold-status-dot" />
          <span className="agent-title">CareerAI Agent</span>
          <span className="agent-dot-divider">•</span>
          <span className="agent-status-text">{statusText}</span>
        </div>
      </div>

      <div className="header-right">
        <div className="career-intelligence-badge">
          <Brain size={17} className="badge-icon" />
          <span className="badge-text">Career Intelligence</span>
        </div>
      </div>
    </header>
  );
};
