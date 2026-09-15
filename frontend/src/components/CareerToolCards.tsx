'use client';

import React from 'react';
import { FileText, Target, Map, Briefcase } from 'lucide-react';

interface CareerToolCardsProps {
  onSelectTool: (toolKey: 'resume' | 'skillgap' | 'roadmap' | 'matcher') => void;
}

export const CareerToolCards: React.FC<CareerToolCardsProps> = ({ onSelectTool }) => {
  const tools: {
    key: 'resume' | 'skillgap' | 'roadmap' | 'matcher';
    name: string;
    description: string;
    icon: React.ReactNode;
  }[] = [
    {
      key: 'resume',
      name: 'Resume Analyzer',
      description: 'Analyze your resume and get actionable insights.',
      icon: <FileText size={26} strokeWidth={1.8} />,
    },
    {
      key: 'skillgap',
      name: 'Skill Gap Analyzer',
      description: 'Identify skill gaps and get recommendations.',
      icon: <Target size={26} strokeWidth={1.8} />,
    },
    {
      key: 'roadmap',
      name: 'Learning Roadmap',
      description: 'Get a personalized roadmap to achieve your goals.',
      icon: <Map size={26} strokeWidth={1.8} />,
    },
    {
      key: 'matcher',
      name: 'Job Matcher',
      description: 'Find jobs that match your skills and preferences.',
      icon: <Briefcase size={26} strokeWidth={1.8} />,
    },
  ];

  return (
    <div className="career-tool-cards-grid">
      {tools.map((tool) => (
        <div
          key={tool.key}
          className="career-tool-card"
          onClick={() => onSelectTool(tool.key)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              onSelectTool(tool.key);
            }
          }}
        >
          <div className="tool-card-icon">{tool.icon}</div>
          <h3 className="tool-card-title">{tool.name}</h3>
          <p className="tool-card-desc">{tool.description}</p>
        </div>
      ))}
    </div>
  );
};
