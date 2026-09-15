'use client';

import React, { useEffect, useRef, useState } from 'react';
import {
  ChatMessage,
  HistoryItem,
  JobListing,
  ResumeAnalysis,
  RoadmapResult,
  SkillGapResult,
  StatusResponse,
} from '@/types';
import {
  addHistoryItem,
  analyzeResume,
  analyzeSkillGap,
  clearConversation,
  deleteHistoryItem,
  fetchHistory,
  fetchStatus,
  generateRoadmap,
  getErrorMessage,
  searchJobs,
  sendChatMessage,
  uploadResumeFile,
} from '@/lib/api';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { HeroSection } from '@/components/HeroSection';
import { CareerToolCards } from '@/components/CareerToolCards';
import { ChatInput } from '@/components/ChatInput';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';

const HISTORY_CACHE_KEY = 'career_advisor_history';

function cacheHistory(items: HistoryItem[]): void {
  try {
    localStorage.setItem(HISTORY_CACHE_KEY, JSON.stringify(items));
  } catch {
    // localStorage unavailable
  }
}

const MAX_PROFILE_CHARS = 4000;

function buildStudentProfile(resumeText: string): string {
  const trimmed = resumeText.trim();
  if (!trimmed) return '';
  return trimmed.length > MAX_PROFILE_CHARS
    ? `${trimmed.slice(0, MAX_PROFILE_CHARS)}\n…(resume truncated)`
    : trimmed;
}

function createOptimisticHistoryItem(query: string): HistoryItem {
  const now = new Date();
  return {
    id: `local_${now.getTime()}`,
    query,
    timestamp: now.toISOString(),
  };
}

export default function Home() {
  // Navigation: 'chat' | 'resume' | 'skillgap' | 'roadmap' | 'matcher'
  const [activeView, setActiveView] = useState<'chat' | 'resume' | 'skillgap' | 'roadmap' | 'matcher'>('chat');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Status & Backend info
  const [, setStatus] = useState<StatusResponse | null>(null);
  const [agentStatusText, setAgentStatusText] = useState('Online');
  const [, setIsThinking] = useState(false);

  // Search History State
  const [searchHistory, setSearchHistory] = useState<HistoryItem[]>([]);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((current) => (current === msg ? null : current));
    }, 2400);
  };

  // Resume state
  const [resumeFilename, setResumeFilename] = useState<string | null>(null);
  const [resumeText, setResumeText] = useState('');
  const [isUploadingResume, setIsUploadingResume] = useState(false);
  const resumeFileInputRef = useRef<HTMLInputElement>(null);

  // Chat State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputVal, setInputVal] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [expandedSources, setExpandedSources] = useState<{ [key: number]: boolean }>({});
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Tool 1: Resume Analyzer
  const [resumeTargetRole, setResumeTargetRole] = useState('');
  const [resumeAnalysis, setResumeAnalysis] = useState<ResumeAnalysis | null>(null);
  const [isResumeAnalyzing, setIsResumeAnalyzing] = useState(false);
  const [resumeError, setResumeError] = useState<string | null>(null);

  // Tool 2: Skill Gap Analyzer
  const [skillGapRole, setSkillGapRole] = useState('');
  const [skillGapSkills, setSkillGapSkills] = useState('');
  const [skillGapResult, setSkillGapResult] = useState<SkillGapResult | null>(null);
  const [isSkillGapAnalyzing, setIsSkillGapAnalyzing] = useState(false);
  const [skillGapError, setSkillGapError] = useState<string | null>(null);

  // Tool 3: Milestone Roadmap
  const [roadmapRole, setRoadmapRole] = useState('');
  const [roadmapSkills, setRoadmapSkills] = useState('');
  const [roadmapTimeframe, setRoadmapTimeframe] = useState('6 Months');
  const [roadmapResult, setRoadmapResult] = useState<RoadmapResult | null>(null);
  const [isRoadmapGenerating, setIsRoadmapGenerating] = useState(false);
  const [roadmapError, setRoadmapError] = useState<string | null>(null);
  const [completedActions, setCompletedActions] = useState<{ [key: string]: boolean }>({});

  // Tool 4: Job Matcher
  const [jobRole, setJobRole] = useState('');
  const [jobRegion, setJobRegion] = useState('all');
  const [jobLocation, setJobLocation] = useState('');
  const [jobSkills, setJobSkills] = useState('');
  const [jobExperience, setJobExperience] = useState('');
  const [jobResults, setJobResults] = useState<JobListing[] | null>(null);
  const [isJobSearching, setIsJobSearching] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);

  // Initial load
  useEffect(() => {
    fetchStatus()
      .then((data) => setStatus(data))
      .catch((err) => console.warn('Backend status check:', err));

    fetchHistory()
      .then((items) => {
        if (items && Array.isArray(items)) {
          setSearchHistory(items);
          cacheHistory(items);
        }
      })
      .catch(() => {
        try {
          const cached = localStorage.getItem(HISTORY_CACHE_KEY);
          if (cached) {
            const parsed = JSON.parse(cached);
            if (Array.isArray(parsed)) setSearchHistory(parsed);
          }
        } catch {
          // No cache
        }
      });
  }, []);

  // Select Search History item
  const handleSelectHistory = (query: string) => {
    setActiveView('chat');
    setIsSidebarOpen(false);
    handleSendMessage(query);
  };

  // Delete Search History item and clear active chat
  const handleDeleteHistory = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();

    setSearchHistory((prev) => {
      const updated = prev.filter((item) => item.id !== id);
      cacheHistory(updated);
      return updated;
    });

    // On clicking delete, the chat is deleted/cleared
    setMessages([]);
    setInputVal('');
    setExpandedSources({});
    showToast('Chat deleted');

    try {
      await deleteHistoryItem(id);
    } catch (err) {
      console.warn('Failed to delete history item on server:', err);
    }
  };

  // Clear conversation
  const handleClearConversation = async () => {
    setMessages([]);
    setInputVal('');
    setExpandedSources({});
    setResumeFilename(null);
    setResumeText('');
    setResumeAnalysis(null);
    setResumeError(null);
    if (resumeFileInputRef.current) resumeFileInputRef.current.value = '';
    setSkillGapResult(null);
    setSkillGapError(null);
    setSkillGapSkills('');
    setSkillGapRole('');
    setRoadmapResult(null);
    setRoadmapError(null);
    setRoadmapSkills('');
    setRoadmapRole('');
    setCompletedActions({});
    setJobResults(null);
    setJobError(null);
    setAgentStatusText('Online');
    setActiveView('chat');
    showToast('Conversation cleared');

    try {
      await clearConversation();
    } catch (err) {
      console.warn('Failed to clear conversation on backend:', err);
    }
  };

  // Resume upload & processing
  const processResumeFile = async (file: File) => {
    if (!file) return;
    setIsUploadingResume(true);
    setResumeError(null);
    try {
      const res = await uploadResumeFile(file);
      setResumeFilename(res.filename);
      setResumeText(res.text);

      const confirmMsg: ChatMessage = {
        role: 'assistant',
        content: `📁 **Resume Loaded:** *${res.filename}* (${(res.size_bytes / 1024).toFixed(1)} KB) has been parsed and loaded into Agent Memory. You can run the **Resume Analyzer** or ask questions about your background.`,
      };
      setMessages((prev) => [...prev, confirmMsg]);
      showToast('Resume uploaded successfully');
    } catch (err: unknown) {
      const msg = getErrorMessage(err, 'Could not parse that resume.');
      setResumeError(msg);
      showToast(`Upload failed: ${msg}`);
    } finally {
      setIsUploadingResume(false);
      if (resumeFileInputRef.current) resumeFileInputRef.current.value = '';
    }
  };

  const handleResumeFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) await processResumeFile(file);
  };

  // Send message
  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputVal).trim();
    if (!query || isChatLoading) return;

    setInputVal('');
    const userMsg: ChatMessage = { role: 'user', content: query };
    const updated = [...messages, userMsg];
    setMessages(updated);
    setIsChatLoading(true);
    setIsThinking(true);
    setAgentStatusText('Thinking...');

    const optimisticItem = createOptimisticHistoryItem(query);
    setSearchHistory((prev) => {
      const filtered = prev.filter((h) => h.query.toLowerCase() !== query.toLowerCase());
      const res = [optimisticItem, ...filtered];
      cacheHistory(res);
      return res;
    });

    addHistoryItem(query)
      .then((savedItem) => {
        setSearchHistory((prev) => {
          const res = [
            savedItem,
            ...prev.filter((h) => h.id !== optimisticItem.id && h.id !== savedItem.id && h.query.toLowerCase() !== query.toLowerCase()),
          ];
          cacheHistory(res);
          return res;
        });
      })
      .catch((err) => console.warn('Search history save:', err));

    try {
      const res = await sendChatMessage(query, messages, buildStudentProfile(resumeText));
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: res.text,
        sources: res.sources,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const errorMsg: ChatMessage = {
        role: 'assistant',
        content: `⚠️ **Error:** ${getErrorMessage(err, 'Failed to reach AI service.')}`,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsChatLoading(false);
      setIsThinking(false);
      setAgentStatusText('Online');
    }
  };

  // Run Resume Scan
  const handleRunResumeScan = async () => {
    if (!resumeText) {
      setResumeError('Please upload a resume (.pdf, .docx, .txt) first.');
      return;
    }
    setResumeError(null);
    setIsResumeAnalyzing(true);
    setAgentStatusText('Scanning Resume...');

    try {
      const res = await analyzeResume(resumeText, resumeTargetRole.trim() || undefined);
      setResumeAnalysis(res);
      if (res.extracted_skills && res.extracted_skills.length > 0) {
        setSkillGapSkills(res.extracted_skills.join(', '));
        setRoadmapSkills(res.extracted_skills.slice(0, 5).join(', '));
      }
      if (res.suggested_target_roles && res.suggested_target_roles.length > 0) {
        setSkillGapRole(res.suggested_target_roles[0]);
        setRoadmapRole(res.suggested_target_roles[0]);
        setJobRole(res.suggested_target_roles[0]);
      }
    } catch (err: unknown) {
      setResumeError(getErrorMessage(err, 'Failed to analyze resume.'));
    } finally {
      setIsResumeAnalyzing(false);
      setAgentStatusText('Online');
    }
  };

  // Run Skill Gap Analysis
  const handleRunSkillGap = async () => {
    if (!skillGapRole.trim()) {
      setSkillGapError('Please enter a target role.');
      return;
    }
    const skills = skillGapSkills.split(',').map((s) => s.trim()).filter(Boolean);
    if (skills.length === 0) {
      setSkillGapError('Please enter at least one skill.');
      return;
    }

    setSkillGapError(null);
    setIsSkillGapAnalyzing(true);
    setAgentStatusText('Benchmarking Stack...');

    try {
      const res = await analyzeSkillGap(skills, skillGapRole.trim());
      setSkillGapResult(res);
    } catch (err: unknown) {
      setSkillGapError(getErrorMessage(err, 'Failed to analyze skill gap.'));
    } finally {
      setIsSkillGapAnalyzing(false);
    }
  };

  // Run Milestone Roadmap Generation
  const handleRunRoadmap = async () => {
    if (!roadmapRole.trim()) {
      setRoadmapError('Please enter a target position or goal.');
      return;
    }
    setIsRoadmapGenerating(true);
    setRoadmapError(null);
    setAgentStatusText('Generating response...');

    try {
      const currentSkillsArray = roadmapSkills.split(',').map((s) => s.trim()).filter(Boolean);
      const months = parseInt(roadmapTimeframe, 10) || 6;
      const res = await generateRoadmap(currentSkillsArray, roadmapRole, months);
      setRoadmapResult(res);
      showToast('Learning roadmap generated!');
      setAgentStatusText('Online');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'API response error: Failed to generate roadmap.';
      setRoadmapError(msg);
      setAgentStatusText('Online');
    } finally {
      setIsRoadmapGenerating(false);
    }
  };

  // Run Job Search
  const handleRunJobSearch = async () => {
    if (!jobRole.trim()) {
      setJobError('Please enter a role or job title.');
      return;
    }
    setIsJobSearching(true);
    setJobError(null);
    setAgentStatusText('Generating response...');

    try {
      const skillsArray = jobSkills.split(',').map((s) => s.trim()).filter(Boolean);
      let resolvedLoc = jobLocation.trim();
      if (jobRegion === 'in') {
        resolvedLoc = resolvedLoc ? `${resolvedLoc}, India` : 'India';
      } else if (jobRegion === 'us') {
        resolvedLoc = resolvedLoc ? `${resolvedLoc}, US` : 'US';
      } else if (jobRegion === 'eu') {
        resolvedLoc = resolvedLoc ? `${resolvedLoc}, Europe` : 'Europe';
      }

      const res = await searchJobs({
        role: jobRole,
        skills: skillsArray.length > 0 ? skillsArray : undefined,
        location: resolvedLoc || undefined,
        experience_level: jobExperience.trim() || undefined,
      });
      setJobResults(res);
      showToast(`Found ${res.length} jobs.`);
      setAgentStatusText('Online');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'API response error: Failed to search jobs.';
      setJobResults(null);
      setJobError(msg);
      setAgentStatusText('Online');
    } finally {
      setIsJobSearching(false);
    }
  };

  const toggleSource = (idx: number) => {
    setExpandedSources((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const toggleActionDone = (key: string) => {
    setCompletedActions((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="app-viewport-container">
      {/* Hidden File Input for Resume upload */}
      <input
        type="file"
        ref={resumeFileInputRef}
        accept=".pdf,.docx,.txt"
        onChange={handleResumeFileChange}
        style={{ display: 'none' }}
      />

      {/* Left Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        activeView={activeView}
        onSelectView={(v) => setActiveView(v)}
        searchHistory={searchHistory}
        onSelectHistory={handleSelectHistory}
        onDeleteHistory={handleDeleteHistory}
        onClearConversation={handleClearConversation}
      />

      {/* Main Content Panel */}
      <main className="app-main-panel">
        {/* Header */}
        <Header
          onOpenSidebar={() => setIsSidebarOpen(true)}
          statusText={agentStatusText}
        />

        {/* Scrollable View Area: single screen without scroll on initial open, scrolling when chatting */}
        <div
          className={`main-panel-scrollable ${
            activeView === 'chat' && messages.length === 0
              ? 'initial-hero-view'
              : 'chat-active-view'
          }`}
        >
          {/* VIEW: Chat Workspace */}
          {activeView === 'chat' && (
            <>
              {messages.length === 0 ? (
                <>
                  {/* Hero Section */}
                  <HeroSection />

                  {/* 4-Column Career Tool Cards */}
                  <CareerToolCards
                    onSelectTool={(toolKey) => setActiveView(toolKey)}
                  />
                </>
              ) : (
                /* Chat Messages Feed */
                <div className="chat-messages-container">
                  {messages.map((msg, idx) => {
                    const isUser = msg.role === 'user';
                    return (
                      <div
                        key={idx}
                        className={`chat-bubble ${isUser ? 'user' : 'assistant'}`}
                      >
                        {!isUser && (
                          <div className="chat-bubble-header">
                            <span>✦ CareerAI</span>
                          </div>
                        )}
                        <MarkdownRenderer content={msg.content} />

                        {/* Grounded Source Citations */}
                        {msg.sources && msg.sources.length > 0 && (
                          <div>
                            <button
                              className="sources-toggle-btn"
                              onClick={() => toggleSource(idx)}
                            >
                              <BookOpen size={12} />
                              <span>{msg.sources.length} Verified Document Excerpt(s)</span>
                              {expandedSources[idx] ? (
                                <ChevronUp size={12} />
                              ) : (
                                <ChevronDown size={12} />
                              )}
                            </button>

                            {expandedSources[idx] && (
                              <div style={{ marginTop: '6px' }}>
                                {msg.sources.map((s, sIdx) => (
                                  <div key={sIdx} className="source-item-card">
                                    <strong style={{ color: 'var(--primary-gold)' }}>
                                      {s.page !== undefined && s.page !== null
                                        ? `Page ${s.page}`
                                        : 'Document Excerpt'}
                                      :
                                    </strong>{' '}
                                    &ldquo;{s.content}&rdquo;
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {isChatLoading && (
                    <div className="chat-bubble assistant">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span className="gold-spinner" />
                        <span style={{ color: 'var(--primary-gold)', fontStyle: 'italic', fontWeight: 500 }}>
                          Generating response...
                        </span>
                      </div>
                    </div>
                  )}

                  <div ref={chatBottomRef} />
                </div>
              )}

              {/* Chat Input Container */}
              <ChatInput
                value={inputVal}
                onChange={setInputVal}
                onSubmit={() => handleSendMessage()}
                isLoading={isChatLoading}
                onAttachmentClick={() => resumeFileInputRef.current?.click()}
                placeholder="Ask me anything about your career..."
              />
            </>
          )}

          {/* VIEW: Tool 1 - Resume Analyzer */}
          {activeView === 'resume' && (
            <div className="tool-workspace-container">
              <div className="tool-view-header">
                <div>
                  <h2 className="tool-view-title">Resume Analyzer</h2>
                  <p className="tool-view-subtitle">
                    Evaluate your resume, extract key skills, and receive actionable insights.
                  </p>
                </div>
                <button className="back-to-chat-btn" onClick={() => setActiveView('chat')}>
                  <ArrowLeft size={14} />
                  <span>Back to Chat</span>
                </button>
              </div>

              <div className="tool-card-panel">
                <div
                  className="dropzone-gold"
                  onClick={() => resumeFileInputRef.current?.click()}
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const file = e.dataTransfer.files?.[0];
                    if (file) processResumeFile(file);
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  <div style={{ fontSize: '28px', marginBottom: '8px' }}>📄</div>
                  <div style={{ fontSize: '13.5px', color: 'var(--text-primary)' }}>
                    {isUploadingResume ? (
                      <span>Parsing your resume...</span>
                    ) : resumeFilename ? (
                      <span style={{ color: 'var(--primary-gold)' }}>
                        ✓ {resumeFilename} (Loaded and ready to analyze)
                      </span>
                    ) : (
                      <>
                        Click to upload your resume (.pdf, .docx, .txt)
                        <br />
                        <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                          Max file size: 5MB
                        </span>
                      </>
                    )}
                  </div>
                </div>

                <div className="form-group-custom">
                  <label className="form-label-custom" htmlFor="resume-target-role">
                    Target Role (Optional)
                  </label>
                  <input
                    type="text"
                    id="resume-target-role"
                    className="form-input-custom"
                    value={resumeTargetRole}
                    onChange={(e) => setResumeTargetRole(e.target.value)}
                    placeholder="Enter the role"
                  />
                </div>

                <button
                  className="gold-submit-btn"
                  onClick={handleRunResumeScan}
                  disabled={isResumeAnalyzing}
                >
                  {isResumeAnalyzing ? (
                    <>
                      <span className="gold-spinner" />
                      <span>Generating response...</span>
                    </>
                  ) : (
                    <span>Analyze Resume</span>
                  )}
                </button>

                {resumeError && (
                  <div style={{ color: '#ef4444', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertCircle size={14} />
                    <span>{resumeError}</span>
                  </div>
                )}

                {resumeAnalysis && (
                  <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <div style={{ fontSize: '13.5px', color: 'var(--text-primary)', lineHeight: 1.6 }}>
                      <strong>Summary:</strong> {resumeAnalysis.experience_summary}
                    </div>

                    {resumeAnalysis.extracted_skills.length > 0 && (
                      <div>
                        <div className="form-label-custom" style={{ marginBottom: '8px' }}>
                          Extracted Skills:
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {resumeAnalysis.extracted_skills.map((s, i) => (
                            <span
                              key={i}
                              style={{
                                background: 'rgba(214, 169, 54, 0.12)',
                                border: '1px solid rgba(214, 169, 54, 0.3)',
                                color: 'var(--primary-gold)',
                                padding: '3px 10px',
                                borderRadius: '6px',
                                fontSize: '12px',
                              }}
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                      <div
                        style={{
                          background: '#0E0E0D',
                          border: '1px solid var(--border-subtle)',
                          borderLeft: '3px solid #10b981',
                          borderRadius: '8px',
                          padding: '14px',
                        }}
                      >
                        <div style={{ color: '#10b981', fontWeight: 600, fontSize: '13px', marginBottom: '8px' }}>
                          ⭐ Key Strengths
                        </div>
                        <ul style={{ paddingLeft: '18px', fontSize: '12.5px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {resumeAnalysis.strengths.map((st, i) => (
                            <li key={i}>{st}</li>
                          ))}
                        </ul>
                      </div>

                      <div
                        style={{
                          background: '#0E0E0D',
                          border: '1px solid var(--border-subtle)',
                          borderLeft: '3px solid var(--primary-gold)',
                          borderRadius: '8px',
                          padding: '14px',
                        }}
                      >
                        <div style={{ color: 'var(--primary-gold)', fontWeight: 600, fontSize: '13px', marginBottom: '8px' }}>
                          🚀 Growth Areas & Polish
                        </div>
                        <ul style={{ paddingLeft: '18px', fontSize: '12.5px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {resumeAnalysis.gaps_or_improvements.map((gap, i) => (
                            <li key={i}>{gap}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* VIEW: Tool 2 - Skill Gap Analyzer */}
          {activeView === 'skillgap' && (
            <div className="tool-workspace-container">
              <div className="tool-view-header">
                <div>
                  <h2 className="tool-view-title">Skill Gap Analyzer</h2>
                  <p className="tool-view-subtitle">
                    Compare your tech stack against target roles to uncover critical missing skills.
                  </p>
                </div>
                <button className="back-to-chat-btn" onClick={() => setActiveView('chat')}>
                  <ArrowLeft size={14} />
                  <span>Back to Chat</span>
                </button>
              </div>

              <div className="tool-card-panel">
                <div className="form-group-custom">
                  <label className="form-label-custom" htmlFor="sg-target-role">
                    Target Role
                  </label>
                  <input
                    type="text"
                    id="sg-target-role"
                    className="form-input-custom"
                    value={skillGapRole}
                    onChange={(e) => setSkillGapRole(e.target.value)}
                    placeholder="Enter the role"
                  />
                </div>

                <div className="form-group-custom">
                  <label className="form-label-custom" htmlFor="sg-current-skills">
                    Your Current Skills
                  </label>
                  <textarea
                    id="sg-current-skills"
                    className="form-textarea-custom"
                    rows={5}
                    value={skillGapSkills}
                    onChange={(e) => setSkillGapSkills(e.target.value)}
                    placeholder="Enter skills"
                  />
                </div>

                <button
                  className="gold-submit-btn"
                  onClick={handleRunSkillGap}
                  disabled={isSkillGapAnalyzing}
                >
                  {isSkillGapAnalyzing ? (
                    <>
                      <span className="gold-spinner" />
                      <span>Generating response...</span>
                    </>
                  ) : (
                    <span>Analyze Readiness Score</span>
                  )}
                </button>

                {skillGapError && (
                  <div style={{ color: '#ef4444', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertCircle size={14} />
                    <span>{skillGapError}</span>
                  </div>
                )}

                {skillGapResult && (
                  <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                        Readiness Score:
                      </span>
                      <span
                        style={{
                          background: 'rgba(214, 169, 54, 0.15)',
                          border: '1px solid var(--primary-gold)',
                          color: 'var(--primary-gold)',
                          padding: '4px 12px',
                          borderRadius: '9999px',
                          fontSize: '12.5px',
                          fontWeight: 600,
                          textTransform: 'capitalize',
                        }}
                      >
                        {skillGapResult.overall_readiness}
                      </span>
                    </div>

                    <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      {skillGapResult.summary}
                    </p>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                      <div style={{ background: '#0E0E0D', padding: '12px', borderRadius: '8px', borderLeft: '3px solid #10b981' }}>
                        <div style={{ color: '#10b981', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                          ✓ Matched Skills ({skillGapResult.matched_skills.length})
                        </div>
                        <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {skillGapResult.matched_skills.join(', ') || 'None'}
                        </p>
                      </div>

                      <div style={{ background: '#0E0E0D', padding: '12px', borderRadius: '8px', borderLeft: '3px solid var(--primary-gold)' }}>
                        <div style={{ color: 'var(--primary-gold)', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                          🟡 Partial / Growing ({skillGapResult.partially_met_skills.length})
                        </div>
                        <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {skillGapResult.partially_met_skills.join(', ') || 'None'}
                        </p>
                      </div>

                      <div style={{ background: '#0E0E0D', padding: '12px', borderRadius: '8px', borderLeft: '3px solid #ef4444' }}>
                        <div style={{ color: '#ef4444', fontSize: '12px', fontWeight: 600, marginBottom: '6px' }}>
                          ❌ Missing Gaps ({skillGapResult.missing_skills.length})
                        </div>
                        <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {skillGapResult.missing_skills.join(', ') || 'None'}
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* VIEW: Tool 3 - Learning Roadmap */}
          {activeView === 'roadmap' && (
            <div className="tool-workspace-container">
              <div className="tool-view-header">
                <div>
                  <h2 className="tool-view-title">Learning Roadmap</h2>
                  <p className="tool-view-subtitle">
                    Build a structured milestone timeline with actionable checklists to reach your target role.
                  </p>
                </div>
                <button className="back-to-chat-btn" onClick={() => setActiveView('chat')}>
                  <ArrowLeft size={14} />
                  <span>Back to Chat</span>
                </button>
              </div>

              <div className="tool-card-panel">
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '14px' }}>
                  <div className="form-group-custom">
                    <label className="form-label-custom" htmlFor="rm-target-pos">
                      Target Position
                    </label>
                    <input
                      type="text"
                      id="rm-target-pos"
                      className="form-input-custom"
                      value={roadmapRole}
                      onChange={(e) => setRoadmapRole(e.target.value)}
                      placeholder="Enter the role"
                    />
                  </div>

                  <div className="form-group-custom">
                    <label className="form-label-custom" htmlFor="rm-timeframe">
                      Timeframe
                    </label>
                    <select
                      id="rm-timeframe"
                      className="form-select-custom"
                      value={roadmapTimeframe}
                      onChange={(e) => setRoadmapTimeframe(e.target.value)}
                    >
                      <option value="3 Months">3 Months (Accelerated)</option>
                      <option value="6 Months">6 Months (Standard)</option>
                      <option value="9 Months">9 Months (Comprehensive)</option>
                      <option value="12 Months">12 Months (Deep-Dive)</option>
                    </select>
                  </div>
                </div>

                <button
                  className="gold-submit-btn"
                  onClick={handleRunRoadmap}
                  disabled={isRoadmapGenerating}
                >
                  {isRoadmapGenerating ? (
                    <>
                      <span className="gold-spinner" />
                      <span>Generating response...</span>
                    </>
                  ) : (
                    <span>Generate Custom Roadmap</span>
                  )}
                </button>

                {roadmapError && (
                  <div style={{ color: '#ef4444', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertCircle size={14} />
                    <span>{roadmapError}</span>
                  </div>
                )}

                {roadmapResult && (
                  <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <p style={{ fontSize: '13.5px', color: 'var(--text-secondary)' }}>
                      {roadmapResult.summary}
                    </p>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {roadmapResult.milestones.map((m, idx) => (
                        <div
                          key={idx}
                          style={{
                            background: '#0E0E0D',
                            border: '1px solid var(--border-subtle)',
                            borderLeft: '3px solid var(--primary-gold)',
                            borderRadius: '10px',
                            padding: '16px',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--primary-gold)' }}>
                              Stage {idx + 1} &middot; {m.duration}
                            </span>
                          </div>
                          <h4 style={{ fontSize: '14px', color: 'var(--text-primary)', marginBottom: '8px' }}>
                            {m.title}
                          </h4>

                          {m.focus_skills.length > 0 && (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
                              {m.focus_skills.map((s, sIdx) => (
                                <span
                                  key={sIdx}
                                  style={{
                                    fontSize: '11px',
                                    background: 'rgba(214, 169, 54, 0.1)',
                                    color: 'var(--primary-gold)',
                                    padding: '2px 8px',
                                    borderRadius: '4px',
                                  }}
                                >
                                  {s}
                                </span>
                              ))}
                            </div>
                          )}

                          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {m.actions.map((act, aIdx) => {
                              const key = `${idx}-${aIdx}`;
                              const isDone = !!completedActions[key];
                              return (
                                <li
                                  key={aIdx}
                                  onClick={() => toggleActionDone(key)}
                                  style={{
                                    fontSize: '12.5px',
                                    color: isDone ? '#10b981' : 'var(--text-secondary)',
                                    textDecoration: isDone ? 'line-through' : 'none',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                  }}
                                >
                                  <CheckCircle2 size={13} color={isDone ? '#10b981' : 'var(--text-muted)'} />
                                  <span>{act}</span>
                                </li>
                              );
                            })}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* VIEW: Tool 4 - Job Matcher */}
          {activeView === 'matcher' && (
            <div className="tool-workspace-container">
              <div className="tool-view-header">
                <div>
                  <h2 className="tool-view-title">Job Matcher</h2>
                  <p className="tool-view-subtitle">
                    Discover live and verified technical opportunities aligned with your background.
                  </p>
                </div>
                <button className="back-to-chat-btn" onClick={() => setActiveView('chat')}>
                  <ArrowLeft size={14} />
                  <span>Back to Chat</span>
                </button>
              </div>

              <div className="tool-card-panel">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                  <div className="form-group-custom">
                    <label className="form-label-custom" htmlFor="jm-role">
                      Job Role
                    </label>
                    <input
                      type="text"
                      id="jm-role"
                      className="form-input-custom"
                      value={jobRole}
                      onChange={(e) => setJobRole(e.target.value)}
                      placeholder="Enter the role"
                    />
                  </div>

                  <div className="form-group-custom">
                    <label className="form-label-custom" htmlFor="jm-region">
                      Target Region
                    </label>
                    <select
                      id="jm-region"
                      className="form-select-custom"
                      value={jobRegion}
                      onChange={(e) => setJobRegion(e.target.value)}
                    >
                      <option value="all">🌐 All Focus Regions (India, US, Europe)</option>
                      <option value="in">🇮🇳 India</option>
                      <option value="us">🇺🇸 United States</option>
                      <option value="eu">🇪🇺 European Countries (UK, Germany, France, NL...)</option>
                    </select>
                  </div>

                  <div className="form-group-custom">
                    <label className="form-label-custom" htmlFor="jm-location">
                      City / Specific Location (Optional)
                    </label>
                    <input
                      type="text"
                      id="jm-location"
                      className="form-input-custom"
                      value={jobLocation}
                      onChange={(e) => setJobLocation(e.target.value)}
                      placeholder="Enter location"
                    />
                  </div>

                  <div className="form-group-custom">
                    <label className="form-label-custom" htmlFor="jm-skills">
                      Skills (Optional)
                    </label>
                    <input
                      type="text"
                      id="jm-skills"
                      className="form-input-custom"
                      value={jobSkills}
                      onChange={(e) => setJobSkills(e.target.value)}
                      placeholder="Enter skills"
                    />
                  </div>

                  <div className="form-group-custom" style={{ gridColumn: 'span 2' }}>
                    <label className="form-label-custom" htmlFor="jm-exp">
                      Experience Level (Optional)
                    </label>
                    <select
                      id="jm-exp"
                      className="form-select-custom"
                      value={jobExperience}
                      onChange={(e) => setJobExperience(e.target.value)}
                    >
                      <option value="">Any Experience</option>
                      <option value="entry">Entry Level</option>
                      <option value="mid">Mid Level</option>
                      <option value="senior">Senior Level</option>
                    </select>
                  </div>
                </div>

                <button
                  className="gold-submit-btn"
                  onClick={handleRunJobSearch}
                  disabled={isJobSearching}
                >
                  {isJobSearching ? (
                    <>
                      <span className="gold-spinner" />
                      <span>Generating response...</span>
                    </>
                  ) : (
                    <span>Search Matching Jobs</span>
                  )}
                </button>

                {jobError && (
                  <div style={{ color: '#ef4444', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertCircle size={14} />
                    <span>{jobError}</span>
                  </div>
                )}

                {jobResults !== null && (
                  <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div style={{ fontSize: '13.5px', color: 'var(--text-secondary)' }}>
                      Found {jobResults.length} matching position(s)
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
                      {jobResults.map((job, idx) => (
                        <div
                          key={idx}
                          style={{
                            background: '#0E0E0D',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: '10px',
                            padding: '14px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                          }}
                        >
                          <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                              <span style={{ fontSize: '10.5px', color: 'var(--primary-gold)', fontWeight: 600 }}>
                                {job.source === 'adzuna' ? 'Live Listing' : 'Verified Dataset'}
                              </span>
                              {job.experience_level && (
                                <span style={{ fontSize: '10.5px', color: '#10b981', textTransform: 'uppercase' }}>
                                  {job.experience_level}
                                </span>
                              )}
                            </div>
                            <h4 style={{ fontSize: '13.5px', color: 'var(--text-primary)', marginBottom: '4px' }}>
                              {job.title}
                            </h4>
                            <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                              {job.company} &middot; {job.location}
                            </div>
                            {job.description && (
                              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4, marginBottom: '8px' }}>
                                {job.description.slice(0, 150)}...
                              </p>
                            )}
                          </div>

                          <div>
                            {job.skills && job.skills.length > 0 && (
                              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                                Skills: {job.skills.join(', ')}
                              </div>
                            )}
                            {job.url && (
                              <a
                                href={job.url}
                                target="_blank"
                                rel="noreferrer"
                                style={{
                                  fontSize: '12px',
                                  color: 'var(--primary-gold)',
                                  textDecoration: 'none',
                                  fontWeight: 600,
                                }}
                              >
                                ↗ View Posting
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Toast Popup Notification */}
      {toastMessage && (
        <div className="toast-popup-gold">
          <span style={{ color: 'var(--primary-gold)', marginRight: '6px' }}>✓</span>
          {toastMessage}
        </div>
      )}
    </div>
  );
}
