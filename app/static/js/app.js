/**
 * app.js — topic selection, build management, chat interface, and LLM settings.
 */

let currentTopic = null;
let pollInterval = null;
let chatHistory = [];
let serverConfig = null;

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  serverConfig = await fetch("/api/config").then(r => r.json()).catch(() => null);
  await refreshTopics();
  initSettings();
  initTheme();

  initAlertModal();
  document.getElementById("topic-select").addEventListener("change", onTopicChange);
  document.getElementById("btn-build").addEventListener("click", onBuild);
  document.getElementById("chat-input").addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  document.getElementById("btn-send").addEventListener("click", sendMessage);
});


// ══════════════════════════════════════════════════════════════════════════════
// ALERT MODAL
// ══════════════════════════════════════════════════════════════════════════════

function initAlertModal() {
  const backdrop = document.getElementById("alert-backdrop");
  document.getElementById("alert-close").addEventListener("click", closeAlertModal);
  document.getElementById("alert-ok").addEventListener("click", closeAlertModal);
  backdrop.addEventListener("click", e => { if (e.target === backdrop) closeAlertModal(); });
}

function showAlert(message, title = "Notice") {
  document.getElementById("alert-title").textContent = title;
  document.getElementById("alert-message").textContent = message;
  document.getElementById("alert-backdrop").style.display = "flex";
}

function closeAlertModal() {
  document.getElementById("alert-backdrop").style.display = "none";
}


// ══════════════════════════════════════════════════════════════════════════════
// THEME — persisted in localStorage
// ══════════════════════════════════════════════════════════════════════════════

function initTheme() {
  const saved = localStorage.getItem("graphrag_theme") || "dark";
  applyTheme(saved);

  document.getElementById("btn-theme").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    applyTheme(next);
    localStorage.setItem("graphrag_theme", next);
  });
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const moon = document.querySelector("#btn-theme .icon-moon");
  const sun  = document.querySelector("#btn-theme .icon-sun");
  if (theme === "light") {
    moon.style.display = "none";
    sun.style.display  = "block";
  } else {
    moon.style.display = "block";
    sun.style.display  = "none";
  }
}


// ══════════════════════════════════════════════════════════════════════════════
// LLM SETTINGS — stored only in sessionStorage, never sent to disk
// ══════════════════════════════════════════════════════════════════════════════

const SETTINGS_KEY = "graphrag_llm_config";

function getLLMConfig() {
  try {
    const raw = sessionStorage.getItem(SETTINGS_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function saveLLMConfig(config) {
  sessionStorage.setItem(SETTINGS_KEY, JSON.stringify(config));
  updateSettingsIndicator();
}

function updateSettingsIndicator() {
  const btn = document.getElementById("btn-settings");
  const config = getLLMConfig();
  const hasKey = config && (config.api_key || config.provider !== "openai");
  btn.classList.toggle("configured", !!hasKey);
  btn.title = hasKey
    ? `LLM: ${config.provider} (${config.extraction_model || "default"})`
    : "LLM Settings — not configured";
}

function initSettings() {
  const btn       = document.getElementById("btn-settings");
  const backdrop  = document.getElementById("settings-backdrop");
  const closeBtn  = document.getElementById("settings-close");
  const saveBtn   = document.getElementById("btn-save-settings");
  const provider  = document.getElementById("llm-provider");

  btn.addEventListener("click", () => openSettingsModal());
  backdrop.addEventListener("click", e => { if (e.target === backdrop) closeSettingsModal(); });
  closeBtn.addEventListener("click", closeSettingsModal);
  saveBtn.addEventListener("click", onSaveSettings);

  // Toggle fields based on provider
  provider.addEventListener("change", () => updateProviderFields());

  updateSettingsIndicator();
}

function openSettingsModal() {
  const config = getLLMConfig() || {};
  document.getElementById("llm-provider").value         = config.provider || "openai";
  document.getElementById("llm-api-key").value           = config.api_key || "";
  document.getElementById("llm-base-url").value          = config.base_url || "";
  document.getElementById("llm-extraction-model").value  = config.extraction_model || "";
  document.getElementById("llm-query-model").value       = config.query_model || "";

  updateProviderFields();
  document.getElementById("settings-backdrop").style.display = "flex";
}

function closeSettingsModal() {
  document.getElementById("settings-backdrop").style.display = "none";
}

function updateProviderFields() {
  const provider = document.getElementById("llm-provider").value;
  const apiKeyGroup  = document.getElementById("group-api-key");
  const baseUrlGroup = document.getElementById("group-base-url");
  const extractionInput = document.getElementById("llm-extraction-model");
  const queryInput      = document.getElementById("llm-query-model");

  if (provider === "openai") {
    apiKeyGroup.style.display  = "block";
    baseUrlGroup.style.display = "none";
    extractionInput.placeholder = "gpt-4o-mini";
    queryInput.placeholder      = "gpt-4o";
  } else if (provider === "lmstudio") {
    apiKeyGroup.style.display  = "none";
    baseUrlGroup.style.display = "none";
    extractionInput.placeholder = "your-model-name";
    queryInput.placeholder      = "your-model-name";
  } else if (provider === "ollama") {
    apiKeyGroup.style.display  = "none";
    baseUrlGroup.style.display = "none";
    extractionInput.placeholder = "llama3";
    queryInput.placeholder      = "llama3";
  } else {
    // custom
    apiKeyGroup.style.display  = "block";
    baseUrlGroup.style.display = "block";
    extractionInput.placeholder = "model-name";
    queryInput.placeholder      = "model-name";
  }
}

function onSaveSettings() {
  const config = {
    provider:         document.getElementById("llm-provider").value,
    api_key:          document.getElementById("llm-api-key").value.trim() || null,
    base_url:         document.getElementById("llm-base-url").value.trim() || null,
    extraction_model: document.getElementById("llm-extraction-model").value.trim() || null,
    query_model:      document.getElementById("llm-query-model").value.trim() || null,
  };
  saveLLMConfig(config);
  closeSettingsModal();
}

/** Build the `llm` payload to include in API requests. Returns null if nothing configured. */
function llmPayload() {
  const config = getLLMConfig();
  if (!config) return null;
  // Only include non-null fields
  const payload = { provider: config.provider };
  if (config.api_key)          payload.api_key = config.api_key;
  if (config.base_url)         payload.base_url = config.base_url;
  if (config.extraction_model) payload.extraction_model = config.extraction_model;
  if (config.query_model)      payload.query_model = config.query_model;
  return payload;
}


// ══════════════════════════════════════════════════════════════════════════════
// TOPIC MANAGEMENT
// ══════════════════════════════════════════════════════════════════════════════

async function refreshTopics() {
  try {
    const res  = await fetch("/api/topics");
    const data = await res.json();

    const select = document.getElementById("topic-select");
    const currentVal = select.value;
    select.innerHTML = '<option value="">— Select a topic —</option>';
    data.forEach(t => {
      const opt = document.createElement("option");
      opt.value = t.topic;
      opt.textContent = t.has_graph
        ? `${t.topic} (${t.node_count || "?"} nodes)`
        : `${t.topic} (not built)`;
      select.appendChild(opt);
    });
    if (currentVal) select.value = currentVal;
  } catch (err) {
    console.error("Failed to load topics:", err);
  }
}

async function onTopicChange() {
  const topic = document.getElementById("topic-select").value;
  if (!topic) {
    currentTopic = null;
    clearGraph();
    clearChat();
    setStatus("", "");
    return;
  }

  currentTopic = topic;
  clearChat();
  stopPolling();

  const status = await fetchTopicStatus(topic);
  applyStatus(status);

  if (status.has_graph) {
    await loadGraph(topic);
  } else {
    clearGraph();
    setStatus("idle", "No graph built yet — click Build Graph");
  }
}

async function fetchTopicStatus(topic) {
  const res = await fetch(`/api/topics/${encodeURIComponent(topic)}/status`);
  return await res.json();
}

function applyStatus(status) {
  if (status.build_status === "building") {
    setStatus("building", status.build_progress || "Building...");
    startPolling(status.topic);
  } else if (status.build_status === "complete") {
    setStatus("complete", `${status.node_count || "?"} nodes · ${status.edge_count || "?"} edges · ${status.community_count || "?"} communities`);
  } else if (status.build_status === "error") {
    setStatus("error", status.build_error || "Build failed");
  } else {
    setStatus("idle", "Ready to build");
  }
}


// ══════════════════════════════════════════════════════════════════════════════
// GRAPH BUILD
// ══════════════════════════════════════════════════════════════════════════════

async function onBuild() {
  if (!currentTopic) {
    showAlert("Please select a topic first.", "No Topic Selected");
    return;
  }

  // Use session LLM config if set, otherwise fall back to server .env config
  const llm = llmPayload();
  const serverReady = serverConfig && serverConfig.has_server_config;
  if (!llm && !serverReady) {
    openSettingsModal();
    appendMessage("system", "Please configure your LLM provider and API key before building.");
    return;
  }
  if (!llm && llm?.provider === "openai" && !llm?.api_key && !serverReady) {
    openSettingsModal();
    appendMessage("system", "Please configure your LLM provider and API key before building.");
    return;
  }

  const btn = document.getElementById("btn-build");
  btn.disabled = true;

  const force = document.getElementById("chk-force-rebuild")?.checked || false;
  const thinking = document.getElementById("chk-thinking")?.checked || false;

  try {
    const res = await fetch(`/api/topics/${encodeURIComponent(currentTopic)}/build`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ llm, force, thinking }),
    });

    if (res.status === 409) {
      const data = await res.json();
      setStatus("building", data.detail || "Already building...");
    } else if (!res.ok) {
      const data = await res.json();
      setStatus("error", data.detail || "Build request failed");
      btn.disabled = false;
      return;
    } else {
      setStatus("building", "Starting...");
    }

    startPolling(currentTopic);
    const chk = document.getElementById("chk-force-rebuild");
    if (chk) chk.checked = false;
  } catch (err) {
    setStatus("error", "Network error: " + err.message);
    btn.disabled = false;
  }
}

function startPolling(topic) {
  stopPolling();
  pollInterval = setInterval(async () => {
    if (!currentTopic || currentTopic !== topic) { stopPolling(); return; }
    try {
      const status = await fetchTopicStatus(topic);
      applyStatus(status);
      if (status.build_status === "complete") {
        stopPolling();
        document.getElementById("btn-build").disabled = false;
        await loadGraph(topic);
        await refreshTopics();
        if (status.up_to_date) showToast("No changes detected — graph is already up to date. Use \"Full rebuild\" to force re-extraction.");
      } else if (status.build_status === "error") {
        stopPolling();
        document.getElementById("btn-build").disabled = false;
      }
    } catch (err) {
      console.error("Poll error:", err);
    }
  }, 10000);
}

function stopPolling() {
  if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
}

function showToast(message, duration = 6000) {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("toast-visible"));
  setTimeout(() => {
    toast.classList.remove("toast-visible");
    toast.addEventListener("transitionend", () => toast.remove());
  }, duration);
}


// ══════════════════════════════════════════════════════════════════════════════
// GRAPH VISUALIZATION
// ══════════════════════════════════════════════════════════════════════════════

async function loadGraph(topic) {
  try {
    const res = await fetch(`/api/topics/${encodeURIComponent(topic)}/graph`);
    if (!res.ok) { clearGraph(); return; }
    const data = await res.json();
    initGraph(data);  // from graph.js
  } catch (err) {
    console.error("Failed to load graph:", err);
    clearGraph();
  }
}


// ══════════════════════════════════════════════════════════════════════════════
// STATUS BADGE
// ══════════════════════════════════════════════════════════════════════════════

function setStatus(state, message) {
  const badge = document.getElementById("status-badge");
  const text  = document.getElementById("status-text");
  badge.className = "status-badge " + (state || "");
  text.textContent = message || "";
}


// ══════════════════════════════════════════════════════════════════════════════
// CHAT
// ══════════════════════════════════════════════════════════════════════════════

function clearChat() {
  chatHistory = [];
  const messages = document.getElementById("chat-messages");
  messages.innerHTML = `
    <div class="chat-welcome">
      <div class="chat-welcome-title">GraphRAG Explorer</div>
      <div class="chat-welcome-sub">Select a topic and ask anything about its knowledge graph.</div>
    </div>`;
}

async function sendMessage() {
  if (!currentTopic) {
    appendMessage("system", "Please select a topic first.");
    return;
  }

  // Use session LLM config if set, otherwise fall back to server .env config
  const llm = llmPayload();
  const serverReady = serverConfig && serverConfig.has_server_config;
  if (!llm && !serverReady) {
    openSettingsModal();
    appendMessage("system", "Please configure your LLM provider and API key before querying.");
    return;
  }

  const input = document.getElementById("chat-input");
  const query = input.value.trim();
  if (!query) return;

  input.value = "";
  appendMessage("user", query);

  const loadingId = appendMessage("assistant", null, true);

  try {
    const res = await fetch(`/api/topics/${encodeURIComponent(currentTopic)}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, llm }),
    });

    const data = await res.json();
    removeMessage(loadingId);

    if (!res.ok) {
      appendMessage("system", data.detail || "Query failed.");
    } else {
      appendMessage("assistant", data.answer, false, {
        communities_checked: data.communities_checked,
        relevant_communities: data.relevant_communities,
      });
    }
  } catch (err) {
    removeMessage(loadingId);
    appendMessage("system", "Network error: " + err.message);
  }
}

let _msgId = 0;

function appendMessage(role, content, loading = false, meta = null) {
  const id = "msg-" + (++_msgId);
  const messages = document.getElementById("chat-messages");

  const div = document.createElement("div");
  div.id = id;
  div.className = `chat-message chat-${role}`;

  if (loading) {
    div.innerHTML = `<div class="chat-loading"><span></span><span></span><span></span></div>`;
  } else {
    const html = (content || "")
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br>");
    div.innerHTML = `<div class="chat-bubble">${html}</div>`;

    if (meta && role === "assistant") {
      div.innerHTML += `
        <div class="chat-meta">
          Checked ${meta.communities_checked} communities ·
          ${meta.relevant_communities} relevant
        </div>`;
    }
  }

  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return id;
}

function removeMessage(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}
