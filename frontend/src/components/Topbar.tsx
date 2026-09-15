'use client';

import React from 'react';
import { ActiveView } from '@/types';
import { Sparkles } from 'lucide-react';

interface TopbarProps {
  activeView: ActiveView;
  modelName: string;
}

export const Topbar: React.FC<TopbarProps> = ({ activeView, modelName }) => {
  const getHeader = () => {
    switch (activeView) {
      case 'chat':
        return {
          badge: '✦ Instant AI Career Intelligence',
          title: 'Your career. Strategically planned.',
          subtitle:
            "I'm your AI career agent. Ask questions, get document-grounded advice, analyze your resume, and discover verified career roadmaps.",
        };
      case 'resume':
        return {
          badge: '📄 Intelligent Resume Parser',
          title: 'Automated Resume Intelligence',
          subtitle:
            'Upload your PDF, DOCX, or TXT resume to extract verified skills, strengths, improvement areas, and tailored target roles.',
        };
      case 'skillgap':
        return {
          badge: '🎯 Precision Skill Matrix',
          title: 'Skill Gap & Readiness Evaluation',
          subtitle:
            'Compare your existing skill set directly against the modern industry requirements for your dream job role.',
        };
      case 'roadmap':
        return {
          badge: '🧭 Milestone Progression System',
          title: 'Custom Learning Roadmap Generator',
          subtitle:
            'Generate a step-by-step milestone curriculum with concrete learning actions and focus skill targets.',
        };
      case 'jobs':
        return {
          badge: '💼 Real-Time Job Matcher',
          title: 'Live Opportunities & Job Matching',
          subtitle:
            'Explore live job listings and verified positions matched to your target role, skill set, and experience level.',
        };
    }
  };

  const header = getHeader();

  return (
    <header style={{ marginBottom: '26px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
        }}
      >
        <div className="status-indicator">
          <span className="status-dot" />
          <span style={{ fontWeight: 600, color: '#ffffff' }}>CareerAI Agent</span>
          <span>·</span>
          <span style={{ color: 'var(--neon-cyan)' }}>Online</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>ENGINE:</span>
          <span className="badge badge-info" style={{ fontSize: '11.5px', fontWeight: 700 }}>
            <Sparkles size={11} /> {modelName || 'AI Engine'}
          </span>
        </div>
      </div>

      <div
        style={{
          background: 'rgba(18, 14, 38, 0.65)',
          border: '1px solid var(--border-violet)',
          borderRadius: '20px',
          padding: '24px 28px',
          backdropFilter: 'blur(16px)',
          boxShadow: '0 8px 32px rgba(139, 92, 246, 0.15)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: '15%',
            right: '15%',
            height: '1px',
            background: 'linear-gradient(90deg, transparent, var(--neon-lavender), transparent)',
          }}
        />
        <div style={{ display: 'inline-flex', marginBottom: '10px' }}>
          <span className="badge badge-cyan" style={{ fontSize: '11.5px', fontWeight: 700 }}>
            {header.badge}
          </span>
        </div>
        <h2
          style={{
            fontSize: '24px',
            fontWeight: 800,
            color: '#ffffff',
            letterSpacing: '-0.02em',
            marginBottom: '6px',
          }}
        >
          {header.title}
        </h2>
        <p style={{ fontSize: '14px', color: 'var(--text-dim)', maxWidth: '820px', lineHeight: 1.5 }}>
          {header.subtitle}
        </p>
      </div>
    </header>
  );
};
