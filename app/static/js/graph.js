/**
 * graph.js — D3.js force-directed knowledge graph visualization.
 * Adapted from graph_template.html.
 *
 * Public API:
 *   initGraph(graphData)  — render a graph in #graph-container
 *   clearGraph()          — clear the SVG
 */

const PALETTE = [
  "#4ECDC4", "#FF6B6B", "#60a5fa", "#FBBF24", "#86efac",
  "#c084fc", "#fb923c", "#f472b6", "#a78bfa", "#34d399",
  "#fca5a5", "#93c5fd", "#6ee7b7", "#fde68a", "#d8b4fe",
];

let _simulation = null;

function clearGraph() {
  if (_simulation) { _simulation.stop(); _simulation = null; }
  const root = document.getElementById("root");
  if (root) root.innerHTML = "";
  const legend = document.getElementById("legend");
  if (legend) legend.innerHTML = "";
  const detail = document.getElementById("detail-panel");
  if (detail) detail.classList.remove("visible");
}

function initGraph(GRAPH_DATA) {
  clearGraph();

  if (!GRAPH_DATA || !GRAPH_DATA.nodes || GRAPH_DATA.nodes.length === 0) {
    document.getElementById("graph-empty").style.display = "flex";
    return;
  }
  document.getElementById("graph-empty").style.display = "none";

  // ── Dynamic COLOR_MAP ─────────────────────────────────────────────────────
  const uniqueTypes = [...new Set(GRAPH_DATA.nodes.map(n => n.type).filter(Boolean))];
  const COLOR_MAP = {};
  uniqueTypes.forEach((type, i) => {
    COLOR_MAP[type] = PALETTE[i % PALETTE.length];
  });
  COLOR_MAP["OTHER"] = COLOR_MAP["OTHER"] || "#94a3b8";

  function nodeColor(type) {
    return COLOR_MAP[type] || COLOR_MAP["OTHER"];
  }

  // ── Setup ─────────────────────────────────────────────────────────────────
  const svg       = d3.select("#graph");
  const root      = d3.select("#root");
  const tooltip   = document.getElementById("tooltip");
  const container = document.getElementById("graph-container");

  let W = container.clientWidth;
  let H = container.clientHeight;

  const zoom = d3.zoom()
    .scaleExtent([0.05, 6])
    .on("zoom", e => root.attr("transform", e.transform));
  svg.call(zoom);

  // ── Force simulation ──────────────────────────────────────────────────────
  const nodes = GRAPH_DATA.nodes.map(d => ({ ...d }));
  const links = GRAPH_DATA.links.map(d => ({ ...d }));

  const degreeMap = {};
  links.forEach(l => {
    degreeMap[l.source] = (degreeMap[l.source] || 0) + 1;
    degreeMap[l.target] = (degreeMap[l.target] || 0) + 1;
  });
  nodes.forEach(n => { n.degree = degreeMap[n.id] || 1; });

  const maxDeg = Math.max(...nodes.map(n => n.degree));
  const minDeg = Math.min(...nodes.map(n => n.degree));
  const nodeRadius = d => {
    const t = (d.degree - minDeg) / (maxDeg - minDeg || 1);
    return 8 + t * 28;
  };

  _simulation = d3.forceSimulation(nodes)
    .force("link",      d3.forceLink(links).id(d => d.id).distance(120))
    .force("charge",    d3.forceManyBody().strength(-300))
    .force("center",    d3.forceCenter(W / 2, H / 2))
    .force("collision", d3.forceCollide().radius(d => nodeRadius(d) + 6));

  // ── Draw links ────────────────────────────────────────────────────────────
  const linkGroup  = root.append("g").attr("class", "links");
  const labelGroup = root.append("g").attr("class", "edge-labels");
  const nodeGroup  = root.append("g").attr("class", "nodes");

  const link = linkGroup.selectAll("line")
    .data(links).join("line")
    .attr("class", "link")
    .attr("marker-end", "url(#arrow)");

  const edgeLabel = labelGroup.selectAll("text")
    .data(links).join("text")
    .attr("class", "edge-label")
    .text(d => d.label || "");

  // ── Draw nodes ────────────────────────────────────────────────────────────
  const node = nodeGroup.selectAll("g")
    .data(nodes).join("g")
    .attr("class", "node")
    .call(d3.drag()
      .on("start", dragStart)
      .on("drag",  dragged)
      .on("end",   dragEnd));

  node.append("circle")
    .attr("r", nodeRadius)
    .attr("fill", d => nodeColor(d.type));

  node.append("text")
    .attr("dy", d => nodeRadius(d) + 11)
    .text(d => d.label && d.label.length > 20 ? d.label.slice(0, 18) + "…" : (d.label || ""))
    .style("font-size", d => d.degree > 3 ? "11px" : "9px")
    .style("opacity", d => d.degree > 2 ? 1 : 0.5);

  // ── Simulation tick ───────────────────────────────────────────────────────
  _simulation.on("tick", () => {
    link
      .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
    edgeLabel
      .attr("x", d => (d.source.x + d.target.x) / 2)
      .attr("y", d => (d.source.y + d.target.y) / 2);
    node.attr("transform", d => `translate(${d.x},${d.y})`);
  });

  // ── Tooltip & selection ───────────────────────────────────────────────────
  let selectedNode = null;
  let _clickTimer = null;

  node
    .on("mouseover", (e, d) => {
      const connections = links.filter(l =>
        l.source.id === d.id || l.target.id === d.id).length;
      tooltip.innerHTML = `
        <div class="tt-name">${d.label}</div>
        <div class="tt-type" style="color:${nodeColor(d.type)}">${d.type}</div>
        ${d.description ? `<div class="tt-desc">${d.description}</div>` : ""}
        <div class="tt-connections"><span>${connections}</span> connection${connections !== 1 ? "s" : ""}</div>
      `;
      tooltip.classList.add("visible");
      positionTooltip(e);
    })
    .on("mousemove", positionTooltip)
    .on("mouseleave", () => tooltip.classList.remove("visible"))
    .on("click", (e, d) => {
      e.stopPropagation();
      tooltip.classList.remove("visible");
      if (_clickTimer) {
        // Second click within 280ms → treat as double-click
        clearTimeout(_clickTimer);
        _clickTimer = null;
        showNodeModal(d, links, nodes, nodeColor);
      } else {
        const captured = d;
        _clickTimer = setTimeout(() => {
          _clickTimer = null;
          if (selectedNode === captured.id) {
            clearSelection();
            hideDetailPanel();
          } else {
            selectNode(captured);
            showNodeDetail(captured, links, nodes, nodeColor);
          }
        }, 280);
      }
    });

  // Edge click — show edge detail panel
  link.on("click", (e, d) => {
    e.stopPropagation();
    showEdgeDetail(d, nodeColor);
  });

  svg.on("click", () => { clearSelection(); hideDetailPanel(); });

  function positionTooltip(e) {
    const rect = container.getBoundingClientRect();
    let x = e.clientX - rect.left + 14;
    let y = e.clientY - rect.top  - 10;
    if (x + 280 > W) x = e.clientX - rect.left - 280;
    tooltip.style.left = x + "px";
    tooltip.style.top  = y + "px";
  }

  function selectNode(d) {
    selectedNode = d.id;
    const connectedIds = new Set([d.id]);
    links.forEach(l => {
      if (l.source.id === d.id) connectedIds.add(l.target.id);
      if (l.target.id === d.id) connectedIds.add(l.source.id);
    });
    node.classed("selected", n => n.id === d.id);
    node.classed("dimmed",   n => !connectedIds.has(n.id));
    link.classed("highlighted", l => l.source.id === d.id || l.target.id === d.id);
    link.classed("dimmed",      l => l.source.id !== d.id && l.target.id !== d.id);
  }

  function clearSelection() {
    selectedNode = null;
    node.classed("selected dimmed", false);
    link.classed("highlighted dimmed", false);
  }

  // ── Drag ──────────────────────────────────────────────────────────────────
  function dragStart(e, d) {
    if (!e.active) _simulation.alphaTarget(0.3).restart();
    d.fx = d.x; d.fy = d.y;
  }
  function dragged(e, d)  { d.fx = e.x; d.fy = e.y; }
  function dragEnd(e, d)  {
    if (!e.active) _simulation.alphaTarget(0);
    d.fx = null; d.fy = null;
  }

  // ── Legend ────────────────────────────────────────────────────────────────
  const typeCounts = {};
  nodes.forEach(n => { typeCounts[n.type] = (typeCounts[n.type] || 0) + 1; });

  const hiddenTypes = new Set();
  const legendEl = document.getElementById("legend");
  legendEl.innerHTML = "";

  Object.entries(COLOR_MAP).forEach(([type, color]) => {
    if (!typeCounts[type]) return;
    const item = document.createElement("div");
    item.className = "legend-item";
    item.innerHTML = `
      <div class="legend-dot" style="background:${color}"></div>
      <span class="legend-name">${type}</span>
      <span class="legend-count">${typeCounts[type]}</span>
    `;
    item.addEventListener("click", () => {
      if (hiddenTypes.has(type)) {
        hiddenTypes.delete(type);
        item.classList.remove("disabled");
      } else {
        hiddenTypes.add(type);
        item.classList.add("disabled");
      }
      applyTypeFilter();
    });
    legendEl.appendChild(item);
  });

  function applyTypeFilter() {
    node.style("display", d => hiddenTypes.has(d.type) ? "none" : null);
    link.style("display", d => {
      const sHidden = hiddenTypes.has(d.source.type);
      const tHidden = hiddenTypes.has(d.target.type);
      return sHidden || tHidden ? "none" : null;
    });
  }

  // ── Search ────────────────────────────────────────────────────────────────
  const searchEl = document.getElementById("search");
  const searchDrop = document.getElementById("search-dropdown");

  function closeSearchDrop() {
    if (searchDrop) searchDrop.innerHTML = "", searchDrop.classList.remove("open");
  }

  function panToNode(d) {
    const container = document.getElementById("graph-container");
    const W = container.clientWidth;
    const H = container.clientHeight;
    const scale = 1.6;
    svg.transition().duration(500).call(
      zoom.transform,
      d3.zoomIdentity.translate(W / 2 - scale * d.x, H / 2 - scale * d.y).scale(scale)
    );
  }

  function pickSearchResult(match) {
    closeSearchDrop();
    if (searchEl) searchEl.value = match.label;
    selectNode(match);
    showNodeDetail(match, links, nodes, nodeColor);
    panToNode(match);
  }

  if (searchEl) {
    searchEl.value = "";
    searchEl.oninput = e => {
      const q = e.target.value.toLowerCase().trim();
      if (!q) { closeSearchDrop(); clearSelection(); hideDetailPanel(); return; }

      const results = nodes
        .filter(n =>
          n.label.toLowerCase().includes(q) ||
          (n.description || "").toLowerCase().includes(q)
        )
        .sort((a, b) => {
          // Exact / prefix matches first
          const aLabel = a.label.toLowerCase();
          const bLabel = b.label.toLowerCase();
          const aStarts = aLabel.startsWith(q) ? 0 : 1;
          const bStarts = bLabel.startsWith(q) ? 0 : 1;
          return aStarts - bStarts || aLabel.localeCompare(bLabel);
        })
        .slice(0, 10);

      if (!searchDrop) {
        if (results[0]) pickSearchResult(results[0]);
        return;
      }

      searchDrop.innerHTML = "";
      if (!results.length) { closeSearchDrop(); return; }

      results.forEach(n => {
        const item = document.createElement("div");
        item.className = "search-result-item";
        const descSnippet = n.description
          ? n.description.slice(0, 80) + (n.description.length > 80 ? "…" : "")
          : "";
        item.innerHTML = `
          <span class="sri-type" style="color:${nodeColor(n.type)}">${n.type}</span>
          <span class="sri-label">${n.label}</span>
          ${descSnippet ? `<span class="sri-desc">${descSnippet}</span>` : ""}
        `;
        item.addEventListener("mousedown", e => { e.preventDefault(); pickSearchResult(n); });
        searchDrop.appendChild(item);
      });
      searchDrop.classList.add("open");
    };

    searchEl.addEventListener("keydown", e => {
      if (!searchDrop || !searchDrop.classList.contains("open")) return;
      const items = searchDrop.querySelectorAll(".search-result-item");
      const active = searchDrop.querySelector(".search-result-item.active");
      let idx = active ? [...items].indexOf(active) : -1;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (active) active.classList.remove("active");
        items[Math.min(idx + 1, items.length - 1)].classList.add("active");
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        if (active) active.classList.remove("active");
        items[Math.max(idx - 1, 0)].classList.add("active");
      } else if (e.key === "Enter") {
        const picked = searchDrop.querySelector(".search-result-item.active") || items[0];
        if (picked) picked.dispatchEvent(new MouseEvent("mousedown"));
      } else if (e.key === "Escape") {
        closeSearchDrop();
      }
    });

    searchEl.addEventListener("blur", () => setTimeout(closeSearchDrop, 150));
  }

  // ── Controls ──────────────────────────────────────────────────────────────
  const linkDistEl = document.getElementById("link-distance");
  if (linkDistEl) {
    linkDistEl.value = 120;
    linkDistEl.oninput = e => {
      _simulation.force("link").distance(+e.target.value);
      _simulation.alpha(0.3).restart();
    };
  }

  const chargeEl = document.getElementById("charge");
  if (chargeEl) {
    chargeEl.value = -300;
    chargeEl.oninput = e => {
      _simulation.force("charge").strength(+e.target.value);
      _simulation.alpha(0.3).restart();
    };
  }

  const labelThreshEl = document.getElementById("label-threshold");
  if (labelThreshEl) {
    labelThreshEl.value = 7;
    labelThreshEl.oninput = e => {
      const threshold = 10 - +e.target.value;
      edgeLabel.classed("visible", d => {
        const minD = Math.min(d.source.degree || 1, d.target.degree || 1);
        return minD >= threshold;
      });
    };
  }

  document.getElementById("btn-reset").onclick = () => {
    svg.transition().duration(500).call(
      zoom.transform, d3.zoomIdentity.translate(0, 0).scale(1)
    );
  };

  document.getElementById("btn-all").onclick = () => {
    hiddenTypes.clear();
    document.querySelectorAll(".legend-item").forEach(el => el.classList.remove("disabled"));
    applyTypeFilter();
    clearSelection();
    hideDetailPanel();
  };

  // ── Resize ────────────────────────────────────────────────────────────────
  window.onresize = () => {
    W = container.clientWidth;
    H = container.clientHeight;
    _simulation.force("center", d3.forceCenter(W / 2, H / 2));
    _simulation.alpha(0.1).restart();
  };
}


// ── Detail panel (Obsidian-style) ─────────────────────────────────────────────

function showNodeDetail(d, links, nodes, nodeColor) {
  const panel = document.getElementById("detail-panel");
  const nodeIndex = {};
  nodes.forEach(n => { nodeIndex[n.id] = n; });

  const outgoing = links.filter(l => l.source.id === d.id);
  const incoming = links.filter(l => l.target.id === d.id);

  let relHTML = "";
  if (outgoing.length > 0) {
    relHTML += `<div class="dp-rel-header">Outgoing</div>`;
    outgoing.forEach(l => {
      const tgt = nodeIndex[l.target.id] || { label: l.target.id, type: "OTHER" };
      relHTML += `
        <div class="dp-rel-item" data-node-id="${tgt.id}" style="cursor:pointer;">
          <span class="dp-rel-label" style="color:${nodeColor ? nodeColor(tgt.type) : '#94a3b8'}">${l.label || "→"}</span>
          <span class="dp-rel-name">${tgt.label}</span>
          ${l.description ? `<div class="dp-rel-desc">${l.description}</div>` : ""}
        </div>`;
    });
  }
  if (incoming.length > 0) {
    relHTML += `<div class="dp-rel-header">Incoming</div>`;
    incoming.forEach(l => {
      const src = nodeIndex[l.source.id] || { label: l.source.id, type: "OTHER" };
      relHTML += `
        <div class="dp-rel-item" data-node-id="${src.id}" style="cursor:pointer;">
          <span class="dp-rel-label" style="color:${nodeColor ? nodeColor(src.type) : '#94a3b8'}">${l.label || "←"}</span>
          <span class="dp-rel-name">${src.label}</span>
          ${l.description ? `<div class="dp-rel-desc">${l.description}</div>` : ""}
        </div>`;
    });
  }

  panel.innerHTML = `
    <div class="dp-close" onclick="hideDetailPanel()">✕</div>
    <div class="dp-type" style="color:${nodeColor ? nodeColor(d.type) : '#94a3b8'}">${d.type}</div>
    <div class="dp-title">${d.label}</div>
    ${d.description ? `<div class="dp-description">${d.description}</div>` : ""}
    ${relHTML ? `<div class="dp-relations">${relHTML}</div>` : ""}
  `;

  panel.classList.add("visible");
}

function showEdgeDetail(d, nodeColor) {
  const panel = document.getElementById("detail-panel");
  const srcLabel = d.source.label || d.source.id || d.source;
  const tgtLabel = d.target.label || d.target.id || d.target;
  const srcType  = d.source.type || "";
  const tgtType  = d.target.type || "";

  panel.innerHTML = `
    <div class="dp-close" onclick="hideDetailPanel()">✕</div>
    <div class="dp-type">RELATIONSHIP</div>
    <div class="dp-title">${d.label || "connected to"}</div>
    ${d.description ? `<div class="dp-description">${d.description}</div>` : ""}
    <div class="dp-relations">
      <div class="dp-rel-header">Connects</div>
      <div class="dp-rel-item">
        <span class="dp-rel-label" style="color:${nodeColor ? nodeColor(srcType) : '#94a3b8'}">${srcType}</span>
        <span class="dp-rel-name">${srcLabel}</span>
      </div>
      <div class="dp-rel-item">
        <span class="dp-rel-label" style="color:${nodeColor ? nodeColor(tgtType) : '#94a3b8'}">${tgtType}</span>
        <span class="dp-rel-name">${tgtLabel}</span>
      </div>
    </div>
  `;

  panel.classList.add("visible");
}

function hideDetailPanel() {
  const panel = document.getElementById("detail-panel");
  if (panel) panel.classList.remove("visible");
}


// ── Node detail modal (Wikipedia-style) ───────────────────────────────────────

function showNodeModal(d, links, nodes, nodeColor) {
  const color = nodeColor ? nodeColor(d.type) : "#94a3b8";
  const content = document.getElementById("node-modal-content");

  // Show loading state immediately
  content.innerHTML = `
    <div class="nm-type" style="color:${color}">${d.type || "ENTITY"}</div>
    <div class="nm-title">${d.label}</div>
    <div class="nm-loading">
      <div class="nm-spinner"></div>
      <span>Generating article…</span>
    </div>
  `;
  document.getElementById("node-modal-backdrop").classList.add("open");
  // Store node on backdrop so Recreate can re-fetch
  document.getElementById("node-modal-backdrop")._modalNode = { d, links, nodes, nodeColor };

  // currentTopic is a global set by app.js
  const topic = (typeof currentTopic !== "undefined") ? currentTopic : null;
  if (!topic) {
    _renderModalFromLocal(d, links, nodes, nodeColor, content);
    return;
  }

  // Include session LLM config so wiki generation uses the user's chosen provider
  const llmCfg = (typeof getLLMConfig === "function") ? getLLMConfig() : null;
  fetch(`/api/topics/${encodeURIComponent(topic)}/nodes/${encodeURIComponent(d.id)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ generate: true, llm: llmCfg }),
  })
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      if (!data) { _renderModalFromLocal(d, links, nodes, nodeColor, content); return; }
      _renderModalFromAPI(data, d, links, nodes, nodeColor, content);
    })
    .catch(() => _renderModalFromLocal(d, links, nodes, nodeColor, content));
}

function _renderModalFromAPI(data, d, links, nodes, nodeColor, content) {
  const color = nodeColor ? nodeColor(data.type) : "#94a3b8";
  const totalConnections = (data.outgoing || []).length + (data.incoming || []).length;

  function relCard(rel, isOutgoing) {
    const otherColor = nodeColor ? nodeColor(rel.node_type) : "#94a3b8";
    return `
      <div class="nm-rel-item" data-node-id="${rel.node_id}">
        <div class="nm-rel-direction" style="color:${isOutgoing ? color : otherColor}">
          ${isOutgoing ? "→ " + (data.type || "") : "← " + (rel.node_type || "")}
        </div>
        <div class="nm-rel-verb">${rel.relation || (isOutgoing ? "relates to" : "related from")}</div>
        <div class="nm-rel-name" style="color:${otherColor}">${rel.node_label}</div>
        ${rel.description ? `<div class="nm-rel-desc">${rel.description}</div>` : ""}
      </div>`;
  }

  const allRels = [
    ...(data.outgoing || []).map(r => relCard(r, true)),
    ...(data.incoming || []).map(r => relCard(r, false)),
  ];

  // Format wiki article paragraphs
  const wikiHTML = data.wiki_article
    ? data.wiki_article.split(/\n\n+/).map(p => `<p>${p.trim()}</p>`).join("")
    : "";

  content.innerHTML = `
    <div class="nm-type" style="color:${color}">${data.type || "ENTITY"}</div>
    <div class="nm-title">${data.label}</div>
    <div class="nm-meta">
      <span>${totalConnections}</span> connection${totalConnections !== 1 ? "s" : ""}
      &nbsp;·&nbsp;
      <span>${(data.outgoing || []).length}</span> outgoing
      &nbsp;·&nbsp;
      <span>${(data.incoming || []).length}</span> incoming
      ${data.has_wiki ? `&nbsp;·&nbsp;<button class="nm-recreate-btn" id="nm-recreate">↺ Recreate</button>` : ""}
    </div>
    ${wikiHTML ? `
      <hr class="nm-divider">
      <div class="nm-wiki-article">${wikiHTML}</div>
    ` : data.description ? `
      <hr class="nm-divider">
      <div class="nm-section-title">Description</div>
      <div class="nm-description">${data.description}</div>
    ` : ""}
    ${data.community_summary ? `
      <hr class="nm-divider">
      <div class="nm-section-title">Cluster Context</div>
      <div class="nm-community-summary">${data.community_summary}</div>
    ` : ""}
    ${allRels.length ? `
      <hr class="nm-divider">
      <div class="nm-section-title">Relationships (${allRels.length})</div>
      <div class="nm-relations">${allRels.join("")}</div>
    ` : ""}
  `;

  content.querySelectorAll(".nm-rel-item[data-node-id]").forEach(el => {
    el.addEventListener("click", () => {
      const targetId = el.dataset.nodeId;
      const targetNode = nodes.find(n => n.id === targetId);
      hideNodeModal();
      if (targetNode) setTimeout(() => showNodeModal(targetNode, links, nodes, nodeColor), 180);
    });
  });

  const recreateBtn = content.querySelector("#nm-recreate");
  if (recreateBtn) {
    recreateBtn.addEventListener("click", () => {
      const ctx = document.getElementById("node-modal-backdrop")._modalNode;
      if (!ctx) return;
      // Show spinner, then re-fetch with force=true
      content.innerHTML = `
        <div class="nm-type" style="color:${color}">${data.type || "ENTITY"}</div>
        <div class="nm-title">${data.label}</div>
        <div class="nm-loading"><div class="nm-spinner"></div><span>Regenerating article…</span></div>
      `;
      const topic = (typeof currentTopic !== "undefined") ? currentTopic : null;
      if (!topic) return;
      const llmCfg = (typeof getLLMConfig === "function") ? getLLMConfig() : null;
      fetch(`/api/topics/${encodeURIComponent(topic)}/nodes/${encodeURIComponent(data.id)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ generate: true, force: true, llm: llmCfg }),
      })
        .then(r => r.ok ? r.json() : null)
        .then(refreshed => {
          if (refreshed) _renderModalFromAPI(refreshed, ctx.d, ctx.links, ctx.nodes, ctx.nodeColor, content);
          else _renderModalFromLocal(ctx.d, ctx.links, ctx.nodes, ctx.nodeColor, content);
        })
        .catch(() => _renderModalFromLocal(ctx.d, ctx.links, ctx.nodes, ctx.nodeColor, content));
    });
  }
}

function _renderModalFromLocal(d, links, nodes, nodeColor, content) {
  const nodeIndex = {};
  nodes.forEach(n => { nodeIndex[n.id] = n; });
  const outgoing = links.filter(l => l.source.id === d.id);
  const incoming = links.filter(l => l.target.id === d.id);
  const totalConnections = outgoing.length + incoming.length;
  const color = nodeColor ? nodeColor(d.type) : "#94a3b8";

  function relCard(l, isOutgoing) {
    const other = isOutgoing
      ? (nodeIndex[l.target.id] || { id: l.target.id, label: l.target.id, type: "OTHER" })
      : (nodeIndex[l.source.id] || { id: l.source.id, label: l.source.id, type: "OTHER" });
    const otherColor = nodeColor ? nodeColor(other.type) : "#94a3b8";
    return `
      <div class="nm-rel-item" data-node-id="${other.id}">
        <div class="nm-rel-direction" style="color:${isOutgoing ? color : otherColor}">
          ${isOutgoing ? "→ " + (d.type || "") : "← " + (other.type || "")}
        </div>
        <div class="nm-rel-verb">${l.label || (isOutgoing ? "relates to" : "related from")}</div>
        <div class="nm-rel-name" style="color:${otherColor}">${other.label || other.id}</div>
        ${l.description ? `<div class="nm-rel-desc">${l.description}</div>` : ""}
      </div>`;
  }

  const allRels = [
    ...outgoing.map(l => relCard(l, true)),
    ...incoming.map(l => relCard(l, false)),
  ];

  content.innerHTML = `
    <div class="nm-type" style="color:${color}">${d.type || "ENTITY"}</div>
    <div class="nm-title">${d.label}</div>
    <div class="nm-meta">
      <span>${totalConnections}</span> connection${totalConnections !== 1 ? "s" : ""}
      &nbsp;·&nbsp;
      <span>${outgoing.length}</span> outgoing
      &nbsp;·&nbsp;
      <span>${incoming.length}</span> incoming
    </div>
    ${d.description ? `
      <hr class="nm-divider">
      <div class="nm-section-title">Description</div>
      <div class="nm-description">${d.description}</div>
    ` : ""}
    ${allRels.length ? `
      <hr class="nm-divider">
      <div class="nm-section-title">Relationships (${allRels.length})</div>
      <div class="nm-relations">${allRels.join("")}</div>
    ` : ""}
  `;

  content.querySelectorAll(".nm-rel-item[data-node-id]").forEach(el => {
    el.addEventListener("click", () => {
      const targetId = el.dataset.nodeId;
      const targetNode = nodes.find(n => n.id === targetId);
      hideNodeModal();
      if (targetNode) setTimeout(() => showNodeModal(targetNode, links, nodes, nodeColor), 180);
    });
  });
}

function hideNodeModal() {
  document.getElementById("node-modal-backdrop").classList.remove("open");
}

// Close on backdrop click or ESC
document.addEventListener("DOMContentLoaded", () => {
  const backdrop = document.getElementById("node-modal-backdrop");
  if (!backdrop) return;

  document.getElementById("node-modal-close").addEventListener("click", hideNodeModal);

  backdrop.addEventListener("click", e => {
    if (e.target === backdrop) hideNodeModal();
  });

  document.addEventListener("keydown", e => {
    if (e.key === "Escape") hideNodeModal();
  });
});
