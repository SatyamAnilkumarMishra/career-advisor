import React from 'react';
import { Brain, Menu, LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

interface HeaderProps {
  onOpenSidebar: () => void;
  statusText?: string;
}

export const Header: React.FC<HeaderProps> = ({ onOpenSidebar, statusText = 'Online' }) => {
  const { user, logout } = useAuth();

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

      <div className="header-right" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div className="career-intelligence-badge">
          <Brain size={17} className="badge-icon" />
          <span className="badge-text">Career Intelligence</span>
        </div>

        {user && (
          <div className="user-profile-header-pill" style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: '#161614',
            border: '1px solid #2B2B28',
            borderRadius: '9999px',
            padding: '4px 10px 4px 6px',
            fontSize: '12px',
          }}>
            {user.photoURL ? (
              <img
                src={user.photoURL}
                alt={user.displayName || 'User'}
                style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover' }}
              />
            ) : (
              <div style={{
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                backgroundColor: '#D6A936',
                color: '#0B0B0A',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 'bold',
                fontSize: '11px',
              }}>
                {(user.displayName || user.email || 'U').charAt(0).toUpperCase()}
              </div>
            )}
            <span style={{ color: '#E8E6E3', fontWeight: 500, maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user.displayName || user.email}
            </span>
            <button
              onClick={() => logout()}
              title="Sign Out"
              style={{
                background: 'none',
                border: 'none',
                color: '#8E8C85',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: '2px',
                marginLeft: '4px',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#E8BA3E')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#8E8C85')}
            >
              <LogOut size={14} />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
