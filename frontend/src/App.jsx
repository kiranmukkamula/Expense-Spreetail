import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, Plus, Trash2, Users, DollarSign, Upload, 
  AlertTriangle, CheckCircle, RefreshCw, LogOut, FileText, 
  ChevronRight, ArrowRight, Shield, Calendar, Edit2, Info, Check, X
} from 'lucide-react';
import { api } from './services/api';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [user, setUser] = useState(null);
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authName, setAuthName] = useState("");
  const [isRegistering, setIsRegistering] = useState(false);
  const [authError, setAuthError] = useState("");

  // Group States
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [selectedGroupDetails, setSelectedGroupDetails] = useState(null);
  const [newGroupName, setNewGroupName] = useState("");
  const [newGroupDesc, setNewGroupDesc] = useState("");
  const [showCreateGroup, setShowCreateGroup] = useState(false);

  // Group member addition
  const [newMemberEmail, setNewMemberEmail] = useState("");

  // Transaction Lists & Balances
  const [expenses, setExpenses] = useState([]);
  const [settlements, setSettlements] = useState([]);
  const [balancesData, setBalancesData] = useState(null);

  // Modals & Forms
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [expenseDesc, setExpenseDesc] = useState("");
  const [expenseAmount, setExpenseAmount] = useState("");
  const [expensePayer, setExpensePayer] = useState("");
  const [expenseSplitType, setExpenseSplitType] = useState("EQUAL");
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().split('T')[0]);
  const [customSplits, setCustomSplits] = useState({}); // userId -> shareValue (percent, exact, share)

  const [showSettlementModal, setShowSettlementModal] = useState(false);
  const [settleFrom, setSettleFrom] = useState("");
  const [settleTo, setSettleTo] = useState("");
  const [settleAmount, setSettleAmount] = useState("");
  const [settleDate, setSettleDate] = useState(new Date().toISOString().split('T')[0]);

  // CSV Import States
  const [uploadFile, setUploadFile] = useState(null);
  const [currentImport, setCurrentImport] = useState(null); // staged CSVImport details
  const [importReport, setImportReport] = useState(null);
  const [resolutions, setResolutions] = useState({}); // recordId -> { action: "IMPORT"|"SKIP"|"CORRECT", corrected_data: {...} }

  // App loading state
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (token) {
      fetchUserProfile();
      fetchGroups();
    } else {
      setUser(null);
      setGroups([]);
    }
  }, [token]);

  useEffect(() => {
    if (selectedGroup) {
      fetchGroupDetails(selectedGroup.id);
    } else {
      setSelectedGroupDetails(null);
      setExpenses([]);
      setSettlements([]);
      setBalancesData(null);
      setCurrentImport(null);
      setImportReport(null);
    }
  }, [selectedGroup]);

  // Profiles and Core
  const fetchUserProfile = async () => {
    try {
      const u = await api.me();
      setUser(u);
    } catch (e) {
      handleAuthFailure();
    }
  };

  const fetchGroups = async () => {
    try {
      const list = await api.listGroups();
      setGroups(list);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchGroupDetails = async (groupId) => {
    setLoading(true);
    try {
      const details = await api.getGroup(groupId);
      setSelectedGroupDetails(details);
      
      const exps = await api.listExpenses(groupId);
      setExpenses(exps);

      const sets = await api.listSettlements(groupId);
      setSettlements(sets);

      const bals = await api.getBalances(groupId);
      setBalancesData(bals);

      // Pre-populate custom split input structure
      const initialSplits = {};
      details.memberships.forEach(m => {
        initialSplits[m.user.id] = "";
      });
      setCustomSplits(initialSplits);

      // Reset modals
      setExpensePayer(details.memberships[0]?.user.id || "");
      setSettleFrom(details.memberships[0]?.user.id || "");
      setSettleTo(details.memberships[1]?.user.id || "");

    } catch (e) {
      alert("Error loading group details: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAuthFailure = () => {
    api.logout();
    setToken("");
    setUser(null);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthError("");
    try {
      const data = await api.login(authEmail, authPassword);
      setToken(data.access_token);
    } catch (err) {
      setAuthError(err.message);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setAuthError("");
    try {
      await api.register(authEmail, authPassword, authName);
      // Auto login
      const data = await api.login(authEmail, authPassword);
      setToken(data.access_token);
    } catch (err) {
      setAuthError(err.message);
    }
  };

  const handleLogout = () => {
    api.logout();
    setToken("");
    setSelectedGroup(null);
  };

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    try {
      const g = await api.createGroup(newGroupName, newGroupDesc);
      setNewGroupName("");
      setNewGroupDesc("");
      setShowCreateGroup(false);
      fetchGroups();
      setSelectedGroup(g);
    } catch (err) {
      alert(err.message);
    }
  };

  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!newMemberEmail) return;
    try {
      await api.addMember(selectedGroup.id, newMemberEmail);
      setNewMemberEmail("");
      fetchGroupDetails(selectedGroup.id);
    } catch (err) {
      alert(err.message);
    }
  };

  const handleDeactivateMember = async (userId) => {
    if (!window.confirm("Are you sure you want to deactivate this membership? The user will not be charged for future expenses.")) return;
    try {
      await api.removeMember(selectedGroup.id, userId);
      fetchGroupDetails(selectedGroup.id);
    } catch (err) {
      alert(err.message);
    }
  };

  // Add Expense
  const handleAddExpense = async (e) => {
    e.preventDefault();
    const amountInCents = parseInt(parseFloat(expenseAmount) * 100);
    if (isNaN(amountInCents) || amountInCents <= 0) {
      alert("Please enter a valid amount.");
      return;
    }

    const payload = {
      description: expenseDesc,
      amount: amountInCents,
      paid_by_user_id: expensePayer,
      split_type: expenseSplitType,
      expense_date: new Date(expenseDate).toISOString(),
      splits: []
    };

    // Build splits details if NOT EQUAL
    if (expenseSplitType !== "EQUAL") {
      const splitsArray = [];
      for (const [userId, val] of Object.entries(customSplits)) {
        if (val && parseFloat(val) > 0) {
          splitsArray.push({
            user_id: userId,
            share_value: parseFloat(val)
          });
        }
      }

      if (splitsArray.length === 0) {
        alert("Please specify splitting values for participants.");
        return;
      }
      payload.splits = splitsArray;
    }

    try {
      await api.createExpense(selectedGroup.id, payload);
      setShowExpenseModal(false);
      // reset
      setExpenseDesc("");
      setExpenseAmount("");
      setExpenseSplitType("EQUAL");
      fetchGroupDetails(selectedGroup.id);
    } catch (err) {
      alert("Error adding expense: " + err.message);
    }
  };

  // Add Settlement
  const handleAddSettlement = async (e) => {
    e.preventDefault();
    if (settleFrom === settleTo) {
      alert("Sender and receiver must be different.");
      return;
    }
    const amountInCents = parseInt(parseFloat(settleAmount) * 100);
    if (isNaN(amountInCents) || amountInCents <= 0) {
      alert("Please enter a valid amount.");
      return;
    }

    try {
      await api.createSettlement(selectedGroup.id, {
        from_user_id: settleFrom,
        to_user_id: settleTo,
        amount: amountInCents,
        settlement_date: new Date(settleDate).toISOString()
      });
      setShowSettlementModal(false);
      setSettleAmount("");
      fetchGroupDetails(selectedGroup.id);
    } catch (err) {
      alert("Error logging settlement: " + err.message);
    }
  };

  // CSV Import Wizard
  const handleCSVUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;
    setLoading(true);
    try {
      const stagedImport = await api.uploadCSV(selectedGroup.id, uploadFile);
      setCurrentImport(stagedImport);
      setUploadFile(null);
      setImportReport(null);

      // Initialize resolutions state from imported records
      const initialResolutions = {};
      stagedImport.records.forEach(rec => {
        initialResolutions[rec.id] = {
          action: "IMPORT",
          corrected_data: {}
        };
      });
      setResolutions(initialResolutions);

    } catch (err) {
      alert("Failed to analyze CSV: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateRecordResolution = (recordId, key, value) => {
    setResolutions(prev => ({
      ...prev,
      [recordId]: {
        ...prev[recordId],
        corrected_data: {
          ...prev[recordId].corrected_data,
          [key]: value
        }
      }
    }));
  };

  const handleToggleRecordAction = (recordId, actionType) => {
    setResolutions(prev => ({
      ...prev,
      [recordId]: {
        ...prev[recordId],
        action: actionType
      }
    }));
  };

  const handleApproveImport = async () => {
    setLoading(true);
    try {
      const resolutionArray = [];
      for (const [recordId, details] of Object.entries(resolutions)) {
        resolutionArray.push({
          record_id: recordId,
          action: details.action,
          corrected_data: Object.keys(details.corrected_data).length > 0 ? details.corrected_data : null
        });
      }

      const report = await api.approveImport(currentImport.id, resolutionArray);
      setImportReport(report);
      setCurrentImport(null);
      fetchGroupDetails(selectedGroup.id);
    } catch (err) {
      alert("Failed to submit import resolutions: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Cent formatting helpers
  const formatCents = (cents) => {
    return (cents / 100).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  };

  if (!token) {
    return (
      <div style={{ display: 'flex', minHeight: '100vh', alignItems: 'center', justifyContent: 'center', background: 'radial-gradient(circle at top right, #1b132e, #0b0f19)' }}>
        <div className="glass-panel animate-fade-in" style={{ width: '420px', padding: '40px', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '24px' }}>
            <span style={{ fontSize: '3rem' }}>💸</span>
          </div>
          <h2 style={{ fontSize: '1.75rem', textAlign: 'center', marginBottom: '8px', color: '#ffffff' }}>Split Expenser</h2>
          <p style={{ color: 'var(--text-secondary)', textAlign: 'center', fontSize: '0.9rem', marginBottom: '32px' }}>
            Premium Expense Splits & Staged CSV Imports
          </p>

          <form onSubmit={isRegistering ? handleRegister : handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {isRegistering && (
              <div className="input-group">
                <label>Name</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={authName}
                  onChange={(e) => setAuthName(e.target.value)}
                  placeholder="Your Name"
                  required
                />
              </div>
            )}
            <div className="input-group">
              <label>Email Address</label>
              <input 
                type="email" 
                className="form-input" 
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>
            <div className="input-group">
              <label>Password</label>
              <input 
                type="password" 
                className="form-input" 
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>

            {authError && (
              <div style={{ display: 'flex', gap: '8px', padding: '12px', borderRadius: '8px', backgroundColor: 'var(--accent-rose-glow)', border: '1px solid rgba(244, 63, 94, 0.2)', color: '#fca5a5', fontSize: '0.85rem' }}>
                <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
                <span>{authError}</span>
              </div>
            )}

            <button type="submit" className="btn btn-primary" style={{ padding: '12px' }}>
              {isRegistering ? "Create Account" : "Access Account"}
            </button>
          </form>

          <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'center' }}>
            <button 
              className="btn btn-secondary" 
              style={{ fontSize: '0.8rem', padding: '6px 12px' }}
              onClick={() => {
                setIsRegistering(!isRegistering);
                setAuthError("");
              }}
            >
              {isRegistering ? "Already have an account? Login" : "New here? Create an account"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', flexDirection: 'column' }}>
      {/* Premium Header */}
      <header className="glass-panel" style={{ margin: '16px', borderRadius: '12px', padding: '14px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', border: '1px solid var(--border-color)', zIndex: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }} onClick={() => setSelectedGroup(null)}>
          <span style={{ fontSize: '1.8rem' }}>💸</span>
          <h1 style={{ fontSize: '1.25rem', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '6px' }}>
            Split Expenser
            <span className="badge badge-purple" style={{ fontSize: '0.65rem', verticalAlign: 'middle' }}>V1.0</span>
          </h1>
        </div>

        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#ffffff' }}>{user.name}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{user.email}</div>
            </div>
            <button className="btn btn-secondary btn-icon" onClick={handleLogout} title="Logout">
              <LogOut size={18} />
            </button>
          </div>
        )}
      </header>

      {/* Main Workspace Layout */}
      <main style={{ flex: 1, display: 'flex', padding: '0 16px 16px 16px', gap: '16px', overflow: 'hidden' }}>
        
        {/* Left Sidebar: Groups */}
        <section className="glass-panel" style={{ width: '280px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px', flexShrink: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Groups</h3>
            <button className="btn btn-primary btn-icon" onClick={() => setShowCreateGroup(true)} title="New Group">
              <Plus size={16} />
            </button>
          </div>

          {showCreateGroup && (
            <form onSubmit={handleCreateGroup} className="glass-panel animate-fade-in" style={{ padding: '16px', border: '1px solid rgba(139, 92, 246, 0.2)', backgroundColor: 'rgba(0, 0, 0, 0.2)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div className="input-group" style={{ marginBottom: 0 }}>
                <label>Group NameLabel</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={newGroupName} 
                  onChange={(e) => setNewGroupName(e.target.value)}
                  placeholder="Roommates, Goa Trip..." 
                  required
                />
              </div>
              <div className="input-group" style={{ marginBottom: 0 }}>
                <label>Description</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={newGroupDesc} 
                  onChange={(e) => setNewGroupDesc(e.target.value)}
                  placeholder="Monthly shared costs..." 
                />
              </div>
              <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                <button type="submit" className="btn btn-primary" style={{ flex: 1, padding: '8px' }}>Create</button>
                <button type="button" className="btn btn-secondary" style={{ padding: '8px' }} onClick={() => setShowCreateGroup(false)}>Cancel</button>
              </div>
            </form>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', flex: 1 }}>
            {groups.map((g) => (
              <button
                key={g.id}
                onClick={() => setSelectedGroup(g)}
                className="btn btn-secondary"
                style={{ 
                  justifyContent: 'flex-start', 
                  padding: '12px 16px', 
                  borderRadius: '10px',
                  textAlign: 'left',
                  borderColor: selectedGroup?.id === g.id ? 'var(--accent-purple)' : 'var(--border-color)',
                  backgroundColor: selectedGroup?.id === g.id ? 'var(--accent-purple-glow)' : 'transparent',
                }}
              >
                <Users size={16} style={{ color: selectedGroup?.id === g.id ? 'var(--accent-purple)' : 'var(--text-secondary)' }} />
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <div style={{ color: '#ffffff', fontWeight: 600, fontSize: '0.85rem' }}>{g.name}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{g.description || 'No description'}</div>
                </div>
              </button>
            ))}
            {groups.length === 0 && (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', padding: '24px 0' }}>
                No groups yet. Click the + icon to get started.
              </div>
            )}
          </div>
        </section>

        {/* Right Dashboard Area */}
        <section style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
          {selectedGroupDetails ? (
            <>
              {/* Timeline import summary report */}
              {importReport && (
                <div className="glass-panel animate-fade-in" style={{ padding: '16px 24px', border: '1px solid rgba(16, 185, 129, 0.3)', backgroundColor: 'var(--accent-emerald-glow)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                    <CheckCircle size={24} style={{ color: 'var(--accent-emerald)' }} />
                    <div>
                      <h4 style={{ color: '#ffffff', fontSize: '0.95rem' }}>CSV Import Successful</h4>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                        Imported {importReport.imported_expenses} expenses and {importReport.imported_settlements} settlements into group.
                      </p>
                    </div>
                  </div>
                  <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.75rem' }} onClick={() => setImportReport(null)}>Dismiss</button>
                </div>
              )}

              {/* Group Roster Header Card */}
              <div className="glass-panel" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', gap: '24px', flexWrap: 'wrap' }}>
                <div style={{ flex: 1 }}>
                  <span className="badge badge-purple" style={{ marginBottom: '8px' }}>Active Group Ledger</span>
                  <h2 style={{ fontSize: '1.5rem', color: '#ffffff', marginBottom: '4px' }}>{selectedGroupDetails.name}</h2>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '16px' }}>{selectedGroupDetails.description || 'No description'}</p>
                  
                  {/* Member timelines */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, marginRight: '4px' }}>Timeline Roster:</span>
                    {selectedGroupDetails.memberships.map(m => (
                      <div key={m.id} className={`badge ${m.left_at ? 'badge-rose' : 'badge-emerald'}`} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <span>{m.user.name}</span>
                        {m.left_at ? (
                          <span style={{ fontSize: '0.65rem', opacity: 0.8 }}>(Left {new Date(m.left_at).toLocaleDateString()})</span>
                        ) : (
                          <button 
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', padding: '0 2px' }} 
                            onClick={() => handleDeactivateMember(m.user.id)}
                            title="Mark member as left"
                          >
                            <X size={10} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', minWidth: '220px' }}>
                  <form onSubmit={handleAddMember} style={{ display: 'flex', gap: '8px' }}>
                    <input 
                      type="email" 
                      className="form-input" 
                      style={{ padding: '8px 12px', fontSize: '0.8rem', flex: 1 }}
                      value={newMemberEmail}
                      onChange={(e) => setNewMemberEmail(e.target.value)}
                      placeholder="Add member by email..." 
                      required
                    />
                    <button type="submit" className="btn btn-primary" style={{ padding: '8px 12px' }} title="Invite member">
                      Add
                    </button>
                  </form>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button className="btn btn-primary" style={{ flex: 1, padding: '10px' }} onClick={() => setShowExpenseModal(true)}>
                      <Plus size={16} /> Expense
                    </button>
                    <button className="btn btn-secondary" style={{ flex: 1, padding: '10px' }} onClick={() => setShowSettlementModal(true)}>
                      <RefreshCw size={14} /> Settlement
                    </button>
                  </div>

                  {/* CSV Upload */}
                  <form onSubmit={handleCSVUpload} style={{ display: 'flex', gap: '8px', borderTop: '1px solid var(--border-color)', paddingTop: '10px' }}>
                    <input 
                      type="file" 
                      accept=".csv"
                      style={{ display: 'none' }}
                      id="csv-file-picker"
                      onChange={(e) => setUploadFile(e.target.files[0])}
                    />
                    <label 
                      htmlFor="csv-file-picker" 
                      className="btn btn-secondary" 
                      style={{ flex: 1, padding: '8px', fontSize: '0.75rem', cursor: 'pointer', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                    >
                      <Upload size={12} /> {uploadFile ? uploadFile.name : "Select CSV"}
                    </label>
                    <button type="submit" className="btn btn-emerald" style={{ padding: '8px 12px', fontSize: '0.75rem' }} disabled={!uploadFile}>
                      Upload
                    </button>
                  </form>
                </div>
              </div>

              {/* CSV Import Anomaly Resolution Wizard (Displays if staged import active) */}
              {currentImport && (
                <div className="glass-panel animate-fade-in" style={{ padding: '24px', border: '1px solid var(--accent-purple)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <div>
                      <span className="badge badge-purple" style={{ marginBottom: '4px' }}>Data Validation Wizard</span>
                      <h3 style={{ fontSize: '1.2rem', color: '#ffffff' }}>Resolve CSV Import Anomalies ({currentImport.filename})</h3>
                    </div>
                    <div style={{ display: 'flex', gap: '10px' }}>
                      <button className="btn btn-secondary" onClick={() => setCurrentImport(null)}>Cancel Import</button>
                      <button className="btn btn-primary" onClick={handleApproveImport}>Confirm & Import Ledger</button>
                    </div>
                  </div>

                  <div className="table-container" style={{ maxHeight: '450px', overflowY: 'auto' }}>
                    <table className="premium-table">
                      <thead>
                        <tr>
                          <th>Row</th>
                          <th>Data Preview</th>
                          <th>Anomalies Found</th>
                          <th>Resolution Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {currentImport.records.map((rec) => {
                          const recordResolution = resolutions[rec.id] || { action: "IMPORT", corrected_data: {} };
                          const isSkipped = recordResolution.action === "SKIP";
                          
                          // Determine severity color
                          let rowClass = "row-severity-valid";
                          if (rec.anomalies.length > 0) {
                            const severities = rec.anomalies.map(a => a.severity);
                            if (severities.includes("CRITICAL")) rowClass = "row-severity-critical";
                            else if (severities.includes("WARNING")) rowClass = "row-severity-warning";
                            else rowClass = "row-severity-info";
                          }

                          return (
                            <tr key={rec.id} className={rowClass} style={{ opacity: isSkipped ? 0.4 : 1, transition: 'opacity 0.2s' }}>
                              <td>{rec.row_index + 1}</td>
                              
                              <td>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxWidth: '300px' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <strong style={{ color: '#ffffff' }}>{rec.raw_data.description || "No description"}</strong>
                                    <span style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>
                                      {rec.raw_data.currency || "INR"} {rec.raw_data.amount}
                                    </span>
                                  </div>
                                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', gap: '8px' }}>
                                    <span>Payer: {rec.raw_data.paid_by || "Missing"}</span>
                                    <span>Split: {rec.raw_data.split_type || "Equal"}</span>
                                  </div>
                                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                    Date: {rec.raw_data.date} | Split With: {rec.raw_data.split_with || "All"}
                                  </div>
                                  {rec.raw_data.split_details && (
                                    <div style={{ fontSize: '0.7rem', color: 'var(--accent-purple)' }}>
                                      Details: {rec.raw_data.split_details}
                                    </div>
                                  )}
                                </div>
                              </td>

                              <td>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxWidth: '280px' }}>
                                  {rec.anomalies.map((anom) => (
                                    <div key={anom.id} style={{ fontSize: '0.75rem' }}>
                                      <span className={`badge ${
                                        anom.severity === 'CRITICAL' ? 'badge-rose' : 
                                        anom.severity === 'WARNING' ? 'badge-amber' : 'badge-purple'
                                      }`} style={{ padding: '1px 5px', fontSize: '0.65rem', marginRight: '4px' }}>
                                        {anom.anomaly_type}
                                      </span>
                                      <span style={{ color: 'var(--text-secondary)' }}>{anom.description}</span>
                                    </div>
                                  ))}
                                  {rec.anomalies.length === 0 && (
                                    <span className="badge badge-emerald" style={{ padding: '2px 6px', fontSize: '0.65rem' }}>Ready to Import</span>
                                  )}
                                </div>
                              </td>

                              <td>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                  <div style={{ display: 'flex', gap: '4px' }}>
                                    <button 
                                      className={`btn ${recordResolution.action === 'IMPORT' ? 'btn-primary' : 'btn-secondary'}`}
                                      style={{ padding: '4px 8px', fontSize: '0.7rem' }}
                                      onClick={() => handleToggleRecordAction(rec.id, "IMPORT")}
                                    >
                                      Import
                                    </button>
                                    <button 
                                      className={`btn ${recordResolution.action === 'SKIP' ? 'btn-rose' : 'btn-secondary'}`}
                                      style={{ padding: '4px 8px', fontSize: '0.7rem' }}
                                      onClick={() => handleToggleRecordAction(rec.id, "SKIP")}
                                    >
                                      Skip Row
                                    </button>
                                  </div>

                                  {/* Custom Correction Options based on detected anomalies */}
                                  {rec.anomalies.some(a => a.anomaly_type === "UNRESOLVED_PAYER" || a.anomaly_type === "MISSING_PAYER") && (
                                    <div className="input-group" style={{ marginBottom: 0 }}>
                                      <label style={{ fontSize: '0.65rem' }}>Map Payer to:</label>
                                      <select 
                                        className="form-input" 
                                        style={{ padding: '4px 8px', fontSize: '0.75rem', backgroundColor: 'var(--bg-tertiary)' }}
                                        value={recordResolution.corrected_data.paid_by_user_id || ""}
                                        onChange={(e) => handleUpdateRecordResolution(rec.id, "paid_by_user_id", e.target.value)}
                                      >
                                        <option value="">Select Group Member...</option>
                                        {selectedGroupDetails.memberships.map(m => (
                                          <option key={m.user.id} value={m.user.id}>{m.user.name} ({m.user.email})</option>
                                        ))}
                                      </select>
                                    </div>
                                  )}

                                  {/* Allow date corrections */}
                                  {rec.anomalies.some(a => a.anomaly_type === "INVALID_DATE_FORMAT" || a.anomaly_type === "FUTURE_DATE") && (
                                    <div className="input-group" style={{ marginBottom: 0 }}>
                                      <label style={{ fontSize: '0.65rem' }}>Correct Date:</label>
                                      <input 
                                        type="date"
                                        className="form-input"
                                        style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                                        onChange={(e) => handleUpdateRecordResolution(rec.id, "date", e.target.value)}
                                      />
                                    </div>
                                  )}

                                  {/* Currency mismatch conversion note */}
                                  {rec.anomalies.some(a => a.anomaly_type === "FOREIGN_CURRENCY") && (
                                    <div style={{ fontSize: '0.65rem', color: 'var(--accent-emerald)' }}>
                                      Auto-converting USD to INR at rate 83.
                                    </div>
                                  )}

                                  {/* Percentage splits corrections */}
                                  {rec.anomalies.some(a => a.anomaly_type === "PERCENTAGE_SUM_MISMATCH") && (
                                    <div className="input-group" style={{ marginBottom: 0 }}>
                                      <label style={{ fontSize: '0.65rem' }}>Correct percentages (semicolon split):Label</label>
                                      <input 
                                        type="text"
                                        className="form-input"
                                        style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                                        placeholder="Aisha 25%; Rohan 25%..."
                                        onChange={(e) => handleUpdateRecordResolution(rec.id, "split_details", e.target.value)}
                                      />
                                    </div>
                                  )}
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Balances & Simplified Settlement Pathways Grid */}
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                
                {/* Balance Summary Sheet */}
                <div className="glass-panel" style={{ flex: '1 1 350px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <h3 style={{ fontSize: '1rem', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <TrendingUp size={18} style={{ color: 'var(--accent-purple)' }} /> Net Group Balances
                  </h3>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {balancesData && Object.entries(balancesData.net_balances).map(([userId, cents]) => {
                      const userInfo = balancesData.users_info[userId] || { name: "Unknown", email: "" };
                      const isOwed = cents > 0;
                      const isOwes = cents < 0;
                      return (
                        <div key={userId} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', borderRadius: '10px', backgroundColor: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-color)' }}>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{userInfo.name}</div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{userInfo.email}</div>
                          </div>
                          <div style={{ 
                            fontWeight: 700, 
                            color: isOwed ? 'var(--accent-emerald)' : isOwes ? 'var(--accent-rose)' : 'var(--text-muted)',
                            fontSize: '0.95rem'
                          }}>
                            {isOwed ? "+" : ""}{formatCents(cents)} INR
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Simplified Settlements */}
                <div className="glass-panel" style={{ flex: '1 1 350px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <h3 style={{ fontSize: '1rem', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Shield size={16} style={{ color: 'var(--accent-emerald)' }} /> Debt Simplification Pathway
                  </h3>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', flex: 1, justifyContent: 'center' }}>
                    {balancesData?.simplified_settlements.map((tx, idx) => (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px', borderRadius: '10px', backgroundColor: 'var(--accent-purple-glow)', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
                          <strong style={{ color: '#ffffff' }}>{tx.from_user_name}</strong>
                          <ArrowRight size={14} style={{ color: 'var(--text-secondary)' }} />
                          <strong style={{ color: '#ffffff' }}>{tx.to_user_name}</strong>
                        </div>
                        <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.9rem' }}>
                          {formatCents(tx.amount)} INR
                        </div>
                      </div>
                    ))}
                    {balancesData?.simplified_settlements.length === 0 && (
                      <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem', padding: '24px 0' }}>
                        🎉 Perfect Balance! All debts are settled.
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Transactions Ledger */}
              <div className="glass-panel" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: '1.1rem', color: '#ffffff', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileText size={18} style={{ color: 'var(--accent-purple)' }} /> Ledger Feed
                </h3>

                <div className="table-container">
                  <table className="premium-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Description</th>
                        <th>Type</th>
                        <th>Payer / Parties</th>
                        <th>Total Amount</th>
                        <th>Calculated Share allocations</th>
                      </tr>
                    </thead>
                    <tbody>
                      {/* Combine Expenses and Settlements */}
                      {[
                        ...expenses.map(e => ({ ...e, type: 'EXPENSE' })),
                        ...settlements.map(s => ({ ...s, type: 'SETTLEMENT' }))
                      ].sort((a, b) => new Date(b.expense_date || b.settlement_date) - new Date(a.expense_date || a.settlement_date)).map((tx) => {
                        const date = new Date(tx.expense_date || tx.settlement_date);
                        
                        if (tx.type === 'EXPENSE') {
                          return (
                            <tr key={tx.id}>
                              <td>{date.toLocaleDateString()}</td>
                              <td>
                                <div style={{ fontWeight: 600 }}>{tx.description}</div>
                                {tx.currency !== 'INR' && <span style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)' }}>Original: {tx.currency}</span>}
                              </td>
                              <td>
                                <span className="badge badge-purple" style={{ fontSize: '0.65rem' }}>EXPENSE ({tx.split_type})</span>
                              </td>
                              <td>
                                <div style={{ fontSize: '0.85rem' }}>Paid by <strong style={{ color: '#ffffff' }}>{selectedGroupDetails.memberships.find(m => m.user.id === tx.paid_by_user_id)?.user.name || "Unknown"}</strong></div>
                              </td>
                              <td style={{ fontWeight: 600 }}>{formatCents(tx.amount)} INR</td>
                              <td>
                                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', fontSize: '0.75rem' }}>
                                  {tx.splits.map(s => {
                                    const uName = selectedGroupDetails.memberships.find(m => m.user.id === s.user_id)?.user.name || "Unknown";
                                    return (
                                      <span key={s.id} style={{ color: 'var(--text-secondary)' }}>
                                        {uName}: {formatCents(s.calculated_amount)}
                                      </span>
                                    );
                                  })}
                                </div>
                              </td>
                            </tr>
                          );
                        } else {
                          // Settlement type
                          const fromName = selectedGroupDetails.memberships.find(m => m.user.id === tx.from_user_id)?.user.name || "Unknown";
                          const toName = selectedGroupDetails.memberships.find(m => m.user.id === tx.to_user_id)?.user.name || "Unknown";
                          return (
                            <tr key={tx.id} style={{ backgroundColor: 'var(--accent-emerald-glow)' }}>
                              <td>{date.toLocaleDateString()}</td>
                              <td>
                                <div style={{ fontWeight: 600 }}>Reconciliation Settlement</div>
                              </td>
                              <td>
                                <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>SETTLEMENT</span>
                              </td>
                              <td>
                                <div style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  <strong>{fromName}</strong> paid <strong>{toName}</strong>
                                </div>
                              </td>
                              <td style={{ fontWeight: 600, color: 'var(--accent-emerald)' }}>{formatCents(tx.amount)} INR</td>
                              <td><span style={{ color: 'var(--text-muted)' }}>Direct Transfer</span></td>
                            </tr>
                          );
                        }
                      })}
                      {expenses.length === 0 && settlements.length === 0 && (
                        <tr>
                          <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '32px 0' }}>
                            No transactions yet. Click Add Expense to log your first shared item.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px', textAlign: 'center' }}>
              <span style={{ fontSize: '4rem', marginBottom: '16px' }}>👥</span>
              <h2 style={{ fontSize: '1.5rem', color: '#ffffff', marginBottom: '8px' }}>Select or Create a Group</h2>
              <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', fontSize: '0.9rem' }}>
                Choose a group from the sidebar ledger roster to review outstanding balances, configure splits, and resolve imports.
              </p>
            </div>
          )}
        </section>
      </main>

      {/* --- ADD EXPENSE MODAL --- */}
      {showExpenseModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div className="glass-panel animate-fade-in" style={{ width: '480px', padding: '32px', backgroundColor: 'var(--bg-secondary)', border: '1px solid rgba(139, 92, 246, 0.3)' }}>
            <h3 style={{ fontSize: '1.25rem', color: '#ffffff', marginBottom: '24px' }}>Add Group Expense</h3>
            
            <form onSubmit={handleAddExpense} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="input-group">
                <label>Description</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={expenseDesc} 
                  onChange={(e) => setExpenseDesc(e.target.value)}
                  placeholder="Rent, Groceries, Dinner..."
                  required
                />
              </div>

              <div style={{ display: 'flex', gap: '16px' }}>
                <div className="input-group" style={{ flex: 1 }}>
                  <label>Amount (INR)</label>
                  <input 
                    type="number" 
                    step="0.01" 
                    className="form-input" 
                    value={expenseAmount} 
                    onChange={(e) => setExpenseAmount(e.target.value)}
                    placeholder="0.00"
                    required
                  />
                </div>
                <div className="input-group" style={{ flex: 1 }}>
                  <label>Date</label>
                  <input 
                    type="date" 
                    className="form-input" 
                    value={expenseDate} 
                    onChange={(e) => setExpenseDate(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '16px' }}>
                <div className="input-group" style={{ flex: 1 }}>
                  <label>Paid By</label>
                  <select 
                    className="form-input" 
                    value={expensePayer} 
                    onChange={(e) => setExpensePayer(e.target.value)}
                  >
                    {selectedGroupDetails.memberships.map(m => (
                      <option key={m.user.id} value={m.user.id}>{m.user.name}</option>
                    ))}
                  </select>
                </div>
                <div className="input-group" style={{ flex: 1 }}>
                  <label>Split Type</label>
                  <select 
                    className="form-input" 
                    value={expenseSplitType} 
                    onChange={(e) => setExpenseSplitType(e.target.value)}
                  >
                    <option value="EQUAL">Split Equally</option>
                    <option value="EXACT">Exact Amounts</option>
                    <option value="PERCENTAGE">Percentages</option>
                    <option value="SHARE">Shares Ratio</option>
                  </select>
                </div>
              </div>

              {/* Custom Split Details input list */}
              {expenseSplitType !== "EQUAL" && (
                <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '14px', maxHeight: '180px', overflowY: 'auto' }}>
                  <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '8px' }}>
                    Define splits for each member:
                  </label>
                  {selectedGroupDetails.memberships.map(m => (
                    <div key={m.user.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <span style={{ fontSize: '0.85rem' }}>{m.user.name}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <input 
                          type="number" 
                          step="any"
                          placeholder="0"
                          className="form-input"
                          style={{ width: '100px', padding: '6px 10px', fontSize: '0.8rem' }}
                          value={customSplits[m.user.id] || ""}
                          onChange={(e) => setCustomSplits(prev => ({ ...prev, [m.user.id]: e.target.value }))}
                        />
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', width: '32px' }}>
                          {expenseSplitType === 'PERCENTAGE' ? "%" : expenseSplitType === 'SHARE' ? "sh" : "INR"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Add Expense</button>
                <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setShowExpenseModal(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- RECORD SETTLEMENT MODAL --- */}
      {showSettlementModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div className="glass-panel animate-fade-in" style={{ width: '400px', padding: '32px', backgroundColor: 'var(--bg-secondary)', border: '1px solid rgba(139, 92, 246, 0.3)' }}>
            <h3 style={{ fontSize: '1.25rem', color: '#ffffff', marginBottom: '24px' }}>Record Payment Settlement</h3>
            
            <form onSubmit={handleAddSettlement} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="input-group">
                <label>Sender (Pays)</label>
                <select 
                  className="form-input" 
                  value={settleFrom} 
                  onChange={(e) => setSettleFrom(e.target.value)}
                >
                  {selectedGroupDetails.memberships.map(m => (
                    <option key={m.user.id} value={m.user.id}>{m.user.name}</option>
                  ))}
                </select>
              </div>

              <div className="input-group">
                <label>Receiver (Gets Paid)</label>
                <select 
                  className="form-input" 
                  value={settleTo} 
                  onChange={(e) => setSettleTo(e.target.value)}
                >
                  {selectedGroupDetails.memberships.map(m => (
                    <option key={m.user.id} value={m.user.id}>{m.user.name}</option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', gap: '16px' }}>
                <div className="input-group" style={{ flex: 1 }}>
                  <label>Amount (INR)</label>
                  <input 
                    type="number" 
                    step="0.01" 
                    className="form-input" 
                    value={settleAmount} 
                    onChange={(e) => setSettleAmount(e.target.value)}
                    placeholder="0.00"
                    required
                  />
                </div>
                <div className="input-group" style={{ flex: 1 }}>
                  <label>Date</label>
                  <input 
                    type="date" 
                    className="form-input" 
                    value={settleDate} 
                    onChange={(e) => setSettleDate(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                <button type="submit" className="btn btn-emerald" style={{ flex: 1 }}>Log Settlement</button>
                <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setShowSettlementModal(false)}>Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Global loading spinner cover */}
      {loading && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.4)', backdropFilter: 'blur(2px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="glass-panel" style={{ padding: '24px 40px', display: 'flex', alignItems: 'center', gap: '16px' }}>
            <RefreshCw size={24} style={{ color: 'var(--accent-purple)', animation: 'spin 1s linear infinite' }} />
            <span style={{ fontWeight: 600 }}>Syncing Transaction Ledger...</span>
          </div>
        </div>
      )}

      {/* Basic rotating spinner styling injection */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
