'use client';

import React, { useState } from 'react';
import { ActiveView, SkillGapResult } from '@/types';
import { analyzeSkillGap, getErrorMessage } from '@/lib/api';
import {
  Target,
  CheckCircle2,
  Clock,
  XCircle,
  Sparkles,
  AlertCircle,
  Map,
  Briefcase,
  ArrowRight,
} from 'lucide-react';

interface SkillGapViewProps {
  targetRole: string;
  userSkills: string[];
  result: SkillGapResult | null;
  onAnalysisComplete: (res: SkillGapResult) => void;
  onTargetRoleChange: (role: string) => void;
  onNavigate?: (view: ActiveView) => void;
}

export const SkillGapView: React.FC<SkillGapViewProps> = ({
  targetRole,
  userSkills,
  result,
  onAnalysisComplete,
  onTargetRoleChange,
  onNavigate,
}) => {
  const [roleInput, setRoleInput] = useState(targetRole || '');
  const [skillsInput, setSkillsInput] = useState(
    userSkills.length > 0 ? userSkills.join(', ') : ''
  );
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleRunAnalysis = async () => {
    if (!roleInput.trim()) {
      setErrorMsg('Please specify a target role.');
      return;
    }
    const skills = skillsInput
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    if (skills.length === 0) {
      setErrorMsg('Please provide at least one skill to evaluate.');
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await analyzeSkillGap(skills, roleInput.trim());
      onTargetRoleChange(roleInput.trim());
      onAnalysisComplete(res);
    } catch (err: unknown) {
      setErrorMsg(getErrorMessage(err, 'Failed to analyze skill gap.'));
    } finally {
      setIsLoading(false);
    }
  };

  const getReadinessBadge = (readiness: string) => {
    switch (readiness?.toLowerCase()) {
      case 'high':
        return <span className="badge badge-ok">● High Readiness</span>;
      case 'medium':
        return <span className="badge badge-warn">● Medium Readiness</span>;
      case 'low':
        return <span className="badge badge-danger">● Foundational / Low Readiness</span>;
      default:
        return <span className="badge badge-info">● Evaluated</span>;
    }
  };

  return (
    <div className="tool-card">
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
        <Target size={22} color="var(--neon-lavender)" />
        <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#ffffff' }}>Skill Gap Matrix</h3>
      </div>
      <p style={{ fontSize: '13.5px', color: 'var(--text-dim)', marginBottom: '22px' }}>
        Benchmark your current technical abilities against standard industry competencies for your desired role.
      </p>

      {/* Inputs */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '16px',
          marginBottom: '20px',
        }}
      >
        <div>
          <label className="form-label">Target Role / Career Goal</label>
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
      </div>

      <button
        onClick={handleRunAnalysis}
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
            <Sparkles size={16} /> Run Skill Gap Analysis
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

      {/* Result Display */}
      {result && (
        <div style={{ borderTop: '1px solid var(--border-violet)', paddingTop: '22px' }}>
          <div
            style={{
              backgroundColor: 'rgba(255, 255, 255, 0.025)',
              border: '1px solid var(--border-violet)',
              borderRadius: '14px',
              padding: '18px',
              marginBottom: '22px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              {getReadinessBadge(result.overall_readiness)}
            </div>
            <p style={{ fontSize: '14px', color: '#f1edf9', lineHeight: 1.6 }}>{result.summary}</p>
          </div>

          {/* 3-Column Skills Matrix */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '16px',
              marginBottom: '20px',
            }}
          >
            {/* Matched */}
            <div
              style={{
                backgroundColor: 'rgba(16, 185, 129, 0.04)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                borderRadius: '14px',
                padding: '16px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  color: '#34d399',
                  fontWeight: 700,
                  fontSize: '14px',
                  marginBottom: '12px',
                }}
              >
                <CheckCircle2 size={16} /> Matched Skills ({result.matched_skills.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {result.matched_skills.length > 0 ? (
                  result.matched_skills.map((s, i) => (
                    <span key={i} className="badge badge-ok" style={{ fontSize: '12px' }}>
                      {s}
                    </span>
                  ))
                ) : (
                  <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>None identified</span>
                )}
              </div>
            </div>

            {/* Partial */}
            <div
              style={{
                backgroundColor: 'rgba(245, 158, 11, 0.04)',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                borderRadius: '14px',
                padding: '16px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  color: '#fbbf24',
                  fontWeight: 700,
                  fontSize: '14px',
                  marginBottom: '12px',
                }}
              >
                <Clock size={16} /> Partial / Developing ({result.partially_met_skills.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {result.partially_met_skills.length > 0 ? (
                  result.partially_met_skills.map((s, i) => (
                    <span key={i} className="badge badge-warn" style={{ fontSize: '12px' }}>
                      {s}
                    </span>
                  ))
                ) : (
                  <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>None identified</span>
                )}
              </div>
            </div>

            {/* Missing Gaps */}
            <div
              style={{
                backgroundColor: 'rgba(244, 63, 94, 0.04)',
                border: '1px solid rgba(244, 63, 94, 0.25)',
                borderRadius: '14px',
                padding: '16px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  color: '#fbbf24',
                  fontWeight: 700,
                  fontSize: '14px',
                  marginBottom: '12px',
                }}
              >
                <XCircle size={16} /> Missing Gaps ({result.missing_skills.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {result.missing_skills.length > 0 ? (
                  result.missing_skills.map((s, i) => (
                    <span key={i} className="badge badge-danger" style={{ fontSize: '12px' }}>
                      {s}
                    </span>
                  ))
                ) : (
                  <span style={{ fontSize: '12px', color: 'var(--text-faint)' }}>No major gaps</span>
                )}
              </div>
            </div>
          </div>

          {/* Action Bridges */}
          {onNavigate && (
            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: '12px',
                paddingTop: '12px',
              }}
            >
              <button
                onClick={() => onNavigate('roadmap')}
                className="btn btn-secondary"
                style={{ fontSize: '13px' }}
              >
                <Map size={14} /> Generate Roadmap <ArrowRight size={14} />
              </button>
              <button
                onClick={() => onNavigate('jobs')}
                className="btn btn-secondary"
                style={{ fontSize: '13px' }}
              >
                <Briefcase size={14} /> Search Matching Jobs <ArrowRight size={14} />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
