'use client';

import React, { useState } from 'react';
import { ActiveView, RoadmapResult } from '@/types';
import { generateRoadmap, getErrorMessage } from '@/lib/api';
import { Map, Calendar, Sparkles, AlertCircle, Briefcase, ArrowRight } from 'lucide-react';

interface RoadmapViewProps {
  targetRole: string;
  userSkills: string[];
  result: RoadmapResult | null;
  onRoadmapGenerated: (res: RoadmapResult) => void;
  onTargetRoleChange: (role: string) => void;
  onNavigate?: (view: ActiveView) => void;
}

export const RoadmapView: React.FC<RoadmapViewProps> = ({
  targetRole,
  userSkills,
  result,
  onRoadmapGenerated,
  onTargetRoleChange,
  onNavigate,
}) => {
  const [roleInput, setRoleInput] = useState(targetRole || '');
  const [skillsInput, setSkillsInput] = useState(
    userSkills.length > 0 ? userSkills.join(', ') : ''
  );
  const [timeframe, setTimeframe] = useState<number>(6);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [completedActions, setCompletedActions] = useState<{ [key: string]: boolean }>({});

  const toggleAction = (key: string) => {
    setCompletedActions((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleGenerate = async () => {
    if (!roleInput.trim()) {
      setErrorMsg('Please specify a target role.');
      return;
    }
    const skills = skillsInput
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await generateRoadmap(skills, roleInput.trim(), timeframe);
      onTargetRoleChange(roleInput.trim());
      onRoadmapGenerated(res);
    } catch (err: unknown) {
      setErrorMsg(getErrorMessage(err, 'Failed to generate learning roadmap.'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="tool-card">
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
        <Map size={22} color="var(--neon-lavender)" />
        <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#ffffff' }}>Learning Roadmap Generator</h3>
      </div>
      <p style={{ fontSize: '13.5px', color: 'var(--text-dim)', marginBottom: '22px' }}>
        Generate a milestone-by-milestone curriculum tailored to bridge your specific skill gaps within your chosen timeframe.
      </p>

      {/* Form Controls */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '16px',
          marginBottom: '20px',
        }}
      >
        <div>
          <label className="form-label">Target Role</label>
          <input
            type="text"
            className="form-input"
            value={roleInput}
            onChange={(e) => setRoleInput(e.target.value)}
            placeholder="Enter the role"
          />
        </div>

        <div>
          <label className="form-label">Current Skills (comma-separated)</label>
          <input
            type="text"
            className="form-input"
            value={skillsInput}
            onChange={(e) => setSkillsInput(e.target.value)}
            placeholder="Enter skills"
          />
        </div>

        <div>
          <label className="form-label">Timeframe (Months)</label>
          <select
            className="form-select"
            value={timeframe}
            onChange={(e) => setTimeframe(Number(e.target.value))}
          >
            <option value={3}>3 Months (Accelerated)</option>
            <option value={6}>6 Months (Standard)</option>
            <option value={9}>9 Months (Comprehensive)</option>
            <option value={12}>12 Months (Deep-Dive)</option>
          </select>
        </div>
      </div>

      <button
        onClick={handleGenerate}
        disabled={isLoading}
        className="btn btn-primary"
        style={{ width: '100%', padding: '12px', fontSize: '15px', marginBottom: '24px' }}
      >
        {isLoading ? (
          <>
            <span className="spinner" /> Generating response...
          </>
        ) : (
          <>
            <Sparkles size={16} /> Generate Customized Roadmap
          </>
        )}
      </button>

      {errorMsg && (
        <div
          style={{
            backgroundColor: 'rgba(244, 63, 94, 0.12)',
            border: '1px solid var(--rose)',
            borderRadius: '10px',
            padding: '12px 16px',
            color: '#fecdd3',
            fontSize: '13.5px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '20px',
          }}
        >
          <AlertCircle size={16} color="var(--rose)" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Roadmap Output */}
      {result && (
        <div style={{ borderTop: '1px solid var(--border-violet)', paddingTop: '22px' }}>
          {/* Summary Box */}
          <div
            style={{
              backgroundColor: 'rgba(255, 255, 255, 0.025)',
              border: '1px solid var(--border-violet)',
              borderRadius: '14px',
              padding: '18px',
              marginBottom: '24px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span className="badge badge-cyan">Target: {result.target_role}</span>
              <span className="badge badge-info">{result.milestones.length} Strategic Milestones</span>
            </div>
            <p style={{ fontSize: '14px', color: '#f1edf9', lineHeight: 1.6 }}>{result.summary}</p>
          </div>

          {/* Sequential Milestones */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {result.milestones.map((m, idx) => (
              <div
                key={idx}
                style={{
                  backgroundColor: 'rgba(18, 14, 38, 0.9)',
                  border: '1px solid var(--border-violet)',
                  borderRadius: '16px',
                  padding: '20px',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: '14px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div
                      style={{
                        width: '30px',
                        height: '30px',
                        borderRadius: '8px',
                        background: 'var(--grad-primary)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '13px',
                        fontWeight: 800,
                        color: '#ffffff',
                      }}
                    >
                      {idx + 1}
                    </div>
                    <div>
                      <h4 style={{ fontSize: '16px', fontWeight: 700, color: '#ffffff' }}>
                        {m.title}
                      </h4>
                    </div>
                  </div>
                  <span className="badge badge-warn" style={{ fontSize: '11.5px' }}>
                    <Calendar size={11} /> {m.duration}
                  </span>
                </div>

                {/* Focus Skills */}
                {m.focus_skills.length > 0 && (
                  <div style={{ marginBottom: '14px' }}>
                    <span style={{ fontSize: '11.5px', color: 'var(--text-faint)', fontWeight: 600, marginRight: '8px' }}>
                      FOCUS SKILLS:
                    </span>
                    <div style={{ display: 'inline-flex', flexWrap: 'wrap', gap: '6px' }}>
                      {m.focus_skills.map((s, sIdx) => (
                        <span key={sIdx} className="badge badge-info" style={{ fontSize: '11.5px', padding: '3px 8px' }}>
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div>
                  <span style={{ fontSize: '11.5px', color: 'var(--text-faint)', fontWeight: 600, display: 'block', marginBottom: '8px' }}>
                    ACTION ITEMS:
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {m.actions.map((act, aIdx) => {
                      const key = `${idx}-${aIdx}`;
                      const isDone = !!completedActions[key];
                      return (
                        <div
                          key={aIdx}
                          onClick={() => toggleAction(key)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '10px',
                            backgroundColor: isDone ? 'rgba(16, 185, 129, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                            border: isDone ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid var(--border-violet)',
                            borderRadius: '8px',
                            padding: '10px 14px',
                            cursor: 'pointer',
                            transition: 'all 0.2s ease',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={isDone}
                            onChange={() => {}}
                            style={{ cursor: 'pointer', accentColor: 'var(--neon-lavender)' }}
                          />
                          <span
                            style={{
                              fontSize: '13.5px',
                              color: isDone ? '#a7f3d0' : '#f1edf9',
                              textDecoration: isDone ? 'line-through' : 'none',
                              lineHeight: 1.4,
                            }}
                          >
                            {act}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Action Bridges */}
          {onNavigate && (
            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: '12px',
                paddingTop: '20px',
              }}
            >
              <button
                onClick={() => onNavigate('jobs')}
                className="btn btn-secondary"
                style={{ fontSize: '13px' }}
              >
                <Briefcase size={14} /> Search Matching Jobs for this Roadmap <ArrowRight size={14} />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
