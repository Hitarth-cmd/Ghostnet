"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  EcologicalAlert,
  IncidentAction,
  IncidentHistoryResponse,
  ResponderAlertItem,
  ResponderAlertsResponse,
  User,
} from "@/types";

interface ResponderPortalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectDetectionOnMap: (externalId: string) => void;
  onIncidentUpdated: () => void;
  theme?: "light" | "dark";
}

export default function ResponderPortal({
  isOpen,
  onClose,
  onSelectDetectionOnMap,
  onIncidentUpdated,
  theme = "light",
}: ResponderPortalProps) {
  const isLight = theme === "light";
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [loginEmail, setLoginEmail] = useState("responder@oceanguard.org");
  const [loginPassword, setLoginPassword] = useState("responder123");
  const [registerForm, setRegisterForm] = useState({
    email: "",
    password: "",
    full_name: "",
    organization: "",
    role: "ngo",
    phone: "",
  });
  const [authError, setAuthError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(false);

  // Portal tabs: "actionable" | "verification" | "ecological" | "history"
  const [activeTab, setActiveTab] = useState<"actionable" | "verification" | "ecological">(
    "actionable"
  );

  const [inbox, setInbox] = useState<ResponderAlertsResponse | null>(null);
  const [ecologicalAlerts, setEcologicalAlerts] = useState<EcologicalAlert[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  // Incident action modal state
  const [selectedIncident, setSelectedIncident] = useState<ResponderAlertItem | null>(null);
  const [actionType, setActionType] = useState<"verify" | "reject" | "assign" | "being_handled" | "resolve">("verify");
  const [assignedTeamInput, setAssignedTeamInput] = useState("");
  const [actionNotesInput, setActionNotesInput] = useState("");
  const [submittingAction, setSubmittingAction] = useState(false);
  const [historyData, setHistoryData] = useState<IncidentHistoryResponse | null>(null);
  const [showHistoryModal, setShowHistoryModal] = useState(false);

  // Check stored user on mount
  useEffect(() => {
    const user = api.getCurrentStoredUser();
    if (user) {
      setCurrentUser(user);
    }
  }, []);

  // Fetch alerts whenever portal opens or user logs in
  useEffect(() => {
    if (isOpen) {
      fetchPortalData();
    }
  }, [isOpen, currentUser]);

  async function fetchPortalData() {
    setLoadingData(true);
    try {
      const [alertsRes, ecoRes] = await Promise.all([
        currentUser ? api.getResponderAlerts() : Promise.resolve(null),
        api.listEcologicalAlerts(),
      ]);
      if (alertsRes) setInbox(alertsRes);
      setEcologicalAlerts(ecoRes.alerts);
    } catch (err: any) {
      console.error("Failed to load responder data", err);
    } finally {
      setLoadingData(false);
    }
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setAuthError(null);
    setAuthLoading(true);
    try {
      const res = await api.login(loginEmail, loginPassword);
      setCurrentUser(res.user);
      await fetchPortalData();
    } catch (err: any) {
      setAuthError(err.message || "Invalid email or password");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setAuthError(null);
    setAuthLoading(true);
    try {
      await api.register(registerForm);
      // Auto login after registration
      const res = await api.login(registerForm.email, registerForm.password);
      setCurrentUser(res.user);
      await fetchPortalData();
    } catch (err: any) {
      setAuthError(err.message || "Registration failed");
    } finally {
      setAuthLoading(false);
    }
  }

  function handleLogout() {
    api.logout();
    setCurrentUser(null);
    setInbox(null);
  }

  async function openActionModal(item: ResponderAlertItem, action: "verify" | "reject" | "assign" | "being_handled" | "resolve") {
    setSelectedIncident(item);
    setActionType(action);
    setAssignedTeamInput(item.assigned_team || "");
    setActionNotesInput("");
    try {
      const hist = await api.getIncidentHistory(item.external_id);
      setHistoryData(hist);
    } catch {
      setHistoryData(null);
    }
  }

  async function submitIncidentAction(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedIncident) return;
    setSubmittingAction(true);
    try {
      await api.updateIncident(selectedIncident.external_id, actionType, {
        assigned_team: assignedTeamInput,
        notes: actionNotesInput,
      });
      setSelectedIncident(null);
      await fetchPortalData();
      onIncidentUpdated();
    } catch (err: any) {
      alert("Action failed: " + err.message);
    } finally {
      setSubmittingAction(false);
    }
  }

  async function viewHistory(item: ResponderAlertItem) {
    try {
      const hist = await api.getIncidentHistory(item.external_id);
      setHistoryData(hist);
      setShowHistoryModal(true);
    } catch (err: any) {
      alert("Could not load audit log: " + err.message);
    }
  }

  async function handleAcknowledgeAlert(id: string) {
    try {
      await api.acknowledgeAlert(id);
      await fetchPortalData();
      onIncidentUpdated();
    } catch (err: any) {
      alert("Could not acknowledge alert: " + err.message);
    }
  }

  async function handleResolveAlert(id: string) {
    try {
      await api.resolveAlert(id);
      await fetchPortalData();
      onIncidentUpdated();
    } catch (err: any) {
      alert("Could not resolve alert: " + err.message);
    }
  }

  if (!isOpen) return null;

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-md ${isLight ? "theme-light" : ""}`}>
      <div className={`relative flex h-[88vh] w-full max-w-5xl flex-col rounded-2xl border shadow-2xl transition-colors ${
        isLight
          ? "border-slate-200/90 bg-white/98 text-slate-800 shadow-slate-900/15"
          : "border-sky-500/20 bg-slate-950/95 text-slate-100"
      }`}>
        {/* Header */}
        <div className={`flex items-center justify-between border-b px-6 py-4 ${
          isLight ? "border-slate-200 bg-slate-50/80" : "border-slate-800"
        }`}>
          <div className="flex items-center gap-3">
            <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${
              isLight ? "bg-sky-100 text-sky-700" : "bg-sky-500/20 text-sky-400"
            }`}>
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h2 className={`text-base font-bold ${isLight ? "text-slate-900" : "text-slate-100"}`}>
                OceanGuard Responder & NGO Operations Centre
              </h2>
              <p className={`text-xs ${isLight ? "text-slate-500" : "text-slate-400"}`}>
                Authorized debris verification, intervention dispatch & marine-life alert management
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {currentUser && (
              <div className={`flex items-center gap-3 rounded-lg border px-3 py-1.5 text-xs ${
                isLight ? "border-slate-200 bg-slate-100" : "border-slate-800 bg-slate-900/80"
              }`}>
                <div className="h-2 w-2 rounded-full bg-emerald-400" />
                <div>
                  <span className={`font-semibold ${isLight ? "text-slate-800" : "text-slate-200"}`}>{currentUser.full_name}</span>
                  <span className="ml-2 text-slate-500">({currentUser.organization || currentUser.role})</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="ml-2 text-[11px] text-rose-500 hover:text-rose-600 underline font-medium"
                >
                  Log Out
                </button>
              </div>
            )}
            <button
              onClick={onClose}
              className={`rounded-lg p-1.5 transition ${
                isLight ? "text-slate-400 hover:bg-slate-100 hover:text-slate-700" : "text-slate-400 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content Body */}
        {!currentUser ? (
          /* Authentication Screen */
          <div className="flex flex-1 items-center justify-center p-8">
            <div className={`w-full max-w-md rounded-xl border p-6 shadow-xl ${
              isLight ? "border-slate-200 bg-white" : "border-sky-500/20 bg-slate-900/90"
            }`}>
              <div className={`mb-6 flex border-b pb-3 ${isLight ? "border-slate-200" : "border-slate-800"}`}>
                <button
                  onClick={() => setAuthMode("login")}
                  className={`flex-1 pb-2 text-sm font-semibold transition ${
                    authMode === "login"
                      ? isLight ? "border-b-2 border-sky-600 text-sky-600" : "border-b-2 border-sky-400 text-sky-400"
                      : isLight ? "text-slate-500 hover:text-slate-800" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Responder Login
                </button>
                <button
                  onClick={() => setAuthMode("register")}
                  className={`flex-1 pb-2 text-sm font-semibold transition ${
                    authMode === "register"
                      ? isLight ? "border-b-2 border-sky-600 text-sky-600" : "border-b-2 border-sky-400 text-sky-400"
                      : isLight ? "text-slate-500 hover:text-slate-800" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Register Organization
                </button>
              </div>

              {authError && (
                <div className={`mb-4 rounded-lg border p-3 text-xs ${
                  isLight ? "border-red-200 bg-red-50 text-red-700" : "border-red-500/30 bg-red-950/60 text-red-300"
                }`}>
                  {authError}
                </div>
              )}

              {authMode === "login" ? (
                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <label className={`block text-xs font-medium ${isLight ? "text-slate-700" : "text-slate-300"}`}>Email Address</label>
                    <input
                      type="email"
                      required
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:border-sky-500 focus:outline-none ${
                        isLight ? "border-slate-300 bg-white text-slate-900 placeholder-slate-400" : "border-slate-700 bg-slate-800/80 text-slate-100 placeholder-slate-500"
                      }`}
                    />
                  </div>
                  <div>
                    <label className={`block text-xs font-medium ${isLight ? "text-slate-700" : "text-slate-300"}`}>Password</label>
                    <input
                      type="password"
                      required
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:border-sky-500 focus:outline-none ${
                        isLight ? "border-slate-300 bg-white text-slate-900 placeholder-slate-400" : "border-slate-700 bg-slate-800/80 text-slate-100 placeholder-slate-500"
                      }`}
                    />
                  </div>

                  <div className={`rounded-xl p-3 text-xs border ${
                    isLight ? "border-slate-200 bg-slate-50" : "border-sky-500/20 bg-slate-950/70"
                  }`}>
                    <div className={`text-[11px] font-bold uppercase tracking-wider mb-2 ${
                      isLight ? "text-sky-700" : "text-sky-400"
                    }`}>
                      Quick Login Shortcuts (Click to Auto-fill):
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setLoginEmail("admin@oceanguard.org");
                          setLoginPassword("admin123456");
                        }}
                        className={`rounded-lg border p-2 text-left transition ${
                          isLight
                            ? "border-purple-200 bg-purple-50 text-purple-900 hover:bg-purple-100"
                            : "border-purple-500/40 bg-purple-950/40 text-purple-200 hover:bg-purple-900/60"
                        }`}
                      >
                        <div className="text-[11px] font-bold">Admin Account</div>
                        <div className={`text-[10px] ${isLight ? "text-purple-700/80" : "text-purple-400/80"}`}>admin@oceanguard.org</div>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setLoginEmail("responder@oceanguard.org");
                          setLoginPassword("responder123");
                        }}
                        className={`rounded-lg border p-2 text-left transition ${
                          isLight
                            ? "border-sky-200 bg-sky-50 text-sky-900 hover:bg-sky-100"
                            : "border-sky-500/40 bg-sky-950/40 text-sky-200 hover:bg-sky-900/60"
                        }`}
                      >
                        <div className="text-[11px] font-bold">NGO Lead (Anya)</div>
                        <div className={`text-[10px] ${isLight ? "text-sky-700/80" : "text-sky-400/80"}`}>responder@oceanguard.org</div>
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={authLoading}
                    className="w-full rounded-lg bg-sky-600 py-2.5 text-sm font-medium text-white transition hover:bg-sky-500 disabled:opacity-50"
                  >
                    {authLoading ? "Authenticating…" : "Sign In to Responder Command"}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleRegister} className="space-y-3">
                  <div>
                    <label className={`block text-xs font-medium ${isLight ? "text-slate-700" : "text-slate-300"}`}>Full Name</label>
                    <input
                      type="text"
                      required
                      value={registerForm.full_name}
                      onChange={(e) => setRegisterForm({ ...registerForm, full_name: e.target.value })}
                      placeholder="Dr. Maya Sen"
                      className={`mt-1 w-full rounded-lg border px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none ${
                        isLight ? "border-slate-300 bg-white text-slate-900 placeholder-slate-400" : "border-slate-700 bg-slate-800/80 text-slate-100"
                      }`}
                    />
                  </div>
                  <div>
                    <label className={`block text-xs font-medium ${isLight ? "text-slate-700" : "text-slate-300"}`}>Email Address</label>
                    <input
                      type="email"
                      required
                      value={registerForm.email}
                      onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })}
                      placeholder="maya@oceansos.org"
                      className={`mt-1 w-full rounded-lg border px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none ${
                        isLight ? "border-slate-300 bg-white text-slate-900 placeholder-slate-400" : "border-slate-700 bg-slate-800/80 text-slate-100"
                      }`}
                    />
                  </div>
                  <div>
                    <label className={`block text-xs font-medium ${isLight ? "text-slate-700" : "text-slate-300"}`}>Organization Name</label>
                    <input
                      type="text"
                      value={registerForm.organization}
                      onChange={(e) => setRegisterForm({ ...registerForm, organization: e.target.value })}
                      placeholder="Ocean SOS / Coast Guard / University"
                      className={`mt-1 w-full rounded-lg border px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none ${
                        isLight ? "border-slate-300 bg-white text-slate-900 placeholder-slate-400" : "border-slate-700 bg-slate-800/80 text-slate-100"
                      }`}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className={`block text-xs font-medium ${isLight ? "text-slate-700" : "text-slate-300"}`}>Role</label>
                      <select
                        value={registerForm.role}
                        onChange={(e) => setRegisterForm({ ...registerForm, role: e.target.value })}
                        className={`mt-1 w-full rounded-lg border px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none ${
                          isLight ? "border-slate-300 bg-white text-slate-900" : "border-slate-700 bg-slate-800/80 text-slate-100"
                        }`}
                      >
                        <option value="ngo">Environmental NGO</option>
                        <option value="admin">Administrator</option>
                      </select>
                    </div>
                    <div>
                      <label className={`block text-xs font-medium ${isLight ? "text-slate-700" : "text-slate-300"}`}>Password</label>
                      <input
                        type="password"
                        required
                        minLength={8}
                        value={registerForm.password}
                        onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })}
                        className={`mt-1 w-full rounded-lg border px-3 py-1.5 text-sm focus:border-sky-500 focus:outline-none ${
                          isLight ? "border-slate-300 bg-white text-slate-900" : "border-slate-700 bg-slate-800/80 text-slate-100"
                        }`}
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    disabled={authLoading}
                    className="mt-2 w-full rounded-lg bg-sky-600 py-2.5 text-sm font-medium text-white transition hover:bg-sky-500 disabled:opacity-50"
                  >
                    {authLoading ? "Registering…" : "Register Organization"}
                  </button>
                </form>
              )}
            </div>
          </div>
        ) : (
          /* Logged In Responder Workspace */
          <div className="flex flex-1 flex-col overflow-hidden">
            {/* Nav Tabs */}
            <div className={`flex items-center gap-2 border-b px-6 py-2.5 ${
              isLight ? "border-slate-200 bg-slate-50" : "border-slate-800 bg-slate-900/50"
            }`}>
              <button
                onClick={() => setActiveTab("actionable")}
                className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition ${
                  activeTab === "actionable"
                    ? isLight ? "bg-sky-100 text-sky-800 border border-sky-300" : "bg-sky-500/20 text-sky-400 border border-sky-500/30"
                    : isLight ? "text-slate-600 hover:text-slate-900" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <span>⚡ High-Confidence Cleanup Alerts</span>
                {inbox && (
                  <span className={`rounded-full px-2 py-0.5 text-[10px] ${
                    isLight ? "bg-orange-100 text-orange-800" : "bg-orange-500/20 text-orange-300"
                  }`}>
                    {inbox.total_actionable}
                  </span>
                )}
              </button>

              <button
                onClick={() => setActiveTab("verification")}
                className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition ${
                  activeTab === "verification"
                    ? isLight ? "bg-amber-100 text-amber-800 border border-amber-300" : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                    : isLight ? "text-slate-600 hover:text-slate-900" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <span>🔍 Human Verification Queue (&lt;70%)</span>
                {inbox && (
                  <span className={`rounded-full px-2 py-0.5 text-[10px] ${
                    isLight ? "bg-amber-100 text-amber-800" : "bg-amber-500/20 text-amber-300"
                  }`}>
                    {inbox.total_requiring_action}
                  </span>
                )}
              </button>

              <button
                onClick={() => setActiveTab("ecological")}
                className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition ${
                  activeTab === "ecological"
                    ? isLight ? "bg-rose-100 text-rose-800 border border-rose-300" : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                    : isLight ? "text-slate-600 hover:text-slate-900" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <span>⚠️ Marine-Life & Ecological Alerts</span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] ${
                  isLight ? "bg-rose-100 text-rose-800" : "bg-rose-500/20 text-rose-300"
                }`}>
                  {ecologicalAlerts.filter((a) => a.status === "active").length} active
                </span>
              </button>

              <div className="ml-auto flex items-center gap-2">
                <button
                  onClick={fetchPortalData}
                  disabled={loadingData}
                  className={`rounded-md border px-2.5 py-1 text-xs transition ${
                    isLight ? "border-slate-300 bg-white text-slate-700 hover:bg-slate-50" : "border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
                  }`}
                >
                  {loadingData ? "Refreshing…" : "↻ Refresh"}
                </button>
              </div>
            </div>

            {/* Tab Views */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* TAB 1: High-Confidence Cleanup Alerts (>70%) */}
              {activeTab === "actionable" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between rounded-lg border border-orange-500/20 bg-orange-950/20 p-3 text-xs text-orange-200">
                    <div>
                      <strong>Actionable Cleanup Stream:</strong> Detections with AI confidence &ge; 70% or verified by verified responders.
                      Ready for immediate vessel dispatch or interception.
                    </div>
                  </div>

                  {inbox?.actionable_alerts.length === 0 ? (
                    <div className="p-12 text-center text-sm text-slate-500">
                      No high-confidence actionable alerts currently waiting.
                    </div>
                  ) : (
                    <div className="grid gap-3">
                      {inbox?.actionable_alerts.map((item) => (
                        <div
                          key={item.id}
                          className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition hover:border-slate-700"
                        >
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-slate-100">{item.external_id}</span>
                                <span className="rounded border border-orange-500/40 bg-orange-500/10 px-2 py-0.5 text-[10px] font-bold text-orange-300">
                                  {(item.confidence * 100).toFixed(1)}% CONFIDENCE
                                </span>
                                <span className="rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-[10px] uppercase text-slate-300">
                                  STATUS: {item.status.replaceAll("_", " ")}
                                </span>
                                {item.risk_level && (
                                  <span
                                    className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                                      item.risk_level === "CRITICAL"
                                        ? "bg-red-500/20 text-red-400 border border-red-500/30"
                                        : item.risk_level === "HIGH"
                                        ? "bg-orange-500/20 text-orange-400 border border-orange-500/30"
                                        : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                                    }`}
                                  >
                                    RISK: {item.risk_level}
                                  </span>
                                )}
                              </div>
                              <div className="mt-1 text-xs text-slate-400">
                                {item.object_class.replaceAll("_", " ")} · Located at{" "}
                                {item.latitude.toFixed(4)}°N, {item.longitude.toFixed(4)}°E · Source: {item.source}
                              </div>
                              {item.assigned_team && (
                                <div className="mt-1 text-xs text-sky-400">
                                  Assigned to: <strong>{item.assigned_team}</strong> ({item.assigned_to || "Field Team"})
                                </div>
                              )}
                              {item.recommended_action && (
                                <div className="mt-1.5 text-xs text-slate-300 italic">
                                  Recommendation: {item.recommended_action}
                                </div>
                              )}
                            </div>

                            <button
                              onClick={() => {
                                onSelectDetectionOnMap(item.external_id);
                                onClose();
                              }}
                              className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-medium text-sky-300 hover:bg-sky-500/20"
                            >
                              Show on Map ↗
                            </button>
                          </div>

                          {/* Action Bar */}
                          <div className="flex flex-wrap items-center gap-2 border-t border-slate-800/80 pt-3">
                            <span className="text-[11px] font-semibold text-slate-400">Responder Actions:</span>

                            {item.status !== "assigned" && (
                              <button
                                onClick={() => openActionModal(item, "assign")}
                                className="rounded bg-sky-600/80 px-2.5 py-1 text-xs font-medium text-white hover:bg-sky-500"
                              >
                                Assign Team / Vessel
                              </button>
                            )}

                            {item.status !== "being_handled" && (
                              <button
                                onClick={() => openActionModal(item, "being_handled")}
                                className="rounded bg-purple-600/80 px-2.5 py-1 text-xs font-medium text-white hover:bg-purple-500"
                              >
                                Mark Being Handled
                              </button>
                            )}

                            {item.status !== "resolved" && (
                              <button
                                onClick={() => openActionModal(item, "resolve")}
                                className="rounded bg-emerald-600/80 px-2.5 py-1 text-xs font-medium text-white hover:bg-emerald-500"
                              >
                                Mark Resolved / Recovered
                              </button>
                            )}

                            <button
                              onClick={() => viewHistory(item)}
                              className="ml-auto rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-300 hover:bg-slate-700"
                            >
                              📜 Audit Trail
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: Low-Confidence Verification Queue (<70%) */}
              {activeTab === "verification" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between rounded-lg border border-amber-500/20 bg-amber-950/20 p-3 text-xs text-amber-200">
                    <div>
                      <strong>Human-in-the-Loop Queue:</strong> Detections with AI confidence &lt; 70% require expert verification by authorized responders before trigger alerts are dispatched to cleanup crews.
                    </div>
                  </div>

                  {inbox?.verification_queue.length === 0 ? (
                    <div className="p-12 text-center text-sm text-slate-500">
                      All low-confidence detections have been verified or rejected. No pending items!
                    </div>
                  ) : (
                    <div className="grid gap-3">
                      {inbox?.verification_queue.map((item) => (
                        <div
                          key={item.id}
                          className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4 transition hover:border-slate-700"
                        >
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-slate-100">{item.external_id}</span>
                                <span className="rounded border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-300">
                                  {(item.confidence * 100).toFixed(1)}% AI CONFIDENCE
                                </span>
                                <span className="rounded border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[10px] uppercase text-red-300">
                                  REQUIRES HUMAN REVIEW
                                </span>
                              </div>
                              <div className="mt-1 text-xs text-slate-400">
                                Object: {item.object_class.replaceAll("_", " ")} · Location:{" "}
                                {item.latitude.toFixed(4)}°N, {item.longitude.toFixed(4)}°E · Source: {item.source}
                              </div>
                              <div className="mt-1 text-xs text-slate-500">
                                Detected: {new Date(item.timestamp).toUTCString()}
                              </div>
                            </div>

                            <button
                              onClick={() => {
                                onSelectDetectionOnMap(item.external_id);
                                onClose();
                              }}
                              className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-medium text-sky-300 hover:bg-sky-500/20"
                            >
                              Inspect Geometry ↗
                            </button>
                          </div>

                          {/* Verification Actions */}
                          <div className="flex items-center gap-3 border-t border-slate-800/80 pt-3">
                            <span className="text-[11px] font-semibold text-slate-400">Responder Decision:</span>
                            <button
                              onClick={() => openActionModal(item, "verify")}
                              className="rounded bg-emerald-600 px-3 py-1 text-xs font-semibold text-white transition hover:bg-emerald-500"
                            >
                              ✓ Verify as Debris
                            </button>
                            <button
                              onClick={() => openActionModal(item, "reject")}
                              className="rounded bg-red-600/80 px-3 py-1 text-xs font-semibold text-white transition hover:bg-red-500"
                            >
                              ✕ Reject (False Positive)
                            </button>
                            <button
                              onClick={() => viewHistory(item)}
                              className="ml-auto rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-300 hover:bg-slate-700"
                            >
                              📜 Audit Trail
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: Marine-life & Ecological Alerts */}
              {activeTab === "ecological" && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between rounded-lg border border-rose-500/20 bg-rose-950/20 p-3 text-xs text-rose-200">
                    <div>
                      <strong>Automated Ecological Proximity Engine:</strong> Alerts triggered when detected marine debris or its predicted drift trajectory approaches coral reefs, Marine Protected Areas, turtle nesting beaches, or cetacean corridors.
                    </div>
                  </div>

                  {ecologicalAlerts.length === 0 ? (
                    <div className="p-12 text-center text-sm text-slate-500">
                      No ecological alerts registered.
                    </div>
                  ) : (
                    <div className="grid gap-3">
                      {ecologicalAlerts.map((alert) => (
                        <div
                          key={alert.id}
                          className={`flex flex-col gap-3 rounded-xl border p-4 transition ${
                            alert.status === "active"
                              ? "border-rose-500/40 bg-rose-950/20"
                              : "border-slate-800 bg-slate-900/60 opacity-80"
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                <span
                                  className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                                    alert.severity === "CRITICAL"
                                      ? "bg-red-600 text-white"
                                      : alert.severity === "HIGH"
                                      ? "bg-orange-500 text-white"
                                      : "bg-amber-500 text-black"
                                  }`}
                                >
                                  {alert.severity}
                                </span>
                                <span className="font-bold text-slate-100">{alert.headline}</span>
                                <span className="rounded border border-slate-700 bg-slate-800 px-2 py-0.5 text-[10px] uppercase text-slate-300">
                                  {alert.status}
                                </span>
                              </div>

                              <p className="text-xs text-slate-300">{alert.details}</p>

                              <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] text-slate-400">
                                <span>Area: <strong className="text-slate-200">{alert.region_name}</strong></span>
                                <span>Distance: <strong className="text-slate-200">{alert.distance_km.toFixed(1)} km</strong></span>
                                <span>Impact ETA: <strong className="text-slate-200">{alert.estimated_impact_hours.toFixed(1)} hrs</strong></span>
                                {alert.species_at_risk.length > 0 && (
                                  <span>Species at risk: <strong className="text-rose-300">{alert.species_at_risk.join(", ")}</strong></span>
                                )}
                              </div>

                              <div className="pt-1 text-[11px] text-emerald-400">
                                <strong>Recommended Action:</strong> {alert.recommended_action}
                              </div>

                              <div className="text-[10px] text-slate-500 italic">
                                Scientific Citation: {alert.source_citation}
                              </div>
                            </div>

                            <button
                              onClick={() => {
                                onSelectDetectionOnMap(alert.external_id);
                                onClose();
                              }}
                              className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-medium text-sky-300 hover:bg-sky-500/20"
                            >
                              View Threat on Map ↗
                            </button>
                          </div>

                          {/* Alert Actions */}
                          <div className="flex items-center gap-2 border-t border-slate-800/80 pt-2 text-xs">
                            {alert.status === "active" && (
                              <button
                                onClick={() => handleAcknowledgeAlert(alert.id)}
                                className="rounded bg-sky-600/70 px-2.5 py-1 text-white hover:bg-sky-500"
                              >
                                Acknowledge Threat
                              </button>
                            )}
                            {alert.status !== "resolved" && (
                              <button
                                onClick={() => handleResolveAlert(alert.id)}
                                className="rounded bg-emerald-600/70 px-2.5 py-1 text-white hover:bg-emerald-500"
                              >
                                Mark Threat Mitigated / Resolved
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* MODAL 1: Incident Action Modal */}
        {selectedIncident && (
          <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/60 p-4">
            <div className={`w-full max-w-lg rounded-xl border p-6 shadow-2xl transition-colors ${
              isLight ? "border-slate-200 bg-white text-slate-800" : "border-sky-500/30 bg-slate-900 text-slate-100"
            }`}>
              <h3 className={`text-sm font-bold uppercase tracking-wider ${
                isLight ? "text-sky-700" : "text-sky-400"
              }`}>
                Update Incident Status: {selectedIncident.external_id}
              </h3>
              <p className={`mt-1 text-xs ${isLight ? "text-slate-500" : "text-slate-400"}`}>
                Action: <strong className={`uppercase ${isLight ? "text-slate-900" : "text-slate-100"}`}>{actionType.replaceAll("_", " ")}</strong>
              </p>

              <form onSubmit={submitIncidentAction} className="mt-4 space-y-4">
                {actionType === "assign" && (
                  <div>
                    <label className={`block text-xs font-medium ${isLight ? "text-slate-700" : "text-slate-300"}`}>Assign Responder Team / Vessel</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Sagar Rakshak Patrol Vessel / Mumbai Coast Guard Unit"
                      value={assignedTeamInput}
                      onChange={(e) => setAssignedTeamInput(e.target.value)}
                      className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:border-sky-500 focus:outline-none ${
                        isLight ? "border-slate-300 bg-white text-slate-900 placeholder-slate-400" : "border-slate-700 bg-slate-800 text-slate-100"
                      }`}
                    />
                  </div>
                )}

                <div>
                  <label className={`block text-xs font-medium ${isLight ? "text-slate-700" : "text-slate-300"}`}>Operational Notes / Reason</label>
                  <textarea
                    rows={3}
                    placeholder="Provide details about the verification or intervention dispatch..."
                    value={actionNotesInput}
                    onChange={(e) => setActionNotesInput(e.target.value)}
                    className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:border-sky-500 focus:outline-none ${
                      isLight ? "border-slate-300 bg-white text-slate-900 placeholder-slate-400" : "border-slate-700 bg-slate-800 text-slate-100"
                    }`}
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setSelectedIncident(null)}
                    className={`rounded-lg border px-4 py-2 text-xs font-medium transition ${
                      isLight ? "border-slate-200 bg-slate-100 text-slate-700 hover:bg-slate-200" : "border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
                    }`}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingAction}
                    className="rounded-lg bg-sky-600 px-4 py-2 text-xs font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
                  >
                    {submittingAction ? "Submitting…" : "Confirm Update"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL 2: Audit History Modal */}
        {showHistoryModal && historyData && (
          <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/60 p-4">
            <div className={`w-full max-w-lg rounded-xl border p-6 shadow-2xl transition-colors ${
              isLight ? "border-slate-200 bg-white text-slate-800" : "border-sky-500/30 bg-slate-900 text-slate-100"
            }`}>
              <div className={`flex items-center justify-between border-b pb-3 ${
                isLight ? "border-slate-200" : "border-slate-800"
              }`}>
                <h3 className={`text-sm font-bold ${isLight ? "text-slate-900" : "text-slate-100"}`}>
                  Incident Audit Trail: {historyData.detection_id}
                </h3>
                <button
                  onClick={() => setShowHistoryModal(false)}
                  className={`transition ${isLight ? "text-slate-400 hover:text-slate-700" : "text-slate-400 hover:text-white"}`}
                >
                  ✕
                </button>
              </div>

              <div className="my-4 max-h-72 space-y-3 overflow-y-auto pr-1">
                {historyData.actions.length === 0 ? (
                  <div className={`py-6 text-center text-xs ${isLight ? "text-slate-400" : "text-slate-500"}`}>
                    No actions logged for this detection yet.
                  </div>
                ) : (
                  historyData.actions.map((act) => (
                    <div key={act.id} className={`rounded-lg border p-3 text-xs ${
                      isLight ? "border-slate-200 bg-slate-50" : "border-slate-800 bg-slate-800/40"
                    }`}>
                      <div className="flex items-center justify-between">
                        <span className={`font-semibold uppercase ${isLight ? "text-sky-700" : "text-sky-400"}`}>{act.action}</span>
                        <span className={`text-[10px] ${isLight ? "text-slate-400" : "text-slate-500"}`}>
                          {new Date(act.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <div className={`mt-1 ${isLight ? "text-slate-700" : "text-slate-300"}`}>
                        Responder: <strong>{act.user_name}</strong> {act.organization ? `(${act.organization})` : ""}
                      </div>
                      <div className={`text-[11px] ${isLight ? "text-slate-500" : "text-slate-400"}`}>
                        Status Change: {act.previous_status || "initial"} &rarr; <span className={isLight ? "text-emerald-700 font-semibold" : "text-emerald-400"}>{act.new_status}</span>
                      </div>
                      {act.assigned_team && (
                        <div className={`text-[11px] font-medium ${isLight ? "text-sky-700" : "text-sky-300"}`}>
                          Assigned Team: {act.assigned_team}
                        </div>
                      )}
                      {act.notes && (
                        <div className={`mt-1 rounded p-2 text-[11px] italic ${
                          isLight ? "bg-white border border-slate-200 text-slate-700" : "bg-slate-900/60 text-slate-300"
                        }`}>
                          &ldquo;{act.notes}&rdquo;
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>

              <div className="flex justify-end">
                <button
                  onClick={() => setShowHistoryModal(false)}
                  className={`rounded-lg border px-4 py-1.5 text-xs font-medium transition ${
                    isLight ? "border-slate-200 bg-slate-100 text-slate-700 hover:bg-slate-200" : "border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
                  }`}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
