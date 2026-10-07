// CineMind Frontend Client Logic

let currentMode = "query";
let currentRetrieval = "hybrid";
let isReplay = true;
let activeScenarioId = "nolan_scifi";
let loadedScenarios = [];
let eventSource = null;

document.addEventListener("DOMContentLoaded", () => {
  initHealth();
  initScenarios();
  initResults();
});

// Navigation
function switchTab(tabName) {
  document.querySelectorAll(".nav-tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".view-panel").forEach(panel => panel.style.display = "none");

  const activeBtn = document.getElementById(`tab-${tabName}`);
  const activePanel = document.getElementById(`view-${tabName}`);
  if (activeBtn) activeBtn.classList.add("active");
  if (activePanel) activePanel.style.display = "block";

  if (tabName === "compare") {
    loadComparison();
  }
}

// Health Check
async function initHealth() {
  const pill = document.getElementById("health-pill");
  const text = document.getElementById("health-status-text");
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health check failed");
    const data = await res.json();
    text.textContent = `Model: ${data.model_name} | Catalog: ${data.catalog_size} movies`;
  } catch (err) {
    text.textContent = "Offline / Server Unavailable";
    pill.style.color = "#f43f5e";
  }
}

// Scenarios
async function initScenarios() {
  const container = document.getElementById("scenarios-container");
  const select = document.getElementById("compare-scenario-select");
  try {
    const res = await fetch("/api/scenarios");
    loadedScenarios = await res.json();
    container.innerHTML = "";
    select.innerHTML = "";

    loadedScenarios.forEach((sc, idx) => {
      // Create scenario card
      const card = document.createElement("button");
      card.type = "button";
      card.className = `scenario-card ${sc.id === activeScenarioId ? "active" : ""}`;
      card.id = `sc-card-${sc.id}`;
      card.onclick = () => selectScenario(sc.id);

      const tagClass = sc.cold_start ? "cold" : (sc.mode === "query" ? "query" : "feed");
      const tagLabel = sc.cold_start ? "★ Cold-Start" : sc.mode.toUpperCase();

      card.innerHTML = `
        <span class="scenario-tag ${tagClass}">${tagLabel}</span>
        <div class="scenario-name">${escapeHtml(sc.title)}</div>
        <div class="scenario-blurb">${escapeHtml(sc.blurb)}</div>
      `;
      container.appendChild(card);

      // Add to compare select
      const opt = document.createElement("option");
      opt.value = sc.id;
      opt.textContent = `${sc.cold_start ? '[Cold-Start] ' : ''}${sc.title}`;
      if (sc.id === activeScenarioId) opt.selected = true;
      select.appendChild(opt);
    });

    // Auto-select first scenario and trigger replay
    if (loadedScenarios.length > 0) {
      selectScenario(loadedScenarios[0].id);
    }
  } catch (err) {
    container.innerHTML = `<div style="color:var(--accent-rose);">Failed to load preset scenarios: ${err.message}</div>`;
  }
}

function selectScenario(scId) {
  activeScenarioId = scId;
  const sc = loadedScenarios.find(s => s.id === scId);
  if (!sc) return;

  // Highlight card
  document.querySelectorAll(".scenario-card").forEach(c => c.classList.remove("active"));
  const card = document.getElementById(`sc-card-${scId}`);
  if (card) card.classList.add("active");

  // Populate inputs
  const input = document.getElementById("query-input");
  if (sc.mode === "query") {
    input.value = sc.query || "";
    setMode("query");
  } else {
    input.value = "";
    input.placeholder = `Viewing history: ${sc.history ? sc.history.map(h => h.title || h.movie_id).join(', ') : 'Profile loaded'}`;
    setMode("feed");
  }

  // Set replay active for instant demo
  if (!isReplay) toggleReplay();

  // Run automatically
  executeRecommendation();
}

function setMode(mode) {
  currentMode = mode;
  document.getElementById("mode-query-btn").classList.toggle("active", mode === "query");
  document.getElementById("mode-feed-btn").classList.toggle("active", mode === "feed");
}

function setRetrieval(retrieval) {
  currentRetrieval = retrieval;
  document.getElementById("cfg-hybrid-btn").classList.toggle("active", retrieval === "hybrid");
  document.getElementById("cfg-vector-btn").classList.toggle("active", retrieval === "vector");
  document.getElementById("cfg-graph-btn").classList.toggle("active", retrieval === "graph");
}

function toggleReplay() {
  isReplay = !isReplay;
  const sw = document.getElementById("replay-switch");
  sw.classList.toggle("checked", isReplay);
}

function toggleStageDrawer(stageName) {
  const drawer = document.getElementById(`drawer-${stageName}`);
  if (!drawer) return;
  drawer.style.display = drawer.style.display === "block" ? "none" : "block";
}

function showError(msg) {
  const banner = document.getElementById("error-banner");
  banner.textContent = msg;
  banner.style.display = "block";
}

function clearError() {
  const banner = document.getElementById("error-banner");
  banner.style.display = "none";
}

function handleFormSubmit(e) {
  e.preventDefault();
  activeScenarioId = null; // Custom run
  executeRecommendation();
}

// Reset stages
function resetStages() {
  ["understanding", "retrieval", "judging", "ranking"].forEach(name => {
    const box = document.getElementById(`stage-box-${name}`);
    const badge = document.getElementById(`badge-${name}`);
    const drawer = document.getElementById(`drawer-${name}`);
    if (box) box.className = "stage-box";
    if (badge) { badge.className = "stage-status-badge idle"; badge.textContent = "Idle"; }
    if (drawer) drawer.textContent = "Waiting for stage execution...";
  });
}

function updateStage(stageName, status, data) {
  const box = document.getElementById(`stage-box-${stageName}`);
  const badge = document.getElementById(`badge-${stageName}`);
  const drawer = document.getElementById(`drawer-${stageName}`);

  if (status === "running") {
    if (box) { box.classList.remove("completed"); box.classList.add("running"); }
    if (badge) { badge.className = "stage-status-badge running"; badge.textContent = "Running"; }
  } else if (status === "completed" || status === "fallback") {
    if (box) { box.classList.remove("running"); box.classList.add(status === "fallback" ? "fallback" : "completed"); }
    if (badge) {
      if (status === "fallback") {
        badge.className = "stage-status-badge fallback-badge";
        badge.textContent = "Fallback";
      } else {
        badge.className = "stage-status-badge done";
        badge.textContent = "Done";
      }
    }
    if (drawer && data) {
      drawer.textContent = JSON.stringify(data, null, 2);
    }
  }
}

// Execute Recommendation (SSE or Replay)
async function executeRecommendation() {
  clearError();
  const query = document.getElementById("query-input").value.trim();
  const activeSc = loadedScenarios.find(s => s.id === activeScenarioId);

  // Validation
  const hasHistory = activeSc && activeSc.history && activeSc.history.length > 0;
  if (!query && !hasHistory) {
    showError("Please enter a search query or select a preset scenario with viewing history.");
    return;
  }

  resetStages();

  const btn = document.getElementById("run-btn");
  const btnText = document.getElementById("run-btn-text");
  const spinner = document.getElementById("run-spinner");
  btn.disabled = true;
  btnText.textContent = isReplay ? "Replaying..." : "Reasoning...";
  spinner.style.display = "inline";

  const payload = {
    mode: currentMode,
    query: query || (activeSc ? activeSc.query : null),
    history: activeSc ? activeSc.history : [],
    retrieval: currentRetrieval,
    replay: isReplay,
    scenario_id: activeScenarioId
  };

  try {
    const response = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      const detail = errData.detail || `Server returned HTTP ${response.status}`;
      throw new Error(detail);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // remainder

      for (const block of lines) {
        if (!block.trim()) continue;
        const eventMatch = block.match(/event:\s*([^\n]+)/);
        const dataMatch = block.match(/data:\s*([^\n]+)/);

        if (eventMatch && dataMatch) {
          const evType = eventMatch[1].trim();
          const evData = JSON.parse(dataMatch[1].trim());

          if (evType === "stage_start") {
            const stName = evData.stage === "summarising" ? "ranking" : evData.stage;
            updateStage(stName, "running");
          } else if (evType === "stage_end") {
            const stName = evData.stage === "summarising" ? "ranking" : evData.stage;
            const rec = evData.record || {};
            const isFb = rec.fallback_used || false;
            updateStage(stName, isFb ? "fallback" : "completed", rec.output);
          } else if (evType === "final") {
            renderRecommendations(evData);
          } else if (evType === "error") {
            showError(evData.error || "An error occurred during stage execution.");
          }
        }
      }
    }
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
    btnText.textContent = "Run CineMind";
    spinner.style.display = "none";
  }
}

// Render Recommendations Cards
function renderRecommendations(trace) {
  const container = document.getElementById("recommendations-container");
  const badgesBar = document.getElementById("run-badges-bar");
  container.innerHTML = "";
  badgesBar.innerHTML = "";

  // Badges
  if (trace.input && trace.input.replay) {
    badgesBar.innerHTML += `<span class="badge badge-replay">⚡ Replay (<1s)</span>`;
  }
  const anyFb = trace.stages && trace.stages.some(s => s.fallback_used);
  if (anyFb) {
    badgesBar.innerHTML += `<span class="badge badge-fallback">⚠ Fallback Used</span>`;
  }
  if (trace.metrics) {
    badgesBar.innerHTML += `<span class="badge" style="background:var(--bg-surface); border:1px solid var(--border-subtle); color:var(--text-secondary);">LLM Calls: ${trace.metrics.llm_calls || 0} | Duration: ${trace.metrics.seconds || 0}s</span>`;
  }

  if (!trace.final || trace.final.length === 0) {
    container.innerHTML = `<div style="padding:2rem; text-align:center; color:var(--text-muted);">No recommendations returned.</div>`;
    return;
  }

  trace.final.forEach(item => {
    const card = document.createElement("article");
    card.className = "rec-card";

    const posterUrl = item.poster_path ? `https://image.tmdb.org/t/p/w300${item.poster_path}` : "";
    const isCold = item.year >= 2023 || item.movie_id >= 202400;

    let tagsHtml = "";
    if (item.sources && item.sources.includes("vector")) {
      tagsHtml += `<span class="source-tag vector">Vector</span>`;
    }
    if (item.sources && item.sources.includes("graph")) {
      tagsHtml += `<span class="source-tag graph">Graph</span>`;
    }
    if (isCold) {
      tagsHtml += `<span class="source-tag cold">★ Cold-Start Release</span>`;
    }
    if (item.is_weak_match) {
      tagsHtml += `<span class="source-tag weak">Weak Match</span>`;
    }

    const fitDisplay = item.fit !== undefined && item.fit !== null ? `(Fit: ${(item.fit * 100).toFixed(0)}%)` : "";

    card.innerHTML = `
      <div class="poster-box">
        ${posterUrl ? `<img src="${posterUrl}" class="poster-img" alt="${escapeHtml(item.title)} poster" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />` : ''}
        <div class="poster-fallback" style="${posterUrl ? 'display:none;' : 'display:flex;'}">
          <div style="font-size:1.8rem; margin-bottom:0.25rem;">🎬</div>
          <div>${escapeHtml(item.title || 'Movie')}</div>
        </div>
      </div>
      <div class="rec-content">
        <div class="rec-top-meta">
          <div class="rec-title-wrap">
            <span class="rec-rank">#${item.rank}</span>
            <span class="rec-title">${escapeHtml(item.title || 'Movie ' + item.movie_id)}</span>
            ${item.year ? `<span class="rec-year">(${item.year})</span>` : ''}
            <span style="font-size:0.8rem; color:var(--accent-purple); font-family:var(--font-mono);">${fitDisplay}</span>
          </div>
          <div class="rec-tags-row">${tagsHtml}</div>
        </div>
        <p class="rec-reason">${escapeHtml(item.reason)}</p>
        ${item.path ? `<div class="rec-path-chip">⮑ Discovery Path: ${escapeHtml(item.path)}</div>` : ''}
        ${item.quote ? `
          <div class="rec-quote-box">
            <span class="quote-label">Verbatim Description Evidence:</span>
            "${escapeHtml(item.quote)}"
          </div>` : ''}
      </div>
    `;
    container.appendChild(card);
  });
}

// Comparison View
async function loadComparison() {
  const select = document.getElementById("compare-scenario-select");
  const scId = select.value || "oppenheimer_coldstart";
  const vecBox = document.getElementById("compare-vector-recs");
  const hybBox = document.getElementById("compare-hybrid-recs");

  vecBox.innerHTML = "Loading similarity-only trace...";
  hybBox.innerHTML = "Loading hybrid trace...";

  try {
    const res = await fetch(`/api/compare/${scId}`);
    if (!res.ok) throw new Error("Comparison traces not found");
    const data = await res.json();

    const vTrace = data.vector || { final: [] };
    const hTrace = data.hybrid || { final: [] };

    const vIds = new Set((vTrace.final || []).map(f => f.movie_id));
    const hIds = new Set((hTrace.final || []).map(f => f.movie_id));

    // Render Vector
    renderRecList(vecBox, vTrace.final, false, new Set());

    // Render Hybrid and highlight movies unique to hybrid!
    const hybridExclusive = new Set([...hIds].filter(x => !vIds.has(x)));
    renderRecList(hybBox, hTrace.final, true, hybridExclusive);

  } catch (err) {
    vecBox.innerHTML = `<div style="color:var(--accent-rose);">${err.message}</div>`;
    hybBox.innerHTML = `<div style="color:var(--accent-rose);">${err.message}</div>`;
  }
}

function renderRecList(targetEl, items, isHybrid, exclusiveSet) {
  targetEl.innerHTML = "";
  if (!items || items.length === 0) {
    targetEl.innerHTML = "<div style='color:var(--text-muted); padding:1rem;'>No recommendations found.</div>";
    return;
  }

  items.forEach(item => {
    const isEx = exclusiveSet.has(item.movie_id);
    const card = document.createElement("article");
    card.className = `rec-card ${isEx ? 'hybrid-unique' : ''}`;

    const posterUrl = item.poster_path ? `https://image.tmdb.org/t/p/w200${item.poster_path}` : "";

    card.innerHTML = `
      <div class="poster-box" style="width:100px; height:140px;">
        ${posterUrl ? `<img src="${posterUrl}" class="poster-img" alt="${escapeHtml(item.title)}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />` : ''}
        <div class="poster-fallback" style="${posterUrl ? 'display:none;' : 'display:flex;'}">
          <div>${escapeHtml(item.title || 'Movie')}</div>
        </div>
      </div>
      <div class="rec-content">
        ${isEx ? `<div class="hybrid-exclusive-banner">★ EXCLUSIVE TO HYBRID (Missed by Vector)</div>` : ''}
        <div class="rec-top-meta">
          <div class="rec-title-wrap">
            <span class="rec-rank">#${item.rank}</span>
            <span class="rec-title" style="font-size:1.05rem;">${escapeHtml(item.title || 'Movie')}</span>
            ${item.year ? `<span class="rec-year">(${item.year})</span>` : ''}
          </div>
        </div>
        <p class="rec-reason" style="font-size:0.85rem;">${escapeHtml(item.reason)}</p>
        ${item.path ? `<div class="rec-path-chip" style="font-size:0.72rem;">⮑ ${escapeHtml(item.path)}</div>` : ''}
      </div>
    `;
    targetEl.appendChild(card);
  });
}

// Evaluation Results Tab
async function initResults() {
  const tbody = document.getElementById("results-tbody");
  const chartBox = document.getElementById("metrics-svg-chart");
  const errBox = document.getElementById("error-analysis-container");

  try {
    const res = await fetch("/api/results");
    if (!res.ok) throw new Error("Could not load evaluation results");
    const data = await res.json();
    const metrics = data.metrics || {};

    tbody.innerHTML = "";
    const cfgDisplay = [
      { key: "vector", label: "Similarity-Only (ARAG Baseline)" },
      { key: "hybrid", label: "Hybrid (CineMind Graph + Vector)" },
      { key: "graph", label: "Graph-Only" }
    ];

    cfgDisplay.forEach(item => {
      const m = metrics[item.key] || {};
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-weight:600; color:${item.key === 'hybrid' ? 'var(--accent-purple)' : 'var(--text-primary)'};">${item.label}</td>
        <td>${m.hit_rate_at_5 !== undefined ? (m.hit_rate_at_5 * 100).toFixed(1) + '%' : '-'}</td>
        <td>${m.hit_rate_at_10 !== undefined ? (m.hit_rate_at_10 * 100).toFixed(1) + '%' : '-'}</td>
        <td>${m.ndcg_at_5 !== undefined ? m.ndcg_at_5.toFixed(4) : '-'}</td>
        <td>${m.ndcg_at_10 !== undefined ? m.ndcg_at_10.toFixed(4) : '-'}</td>
        <td style="font-weight:700; color:var(--accent-cyan);">${m.recall_at_50 !== undefined ? (m.recall_at_50 * 100).toFixed(1) + '%' : '-'}</td>
        <td>${m.avg_llm_calls || '-'}</td>
        <td>${m.avg_seconds !== undefined ? m.avg_seconds + 's' : '-'}</td>
      `;
      tbody.appendChild(tr);
    });

    // Draw SVG Chart
    drawMetricsChart(chartBox, metrics);

    // Error analysis
    errBox.innerHTML = "";
    (data.error_analysis || []).forEach((c, idx) => {
      const card = document.createElement("article");
      card.className = "rec-card";
      card.style.gridTemplateColumns = "1fr";
      card.innerHTML = `
        <div class="rec-content">
          <div style="font-weight:700; font-size:1rem; margin-bottom:0.35rem; color:var(--text-primary);">
            Case #${idx + 1} — Test Viewer #${c.user_id}
          </div>
          <div style="font-size:0.85rem; color:var(--accent-amber); margin-bottom:0.5rem;">
            Target Cold-Start Item: <strong>${escapeHtml(c.ground_truth)}</strong>
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem; font-size:0.82rem; background:var(--bg-canvas); padding:0.75rem; border-radius:var(--radius-sm);">
            <div>
              <span style="color:var(--accent-cyan); font-weight:600;">Similarity-Only (Hit: ${c.vector_hit ? 'YES' : 'NO'}):</span>
              <div style="color:var(--text-secondary); margin-top:0.2rem;">${escapeHtml(c.vector_recommendations.join(', '))}</div>
            </div>
            <div>
              <span style="color:var(--accent-purple); font-weight:600;">Hybrid Discovery (Hit: ${c.hybrid_hit ? 'YES' : 'NO'}):</span>
              <div style="color:var(--text-secondary); margin-top:0.2rem;">${escapeHtml(c.hybrid_recommendations.join(', '))}</div>
            </div>
          </div>
        </div>
      `;
      errBox.appendChild(card);
    });

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" style="color:var(--accent-rose);">${err.message}</td></tr>`;
  }
}

// Crisp SVG Bar Chart
function drawMetricsChart(container, metrics) {
  const v = metrics.vector || {};
  const h = metrics.hybrid || {};
  const g = metrics.graph || {};

  const svg = `
    <svg width="100%" height="240" viewBox="0 0 600 240" xmlns="http://www.w3.org/2000/svg">
      <!-- Axis lines -->
      <line x1="50" y1="20" x2="50" y2="200" stroke="#242c3d" stroke-width="1.5" />
      <line x1="50" y1="200" x2="570" y2="200" stroke="#242c3d" stroke-width="1.5" />
      
      <!-- Grid ticks -->
      <text x="40" y="25" fill="#64748b" font-size="10" text-anchor="end">1.0</text>
      <text x="40" y="115" fill="#64748b" font-size="10" text-anchor="end">0.5</text>
      <text x="40" y="200" fill="#64748b" font-size="10" text-anchor="end">0.0</text>

      <!-- Metric 1: HitRate@5 -->
      <text x="140" y="222" fill="#94a3b8" font-size="12" text-anchor="middle" font-weight="600">HitRate@5</text>
      <!-- Bars -->
      <rect x="80" y="${200 - (v.hit_rate_at_5||0.76)*180}" width="34" height="${(v.hit_rate_at_5||0.76)*180}" fill="#06b6d4" rx="3" />
      <rect x="122" y="${200 - (h.hit_rate_at_5||0.74)*180}" width="34" height="${(h.hit_rate_at_5||0.74)*180}" fill="#8b5cf6" rx="3" />
      <rect x="164" y="${200 - (g.hit_rate_at_5||0.80)*180}" width="34" height="${(g.hit_rate_at_5||0.80)*180}" fill="#10b981" rx="3" />

      <!-- Metric 2: NDCG@5 -->
      <text x="310" y="222" fill="#94a3b8" font-size="12" text-anchor="middle" font-weight="600">NDCG@5</text>
      <rect x="250" y="${200 - (v.ndcg_at_5||0.39)*180}" width="34" height="${(v.ndcg_at_5||0.39)*180}" fill="#06b6d4" rx="3" />
      <rect x="292" y="${200 - (h.ndcg_at_5||0.39)*180}" width="34" height="${(h.ndcg_at_5||0.39)*180}" fill="#8b5cf6" rx="3" />
      <rect x="334" y="${200 - (g.ndcg_at_5||0.42)*180}" width="34" height="${(g.ndcg_at_5||0.42)*180}" fill="#10b981" rx="3" />

      <!-- Metric 3: Recall@50 -->
      <text x="480" y="222" fill="#94a3b8" font-size="12" text-anchor="middle" font-weight="600">Recall@50</text>
      <rect x="420" y="${200 - (v.recall_at_50||1.0)*180}" width="34" height="${(v.recall_at_50||1.0)*180}" fill="#06b6d4" rx="3" />
      <rect x="462" y="${200 - (h.recall_at_50||1.0)*180}" width="34" height="${(h.recall_at_50||1.0)*180}" fill="#8b5cf6" rx="3" />
      <rect x="504" y="${200 - (g.recall_at_50||1.0)*180}" width="34" height="${(g.recall_at_50||1.0)*180}" fill="#10b981" rx="3" />

      <!-- Legend -->
      <rect x="340" y="15" width="12" height="12" fill="#06b6d4" rx="2" />
      <text x="358" y="25" fill="#cbd5e1" font-size="10">Similarity-Only</text>
      <rect x="430" y="15" width="12" height="12" fill="#8b5cf6" rx="2" />
      <text x="448" y="25" fill="#cbd5e1" font-size="10">Hybrid</text>
      <rect x="500" y="15" width="12" height="12" fill="#10b981" rx="2" />
      <text x="518" y="25" fill="#cbd5e1" font-size="10">Graph-Only</text>
    </svg>
  `;
  container.innerHTML = svg;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
