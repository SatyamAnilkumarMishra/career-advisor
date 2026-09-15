'use client';

import React, { useState } from 'react';
import { JobListing } from '@/types';
import { getErrorMessage, searchJobs } from '@/lib/api';
import {
  Briefcase,
  MapPin,
  Building,
  ExternalLink,
  Search,
  AlertCircle,
  Tag,
} from 'lucide-react';

interface JobsViewProps {
  targetRole: string;
  userSkills: string[];
  results: JobListing[] | null;
  onSearchResults: (jobs: JobListing[]) => void;
  hasJobApi: boolean;
}

export const JobsView: React.FC<JobsViewProps> = ({
  targetRole,
  userSkills,
  results,
  onSearchResults,
  hasJobApi,
}) => {
  const [roleInput, setRoleInput] = useState(targetRole || '');
  const [regionInput, setRegionInput] = useState('all');
  const [locationInput, setLocationInput] = useState('');
  const [skillsInput, setSkillsInput] = useState(
    userSkills.length > 0 ? userSkills.slice(0, 4).join(', ') : ''
  );
  const [expLevel, setExpLevel] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!roleInput.trim()) {
      setErrorMsg('Please specify a job role or title.');
      return;
    }
    const skills = skillsInput
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    let resolvedLoc = locationInput.trim();
    if (regionInput === 'in') {
      resolvedLoc = resolvedLoc ? `${resolvedLoc}, India` : 'India';
    } else if (regionInput === 'us') {
      resolvedLoc = resolvedLoc ? `${resolvedLoc}, US` : 'US';
    } else if (regionInput === 'eu') {
      resolvedLoc = resolvedLoc ? `${resolvedLoc}, Europe` : 'Europe';
    }

    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await searchJobs({
        role: roleInput.trim(),
        location: resolvedLoc || undefined,
        skills: skills.length > 0 ? skills : undefined,
        experience_level: expLevel || undefined,
        limit: 15,
      });
      onSearchResults(res);
    } catch (err: unknown) {
      setErrorMsg(getErrorMessage(err, 'Failed to search job listings.'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="tool-card">
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
        <Briefcase size={22} color="var(--neon-lavender)" />
        <h3 style={{ fontSize: '20px', fontWeight: 800, color: '#ffffff' }}>Job Matcher</h3>
      </div>
      <p style={{ fontSize: '13.5px', color: 'var(--text-dim)', marginBottom: '22px' }}>
        Discover live career openings matched to your verified skills and target role.
        {hasJobApi ? (
          <span className="badge badge-ok" style={{ marginLeft: '8px', fontSize: '11px' }}>
            ● Live Adzuna API Active
          </span>
        ) : (
          <span className="badge badge-info" style={{ marginLeft: '8px', fontSize: '11px' }}>
            ○ Verified Job Directory
          </span>
        )}
      </p>

      {/* Filter Inputs Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '16px',
          marginBottom: '20px',
        }}
      >
        <div>
          <label className="form-label">Role / Title</label>
          <input
            type="text"
            className="form-input"
            value={roleInput}
            onChange={(e) => setRoleInput(e.target.value)}
            placeholder="Enter the role"
          />
        </div>

        <div>
          <label className="form-label">Target Region</label>
          <select
            className="form-select"
            value={regionInput}
            onChange={(e) => setRegionInput(e.target.value)}
          >
            <option value="all">🌐 All Focus Regions (India, US, Europe)</option>
            <option value="in">🇮🇳 India</option>
            <option value="us">🇺🇸 United States</option>
            <option value="eu">🇪🇺 European Countries (UK, Germany, France...)</option>
          </select>
        </div>

        <div>
          <label className="form-label">City / Location (Optional)</label>
          <input
            type="text"
            className="form-input"
            value={locationInput}
            onChange={(e) => setLocationInput(e.target.value)}
            placeholder="Enter location"
          />
        </div>

        <div>
          <label className="form-label">Key Skills (Optional)</label>
          <input
            type="text"
            className="form-input"
            value={skillsInput}
            onChange={(e) => setSkillsInput(e.target.value)}
            placeholder="Enter skills"
          />
        </div>

        <div>
          <label className="form-label">Experience Level</label>
          <select
            className="form-select"
            value={expLevel}
            onChange={(e) => setExpLevel(e.target.value)}
          >
            <option value="">Any Experience Level</option>
            <option value="entry">Entry Level / Junior</option>
            <option value="mid">Mid Level</option>
            <option value="senior">Senior Level</option>
          </select>
        </div>
      </div>

      <button
        onClick={handleSearch}
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
            <Search size={16} /> Search Matching Jobs
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

      {/* Results List */}
      {results !== null && (
        <div style={{ borderTop: '1px solid var(--border-violet)', paddingTop: '22px' }}>
          {results.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '30px',
                color: 'var(--text-dim)',
                backgroundColor: 'rgba(255, 255, 255, 0.02)',
                borderRadius: '14px',
              }}
            >
              <p style={{ fontSize: '15px', fontWeight: 600, color: '#ffffff', marginBottom: '6px' }}>
                No direct matches found
              </p>
              <p style={{ fontSize: '13px' }}>
                Try broadening your search title, clearing specific location filters, or adjusting skill keywords.
              </p>
            </div>
          ) : (
            <div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--neon-cyan)', marginBottom: '16px' }}>
                FOUND {results.length} OPPORTUNITY LISTINGS
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {results.map((job, idx) => (
                  <div key={idx} className="output-card">
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        marginBottom: '8px',
                      }}
                    >
                      <div>
                        <h4 style={{ fontSize: '16px', fontWeight: 700, color: '#ffffff', marginBottom: '4px' }}>
                          {job.title}
                        </h4>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '13px', color: 'var(--neon-lavender)', fontWeight: 600 }}>
                            <Building size={13} /> {job.company}
                          </span>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '13px', color: 'var(--text-dim)' }}>
                            <MapPin size={13} /> {job.location}
                          </span>
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: '6px' }}>
                        {job.source === 'adzuna' ? (
                          <span className="badge badge-ok" style={{ fontSize: '11px' }}>Adzuna Live</span>
                        ) : (
                          <span className="badge badge-info" style={{ fontSize: '11px' }}>Verified Directory</span>
                        )}
                        {job.experience_level && (
                          <span className="badge badge-warn" style={{ fontSize: '11px' }}>
                            {job.experience_level.toUpperCase()}
                          </span>
                        )}
                      </div>
                    </div>

                    {job.description && (
                      <p style={{ fontSize: '13.5px', color: '#d5cfe3', lineHeight: 1.5, margin: '10px 0' }}>
                        {job.description}
                      </p>
                    )}

                    {job.skills && job.skills.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', margin: '8px 0 12px' }}>
                        {job.skills.map((s, sIdx) => (
                          <span key={sIdx} className="badge badge-cyan" style={{ fontSize: '11.5px', padding: '3px 8px' }}>
                            <Tag size={10} /> {s}
                          </span>
                        ))}
                      </div>
                    )}

                    {job.url && (
                      <div style={{ marginTop: '10px' }}>
                        <a
                          href={job.url}
                          target="_blank"
                          rel="noreferrer"
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            color: 'var(--neon-cyan)',
                            textDecoration: 'none',
                            fontWeight: 600,
                            fontSize: '13px',
                          }}
                        >
                          <span>View Job Listing</span>
                          <ExternalLink size={13} />
                        </a>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
