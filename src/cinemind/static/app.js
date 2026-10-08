/**
 * CineMind Interactive Studio & Benchmark Frontend Controller
 * Professional Editorial Film Intelligence System
 */

let activeScenarioId = "oppenheimer_coldstart";
let currentMode = "feed";
let currentRetrieval = "hybrid";
let isReplay = true;
let allowFallback = false; // Default: Strict Errors (No Fallback)
let loadedScenarios = [];
let currentTrace = null;

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  init();
});

async function init() {
  await checkHealth();
  await loadScenarios();
  await loadEvaluationResults();

  // Auto-run the featured scenario so the user is immediately greeted by rich movie cards
  if (loadedScenarios.length > 0) {
    selectScenario(activeScenarioId || loadedScenarios[0].id);
  }

  // When user types a custom search
  const queryInput = document.getElementById("query-input");
  if (queryInput) {
    queryInput.addEventListener("input", (e) => {
      const val = e.target.value.trim().toLowerCase();
      const matchedSc = loadedScenarios.find(s => s.query && s.query.toLowerCase().includes(val));
      if (matchedSc) {
        activeScenarioId = matchedSc.id;
        document.querySelectorAll(".scenario-tile").forEach(t => t.classList.toggle("active", t.id === `scenario-tile-${matchedSc.id}`));
      } else {
        activeScenarioId = null;
        document.querySelectorAll(".scenario-tile").forEach(t => t.classList.remove("active"));
      }
    });
  }
}

// Health Check
async function checkHealth() {
  const pill = document.getElementById("health-pill");
  const text = document.getElementById("health-status-text");
  const dot = pill ? pill.querySelector(".status-dot") : null;
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health endpoint error");
    const data = await res.json();
    if (text) {
      text.textContent = `${data.model_name || 'qwen3:8b'} · ${(data.catalog_size || 0).toLocaleString()} films`;
    }
    if (dot) {
      dot.className = "status-dot online";
    }
    if (pill) {
      pill.title = `Model: ${data.model_name} | Catalog: ${data.catalog_size} movies | Graph: Ready`;
    }
  } catch (err) {
    if (text) text.textContent = "Server offline (Replay ready)";
    if (dot) dot.className = "status-dot offline";
  }
}

// Load Presets
async function loadScenarios() {
  const container = document.getElementById("scenarios-container");
  const select = document.getElementById("compare-scenario-select");
  try {
    const res = await fetch("/api/scenarios");
    if (!res.ok) throw new Error("Could not load scenarios");
    loadedScenarios = await res.json();

    if (container) container.innerHTML = "";
    if (select) select.innerHTML = "";

    loadedScenarios.forEach((sc) => {
      // Tile for Studio
      if (container) {
        const tile = document.createElement("div");
        tile.className = `scenario-tile ${sc.id === activeScenarioId ? "active" : ""}`;
        tile.id = `scenario-tile-${sc.id}`;
        tile.onclick = () => selectScenario(sc.id);

        const tagClass = sc.cold_start ? "cold" : sc.mode;
        const tagLabel = sc.cold_start ? "COLD-START" : (sc.mode === "query" ? "QUERY" : "FEED");

        tile.innerHTML = `
          <div class="tile-badge-row">
            <span class="tile-tag ${tagClass}">${tagLabel}</span>
          </div>
          <div class="tile-title">${escapeHtml(sc.title)}</div>
          <div class="tile-desc">${escapeHtml(sc.blurb)}</div>
        `;
        container.appendChild(tile);
      }

      // Select option for Comparison View
      if (select) {
        const opt = document.createElement("option");
        opt.value = sc.id;
        opt.textContent = `${sc.title} (${sc.mode.toUpperCase()}${sc.cold_start ? ' - Cold Start' : ''})`;
        select.appendChild(opt);
      }
    });

    if (loadedScenarios.length > 0 && !activeScenarioId) {
      activeScenarioId = loadedScenarios[0].id;
    }
  } catch (err) {
    if (container) {
      container.innerHTML = `<div style="color:var(--text-muted); padding:1rem;">Could not load scenario presets.</div>`;
    }
  }
}

function selectScenario(id) {
  activeScenarioId = id;
  isReplay = true;
  const track = document.getElementById("replay-switch");
  if (track) track.classList.add("active");

  const sc = loadedScenarios.find(s => s.id === id);
  if (!sc) return;

  // Update UI tile states
  document.querySelectorAll(".scenario-tile").forEach(t => t.classList.remove("active"));
  const activeTile = document.getElementById(`scenario-tile-${id}`);
  if (activeTile) activeTile.classList.add("active");

  // Populate inputs
  const input = document.getElementById("query-input");
  if (input) {
    if (sc.mode === "query") {
      input.value = sc.query || "";
      input.placeholder = "Enter query...";
    } else {
      const movieTitles = (sc.history || []).map(h => h.title).join(", ");
      input.value = "";
      input.placeholder = `Viewing history: ${movieTitles}`;
    }
  }

  setMode(sc.mode);
  executeRecommendation();
}

// Mode Selection
function setMode(mode) {
  currentMode = mode;
  const qBtn = document.getElementById("mode-query-btn");
  const fBtn = document.getElementById("mode-feed-btn");
  if (qBtn) qBtn.classList.toggle("active", mode === "query");
  if (fBtn) fBtn.classList.toggle("active", mode === "feed");
}

// Retrieval Configuration Selection
function setRetrieval(config) {
  currentRetrieval = config;
  const hBtn = document.getElementById("cfg-hybrid-btn");
  const vBtn = document.getElementById("cfg-vector-btn");
  const gBtn = document.getElementById("cfg-graph-btn");
  if (hBtn) hBtn.classList.toggle("active", config === "hybrid");
  if (vBtn) vBtn.classList.toggle("active", config === "vector");
  if (gBtn) gBtn.classList.toggle("active", config === "graph");
}

// Toggle Replay Switch
function toggleReplay() {
  if (!activeScenarioId && !isReplay) {
    if (loadedScenarios.length > 0) {
      selectScenario(loadedScenarios[0].id);
      return;
    }
  }
  isReplay = !isReplay;
  const track = document.getElementById("replay-switch");
  if (track) track.classList.toggle("active", isReplay);
}

// Fallback Policy Toggle (Default: Strict Errors / No Fallbacks)
function toggleFallbackMode() {
  allowFallback = !allowFallback;
  const track = document.getElementById("fallback-switch");
  const label = document.getElementById("fallback-toggle-label");
  if (track) track.classList.toggle("active", allowFallback);
  if (label) {
    label.textContent = allowFallback ? "Fallbacks Enabled" : "Strict Errors (No Fallback)";
  }
}

// Navigation Tabs
function switchTab(tabName) {
  ["demo", "compare", "results"].forEach(t => {
    const view = document.getElementById(`view-${t}`);
    const tabBtn = document.getElementById(`tab-${t}`);
    if (view) view.style.display = t === tabName ? "flex" : "none";
    if (tabBtn) tabBtn.classList.toggle("active", t === tabName);
  });

  if (tabName === "compare") {
    loadComparison();
  }
}

// Drawers for inspecting raw pipeline output
function toggleStageDrawer(stageName) {
  const drawer = document.getElementById(`drawer-${stageName}`);
  if (!drawer) return;
  const isOpen = drawer.style.display === "block";
  drawer.style.display = isOpen ? "none" : "block";
}

function showError(msg) {
  const banner = document.getElementById("error-banner");
  if (!banner) return;
  banner.textContent = msg;
  banner.style.display = "flex";
}

function clearError() {
  const banner = document.getElementById("error-banner");
  if (banner) banner.style.display = "none";
}

function handleFormSubmit(e) {
  e.preventDefault();
  activeScenarioId = null; // Free-form custom run
  isReplay = false;
  const track = document.getElementById("replay-switch");
  if (track) track.classList.remove("active");
  document.querySelectorAll(".scenario-tile").forEach(t => t.classList.remove("active"));
  executeRecommendation();
}

function resetStages() {
  ["understanding", "retrieval", "judging", "summarising", "ranking"].forEach(name => {
    const box = document.getElementById(`stage-box-${name}`);
    const badge = document.getElementById(`badge-${name}`);
    const drawer = document.getElementById(`drawer-${name}`);
    if (box) box.className = "step-card";
    if (badge) { badge.className = "step-badge idle"; badge.textContent = "Idle"; }
    if (drawer) {
      drawer.textContent = "Waiting for stage execution...";
      drawer.style.display = "none";
    }
  });
  const label = document.getElementById("pipeline-status-label");
  if (label) label.textContent = "Processing...";
}

function updateStage(stageName, status, data) {
  const box = document.getElementById(`stage-box-${stageName}`);
  const badge = document.getElementById(`badge-${stageName}`);
  const drawer = document.getElementById(`drawer-${stageName}`);

  if (status === "running") {
    if (box) { box.classList.remove("completed", "fallback", "failed"); box.classList.add("running"); }
    if (badge) { badge.className = "step-badge running"; badge.textContent = "Running"; }
  } else if (status === "failed") {
    if (box) { box.classList.remove("running", "completed", "fallback"); box.classList.add("failed"); }
    if (badge) {
      badge.className = "step-badge failed";
      badge.textContent = "Failed";
    }
    if (drawer && data) {
      drawer.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
      drawer.style.display = "block";
    }
  } else if (status === "completed" || status === "fallback") {
    if (box) { box.classList.remove("running", "failed"); box.classList.add(status === "fallback" ? "fallback" : "completed"); }
    if (badge) {
      if (status === "fallback") {
        badge.className = "step-badge fallback";
        badge.textContent = "Fallback";
      } else {
        badge.className = "step-badge done";
        badge.textContent = "Done";
      }
    }
    if (drawer && data) {
      drawer.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
    }
  }
}

// Execute Recommendation
async function executeRecommendation() {
  clearError();
  const inputEl = document.getElementById("query-input");
  const query = inputEl ? inputEl.value.trim() : "";
  const activeSc = loadedScenarios.find(s => s.id === activeScenarioId);

  // Validation
  const hasHistory = activeSc && activeSc.history && activeSc.history.length > 0;
  if (!query && !hasHistory) {
    showError("Please enter a search query or select a preset scenario.");
    return;
  }

  const effectiveReplay = Boolean(activeScenarioId && isReplay);
  resetStages();

  const btn = document.getElementById("run-btn");
  const btnText = document.getElementById("run-btn-text");
  const spinner = document.getElementById("run-spinner");
  if (btn) btn.disabled = true;
  if (btnText) btnText.textContent = effectiveReplay ? "Retrieving..." : "Reasoning...";
  if (spinner) spinner.style.display = "inline-block";

  const payload = {
    mode: currentMode,
    query: query || (activeSc ? activeSc.query : null),
    history: activeSc ? activeSc.history : [],
    retrieval: currentRetrieval,
    replay: effectiveReplay,
    scenario_id: effectiveReplay ? activeScenarioId : null,
    allow_fallback: allowFallback
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
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";

      for (const evText of events) {
        if (!evText.trim()) continue;
        const lines = evText.split("\n");
        let eventType = "message";
        let dataStr = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.substring(7).trim();
          } else if (line.startsWith("data: ")) {
            dataStr = line.substring(6).trim();
          }
        }

        if (dataStr) {
          try {
            const data = JSON.parse(dataStr);
            handlePipelineEvent(eventType, data);
          } catch (e) {
            console.error("Failed to parse event JSON", e);
          }
        }
      }
    }
  } catch (err) {
    showError(err.message || "Failed to generate recommendations");
  } finally {
    if (btn) btn.disabled = false;
    if (btnText) btnText.textContent = "Discover";
    if (spinner) spinner.style.display = "none";
    const label = document.getElementById("pipeline-status-label");
    if (label) label.textContent = "Completed";
  }
}

function handlePipelineEvent(eventType, data) {
  if (eventType === "stage_start") {
    updateStage(data.stage, "running");
  } else if (eventType === "stage_end") {
    const isFailed = data.record && (data.record.status === "failed" || Boolean(data.record.error));
    const isFb = data.record && data.record.fallback_used;
    if (isFailed) {
      updateStage(data.stage, "failed", data.record.error || "Stage execution failed");
      showError(`Stage '${data.stage}' failed: ${data.record.error || "Unknown error"}`);
    } else {
      updateStage(data.stage, isFb ? "fallback" : "completed", data.record ? data.record.output : data);
    }
  } else if (eventType === "error") {
    showError(data.message || data.error || "Pipeline execution failed");
  } else if (eventType === "final") {
    currentTrace = data;
    renderRecommendations(data);
  }
}

// Render Movie Recommendation Cards
function renderRecommendations(trace) {
  const container = document.getElementById("recommendations-container");
  const badgesBar = document.getElementById("run-badges-bar");
  if (!container || !badgesBar) return;

  container.innerHTML = "";
  badgesBar.innerHTML = "";

  // Header badges
  if (trace.input && trace.input.replay) {
    badgesBar.innerHTML += `<span class="badge-pill replay">REPLAY TRACE</span>`;
  }
  const anyFb = trace.stages && trace.stages.some(s => s.fallback_used);
  if (anyFb) {
    badgesBar.innerHTML += `<span class="badge-pill fallback">FALLBACK</span>`;
  }
  if (trace.metrics) {
    badgesBar.innerHTML += `<span class="badge-pill">${trace.metrics.llm_calls || 0} Model Calls</span>`;
    badgesBar.innerHTML += `<span class="badge-pill">${(trace.metrics.seconds || 0).toFixed(2)}s</span>`;
  }

  if (!trace.final || trace.final.length === 0) {
    container.innerHTML = `<div style="padding:2.5rem; text-align:center; color:var(--text-muted); background:var(--bg-card); border-radius:var(--radius-md); border:1px solid var(--border-subtle);">No recommendations found. Try another query.</div>`;
    return;
  }

  trace.final.forEach((item, idx) => {
    const card = document.createElement("article");
    const isCold = (item.year && item.year >= 2022) || (item.movie_id >= 202000);
    const isHybridEx = item.sources && item.sources.includes("graph") && !item.sources.includes("vector");

    card.className = `movie-rec-card ${isHybridEx ? 'hybrid-exclusive' : ''}`;

    const posterUrl = item.poster_path ? `https://image.tmdb.org/t/p/w500${item.poster_path}` : "";

    let tagsHtml = "";
    if (isHybridEx) {
      tagsHtml += `<span class="tag-badge hybrid-ex">HYBRID EXCLUSIVE</span>`;
    }
    if (item.sources && item.sources.includes("graph")) {
      tagsHtml += `<span class="tag-badge graph">GRAPH</span>`;
    }
    if (item.sources && item.sources.includes("vector")) {
      tagsHtml += `<span class="tag-badge vector">VECTOR</span>`;
    }
    if (isCold) {
      tagsHtml += `<span class="tag-badge cold">COLD-START</span>`;
    }

    const fitVal = item.fit !== undefined && item.fit !== null ? Math.round(item.fit * 100) : 95;

    card.innerHTML = `
      <div class="poster-wrapper">
        ${posterUrl ? `<img src="${posterUrl}" class="poster-image" alt="${escapeHtml(item.title)} poster" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />` : ''}
        <div class="poster-placeholder" style="${posterUrl ? 'display:none;' : 'display:flex;'}">
          <div class="poster-slate-title">${escapeHtml(item.title || 'Film')}</div>
          ${item.year ? `<div class="poster-slate-year">${item.year}</div>` : ''}
        </div>
      </div>
      <div class="rec-details">
        <div class="card-title-row">
          <div class="title-rank-cluster">
            <span class="rank-laurel">#${item.rank || (idx + 1)}</span>
            <h4 class="movie-title-text">${escapeHtml(item.title || 'Movie ' + item.movie_id)}</h4>
            ${item.year ? `<span class="movie-year-tag">(${item.year})</span>` : ''}
          </div>
          <div class="fit-meter">
            <span>Match</span>
            <strong style="color:var(--text-primary);">${fitVal}%</strong>
          </div>
        </div>

        <div class="card-tags-cluster">${tagsHtml}</div>

        <p class="personalized-reason">${escapeHtml(item.reason || '')}</p>

        ${item.path ? `
          <div class="discovery-path-chip">
            <span>Path: <strong>${escapeHtml(item.path)}</strong></span>
          </div>` : ''}

        ${item.quote ? `
          <div class="quote-evidence-card">
            <span class="quote-label-badge">VERBATIM OVERVIEW EVIDENCE</span>
            "${escapeHtml(item.quote)}"
          </div>` : ''}
      </div>
    `;
    container.appendChild(card);
  });
}

// Comparison View Matrix
async function loadComparison() {
  const select = document.getElementById("compare-scenario-select");
  const scId = (select && select.value) ? select.value : "oppenheimer_coldstart";
  const vecBox = document.getElementById("compare-vector-recs");
  const hybBox = document.getElementById("compare-hybrid-recs");

  if (vecBox) vecBox.innerHTML = "<div style='color:var(--text-muted); padding:1rem;'>Loading similarity baseline...</div>";
  if (hybBox) hybBox.innerHTML = "<div style='color:var(--text-muted); padding:1rem;'>Loading hybrid graph discovery...</div>";

  try {
    const res = await fetch(`/api/compare/${scId}`);
    if (!res.ok) throw new Error("Comparison traces not found");
    const data = await res.json();

    const vTrace = data.vector || { final: [] };
    const hTrace = data.hybrid || { final: [] };

    const vIds = new Set((vTrace.final || []).map(f => f.movie_id));
    const hIds = new Set((hTrace.final || []).map(f => f.movie_id));

    // Render Vector list
    if (vecBox) renderMiniRecList(vecBox, vTrace.final, false, new Set());

    // Render Hybrid list (highlighting movies unique to hybrid)
    const hybridExclusiveIds = new Set([...hIds].filter(id => !vIds.has(id)));
    if (hybBox) renderMiniRecList(hybBox, hTrace.final, true, hybridExclusiveIds);
  } catch (err) {
    if (vecBox) vecBox.innerHTML = `<div style="color:var(--text-muted); padding:1rem;">Failed to load comparison.</div>`;
    if (hybBox) hybBox.innerHTML = `<div style="color:var(--text-muted); padding:1rem;">Failed to load comparison.</div>`;
  }
}

function renderMiniRecList(container, items, isHybrid, exclusiveIds) {
  container.innerHTML = "";
  if (!items || items.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted); padding:1rem;">No items recorded.</div>`;
    return;
  }

  items.forEach(item => {
    const card = document.createElement("div");
    const isExclusive = exclusiveIds.has(item.movie_id);
    card.className = `movie-rec-card ${isExclusive ? 'hybrid-exclusive' : ''}`;
    card.style.padding = "0.9rem";
    card.style.gap = "1rem";

    const posterUrl = item.poster_path ? `https://image.tmdb.org/t/p/w200${item.poster_path}` : "";

    card.innerHTML = `
      <div class="poster-wrapper" style="width:75px; height:110px;">
        ${posterUrl ? `<img src="${posterUrl}" class="poster-image" alt="${escapeHtml(item.title)}" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />` : ''}
        <div class="poster-placeholder" style="${posterUrl ? 'display:none;' : 'display:flex;'} font-size:0.65rem;">
          <div class="poster-slate-title">${escapeHtml(item.title || 'Film')}</div>
        </div>
      </div>
      <div class="rec-details">
        <div class="card-title-row" style="margin-bottom:0.25rem;">
          <div class="title-rank-cluster" style="gap:0.4rem;">
            <span class="rank-laurel">#${item.rank}</span>
            <span style="font-size:0.95rem; font-weight:700; color:var(--text-primary);">${escapeHtml(item.title)}</span>
            <span style="font-size:0.75rem; color:var(--text-muted); font-family:var(--font-mono);">(${item.year || ''})</span>
          </div>
          ${isExclusive ? `<span class="tag-badge hybrid-ex">HYBRID EXCLUSIVE</span>` : ''}
        </div>
        <p style="font-size:0.8rem; color:var(--text-secondary); line-height:1.4; margin-bottom:0.35rem;">${escapeHtml(item.reason || '')}</p>
        ${item.path ? `
          <div class="discovery-path-chip" style="font-size:0.68rem; padding:0.2rem 0.5rem;">
            ${escapeHtml(item.path)}
          </div>` : ''}
      </div>
    `;
    container.appendChild(card);
  });
}

// Load Evaluation Results
async function loadEvaluationResults() {
  const tbody = document.getElementById("eval-table-body") || document.getElementById("results-tbody");
  const errBox = document.getElementById("error-analysis-container");
  if (!tbody) return;

  try {
    const res = await fetch("/api/results");
    if (!res.ok) throw new Error("Results endpoint error");
    const data = await res.json();

    const metrics = data.metrics || {};
    tbody.innerHTML = "";

    const rows = [
      { key: "vector", label: "Similarity-Only (ARAG Baseline)" },
      { key: "graph", label: "Graph-Only (PPR)" },
      { key: "hybrid", label: "Hybrid (CineMind Knowledge Graph)", highlight: true }
    ];

    rows.forEach(r => {
      const m = metrics[r.key] || {};
      const tr = document.createElement("tr");
      if (r.highlight) {
        tr.style.background = "var(--bg-subtle)";
        tr.style.fontWeight = "600";
      }
      tr.innerHTML = `
        <td style="${r.highlight ? 'color:#fff; font-weight:700;' : ''}">${r.label}</td>
        <td>${(m.hit_rate_at_5 || 0).toFixed(4)}</td>
        <td>${(m.hit_rate_at_10 || 0).toFixed(4)}</td>
        <td>${(m.ndcg_at_5 || 0).toFixed(4)}</td>
        <td>${(m.ndcg_at_10 || 0).toFixed(4)}</td>
        <td>${(m.avg_seconds || 0).toFixed(2)}s</td>
        <td>${(m.avg_llm_calls || 0).toFixed(1)}</td>
      `;
      tbody.appendChild(tr);
    });

    // Error analysis exemplar cards
    if (errBox && data.error_analysis && data.error_analysis.length > 0) {
      errBox.innerHTML = "";
      data.error_analysis.slice(0, 5).forEach(c => {
        const itemCard = document.createElement("div");
        itemCard.className = "movie-rec-card";
        itemCard.style.padding = "1rem";
        itemCard.innerHTML = `
          <div class="rec-details">
            <div class="card-title-row">
              <span style="font-family:var(--font-mono); font-size:0.8rem; font-weight:700; color:var(--text-primary);">Test Viewer #${c.user_id}</span>
              <span class="tag-badge cold">Target: ${escapeHtml(c.ground_truth)}</span>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; margin-top:0.4rem; font-size:0.8rem;">
              <div style="background:var(--bg-canvas); padding:0.65rem; border-radius:var(--radius-xs); border:1px solid var(--border-subtle);">
                <div style="color:var(--text-muted); font-size:0.7rem; font-family:var(--font-mono); font-weight:600; margin-bottom:0.25rem;">SIMILARITY-ONLY TOP PICKS:</div>
                <div style="color:var(--text-secondary);">${(c.vector_recommendations || []).join(", ")}</div>
              </div>
              <div style="background:var(--bg-canvas); padding:0.65rem; border-radius:var(--radius-xs); border:1px solid rgba(16,185,129,0.3);">
                <div style="color:var(--accent-emerald); font-size:0.7rem; font-family:var(--font-mono); font-weight:600; margin-bottom:0.25rem;">HYBRID TOP PICKS:</div>
                <div style="color:var(--text-secondary);">${(c.hybrid_recommendations || []).join(", ")}</div>
              </div>
            </div>
          </div>
        `;
        errBox.appendChild(itemCard);
      });
    }
  } catch (err) {
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:2rem;">Benchmark metrics unavailable.</td></tr>`;
    }
  }
}

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Sage Garden Theme Toggle Function
function toggleTheme() {
  const isDark = document.documentElement.classList.toggle("dark");
  localStorage.setItem("cinemind-theme", isDark ? "dark" : "light");
}
