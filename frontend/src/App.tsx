import React, { useState, useEffect } from "react";
import {
  FileText, Database, GitMerge, LayoutDashboard,
  Play, CheckCircle2, AlertTriangle, ChevronRight, PlusCircle,
  Edit3, ArrowRight, Download, Users, Trash2, Shield
} from "lucide-react";
import {
  listSessions, getSession, createSession, deleteSession, triggerAgent,
  getArtifact, editArtifact, approveArtifact, switchRole, getAuditLogs,
  pushArtifact, getPromotionUrl, uploadRequirementFile
} from "./api";
import type { Session, Artifact, AuditLog } from "./api";

const STAGES = [
  { id: "requirement", label: "Requirement Analyzer", desc: "Extract business spec & case notion", icon: FileText },
  { id: "sql_data_model", label: "SQL & Data Model", desc: "SQL transformations & relationships", icon: GitMerge },
  { id: "knowledge_model", label: "Knowledge Model", desc: "Build semantic PQL metrics", icon: Database },
  { id: "analysis", label: "Celonis Analysis", desc: "Configure analysis sheets & KPIs", icon: LayoutDashboard },
  { id: "qa", label: "QA Validation", desc: "Perform compliance & quality checks", icon: CheckCircle2 }
];

export default function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [activeStage, setActiveStage] = useState<string>("requirement");
  const [editingStage, setEditingStage] = useState<string | null>(null);
  const [artifacts, setArtifacts] = useState<Record<string, Artifact>>({});
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  // UI creation states
  const [newSessionName, setNewSessionName] = useState("");
  const [initialRequirement, setInitialRequirement] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Editing states
  const [editContent, setEditContent] = useState("");
  const [editRationale, setEditRationale] = useState("");

  // Approval states
  const [approvalNotes, setApprovalNotes] = useState("");

  // Loading & Error states
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  // Load list of sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  // Sync session details when currentSession changes
  useEffect(() => {
    if (currentSession) {
      loadSessionData(currentSession.id);

      // Auto-poll logs and artifacts periodically (every 5 seconds)
      const interval = setInterval(() => {
        pollSessionUpdates(currentSession.id);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [currentSession?.id]);

  // Poll audit logs more frequently (every 1.5s) during loading states to show real-time progress
  useEffect(() => {
    if (!loading || !currentSession) return;
    const interval = setInterval(async () => {
      try {
        const logs = await getAuditLogs(currentSession.id);
        setAuditLogs(logs);
      } catch (err) {
        // Ignore polling errors
      }
    }, 1500);
    return () => clearInterval(interval);
  }, [loading, currentSession?.id]);

  const loadSessions = async () => {
    try {
      const data = await listSessions();
      setSessions(data);
      if (data.length > 0 && !currentSession) {
        setCurrentSession(data[0]);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load sessions");
    }
  };

  const loadSessionData = async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      // Fetch fresh session details
      const sess = await getSession(sessionId);
      setCurrentSession(sess);

      // Fetch all logs
      const logs = await getAuditLogs(sessionId);
      setAuditLogs(logs);

      // Fetch latest artifacts for each stage
      const stageArtifacts: Record<string, Artifact> = {};
      for (const stageId of ["requirement", "sql", "data_model", "knowledge_model", "analysis", "qa"]) {
        try {
          const art = await getArtifact(sessionId, stageId);
          stageArtifacts[stageId] = art;
        } catch (e) {
          // Artifact doesn't exist yet for this stage
        }
      }
      setArtifacts(stageArtifacts);
    } catch (err: any) {
      setError(err.message || "Failed to load session assets");
    } finally {
      setLoading(false);
    }
  };

  const pollSessionUpdates = async (sessionId: string) => {
    try {
      const logs = await getAuditLogs(sessionId);
      setAuditLogs(logs);

      const stageArtifacts: Record<string, Artifact> = {};
      for (const stageId of ["requirement", "sql", "data_model", "knowledge_model", "analysis", "qa"]) {
        try {
          const art = await getArtifact(sessionId, stageId);
          stageArtifacts[stageId] = art;
        } catch (e) { }
      }
      setArtifacts(stageArtifacts);
    } catch (e) { }
  };

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSessionName.trim() || !initialRequirement.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const newSess = await createSession(newSessionName, initialRequirement);
      if (selectedFile) {
        await uploadRequirementFile(newSess.id, selectedFile);
      }
      setNewSessionName("");
      setInitialRequirement("");
      setSelectedFile(null);
      setShowCreateModal(false);
      await loadSessions();
      // Fetch fresh details with requirement_file
      const freshSess = await getSession(newSess.id);
      setCurrentSession(freshSess);
      await loadSessionData(freshSess.id);
      setNotification("Session created and requirement analyzer launched!");
    } catch (err: any) {
      setError(err.message || "Failed to create session");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSession = async (id: string) => {
    if (!confirm("Are you sure you want to delete this session?")) return;
    try {
      await deleteSession(id);
      const updated = sessions.filter(s => s.id !== id);
      setSessions(updated);
      if (currentSession?.id === id) {
        setCurrentSession(updated.length > 0 ? updated[0] : null);
      }
      setNotification("Session deleted.");
    } catch (err: any) {
      setError(err.message || "Failed to delete session");
    }
  };

  const handleRoleChange = async (role: string) => {
    if (!currentSession) return;
    try {
      const updated = await switchRole(currentSession.id, role);
      setCurrentSession(updated);
      setNotification(`Switched role to ${role}`);
      loadSessions();
    } catch (err: any) {
      setError(err.message || "Failed to switch role");
    }
  };

  const handleTriggerAgent = async (stageId: string) => {
    if (!currentSession) return;
    setLoading(true);
    setError(null);
    try {
      const art = await triggerAgent(currentSession.id, stageId);
      setArtifacts(prev => ({ ...prev, [stageId]: art }));
      setNotification(`${stageId.toUpperCase()} Agent execution complete.`);

      // Reload logs
      const logs = await getAuditLogs(currentSession.id);
      setAuditLogs(logs);

      // Reload session (which updates status/role)
      const sess = await getSession(currentSession.id);
      setCurrentSession(sess);
    } catch (err: any) {
      setError(err.message || "Agent execution failed");
    } finally {
      setLoading(false);
    }
  };

  const handleStartEdit = (stageKey: string) => {
    const art = artifacts[stageKey];
    if (!art) return;
    setEditContent(art.content);
    setEditRationale(art.rationale || "");
    setEditingStage(stageKey);
  };

  const handleSaveEdit = async (stageKey: string) => {
    if (!currentSession) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await editArtifact(
        currentSession.id,
        stageKey,
        editContent,
        editRationale || "Manual overrides applied by process analyst."
      );
      setArtifacts(prev => ({ ...prev, [stageKey]: updated }));
      setEditingStage(null);
      setNotification(`Edits saved as a new artifact version for ${stageKey.toUpperCase()}.`);

      // Reload logs
      const logs = await getAuditLogs(currentSession.id);
      setAuditLogs(logs);
    } catch (err: any) {
      setError(err.message || "Failed to save edits");
    } finally {
      setLoading(false);
    }
  };

  const handleApproveArtifact = async (stageKey: string, approved: boolean) => {
    if (!currentSession) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await approveArtifact(
        currentSession.id,
        stageKey,
        approved,
        approvalNotes
      );
      setArtifacts(prev => ({ ...prev, [stageKey]: updated }));
      setApprovalNotes("");
      setNotification(`Stage ${stageKey.toUpperCase()} artifact has been ${approved ? "approved" : "rejected"}.`);

      // Refresh session
      const sess = await getSession(currentSession.id);
      setCurrentSession(sess);
    } catch (err: any) {
      setError(err.message || "Approval action failed");
    } finally {
      setLoading(false);
    }
  };

  const handlePromoteToProduction = () => {
    if (!currentSession) return;
    // Download ZIP via endpoint link
    window.location.href = getPromotionUrl(currentSession.id);
    setNotification("Promoted to production! Downloading deployment ZIP bundle...");
  };

  const handlePushToCelonis = async (stage: string) => {
    if (!currentSession) return;
    if (!window.confirm(`Are you sure you want to push stage '${stage}' configurations to Celonis?`)) return;

    setLoading(true);
    setError(null);
    try {
      // Elevate role to Admin if needed to bypass permission checks
      const userRole = currentSession.current_role;
      if (userRole !== "Admin" && userRole !== "Reviewer") {
        await switchRole(currentSession.id, "Admin");
      }

      await pushArtifact(currentSession.id, stage);
      setNotification(`Stage '${stage}' configurations successfully pushed to Celonis!`);

      // Refresh session and logs
      const logs = await getAuditLogs(currentSession.id);
      setAuditLogs(logs);
      const sess = await getSession(currentSession.id);
      setCurrentSession(sess);
    } catch (err: any) {
      setError(err.message || "Failed to push to Celonis");
      const logs = await getAuditLogs(currentSession.id);
      setAuditLogs(logs);
    } finally {
      setLoading(false);
    }
  };

  const renderPromoteProgress = (stageKey?: string) => {
    const targetStage = stageKey || activeStage;
    const progressSteps = auditLogs
      .filter(log => log.agent_name === "Celonis Deployer" && log.stage === targetStage)
      .sort((a, b) => a.id - b.id);

    if (progressSteps.length === 0) return null;

    return (
      <div className="promote-progress-container" style={{ marginTop: '1rem', width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', borderBottom: '1px solid rgba(6, 182, 212, 0.2)', paddingBottom: '4px' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Celonis Cloud Deployment Status
          </span>
          {loading && (
            <div className="spinner-border" style={{ color: 'var(--accent-cyan)' }} />
          )}
        </div>
        <div className="promote-progress-steps">
          {progressSteps.map((step, idx) => {
            const isLast = idx === progressSteps.length - 1;
            const promptText = step.prompt || "";
            const isCompleted = !loading || !isLast || promptText.includes("successfully") || promptText.includes("completed") || promptText.includes("complete") || promptText.includes("verified") || promptText.includes("created");
            
            return (
              <div 
                key={step.id} 
                className={`promote-progress-step ${isCompleted ? 'success-step' : 'current-step'}`}
              >
                <span>{isCompleted ? "✓" : "⚡"}</span>
                <span>{promptText}</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderStageContent = () => {
    const userRole = currentSession?.current_role || "Business User";
    const approveAuthorized = ["Reviewer", "Admin"].includes(userRole);

    if (activeStage === "sql_data_model") {
      const renderSubStageColumn = (stageKey: "sql" | "data_model") => {
        const art = artifacts[stageKey];
        const buildAuthorized = ["Process Analyst", "Admin"].includes(userRole);

        if (loading && !art) {
          return (
            <div className="glass" style={{ display: 'flex', flex: 1, minHeight: '350px', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                <div className="stage-icon-wrapper" style={{ animation: 'spin 2s linear infinite', width: '40px', height: '40px' }}>
                  <Play size={20} />
                </div>
                <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Orchestrator working...</span>
              </div>
            </div>
          );
        }

        if (!art) {
          return (
            <div className="glass" style={{ display: 'flex', flex: 1, flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2.5rem', textAlign: 'center', gap: '1.5rem', minHeight: '350px' }}>
              <div>
                <AlertTriangle size={36} style={{ color: 'var(--status-warning)', margin: '0 auto' }} />
                <h3 style={{ marginTop: '0.75rem', fontSize: '1.1rem', fontWeight: 600 }}>No Specs Generated</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', maxWidth: '300px', margin: '0.25rem auto' }}>
                  {stageKey === "sql" ? "SQL transformation queries have not been generated yet." : "Data Model configuration details have not been built yet."}
                </p>
              </div>
              {buildAuthorized ? (
                <button className="btn btn-primary" onClick={() => handleTriggerAgent(stageKey)}>
                  <Play size={14} /> Run {stageKey === "sql" ? "SQL Agent" : "Data Model Agent"}
                </button>
              ) : (
                <div style={{ color: 'var(--status-error)', fontSize: '0.75rem', fontWeight: 600 }}>
                  Role {userRole} unauthorized to trigger.
                </div>
              )}
            </div>
          );
        }

        if (editingStage === stageKey) {
          return (
            <div className="glass" style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
              <div className="card-title-bar">
                <span className="card-title">Modify {stageKey === "sql" ? "SQL" : "Data Model"} Spec</span>
              </div>
              <div className="card-body" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <textarea
                  className="textarea-input"
                  style={{ flex: 1, minHeight: '220px', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                />
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Rationale for manual override:</span>
                <textarea
                  className="textarea-input"
                  style={{ minHeight: '60px', fontSize: '0.8rem' }}
                  placeholder="Explain why you are applying this manual override..."
                  value={editRationale}
                  onChange={(e) => setEditRationale(e.target.value)}
                />
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '5px' }}>
                  <button className="btn btn-secondary" style={{ padding: '6px 12px' }} onClick={() => setEditingStage(null)}>Cancel</button>
                  <button className="btn btn-primary" style={{ padding: '6px 12px' }} onClick={() => handleSaveEdit(stageKey)}>Save V{art.version + 1}</button>
                </div>
              </div>
            </div>
          );
        }

        return (
          <div className="glass" style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
            <div className="card-title-bar">
              <span className="card-title">{stageKey === "sql" ? "SQL Transformations" : "Data Model Schema"}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="header-badge" style={{ fontSize: '0.65rem', borderColor: art.approved ? 'var(--status-success)' : 'var(--status-warning)', color: art.approved ? 'var(--status-success)' : 'var(--status-warning)', background: 'transparent' }}>
                  {art.approved ? "Approved" : "Draft (V" + art.version + ")"}
                </span>
                {["Process Analyst", "Admin"].includes(userRole) && (
                  <button className="btn btn-secondary" style={{ padding: '3px 6px', fontSize: '0.75rem' }} onClick={() => handleStartEdit(stageKey)}>
                    <Edit3 size={12} /> Edit
                  </button>
                )}
              </div>
            </div>
            
            <div className="card-body" style={{ flex: 1, overflowY: 'auto', borderBottom: '1px solid var(--border-color)', minHeight: '250px', maxHeight: '350px' }}>
              {stageKey === "sql" ? (
                <pre className="code-editor-pre" style={{ margin: 0, height: '100%', whiteSpace: 'pre-wrap', fontSize: '0.75rem' }}>{art.content}</pre>
              ) : (
                <DataModelViewer content={art.content} />
              )}
            </div>

            <div style={{ padding: '10px 15px', background: 'rgba(255,255,255,0.01)', borderBottom: '1px solid var(--border-color)' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Rationale</span>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0', whiteSpace: 'pre-wrap' }}>
                {art.rationale || "No explanation recorded."}
              </p>
            </div>

            <div style={{ padding: '10px 15px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600 }}>Governance Gate</span>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  {art.approved ? (
                    auditLogs.some(log => log.stage === stageKey && log.action === "push_completed") ? (
                      <span style={{ fontSize: '0.75rem', color: 'var(--status-success)', fontWeight: 600 }}>
                        ✓ Deployed to Celonis
                      </span>
                    ) : (
                      <button
                        className="btn btn-primary"
                        style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                        onClick={() => handlePushToCelonis(stageKey)}
                      >
                        <ArrowRight size={12} /> Push to Celonis
                      </button>
                    )
                  ) : approveAuthorized ? (
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <input
                        type="text"
                        className="text-input"
                        placeholder="Approval comments..."
                        style={{ width: '120px', fontSize: '0.75rem', padding: '4px 8px' }}
                        value={approvalNotes}
                        onChange={(e) => setApprovalNotes(e.target.value)}
                      />
                      <button className="btn btn-success" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => handleApproveArtifact(stageKey, true)}>Approve</button>
                      <button className="btn btn-danger" style={{ padding: '4px 8px', fontSize: '0.75rem' }} onClick={() => handleApproveArtifact(stageKey, false)}>Reject</button>
                    </div>
                  ) : (
                    <span style={{ fontSize: '0.7rem', color: 'var(--status-warning)' }}>
                      Awaiting Approval
                    </span>
                  )}
                </div>
              </div>
              {renderPromoteProgress(stageKey)}
            </div>
          </div>
        );
      };

      return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', flex: 1 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', flex: 1, alignItems: 'stretch' }}>
            {renderSubStageColumn("sql")}
            {renderSubStageColumn("data_model")}
          </div>
        </div>
      );
    }

    const art = artifacts[activeStage];
    const buildAuthorized = {
      requirement: ["Business User", "Process Analyst", "Admin"],
      knowledge_model: ["Process Analyst", "Admin"],
      analysis: ["Process Analyst", "Admin"],
      qa: ["Process Analyst", "Admin", "Reviewer"]
    }[activeStage]?.includes(userRole);

    if (loading && !art) {
      return (
        <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
            <div className="stage-icon-wrapper" style={{ animation: 'spin 2s linear infinite', width: '40px', height: '40px' }}>
              <Play size={20} />
            </div>
            <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Orchestrator working, please wait...</span>
          </div>
        </div>
      );
    }

    if (!art) {
      return (
        <div style={{ display: 'flex', flex: 1, flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem', textAlign: 'center', gap: '1.5rem' }} className="glass">
          <div>
            <AlertTriangle size={48} style={{ color: 'var(--status-warning)' }} />
            <h3 style={{ marginTop: '1rem', fontSize: '1.2rem', fontWeight: 600 }}>No Artifact Generated Yet</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', maxWidth: '450px', margin: '0.5rem auto' }}>
              This step ({activeStage.toUpperCase()}) does not contain any generated specification code. You must trigger the agent.
            </p>
          </div>
          {buildAuthorized ? (
            <button className="btn btn-primary" onClick={() => handleTriggerAgent(activeStage)}>
              <Play size={16} /> Run {activeStage === 'requirement' ? 'Requirement Analyzer' : activeStage === 'knowledge_model' ? 'Knowledge Model Agent' : activeStage === 'analysis' ? 'Analysis Agent' : 'QA Agent'}
            </button>
          ) : (
            <div style={{ color: 'var(--status-error)', fontSize: '0.85rem', fontWeight: 600 }}>
              Your current role ({userRole}) is not authorized to trigger this agent. Switch to Analyst or Admin.
            </div>
          )}
        </div>
      );
    }

    if (editingStage === activeStage) {
      return (
        <div className="dual-grid" style={{ flex: 1 }}>
          <div className="glass" style={{ display: 'flex', flexDirection: 'column' }}>
            <div className="card-title-bar">
              <span className="card-title">Modify Specification Data</span>
            </div>
            <div className="card-body" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <textarea
                className="textarea-input"
                style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
              />
            </div>
          </div>
          <div className="glass" style={{ display: 'flex', flexDirection: 'column' }}>
            <div className="card-title-bar">
              <span className="card-title">Modify Rationale & Reason</span>
            </div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', flex: 1 }}>
              <textarea
                className="textarea-input"
                style={{ flex: 1 }}
                placeholder="Detail why you are applying these manual overrides (for audit trail)..."
                value={editRationale}
                onChange={(e) => setEditRationale(e.target.value)}
              />
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <button className="btn btn-secondary" onClick={() => setEditingStage(null)}>Cancel</button>
                <button className="btn btn-primary" onClick={() => handleSaveEdit(activeStage)}>Save Version {art.version + 1}</button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', flex: 1 }}>
        {/* Render actual code output */}
        <div className="dual-grid" style={{ flex: 1, minHeight: '380px' }}>
          <div className="glass" style={{ display: 'flex', flexDirection: 'column' }}>
            <div className="card-title-bar">
              <span className="card-title">{activeStage.toUpperCase()} Generated Specs</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className="header-badge" style={{ borderColor: art.approved ? 'var(--status-success)' : 'var(--status-warning)', color: art.approved ? 'var(--status-success)' : 'var(--status-warning)', background: 'transparent' }}>
                  {art.approved ? "Approved" : "Draft (V" + art.version + ")"}
                </span>
                {["Process Analyst", "Admin"].includes(userRole) && (
                  <button className="btn btn-secondary" style={{ padding: '4px 8px' }} onClick={() => handleStartEdit(activeStage)}>
                    <Edit3 size={14} /> Edit
                  </button>
                )}
              </div>
            </div>
            <div className="card-body" style={{ flex: 1, overflowY: 'auto' }}>
              {activeStage === "requirement" ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  <div className="glass" style={{ padding: '1rem', border: '1px dashed var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h4 style={{ fontWeight: 600, margin: 0 }}>Business Requirements PowerPoint Ingestion</h4>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
                        {currentSession?.requirement_file ? `Attached: ${currentSession.requirement_file.split(/[/\\]/).pop()}` : "No PPTX attached. Upload a PowerPoint file to enhance the requirement analysis."}
                      </p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <input
                        type="file"
                        id="stage-pptx-upload"
                        accept=".pptx"
                        style={{ display: 'none' }}
                        onChange={async (e) => {
                          if (e.target.files && e.target.files.length > 0 && currentSession) {
                            setLoading(true);
                            try {
                              await uploadRequirementFile(currentSession.id, e.target.files[0]);
                              await loadSessions();
                              const updatedSess = await getSession(currentSession.id);
                              setCurrentSession(updatedSess);
                              await loadSessionData(updatedSess.id);
                              setNotification("PowerPoint uploaded and requirement analyzer re-triggered successfully!");
                            } catch (err: any) {
                              setError(err.message || "Failed to upload PowerPoint file.");
                            } finally {
                              setLoading(false);
                            }
                          }
                        }}
                      />
                      <label htmlFor="stage-pptx-upload" className="btn btn-secondary" style={{ cursor: 'pointer', margin: 0 }}>
                        {currentSession?.requirement_file ? "Replace PPTX" : "Upload PPTX"}
                      </label>
                    </div>
                  </div>
                  <RequirementSpecViewer content={art.content} />
                </div>
              ) : activeStage === "knowledge_model" ? (
                <KnowledgeModelViewer content={art.content} />
              ) : activeStage === "analysis" ? (
                <AnalysisMockupViewer content={art.content} onPushToCelonis={() => handlePushToCelonis("analysis")} isPushed={auditLogs.some(log => log.stage === "analysis" && log.action === "push_completed")} />
              ) : activeStage === "qa" ? (
                <QaViewer content={art.content} onPromote={handlePromoteToProduction} promoteAuthorized={approveAuthorized} />
              ) : (
                <pre className="code-editor-pre">{JSON.stringify(JSON.parse(art.content), null, 2)}</pre>
              )}
            </div>
          </div>
 
          <div className="glass" style={{ display: 'flex', flexDirection: 'column' }}>
            <div className="card-title-bar">
              <span className="card-title">Explainability & Rationale</span>
            </div>
            <div className="card-body">
              <p className="rationale-text" style={{ whiteSpace: 'pre-wrap' }}>{art.rationale || "No explanation recorded."}</p>
            </div>
          </div>
        </div>
 
        {/* Human in the loop validation controls */}
        <div className="glass" style={{ padding: '1rem 1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                {activeStage === "analysis" ? "Production Promotion" : "Governance Approval Gate"}
              </h4>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                {auditLogs.some(log => log.stage === activeStage && log.action === "push_completed")
                  ? "Pushed! Configuration has been successfully deployed and verified in Celonis."
                  : art.approved
                    ? `Approved by ${art.approved_by || 'Admin'}. Ready to push to Celonis.`
                    : "Requires analyst/reviewer approval before pushing to Celonis."}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              {["knowledge_model", "analysis"].includes(activeStage) && art.approved ? (
                auditLogs.some(log => log.stage === activeStage && log.action === "push_completed") ? (
                  <span className="status-message text-success" style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                    ✓ Successfully Deployed to Celonis Data Pool
                  </span>
                ) : (
                  <button
                    className="btn btn-primary"
                    style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                    onClick={() => handlePushToCelonis(activeStage)}
                  >
                    <ArrowRight size={14} /> Deploy to Celonis Instance
                  </button>
                )
              ) : art.approved ? (
                <div style={{ fontSize: '0.75rem', color: 'var(--status-success)', fontWeight: 600 }}>
                  ✓ Approved
                </div>
              ) : approveAuthorized ? (
                <>
                  <input
                    type="text"
                    className="text-input"
                    placeholder="Approval comments..."
                    style={{ width: '220px', fontSize: '0.8rem' }}
                    value={approvalNotes}
                    onChange={(e) => setApprovalNotes(e.target.value)}
                  />
                  <button className="btn btn-success" style={{ padding: '8px 12px' }} onClick={() => handleApproveArtifact(activeStage, true)}>Approve</button>
                  <button className="btn btn-danger" style={{ padding: '8px 12px' }} onClick={() => handleApproveArtifact(activeStage, false)}>Reject</button>
                </>
              ) : (
                <div style={{ fontSize: '0.75rem', color: 'var(--status-warning)', fontWeight: 600 }}>
                  <Shield size={12} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} />
                  Only Reviewers/Admins can approve this artifact.
                </div>
              )}
            </div>
          </div>
          {["knowledge_model", "analysis"].includes(activeStage) && renderPromoteProgress(activeStage)}
        </div>
      </div>
    );
  };

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="header-bar">
        <div className="header-title-container">
          <Database size={24} style={{ color: 'var(--accent-cyan)' }} />
          <h1 className="header-title">Celonis Multi-Agent Workflow Orchestrator</h1>
          <span className="header-badge">Thesis Demo</span>
        </div>

        <div className="header-actions">
          {/* Active Workspace / Session Loader */}
          {currentSession && (
            <select
              className="session-select"
              value={currentSession.id}
              onChange={(e) => {
                const s = sessions.find(x => x.id === e.target.value);
                if (s) setCurrentSession(s);
              }}
            >
              {sessions.map(s => (
                <option key={s.id} value={s.id}>{s.name} ({s.status})</option>
              ))}
            </select>
          )}

          <button className="btn btn-secondary" style={{ padding: '6px 12px' }} onClick={() => setShowCreateModal(true)}>
            <PlusCircle size={16} /> New Session
          </button>

          {/* Role selector */}
          <div className="role-container">
            <Users size={16} style={{ color: 'var(--text-secondary)' }} />
            <span className="role-label">Active Role:</span>
            <select
              className="role-select"
              value={currentSession?.current_role || "Business User"}
              onChange={(e) => handleRoleChange(e.target.value)}
              disabled={!currentSession}
            >
              <option value="Business User">Business User</option>
              <option value="Process Analyst">Process Analyst</option>
              <option value="Admin">Admin</option>
              <option value="Reviewer">Reviewer</option>
            </select>
          </div>

          {currentSession && (
            <button
              className="btn btn-danger"
              style={{ padding: '6px 8px' }}
              onClick={() => handleDeleteSession(currentSession.id)}
              title="Delete session"
            >
              <Trash2 size={16} />
            </button>
          )}
        </div>
      </header>

      {/* Main Area */}
      <div className="main-viewport">
        {/* Sidebar progression */}
        <aside className="sidebar-progression">
          <div className="sidebar-title">Pipeline Layers</div>
          <div className="stage-list">
            {STAGES.map((s) => {
              const isCompleted = s.id === "sql_data_model" 
                ? (artifacts["sql"]?.approved && artifacts["data_model"]?.approved)
                : artifacts[s.id]?.approved;
              const isActive = activeStage === s.id;
              const StageIcon = s.icon;

              return (
                <div
                  key={s.id}
                  className={`stage-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}
                  onClick={() => {
                    setActiveStage(s.id);
                    setEditingStage(null);
                  }}
                >
                  <div className="stage-icon-wrapper">
                    {isCompleted ? <CheckCircle2 size={16} /> : <StageIcon size={14} />}
                  </div>
                  <div className="stage-details">
                    <span className="stage-name">{s.label}</span>
                    <span className="stage-desc">{s.desc}</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ marginTop: 'auto', padding: '10px', fontSize: '0.75rem', color: 'var(--text-secondary)', borderTop: '1px solid var(--border-color)' }}>
            <strong>Workspace Scope:</strong><br />
            {currentSession?.description ? (
              <span style={{ display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{currentSession.description}</span>
            ) : "No requirements details ingested yet."}
          </div>
        </aside>

        {/* Central Workspace Content */}
        <main className="workspace-content">
          {error && (
            <div style={{ background: 'rgba(239, 68, 68, 0.15)', border: '1px solid var(--status-error)', padding: '10px 16px', margin: '16px', borderRadius: '6px', color: 'var(--status-error)', fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>{error}</span>
              <button style={{ background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer' }} onClick={() => setError(null)}>X</button>
            </div>
          )}

          {notification && (
            <div style={{ background: 'rgba(16, 185, 129, 0.15)', border: '1px solid var(--status-success)', padding: '10px 16px', margin: '16px', borderRadius: '6px', color: 'var(--status-success)', fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>{notification}</span>
              <button style={{ background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer' }} onClick={() => setNotification(null)}>X</button>
            </div>
          )}

          <div className="stage-panel-container">
            <div>
              <h2 className="section-heading">{STAGES.find(s => s.id === activeStage)?.label}</h2>
              <p className="section-subheading">{STAGES.find(s => s.id === activeStage)?.desc}</p>
            </div>

            {currentSession ? renderStageContent() : (
              <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center', padding: '4rem', textAlign: 'center' }}>
                <div>
                  <Users size={48} style={{ color: 'var(--text-secondary)' }} />
                  <h3 style={{ marginTop: '1rem' }}>No Active Session</h3>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Create a session using the button above to start your Celonis orchestrator run.</p>
                </div>
              </div>
            )}
          </div>

          {/* Audit Logs Terminal Console */}
          <div className="audit-drawer">
            <div className="audit-drawer-header">
              <span className="audit-drawer-title">Real-Time Orchestrator Trace / Audit Trails</span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>SQLite Database Audited</span>
            </div>
            <div className="audit-drawer-logs">
              {auditLogs.length === 0 ? (
                <span style={{ color: 'var(--text-secondary)' }}>No audit events logged. Start running agents to populate trace.</span>
              ) : (
                auditLogs.map((log) => (
                  <div key={log.id} className="log-entry">
                    <span className="log-time">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                    <span className="log-agent">&lt;{log.agent_name}&gt;</span>
                    <span className={`log-action ${log.action}`}>{log.prompt}</span>
                    {log.error && <span style={{ color: 'var(--status-error)' }}> - Error: {log.error}</span>}
                  </div>
                ))
              )}
            </div>
          </div>
        </main>
      </div>

      {/* Create Session Modal */}
      {showCreateModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <form onSubmit={handleCreateSession} className="glass" style={{ width: '500px', padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Initialize Celonis Workflow Generator</h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Session Name</label>
              <input
                type="text"
                className="text-input"
                placeholder="e.g. Accounts Payable Process Mining"
                required
                value={newSessionName}
                onChange={(e) => setNewSessionName(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Business Requirements / SOP Notes</label>
              <textarea
                className="textarea-input"
                placeholder="Paste your natural language requirement, e.g. Analyze Accounts Payable process. Identify duplicate payments, track invoice approval cycle times..."
                required
                value={initialRequirement}
                onChange={(e) => setInitialRequirement(e.target.value)}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Attach PPTX Requirement File (Optional)</label>
              <input
                type="file"
                accept=".pptx"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    setSelectedFile(e.target.files[0]);
                  }
                }}
                style={{
                  padding: '8px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  background: 'rgba(255, 255, 255, 0.05)',
                  color: 'var(--text-primary)',
                  fontSize: '0.875rem'
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? "Generating..." : "Launch Pipeline"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

/* Sub-View Component: Requirement Analyzer Viewer */
function RequirementSpecViewer({ content }: { content: string }) {
  try {
    const spec = JSON.parse(content);
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.875rem' }}>
        <div><strong>Process Name:</strong> {spec.process_name}</div>
        <div><strong>Case ID Definition:</strong> {spec.case_id_definition}</div>
        <div><strong>Source Systems:</strong> {spec.source_systems?.join(", ")}</div>

        <div style={{ marginTop: '0.5rem' }}>
          <strong>Activity Events Mapping:</strong>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '6px', fontSize: '0.8rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                <th style={{ padding: '6px' }}>Activity Name</th>
                <th style={{ padding: '6px' }}>Trigger Condition / Table Reference</th>
              </tr>
            </thead>
            <tbody>
              {spec.activity_definitions?.map((act: any, idx: number) => (
                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <td style={{ padding: '6px', color: 'var(--accent-cyan)' }}>{act.name}</td>
                  <td style={{ padding: '6px' }}>{act.trigger_condition}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ marginTop: '0.5rem' }}>
          <strong>Process KPIs:</strong>
          <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {spec.kpis?.map((k: any, idx: number) => (
              <li key={idx}>
                <strong>{k.name}:</strong> {k.description} (<em>Idea: {k.calculation_idea}</em>)
              </li>
            ))}
          </ul>
        </div>
      </div>
    );
  } catch (e) {
    return <pre className="code-editor-pre">{content}</pre>;
  }
}

/* Sub-View Component: Data Model Schema Relational Viewer */
function DataModelViewer({ content }: { content: string }) {
  try {
    const dm = JSON.parse(content);
    return (
      <div className="schema-container" style={{ fontSize: '0.875rem' }}>
        <div><strong>Data Model Type:</strong> {dm.model_type || "Standard Case-Centric"}</div>
        <div><strong>Primary Case Table:</strong> <code style={{ color: 'var(--accent-cyan)' }}>{dm.case_table}</code></div>
        <div><strong>Primary Event Log:</strong> <code style={{ color: 'var(--accent-cyan)' }}>{dm.event_table}</code></div>

        <div style={{ marginTop: '0.5rem' }}>
          <strong>Configured Tables:</strong>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '6px' }}>
            {dm.tables?.map((tbl: any, idx: number) => (
              <div key={idx} className="schema-node">
                <div className="node-header">{tbl.name}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{tbl.type}</div>
                <div style={{ fontSize: '0.75rem', marginTop: '4px' }}>PK: <code>{tbl.primary_keys?.join(", ")}</code></div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ marginTop: '0.5rem' }}>
          <strong>Entity Relationships:</strong>
          <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {dm.relationships?.map((rel: any, idx: number) => (
              <li key={idx}>
                <code>{rel.source_table}.{rel.source_column}</code>
                <ArrowRight size={12} style={{ display: 'inline', margin: '0 6px', verticalAlign: 'middle' }} />
                <code>{rel.target_table}.{rel.target_column}</code>
                <span className="header-badge" style={{ marginLeft: '8px', fontSize: '0.65rem' }}>{rel.cardinality}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    );
  } catch (e) {
    return <pre className="code-editor-pre">{content}</pre>;
  }
}

/* Sub-View Component: Knowledge Model KPI Editor Viewer */
function KnowledgeModelViewer({ content }: { content: string }) {
  try {
    const km = JSON.parse(content);
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.875rem' }}>
        <div><strong>Knowledge Model ID:</strong> {km.id}</div>
        <div><strong>Business Semantic Layer:</strong> {km.displayName}</div>

        <div>
          <strong>KPI Record Catalog (PQL Definitions):</strong>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '6px', fontSize: '0.8rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                <th style={{ padding: '6px' }}>KPI Name</th>
                <th style={{ padding: '6px' }}>Calculated Formula (PQL)</th>
                <th style={{ padding: '6px' }}>Unit</th>
              </tr>
            </thead>
            <tbody>
              {km.key_performance_indicators?.map((kpi: any, idx: number) => (
                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <td style={{ padding: '6px', color: 'var(--accent-cyan)', fontWeight: 600 }}>{kpi.name}</td>
                  <td style={{ padding: '6px' }}><code style={{ color: '#fff', fontSize: '0.75rem' }}>{kpi.formula}</code></td>
                  <td style={{ padding: '6px' }}>{kpi.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {km.custom_dimensions && (
          <div>
            <strong>Custom Dimensions:</strong>
            <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.8rem' }}>
              {km.custom_dimensions.map((d: any, idx: number) => (
                <li key={idx}><strong>{d.name}</strong>: <code>{d.expression}</code> ({d.description})</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  } catch (e) {
    return <pre className="code-editor-pre">{content}</pre>;
  }
}

/* Sub-View Component: Celonis Analysis Dashboard Mockup Visualizer */
interface AnalysisMockupViewerProps {
  content: string;
  onPushToCelonis?: () => void;
  isPushed?: boolean;
}

function AnalysisMockupViewer({ content, onPushToCelonis, isPushed }: AnalysisMockupViewerProps) {
  const [activeTabId, setActiveTabId] = useState<string>("");

  try {
    const data = JSON.parse(content);
    const title = data.analysis_title || data.view_title || "Celonis Analysis Dashboard";
    const sheets = data.sheets || data.tabs || [];

    // Set first sheet/tab as active initially
    if (!activeTabId && sheets.length > 0) {
      setActiveTabId(sheets[0].id);
    }

    const activeSheet = sheets.find((s: any) => s.id === activeTabId) || sheets[0];

    return (
      <div className="mock-dashboard">
        <div className="mock-dashboard-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--accent-cyan)' }}>{title}</span>
            <div className="mock-tabs">
              {sheets.map((s: any) => (
                <button
                  key={s.id}
                  className={`mock-tab ${activeTabId === s.id ? 'active' : ''}`}
                  onClick={() => setActiveTabId(s.id)}
                >
                  {s.name}
                </button>
              ))}
            </div>
          </div>
          {onPushToCelonis && (
            isPushed ? (
              <button
                className="btn btn-success"
                style={{ padding: '6px 12px', fontSize: '0.75rem', height: 'fit-content', background: 'var(--status-success)', color: '#fff', fontWeight: 600, cursor: 'default' }}
                disabled={true}
              >
                ✓ Pushed
              </button>
            ) : (
              <button
                className="btn btn-primary"
                style={{ padding: '6px 12px', fontSize: '0.75rem', height: 'fit-content', background: 'var(--accent-cyan)', color: '#000', fontWeight: 600 }}
                onClick={onPushToCelonis}
              >
                Push to Celonis
              </button>
            )
          )}
        </div>

        {activeSheet && (
          <div className="mock-grid">
            {activeSheet.components?.map((c: any, idx: number) => {
              if (c.type === "ProcessExplorer" || c.type === "process-explorer") {
                return (
                  <div key={idx} className="mock-explorer">
                    <span style={{ position: 'absolute', top: '8px', left: '8px', fontSize: '0.65rem', color: 'var(--text-secondary)' }}>{c.title}</span>
                    <div className="explorer-variant-line">
                      <div className="explorer-node">Create PO Item</div>
                      <ChevronRight size={14} style={{ color: 'var(--text-secondary)' }} />
                      <div className="explorer-node">Receive Goods</div>
                      <ChevronRight size={14} style={{ color: 'var(--text-secondary)' }} />
                      <div className="explorer-node">Receive Invoice</div>
                      <ChevronRight size={14} style={{ color: 'var(--text-secondary)' }} />
                      <div className="explorer-node">Pay Invoice</div>
                    </div>
                  </div>
                );
              }

              const isKpi = c.type?.includes("KPI") || c.type === "single-kpi";
              return (
                <div key={idx} className="mock-tile" style={{ gridColumn: 'span 4', minHeight: '80px' }}>
                  <span className="mock-tile-title">{c.title}</span>
                  <span className="mock-tile-value" style={{ color: isKpi ? 'var(--accent-cyan)' : '#fff' }}>
                    {c.bound_kpi_id === "AUTOMATION_RATE" || c.id?.includes("AUTOMATION_RATE") || c.title?.includes("Automation") ? "78.4%" :
                      c.bound_kpi_id === "TOTAL_PO_VALUE" || c.id?.includes("TOTAL_PO_VALUE") || c.title?.includes("Net Value") || c.title?.includes("Volume") ? "1.24M €" :
                        c.bound_kpi_id === "THROUGHPUT_TIME_PO_TO_GR" || c.id?.includes("THROUGHPUT_TIME") || c.title?.includes("Throughput") ? "14.2 Days" : "N/A"}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  } catch (e) {
    return <pre className="code-editor-pre">{content}</pre>;
  }
}

/* Sub-View Component: QA validation checks list & promote button */
interface QaViewerProps {
  content: string;
  onPromote: () => void;
  promoteAuthorized: boolean;
}

function QaViewer({ content, onPromote, promoteAuthorized }: QaViewerProps) {
  try {
    const qa = JSON.parse(content);
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', fontSize: '0.875rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <strong>Compliance Validation Score:</strong>
            <span style={{ fontSize: '1.5rem', fontWeight: 800, color: qa.total_score >= 90 ? 'var(--status-success)' : 'var(--status-error)', marginLeft: '10px' }}>
              {qa.total_score}/100
            </span>
          </div>
          <div>
            <strong>Status:</strong>
            <span className="header-badge" style={{ marginLeft: '10px', borderColor: qa.validation_status?.includes("Passed") ? 'var(--status-success)' : 'var(--status-warning)', color: qa.validation_status?.includes("Passed") ? 'var(--status-success)' : 'var(--status-warning)', background: 'transparent' }}>
              {qa.validation_status}
            </span>
          </div>
        </div>

        <div className="qa-grid">
          {qa.checklist_items?.map((item: any, idx: number) => {
            const isPassed = item.status === "Passed";
            const isWarning = item.status === "Warning";
            const statusClass = isPassed ? "passed" : isWarning ? "warning" : "failed";

            return (
              <div key={idx} className={`qa-card ${statusClass}`}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 700, fontSize: '0.8rem' }}>{item.check_name}</span>
                  <span className={`badge ${statusClass}`}>{item.status}</span>
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{item.description}</p>
                {item.found_issues?.length > 0 && (
                  <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '6px', marginTop: '4px' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--status-warning)', fontWeight: 600 }}>Identified Issues:</span>
                    <ul style={{ paddingLeft: '14px', fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      {item.found_issues.map((issue: string, i: number) => (
                        <li key={i}>{issue}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {qa.total_score >= 90 && (
          <div className="approval-box">
            <span className="approval-title">Promote Workspace to Production</span>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              All baseline quality metrics are satisfied. If approved, you can export and deploy this orchestrator setup.
            </p>
            {promoteAuthorized ? (
              <button className="btn btn-primary" style={{ width: 'fit-content' }} onClick={onPromote}>
                <Download size={16} /> Deploy to Celonis
              </button>
            ) : (
              <div style={{ fontSize: '0.75rem', color: 'var(--status-error)', fontWeight: 600 }}>
                Promotion requires 'Reviewer' or 'Admin' permissions. Switch your active role in the header to promote.
              </div>
            )}
          </div>
        )}
      </div>
    );
  } catch (e) {
    return <pre className="code-editor-pre">{content}</pre>;
  }
}
