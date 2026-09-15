'use client';

import React, { useState } from 'react';
import { ActiveView, ResumeAnalysis } from '@/types';
import { analyzeResume, getErrorMessage, uploadResumeFile } from '@/lib/api';
import {
  FileText,
  Upload,
  AlertCircle,
  Award,
  TrendingUp,
  Sparkles,
  Compass,
  ArrowRight,
  Target,
} from 'lucide-react';

interface ResumeViewProps {
  resumeFilename?: string | null;
  resumeText: string;
  targetRole: string;
  analysis: ResumeAnalysis | null;
  onAnalysisComplete: (result: ResumeAnalysis) => void;
  onResumeUploaded: (filename: string, text: string) => void;
  onNavigate?: (view: ActiveView) => void;
  onTargetRoleChange?: (role: string) => void;
}

export const ResumeView: React.FC<ResumeViewProps> = ({
  resumeFilename,
  resumeText,
  targetRole,
  analysis,
  onAnalysisComplete,
  onResumeUploaded,
  onNavigate,
  onTargetRoleChange,
}) => {
  const [roleInput, setRoleInput] = useState(targetRole || '');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await uploadResumeFile(file);
      onResumeUploaded(res.filename, res.text);
    } catch (err: unknown) {
      setErrorMsg(getErrorMessage(err, 'Failed to upload resume file.'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunAnalysis = async () => {
    if (!resumeText) {
      setErrorMsg('Please upload a resume file (PDF, DOCX, or TXT) first.');
      return;
    }
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await analyzeResume(resumeText, roleInput.trim() || undefined);
      if (roleInput.trim() && onTargetRoleChange) {
        onTargetRoleChange(roleInput.trim());
      }
      onAnalysisComplete(res);
    } catch (err: unknown) {
      setErrorMsg(getErrorMessage(err, 'Failed to analyze resume.'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectRole = (role: string) => {
    setRoleInput(role);
    if (onTargetRoleChange) {
      onTargetRoleChange(role);
    }
  };

  return (
    <div className="tool-card">
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
        <FileText size={22} color="var(--neon-lavender)" />
        <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#ffffff' }}>Resume Analyzer</h3>
      </div>
      <p style={{ fontSize: '13.5px', color: 'var(--text-dim)', marginBottom: '22px' }}>
        Extract verified skills, identify strengths, spotlight growth gaps, and get ATS feedback.
      </p>

      {/* Upload & Options Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '16px',
          marginBottom: '20px',
        }}
      >
        <div>
          <label className="form-label">Resume Document</label>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: 'rgba(15, 12, 34, 0.85)',
              border: '1px dashed var(--border-violet-strong)',
              borderRadius: '10px',
              padding: '10px 14px',
            }}
          >
            <span style={{ fontSize: '13px', color: resumeFilename ? '#ffffff' : 'var(--text-faint)' }}>
              {resumeFilename ? `📄 ${resumeFilename}` : 'No resume file uploaded yet'}
            </span>
            <label
              className="btn btn-secondary"
              style={{ fontSize: '12px', padding: '5px 12px', cursor: 'pointer', margin: 0 }}
            >
              <Upload size={12} /> Browse
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileUpload}
                style={{ display: 'none' }}
              />
            </label>
          </div>
        </div>

        <div>
          <label className="form-label">Target Role (Optional)</label>
          <input
            type="text"
            className="form-input"
            value={roleInput}
            onChange={(e) => setRoleInput(e.target.value)}
            placeholder="Enter the role"
          />
        </div>
      </div>

      <button
        onClick={handleRunAnalysis}
        disabled={isLoading || !resumeText}
        className="btn btn-primary"
        style={{ width: '100%', padding: '12px', fontSize: '15px', marginBottom: '24px' }}
      >
        {isLoading ? (
          <>
            <span className="spinner" /> Generating response...
          </>
        ) : (
          <>
            <Sparkles size={16} /> Run Full Resume Analysis
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

      {/* Analysis Results Display */}
      {analysis && (
        <div
          style={{
            borderTop: '1px solid var(--border-violet)',
            paddingTop: '22px',
          }}
        >
          <div
            style={{
              backgroundColor: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-violet)',
              borderRadius: '14px',
              padding: '18px',
              marginBottom: '20px',
            }}
          >
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--neon-cyan)', marginBottom: '4px' }}>
              EXECUTIVE EXPERIENCE SUMMARY
            </div>
            <p style={{ fontSize: '14px', color: '#f1edf9', lineHeight: 1.6 }}>
              {analysis.experience_summary}
            </p>
          </div>

          {/* Extracted Skills Badges */}
          <div style={{ marginBottom: '20px' }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--neon-lavender)', marginBottom: '10px' }}>
              EXTRACTED VERIFIED SKILLS ({analysis.extracted_skills.length})
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {analysis.extracted_skills.map((skill, sIdx) => (
                <span key={sIdx} className="badge badge-info" style={{ fontSize: '12.5px', padding: '5px 12px' }}>
                  {skill}
                </span>
              ))}
            </div>
          </div>

          {/* Strengths & Growth Areas Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
              gap: '18px',
              marginBottom: '20px',
            }}
          >
            {/* Strengths */}
            <div
              style={{
                backgroundColor: 'rgba(16, 185, 129, 0.04)',
                border: '1px solid rgba(16, 185, 129, 0.25)',
                borderRadius: '14px',
                padding: '18px',
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
                <Award size={18} /> Candidate Strengths
              </div>
              <ul style={{ paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {analysis.strengths.map((s, idx) => (
                  <li key={idx} style={{ fontSize: '13.5px', color: '#f1edf9', lineHeight: 1.4 }}>
                    {s}
                  </li>
                ))}
              </ul>
            </div>

            {/* Growth Areas */}
            <div
              style={{
                backgroundColor: 'rgba(245, 158, 11, 0.04)',
                border: '1px solid rgba(245, 158, 11, 0.25)',
                borderRadius: '14px',
                padding: '18px',
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
                <TrendingUp size={18} /> Growth Areas & Improvements
              </div>
              <ul style={{ paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {analysis.gaps_or_improvements.map((g, idx) => (
                  <li key={idx} style={{ fontSize: '13.5px', color: '#f1edf9', lineHeight: 1.4 }}>
                    {g}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Suggested Target Roles */}
          {analysis.suggested_target_roles.length > 0 && (
            <div
              style={{
                backgroundColor: 'rgba(6, 182, 212, 0.04)',
                border: '1px solid rgba(6, 182, 212, 0.25)',
                borderRadius: '14px',
                padding: '16px 18px',
                marginBottom: '20px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  color: 'var(--neon-cyan)',
                  fontWeight: 700,
                  fontSize: '13.5px',
                  marginBottom: '10px',
                }}
              >
                <Compass size={16} /> Recommended Target Roles (Click to select)
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {analysis.suggested_target_roles.map((role, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSelectRole(role)}
                    className="badge badge-ok"
                    style={{
                      fontSize: '12px',
                      padding: '6px 12px',
                      cursor: 'pointer',
                      border: roleInput === role ? '1px solid #34d399' : '1px solid rgba(16,185,129,0.35)',
                      backgroundColor: roleInput === role ? 'rgba(16,185,129,0.25)' : 'rgba(16,185,129,0.12)',
                    }}
                  >
                    {role} {roleInput === role && '✓'}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Next Action Bridge */}
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
                onClick={() => onNavigate('skillgap')}
                className="btn btn-secondary"
                style={{ fontSize: '13px' }}
              >
                <Target size={14} /> Evaluate Skill Gaps <ArrowRight size={14} />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
