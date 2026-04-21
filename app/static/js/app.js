/**
 * app.js — topic selection, build management, chat interface, and LLM settings.
 */

let currentTopic = null;
let currentTopicHasGraph = false;
let pollInterval = null;
let chatHistory = [];
let serverConfig = null;

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  serverConfig = await fetch("/api/config").then(r => r.json()).catch(() => null);
  await refreshTopics();
  initSettings();
  initTheme();
  updateLLMIndicator();

  initAlertModal();
  initContextModal();
  document.getElementById("topic-select").addEventListener("change", onTopicChange);
  document.getElementById("btn-build").addEventListener("click", onBuild);
  const chatInputEl = document.getElementById("chat-input");
  chatInputEl.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  chatInputEl.addEventListener("input", () => autosizeTextarea(chatInputEl));
  document.getElementById("btn-send").addEventListener("click", sendMessage);

  const exportBtn = document.getElementById("btn-export-obsidian");
  if (exportBtn) exportBtn.addEventListener("click", onExportObsidian);

  // Mode toggle
  const modeToggle = document.getElementById("mode-toggle");
  const modeLabelOn = document.getElementById("mode-label-on");
  if (modeToggle) {
    modeToggle.addEventListener("change", () => {
      modeLabelOn.classList.toggle("mode-label-active", modeToggle.checked);
    });
  }

  // Delegated click handler for citation chips in chat messages.
  document.addEventListener("click", (e) => {
    const chip = e.target.closest(".cite-chip");
    if (chip) {
      const name = chip.dataset.cite;
      if (!name) return;
      const ok = window.graphSelectByLabel && window.graphSelectByLabel(name);
      if (!ok) {
        chip.classList.add("cite-chip-miss");
        setTimeout(() => chip.classList.remove("cite-chip-miss"), 800);
      }
      return;
    }
    const pinBtn = e.target.closest(".chat-pin-btn");
    if (pinBtn) {
      if (pinBtn.classList.contains("pinned") || pinBtn.disabled) return;
      const msgId = pinBtn.dataset.pinMsg;
      const div = document.getElementById(msgId);
      if (div) pinChatAnswer(div);
      return;
    }
    const delBtn = e.target.closest(".pinned-del");
    if (delBtn) {
      e.stopPropagation();
      deletePinned(delBtn.dataset.delId);
      return;
    }
    const pinnedItem = e.target.closest(".pinned-item");
    if (pinnedItem) {
      loadPinnedIntoChat(pinnedItem.dataset.pinId);
      return;
    }
  });
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
// BUILD CONTEXT MODAL
// ══════════════════════════════════════════════════════════════════════════════

function initContextModal() {
  const backdrop = document.getElementById("context-backdrop");
  document.getElementById("context-close").addEventListener("click", () => closeContextModal(false));
  document.getElementById("btn-context-skip").addEventListener("click", () => closeContextModal(true));
  document.getElementById("btn-context-build").addEventListener("click", () => closeContextModal(true));
  backdrop.addEventListener("click", e => { if (e.target === backdrop) closeContextModal(false); });
}

let _contextResolve = null;

async function openContextModal(topic) {
  const input = document.getElementById("build-context-input");
  input.value = "";
  // Prefill with the last build_context used for this topic, if any.
  // Saves the user retyping it on every incremental rebuild.
  if (topic) {
    try {
      const res = await fetch(`/api/topics/${encodeURIComponent(topic)}/build_context`);
      if (res.ok) {
        const data = await res.json();
        if (data.build_context) input.value = data.build_context;
      }
    } catch { /* no prior context — leave blank */ }
  }
  document.getElementById("context-backdrop").style.display = "flex";
  input.focus();
  return new Promise(resolve => { _contextResolve = resolve; });
}

function closeContextModal(proceed) {
  const context = document.getElementById("build-context-input").value.trim() || null;
  document.getElementById("context-backdrop").style.display = "none";
  if (_contextResolve) {
    _contextResolve(proceed ? context : false);
    _contextResolve = null;
  }
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
  updateLLMIndicator();
}

const _PROVIDER_LABELS = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  gemini: "Gemini",
  lmstudio: "LM Studio",
  ollama: "Ollama",
  custom: "Custom",
};

/**
 * Render a plain-text indicator in the navbar showing which LLM will be used
 * for the next request. Browser session config overrides server .env — this
 * makes the precedence visible so users don't hit the "why is LM Studio
 * silent?" surprise from a stale Claude key saved in sessionStorage.
 */
function updateLLMIndicator() {
  const el = document.getElementById("llm-indicator");
  if (!el) return;

  const session = getLLMConfig();
  const hasSession = session && (session.api_key || session.provider !== "openai"
                                 || session.base_url || session.extraction_model
                                 || session.query_model);
  let source, provider, extraction, query, baseUrl;

  if (hasSession) {
    source = "browser";
    provider = session.provider || "openai";
    extraction = session.extraction_model || "(default)";
    query = session.query_model || extraction;
    baseUrl = session.base_url || null;
  } else if (serverConfig && serverConfig.has_server_config) {
    source = "server";
    provider = serverConfig.provider || "openai";
    extraction = serverConfig.extraction_model || "(default)";
    query = serverConfig.query_model || extraction;
    baseUrl = serverConfig.base_url || null;
  } else {
    source = "none";
    provider = null;
    extraction = "";
    query = "";
    baseUrl = null;
  }

  el.dataset.source = source;
  if (source === "none") {
    el.textContent = "LLM not configured";
  } else {
    const label = _PROVIDER_LABELS[provider] || provider;
    el.textContent = `${label} — ${query}`;
  }

  const lines = [`Source: ${source === "browser" ? "browser session (overrides .env)" : source === "server" ? "server .env" : "none"}`];
  if (source !== "none") {
    lines.push(`Provider: ${provider}`);
    lines.push(`Query model: ${query}`);
    if (extraction !== query) lines.push(`Extraction model: ${extraction}`);
    if (baseUrl) lines.push(`Endpoint: ${baseUrl}`);
  }
  el.title = lines.join("\n");
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
  document.getElementById("llm-max-tokens").value        = config.max_tokens || "";

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
  } else if (provider === "anthropic") {
    apiKeyGroup.style.display  = "block";
    baseUrlGroup.style.display = "none";
    extractionInput.placeholder = "claude-haiku-4-5-20251001";
    queryInput.placeholder      = "claude-sonnet-4-6";
  } else if (provider === "gemini") {
    apiKeyGroup.style.display  = "block";
    baseUrlGroup.style.display = "none";
    extractionInput.placeholder = "gemini-2.0-flash";
    queryInput.placeholder      = "gemini-2.5-pro-preview-05-06";
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
    max_tokens:       parseInt(document.getElementById("llm-max-tokens").value) || null,
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
  if (config.max_tokens)       payload.max_tokens = config.max_tokens;
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
    currentTopicHasGraph = false;
    clearGraph();
    clearChat();
    setStatus("", "");
    refreshPinnedPanel(null);
    return;
  }

  currentTopic = topic;
  clearChat();
  stopPolling();
  refreshPinnedPanel(topic);

  // Refresh serverConfig — the server may have been reconfigured (e.g. the
  // user set OPENAI_API_KEY in .env and restarted) since the initial load.
  // Silent failure is fine: we fall back to the stale cached value.
  fetch("/api/config").then(r => r.json()).then(cfg => {
    serverConfig = cfg;
    updateLLMIndicator();
  }).catch(() => {});

  const status = await fetchTopicStatus(topic);
  currentTopicHasGraph = status.has_graph;
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
    const prog = status.build_progress || "Building...";
    const live = status.nodes_extracted != null
      ? ` · ${status.nodes_extracted} nodes · ${status.edges_extracted} edges`
      : "";
    setStatus("building", prog + live);
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

  const llm = llmPayload();
  const serverReady = serverConfig && serverConfig.has_server_config;
  if (!llm && !serverReady) {
    openSettingsModal();
    appendMessage("system", "Please configure your LLM provider and API key before building.");
    return;
  }

  const force = document.getElementById("chk-force-rebuild")?.checked || false;

  // Always offer the context modal — it influences the extraction prompt for any
  // documents being processed (new files on incremental, all files on full rebuild).
  // The modal pre-fills with the last-used context for this topic if any exists.
  const result = await openContextModal(currentTopic);
  if (result === false) return; // user cancelled
  const build_context = result; // null = empty input (backend uses default)

  await submitBuild(llm, force, build_context);
}

async function submitBuild(llm, force, build_context) {
  const btn = document.getElementById("btn-build");
  btn.disabled = true;

  const thinking = document.getElementById("chk-thinking")?.checked || false;

  try {
    const res = await fetch(`/api/topics/${encodeURIComponent(currentTopic)}/build`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ llm, force, thinking, build_context }),
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
        currentTopicHasGraph = true;
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
    const [graphRes, indexRes] = await Promise.all([
      fetch(`/api/topics/${encodeURIComponent(topic)}/graph`),
      fetch(`/api/topics/${encodeURIComponent(topic)}/index`),
    ]);
    if (!graphRes.ok) { clearGraph(); return; }
    const data = await graphRes.json();
    let index = null;
    if (indexRes.ok) {
      try { index = await indexRes.json(); } catch { index = null; }
    }
    initGraph(data, index);  // from graph.js
  } catch (err) {
    console.error("Failed to load graph:", err);
    clearGraph();
  }
}


async function onExportObsidian() {
  if (!currentTopic) {
    showAlert("Select a topic first.", "No topic");
    return;
  }
  if (!currentTopicHasGraph) {
    showAlert("Build the graph first before exporting.", "No graph");
    return;
  }
  const btn = document.getElementById("btn-export-obsidian");
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = "Exporting…";
  try {
    const url = `/api/topics/${encodeURIComponent(currentTopic)}/export/obsidian`;
    const res = await fetch(url);
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status} ${detail}`);
    }
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${currentTopic}_obsidian.zip`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  } catch (err) {
    console.error("Obsidian export failed:", err);
    showAlert(err.message || String(err), "Export failed");
  } finally {
    btn.disabled = false;
    btn.textContent = original;
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
  autosizeTextarea(input);
  appendMessage("user", query);

  const modeToggleEl = document.getElementById("mode-toggle");
  const mode = modeToggleEl && modeToggleEl.checked ? "extended" : "graph";

  // Streaming chat — consume an NDJSON stream from the server, rendering
  // tokens into the bubble as they arrive.
  const streamId = createStreamingMessage();
  setStreamingStatus(streamId, "Checking communities...");

  let answerText = "";
  let meta = { communities_checked: 0, relevant_communities: 0, mode, sources: [] };

  try {
    const res = await fetch(`/api/topics/${encodeURIComponent(currentTopic)}/query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, llm, mode }),
    });

    if (!res.ok) {
      // Error response is JSON (not streamed)
      let detail = "Query failed.";
      try { detail = (await res.json()).detail || detail; } catch {}
      removeMessage(streamId);
      appendMessage("system", detail);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let nl;
      while ((nl = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, nl).trim();
        buffer = buffer.slice(nl + 1);
        if (!line) continue;
        let event;
        try { event = JSON.parse(line); } catch { continue; }

        if (event.type === "status") {
          setStreamingStatus(streamId, event.message || "");
        } else if (event.type === "meta") {
          meta = { ...meta, ...event, mode };
          setStreamingStatus(streamId, ""); // clear — first token is imminent
        } else if (event.type === "token") {
          answerText += event.text || "";
          updateStreamingBody(streamId, answerText);
        } else if (event.type === "replace") {
          // Backend ran post-hoc citation filter — replace the streamed body.
          answerText = event.text || answerText;
          updateStreamingBody(streamId, answerText);
        } else if (event.type === "error") {
          answerText += `\n\n_Error: ${event.message || "unknown"}_`;
          updateStreamingBody(streamId, answerText);
        } else if (event.type === "done") {
          // handled via stream end below
        }
      }
    }

    finalizeStreamingMessage(streamId, meta, query, answerText);
  } catch (err) {
    removeMessage(streamId);
    appendMessage("system", "Network error: " + err.message);
  }
}

// ── Streaming message helpers ────────────────────────────────────────────────

function createStreamingMessage() {
  const id = "msg-" + (++_msgId);
  const messages = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.id = id;
  div.className = "chat-message chat-assistant";
  div.innerHTML = `
    <div class="chat-bubble" id="${id}-bubble"></div>
    <div class="chat-stream-status" id="${id}-status"></div>`;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return id;
}

function setStreamingStatus(id, text) {
  const el = document.getElementById(`${id}-status`);
  if (!el) return;
  if (!text) { el.style.display = "none"; el.textContent = ""; return; }
  el.style.display = "";
  el.innerHTML = `<span class="stream-dot"></span><span class="stream-dot"></span><span class="stream-dot"></span> ${text}`;
}

function updateStreamingBody(id, text) {
  const bubble = document.getElementById(`${id}-bubble`);
  if (!bubble) return;
  bubble.innerHTML = renderMarkdown(text);
  const messages = document.getElementById("chat-messages");
  messages.scrollTop = messages.scrollHeight;
}

function finalizeStreamingMessage(id, meta, question, answer) {
  const statusEl = document.getElementById(`${id}-status`);
  if (statusEl) statusEl.remove();
  const div = document.getElementById(id);
  if (!div) return;
  const modeLabel = meta.mode === "extended" ? " · Graph + AI knowledge" : "";
  let sourcesHTML = "";
  if (meta.sources && meta.sources.length > 0) {
    const items = meta.sources.map(s => `
      <div class="source-item">
        <div class="source-header" onclick="this.parentElement.classList.toggle('open')">
          <span class="source-num">Cluster ${s.id}</span>
          <span class="source-arrow">▸</span>
        </div>
        <div class="source-body">${s.summary.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/\n/g,"<br>")}</div>
      </div>`).join("");
    sourcesHTML = `
      <div class="chat-sources">
        <div class="sources-toggle" onclick="this.nextElementSibling.classList.toggle('open')">
          Sources (${meta.sources.length}) ▸
        </div>
        <div class="sources-list">${items}</div>
      </div>`;
  }
  // Pin button — only meaningful when we know what was asked & answered.
  let pinHTML = "";
  if (question && answer) {
    div.dataset.question = question;
    div.dataset.answer = answer;
    div.dataset.mode = meta.mode || "graph";
    div.dataset.sources = JSON.stringify(meta.sources || []);
    pinHTML = `<button class="chat-pin-btn" data-pin-msg="${id}" title="Pin this answer to the topic so you can revisit it later">📌 Pin answer</button>`;
  }
  div.innerHTML += `
    <div class="chat-meta">
      Checked ${meta.communities_checked} communities · ${meta.relevant_communities} relevant${modeLabel}
      ${pinHTML}
    </div>${sourcesHTML}`;
}

async function pinChatAnswer(messageDiv) {
  if (!currentTopic) return;
  const question = messageDiv.dataset.question;
  const answer = messageDiv.dataset.answer;
  const mode = messageDiv.dataset.mode || "graph";
  let sources = [];
  try { sources = JSON.parse(messageDiv.dataset.sources || "[]"); } catch {}
  const btn = messageDiv.querySelector(".chat-pin-btn");
  if (btn) { btn.disabled = true; btn.textContent = "Pinning…"; }
  try {
    const res = await fetch(`/api/topics/${encodeURIComponent(currentTopic)}/pinned`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, answer, mode, sources }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    if (btn) { btn.textContent = "✓ Pinned"; btn.classList.add("pinned"); }
    refreshPinnedPanel(currentTopic);
  } catch (err) {
    if (btn) { btn.disabled = false; btn.textContent = "📌 Pin answer"; }
    showAlert("Could not pin: " + (err.message || err), "Pin failed");
  }
}

async function refreshPinnedPanel(topic) {
  const panel = document.getElementById("pinned-list");
  if (!panel) return;
  if (!topic) { panel.innerHTML = ""; return; }
  try {
    const res = await fetch(`/api/topics/${encodeURIComponent(topic)}/pinned`);
    if (!res.ok) { panel.innerHTML = ""; return; }
    const items = await res.json();
    if (!items || !items.length) {
      panel.innerHTML = `<div class="pinned-empty">No pinned answers yet.</div>`;
      return;
    }
    panel.innerHTML = items.map(it => {
      const q = (it.question || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
      const short = q.length > 80 ? q.slice(0, 80) + "…" : q;
      return `<div class="pinned-item" data-pin-id="${it.id}" title="Click to load this answer into the chat">
        <div class="pinned-q">${short}</div>
        <button class="pinned-del" data-del-id="${it.id}" title="Remove">&#10005;</button>
      </div>`;
    }).join("");
  } catch {
    panel.innerHTML = "";
  }
}

async function loadPinnedIntoChat(pinId) {
  if (!currentTopic) return;
  try {
    const res = await fetch(`/api/topics/${encodeURIComponent(currentTopic)}/pinned`);
    if (!res.ok) return;
    const items = await res.json();
    const item = items.find(i => i.id === pinId);
    if (!item) return;
    appendMessage("user", item.question);
    const id = "msg-" + (++_msgId);
    const messages = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.id = id;
    div.className = "chat-message chat-assistant";
    div.innerHTML = `<div class="chat-bubble">${renderMarkdown(item.answer)}</div>`;
    messages.appendChild(div);
    finalizeStreamingMessage(id, {
      mode: item.mode || "graph",
      communities_checked: 0,
      relevant_communities: 0,
      sources: item.sources || [],
    }, item.question, item.answer);
    messages.scrollTop = messages.scrollHeight;
  } catch {}
}

async function deletePinned(pinId) {
  if (!currentTopic || !pinId) return;
  try {
    await fetch(`/api/topics/${encodeURIComponent(currentTopic)}/pinned/${pinId}`, { method: "DELETE" });
    refreshPinnedPanel(currentTopic);
  } catch {}
}

let _msgId = 0;

function autosizeTextarea(el) {
  if (!el) return;
  // Reset height so shrink works when text is deleted; then size to scrollHeight
  // capped by the CSS max-height (the element handles its own scroll past that).
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 200) + "px";
}

function renderMarkdown(text) {
  const lines = text.split('\n');
  let html = '';
  let inUl = false, inOl = false;
  let tableLines = [];
  let inCode = false;
  let codeLang = '';
  let codeBuf = [];

  function closeLists() {
    if (inUl) { html += '</ul>'; inUl = false; }
    if (inOl) { html += '</ol>'; inOl = false; }
  }

  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function flushTable() {
    if (tableLines.length < 2) {
      tableLines.forEach(l => { html += `<p>${inline(l)}</p>`; });
      tableLines = [];
      return;
    }
    // Find separator row index (|---|---|)
    const sepIdx = tableLines.findIndex(l => /^\|[\s\-|:]+\|$/.test(l.trim()));
    if (sepIdx < 1) {
      tableLines.forEach(l => { html += `<p>${inline(l)}</p>`; });
      tableLines = [];
      return;
    }
    const parseRow = l => l.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
    let t = '<table class="chat-table"><thead><tr>';
    parseRow(tableLines[sepIdx - 1]).forEach(h => { t += `<th>${inline(h)}</th>`; });
    t += '</tr></thead><tbody>';
    tableLines.slice(sepIdx + 1).forEach(l => {
      t += '<tr>';
      parseRow(l).forEach(c => { t += `<td>${inline(c)}</td>`; });
      t += '</tr>';
    });
    t += '</tbody></table>';
    html += t;
    tableLines = [];
  }

  function inline(s) {
    return s
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\[\[([^\[\]\n]{1,80})\]\]/g, (_, name) => {
        const safe = name.replace(/"/g, '&quot;');
        return `<span class="cite-chip" data-cite="${safe}" title="Click to select in graph">${name}</span>`;
      })
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*([^*]+?)\*/g, '<em>$1</em>');
  }

  for (const raw of lines) {
    const line = raw.trimEnd();
    // Fenced code blocks — opened and closed with ``` on their own line.
    // Content inside is rendered verbatim (no inline markdown applied).
    const fenceMatch = line.match(/^```(\w*)\s*$/);
    if (fenceMatch) {
      if (inCode) {
        html += `<pre class="chat-pre"><code${codeLang ? ` class="lang-${codeLang}"` : ''}>${escapeHtml(codeBuf.join('\n'))}</code></pre>`;
        inCode = false;
        codeLang = '';
        codeBuf = [];
      } else {
        closeLists();
        if (tableLines.length) flushTable();
        inCode = true;
        codeLang = fenceMatch[1] || '';
      }
      continue;
    }
    if (inCode) {
      codeBuf.push(raw);
      continue;
    }
    if (/^\|/.test(line)) {
      closeLists();
      tableLines.push(line);
    } else {
      if (tableLines.length) flushTable();
      if (/^## /.test(line)) {
        closeLists();
        html += `<h2 class="chat-h2">${inline(line.slice(3))}</h2>`;
      } else if (/^### /.test(line)) {
        closeLists();
        html += `<h3 class="chat-h3">${inline(line.slice(4))}</h3>`;
      } else if (/^- /.test(line)) {
        if (inOl) { html += '</ol>'; inOl = false; }
        if (!inUl) { html += '<ul class="chat-ul">'; inUl = true; }
        html += `<li>${inline(line.slice(2))}</li>`;
      } else if (/^\d+\. /.test(line)) {
        if (inUl) { html += '</ul>'; inUl = false; }
        if (!inOl) { html += '<ol class="chat-ol">'; inOl = true; }
        html += `<li>${inline(line.replace(/^\d+\. /, ''))}</li>`;
      } else if (line.trim() === '') {
        closeLists();
        html += '<br>';
      } else {
        closeLists();
        html += `<p>${inline(line)}</p>`;
      }
    }
  }
  if (inCode) {
    // Unclosed fence — render what we have so content isn't lost
    html += `<pre class="chat-pre"><code>${escapeHtml(codeBuf.join('\n'))}</code></pre>`;
  }
  if (tableLines.length) flushTable();
  closeLists();
  return html;
}

function appendMessage(role, content, loading = false, meta = null) {
  const id = "msg-" + (++_msgId);
  const messages = document.getElementById("chat-messages");

  const div = document.createElement("div");
  div.id = id;
  div.className = `chat-message chat-${role}`;

  if (loading) {
    div.innerHTML = `<div class="chat-loading"><span></span><span></span><span></span></div>`;
  } else {
    div.innerHTML = `<div class="chat-bubble">${renderMarkdown(content || "")}</div>`;

    if (meta && role === "assistant") {
      const modeLabel = meta.mode === "extended" ? " · Graph + AI knowledge" : "";
      let sourcesHTML = "";
      if (meta.sources && meta.sources.length > 0) {
        const items = meta.sources.map((s, i) => `
          <div class="source-item">
            <div class="source-header" onclick="this.parentElement.classList.toggle('open')">
              <span class="source-num">Cluster ${s.id}</span>
              <span class="source-arrow">▸</span>
            </div>
            <div class="source-body">${s.summary.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/\n/g,"<br>")}</div>
          </div>`).join("");
        sourcesHTML = `
          <div class="chat-sources">
            <div class="sources-toggle" onclick="this.nextElementSibling.classList.toggle('open')">
              Sources (${meta.sources.length}) ▸
            </div>
            <div class="sources-list">${items}</div>
          </div>`;
      }
      div.innerHTML += `
        <div class="chat-meta">
          Checked ${meta.communities_checked} communities · ${meta.relevant_communities} relevant${modeLabel}
        </div>${sourcesHTML}`;
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
