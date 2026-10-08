/* CineMind frontend — vanilla JS, no build step. */
"use strict";

const STAGES = ["understanding", "retrieval", "judging", "summarising", "ranking"];
const STAGE_TITLES = {
  understanding: "1 · Understand you",
  retrieval: "2 · Find candidates",
  judging: "3 · Judge each one",
  summarising: "4 · Summarise",
  ranking: "5 · Pick top 5",
};
const RETRIEVAL_LABEL = { vector: "Text similarity only", graph: "Movie graph only", hybrid: "Both (ours)" };

const state = { scenarios: [], selected: null, running: false, stageOutputs: {}, health: null };

const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const radio = (name) => document.querySelector(`input[name="${name}"]:checked`).value;
const fmt = (x, d = 3) => (typeof x === "number" ? x.toFixed(d) : "—");
const pct = (x) => (typeof x === "number" ? `${(x * 100).toFixed(1)}%` : "—");

/* ---------------- Tabs ---------------- */
function switchTab(name) {
  document.querySelectorAll(".tab").forEach((t) => {
    const on = t.dataset.tab === name;
    t.classList.toggle("active", on);
    t.setAttribute("aria-selected", on ? "true" : "false");
  });
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${name}`));
  if (name === "compare") loadComparison();
  if (name === "results") loadResults();
}

/* ---------------- Health ---------------- */
async function checkHealth() {
  const dot = $("status-dot"), text = $("status-text"), box = $("status");
  try {
    const h = await (await fetch("/api/health")).json();
    state.health = h;
    if (!h.catalog_size) {
      dot.className = "dot bad";
      text.textContent = "Data not built (run make data)";
    } else if (h.model_ready) {
      dot.className = "dot ok";
      text.textContent = `AI ready · ${h.model_name} · ${h.catalog_size.toLocaleString()} movies`;
    } else {
      dot.className = "dot warn";
      text.textContent = `AI offline (saved runs work) · ${h.catalog_size.toLocaleString()} movies`;
    }
    box.title = `Model ${h.model_name}: ${h.model_ready ? "ready" : "not reachable"} · Graph: ${h.graph_ready ? "built" : "not built"}`;
  } catch {
    dot.className = "dot bad";
    text.textContent = "Server not reachable";
  }
}

/* ---------------- Examples ---------------- */
function scenarioTags(sc) {
  const tags = [];
  if (sc.query) tags.push(`<span class="tag query">Typed request</span>`);
  if (sc.user_id) tags.push(`<span class="tag viewer">Real viewer #${esc(sc.user_id)}</span>`);
  else if ((sc.history || []).length) tags.push(`<span class="tag viewer">Viewing history</span>`);
  if (sc.cold_start) tags.push(`<span class="tag new">New-movie test</span>`);
  return tags.join("");
}

async function loadScenarios() {
  const box = $("scenarios-container");
  try {
    state.scenarios = await (await fetch("/api/scenarios")).json();
  } catch {
    box.innerHTML = `<div class="empty">Could not load examples.</div>`;
    return;
  }
  box.innerHTML = "";
  state.scenarios.forEach((sc) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "example";
    b.dataset.id = sc.id;
    b.innerHTML = `<span class="tags">${scenarioTags(sc)}</span>
      <span class="example-title">${esc(sc.title)}</span>
      <span class="example-desc">${esc(sc.blurb)}</span>`;
    b.addEventListener("click", () => { selectScenario(sc); executeRecommendation(); });
    box.appendChild(b);
  });
  const sel = $("compare-select");
  sel.innerHTML = state.scenarios.map((sc) => `<option value="${esc(sc.id)}">${esc(sc.title)}</option>`).join("");
}

function selectScenario(sc) {
  state.selected = sc;
  document.querySelectorAll(".example").forEach((e) => e.classList.toggle("selected", e.dataset.id === sc?.id));
  $("query").value = sc?.query || "";
  const vb = $("viewer-box");
  const hist = sc?.history || [];
  if (!sc || !hist.length) { vb.hidden = true; return; }
  const loved = [...hist].filter((h) => h.rating >= 4).sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0)).slice(0, 6);
  let html = `<b>${sc.user_id ? `Real MovieLens viewer #${esc(sc.user_id)}` : "Viewing history"}</b> · ${hist.length} ratings used`;
  if (loved.length) html += `<br>Recently loved: ${loved.map((h) => `${esc(h.title)} (${h.rating}★)`).join(", ")}`;
  if ((sc.ground_truth || []).length) {
    html += `<br>After the cut-off this viewer rated 4★+: <b>${sc.ground_truth.map((g) => esc(g.title)).join(", ")}</b> (zero ratings before, so a "new movie").`;
  }
  vb.innerHTML = html;
  vb.hidden = false;
}

/* ---------------- Run ---------------- */
function showError(msg) {
  const e = $("error");
  e.textContent = msg;
  e.hidden = !msg;
}

function resetSteps() {
  state.stageOutputs = {};
  document.querySelectorAll("#steps li").forEach((li) => {
    li.className = "";
    li.querySelector(".state").textContent = "waiting";
  });
  $("stage-details").hidden = true;
  $("stage-details-body").innerHTML = "";
  $("run-info").hidden = true;
  $("recs").innerHTML = "";
}

function setStep(stage, cls, text) {
  const li = document.querySelector(`#steps li[data-stage="${stage}"]`);
  if (!li) return;
  li.className = cls;
  li.querySelector(".state").textContent = text;
}

function stageSummary(stage, out) {
  if (!out) return "done";
  if (stage === "understanding") return `${(out.likes || []).length} likes · ${(out.constraints || []).length} rules`;
  if (stage === "retrieval") return `${out.candidate_count ?? (out.candidates || []).length} candidates`;
  if (stage === "judging") {
    const v = out.verdicts || [];
    return `${v.filter((x) => x.match).length} of ${v.length} match`;
  }
  if (stage === "summarising") return `${(out.strong || []).length} standouts`;
  if (stage === "ranking") return `${(out.rankings || []).length} picked`;
  return "done";
}

async function executeRecommendation() {
  if (state.running) return;
  showError("");
  const query = $("query").value.trim();
  const sc = state.selected && (state.selected.query || "") === query ? state.selected : null;
  if (!sc && state.selected && query !== (state.selected.query || "")) selectScenario(null);
  const replay = radio("runmode") === "replay";
  const history = sc?.history || [];

  if (!query && !history.length) { showError("Type a request or pick an example."); return; }
  if (replay && !sc) { showError("Saved runs exist only for the examples. Pick an example, or choose “Live AI”."); return; }

  const payload = {
    mode: sc ? sc.mode : "query",
    query: query || null,
    history: history.length ? history : null,
    retrieval: radio("retrieval"),
    replay,
    scenario_id: sc ? sc.id : null,
  };

  resetSteps();
  state.running = true;
  const btn = $("run-btn");
  btn.disabled = true;
  btn.textContent = replay ? "Loading…" : "Thinking…";
  try {
    const res = await fetch("/api/recommend", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${res.status}`);
    }
    await readEvents(res, replay);
  } catch (e) {
    showError(e.message || String(e));
    document.querySelectorAll("#steps li.running").forEach((li) => { li.className = "failed"; li.querySelector(".state").textContent = "failed"; });
  } finally {
    state.running = false;
    btn.disabled = false;
    btn.textContent = "Recommend";
  }
}

async function readEvents(res, replay) {
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    const parts = buf.split("\n\n");
    buf = parts.pop() || "";
    for (const part of parts) {
      let ev = "message", data = "";
      part.split("\n").forEach((line) => {
        if (line.startsWith("event:")) ev = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      });
      if (!data) continue;
      let obj;
      try { obj = JSON.parse(data); } catch { continue; }
      handleEvent(ev, obj, replay);
    }
  }
}

function handleEvent(ev, d, replay) {
  if (ev === "stage_start") setStep(d.stage, "running", "working…");
  else if (ev === "stage_progress") setStep(d.stage, "running", d.message || "working…");
  else if (ev === "stage_end") {
    const r = d.record || {};
    state.stageOutputs[d.stage] = r;
    if (r.status === "failed" || r.error) setStep(d.stage, "failed", "failed");
    else if (r.fallback_used) setStep(d.stage, "fallback", `backup rule used · ${stageSummary(d.stage, r.output)}`);
    else setStep(d.stage, "done", `${stageSummary(d.stage, r.output)} · ${secs(r)}`);
  } else if (ev === "final") {
    (d.stages || []).forEach((st) => { if (!state.stageOutputs[st.name]) state.stageOutputs[st.name] = st; });
    renderStageDetails();
    renderRunInfo(d, replay);
    renderRecs(d);
  } else if (ev === "error") {
    showError(d.message || d.error || "The run failed.");
  }
}

const secs = (r) => (r.ended && r.started ? `${Math.max(0, r.ended - r.started).toFixed(1)}s` : "");

/* ---------------- Stage details ---------------- */
function renderStageDetails() {
  const body = $("stage-details-body");
  body.innerHTML = STAGES.map((s) => {
    const r = state.stageOutputs[s];
    if (!r) return "";
    const warn = r.fallback_used ? ` <span class="tag warn">backup rule used</span>` : "";
    const err = r.error ? `<p class="error">${esc(r.error)}</p>` : "";
    return `<div class="stage-block"><h4>${STAGE_TITLES[s]}${warn}</h4>${err}${stageBody(s, r.output)}</div>`;
  }).join("");
  $("stage-details").hidden = false;
}

function stageBody(stage, out) {
  if (!out) return `<p class="muted small">No output.</p>`;
  const list = (a) => (a && a.length ? a.map(esc).join(", ") : "—");
  if (stage === "understanding") {
    return `<dl class="kv"><dt>Summary</dt><dd>${esc(out.summary)}</dd><dt>Likes</dt><dd>${list(out.likes)}</dd>
      <dt>Dislikes</dt><dd>${list(out.dislikes)}</dd><dt>Rules</dt><dd>${list(out.constraints)}</dd><dt>Mood</dt><dd>${esc(out.mood || "—")}</dd></dl>`;
  }
  if (stage === "retrieval") {
    const c = out.candidates || [];
    const n = (src) => c.filter((x) => (x.sources || []).includes(src)).length;
    return `<p class="small">${c.length} candidates · ${n("vector")} by text similarity · ${n("graph")} by movie graph · ${c.filter((x) => (x.sources || []).length > 1).length} by both</p>
      <div class="scroll"><table class="mini-table"><tr><th>Movie</th><th>Found by</th><th>Graph path</th></tr>
      ${c.map((x) => `<tr><td>${esc(x.title)} ${x.year ? `(${x.year})` : ""}${x.n_ratings_train === 0 ? ' <span class="tag new">new</span>' : ""}</td>
        <td>${(x.sources || []).map(sourceName).join(" + ")}</td><td>${esc(x.path || "")}</td></tr>`).join("")}</table></div>`;
  }
  if (stage === "judging") {
    const v = [...(out.verdicts || [])].sort((a, b) => b.fit - a.fit);
    const titles = Object.fromEntries((state.stageOutputs.retrieval?.output?.candidates || []).map((c) => [c.movie_id, c.title]));
    return `<div class="scroll"><table class="mini-table"><tr><th>Movie</th><th>Fit</th><th>Match</th><th>Reason</th></tr>
      ${v.map((x) => `<tr><td>${esc(titles[x.movie_id] || x.movie_id)}</td><td>${fmt(x.fit, 2)}</td><td>${x.match ? "yes" : "no"}</td><td>${esc(x.reason)}</td></tr>`).join("")}</table></div>`;
  }
  if (stage === "summarising") {
    return `<dl class="kv"><dt>Standouts</dt><dd>${list(out.strong)}</dd><dt>Broke rules</dt><dd>${list(out.violations)}</dd><dt>Notes</dt><dd>${esc(out.notes || "—")}</dd></dl>`;
  }
  if (stage === "ranking") {
    return `<ol class="small">${(out.rankings || []).map((r) => `<li>${esc(r.title || r.movie_id)} — ${esc(r.reason)}</li>`).join("")}</ol>`;
  }
  return `<pre class="small">${esc(JSON.stringify(out, null, 2))}</pre>`;
}

const sourceName = (s) => (s === "vector" ? "text similarity" : s === "graph" ? "movie graph" : s);

/* ---------------- Results cards ---------------- */
function renderRunInfo(trace, replay) {
  const m = trace.metrics || {};
  const started = trace.stages && trace.stages[0] ? new Date(trace.stages[0].started * 1000) : null;
  const bits = [];
  bits.push(replay ? `<span class="tag">Saved run${started ? ` · recorded ${started.toISOString().slice(0, 10)}` : ""}</span>` : `<span class="tag good">Live run</span>`);
  bits.push(`<span>Model: <b>${esc(m.model || "unknown")}</b></span>`);
  bits.push(`<span>Found with: <b>${esc(RETRIEVAL_LABEL[trace.config] || trace.config)}</b></span>`);
  bits.push(`<span>${m.llm_calls ?? "?"} AI calls · ${typeof m.seconds === "number" ? m.seconds.toFixed(1) : "?"}s</span>`);
  if ((trace.stages || []).some((s) => s.fallback_used)) bits.push(`<span class="tag warn">A step used the backup rule — see details above</span>`);
  if (m.ignored_history) bits.push(`<span class="muted">${m.ignored_history} history movies not in catalog were ignored</span>`);
  const box = $("run-info");
  box.innerHTML = bits.join("");
  box.hidden = false;
}

function poster(item, w = 185) {
  const initials = esc((item.title || "?").split(/\s+/).slice(0, 2).map((x) => x[0]).join(""));
  if (!item.poster_path) return `<div class="poster" aria-hidden="true">${initials}</div>`;
  return `<img class="poster" src="https://image.tmdb.org/t/p/w${w}${esc(item.poster_path)}" alt="" loading="lazy"
    onerror="this.outerHTML='<div class=&quot;poster&quot;>${initials}</div>'">`;
}

function foundBy(item) {
  const src = item.sources || [];
  if (item.path) return `<span class="path">${esc(item.path)}</span>${src.includes("vector") ? " <span class='muted'>+ similar description</span>" : ""}`;
  if (src.includes("vector")) return "Similar description to your profile";
  return src.map(sourceName).join(" + ") || "—";
}

function itemTags(item) {
  const gt = new Set((state.selected?.ground_truth_ids) || []);
  const t = [];
  if (item.n_ratings_train === 0) t.push(`<span class="tag new">New movie · 0 ratings before cut-off</span>`);
  if ((item.sources || []).length === 1 && item.sources[0] === "graph") t.push(`<span class="tag graph">Found by movie graph</span>`);
  if (gt.has(item.movie_id)) t.push(`<span class="tag good">✓ This viewer really loved it</span>`);
  if (item.is_weak_match) t.push(`<span class="tag warn">Weak match (filler)</span>`);
  return t.join("");
}

function renderRecs(trace) {
  const box = $("recs");
  const items = trace.final || [];
  if (!items.length) { box.innerHTML = `<div class="empty">No recommendations were returned.</div>`; return; }
  box.innerHTML = items.map((it) => `
    <article class="rec">
      ${poster(it)}
      <div>
        <div class="rec-head"><span class="rank">#${it.rank}</span><span class="rec-title">${esc(it.title)}</span><span class="rec-year">${esc(it.year || "")}</span>
          ${typeof it.fit === "number" ? `<span class="muted small">fit ${it.fit.toFixed(2)}</span>` : ""}</div>
        <div class="tags">${itemTags(it)}</div>
        <div class="rec-row"><span class="k">Why</span>${esc(it.reason)}</div>
        <div class="rec-row"><span class="k">Found by</span>${foundBy(it)}</div>
        ${it.quote ? `<blockquote>“${esc(it.quote)}”</blockquote>` : ""}
      </div>
    </article>`).join("");
}

/* ---------------- Compare ---------------- */
async function loadComparison() {
  const id = $("compare-select").value;
  const vBox = $("compare-vector"), hBox = $("compare-hybrid");
  if (!id) return;
  vBox.innerHTML = hBox.innerHTML = `<div class="empty">Loading…</div>`;
  try {
    const res = await fetch(`/api/compare/${encodeURIComponent(id)}`);
    if (!res.ok) throw new Error("No saved runs for this example yet. Run `make record` with the AI model running.");
    const d = await res.json();
    const sc = state.scenarios.find((s) => s.id === id);
    const gt = new Set(sc?.ground_truth_ids || []);
    const v = d.vector?.final || [], h = d.hybrid?.final || [];
    const vIds = new Set(v.map((x) => x.movie_id));
    const mini = (it, only) => `<div class="mini${only ? " only" : ""}">
      <div class="rec-head"><span class="rank">#${it.rank}</span><b>${esc(it.title)}</b><span class="rec-year">${esc(it.year || "")}</span></div>
      <div class="tags">${only ? '<span class="tag graph">Found only with graph</span>' : ""}${it.n_ratings_train === 0 ? '<span class="tag new">New movie</span>' : ""}${gt.has(it.movie_id) ? '<span class="tag good">✓ Viewer loved it</span>' : ""}</div>
      <div class="rec-row muted">${foundBy(it)}</div></div>`;
    vBox.innerHTML = v.length ? v.map((x) => mini(x, false)).join("") : `<div class="empty">No saved run.</div>`;
    hBox.innerHTML = h.length ? h.map((x) => mini(x, !vIds.has(x.movie_id))).join("") : `<div class="empty">No saved run.</div>`;
  } catch (e) {
    vBox.innerHTML = hBox.innerHTML = `<div class="empty">${esc(e.message)}</div>`;
  }
}

/* ---------------- Results ---------------- */
async function loadResults() {
  try {
    const st = await (await fetch("/api/stats")).json();
    const cutoff = st.cutoff_ts ? new Date(st.cutoff_ts * 1000).toISOString().slice(0, 10) : "—";
    $("stats").innerHTML = [
      [st.catalog_size, "movies in catalog"],
      [st.cold_start, "new movies (0 ratings before cut-off)"],
      [st.graph_edges, "connections in the movie graph"],
      [cutoff, "cut-off date"],
    ].map(([v, k]) => `<div class="stat"><div class="v">${typeof v === "number" ? v.toLocaleString() : esc(v)}</div><div class="k">${k}</div></div>`).join("");
  } catch { /* optional */ }

  const body = $("results-body");
  let data;
  try { data = await (await fetch("/api/results")).json(); } catch { data = { error: "Could not load results." }; }
  if (data.error || !data.metrics) {
    body.innerHTML = `<tr><td colspan="8" class="muted">${esc(data.error || "No results yet. Run `make eval`.")}</td></tr>`;
    $("results-verdict").hidden = true;
    return;
  }
  const M = data.metrics;
  const rows = [["vector", "Text similarity only (baseline)"], ["graph", "Movie graph only"], ["hybrid", "Both (ours)"]];
  const keys = ["hit_rate_at_5", "hit_rate_at_10", "ndcg_at_5", "ndcg_at_10", "recall_at_50"];
  const best = Object.fromEntries(keys.map((k) => [k, Math.max(...rows.map(([c]) => M[c]?.[k] ?? -1))]));
  body.innerHTML = rows.map(([c, label]) => {
    const m = M[c] || {};
    const cell = (k, f) => `<td class="${m[k] === best[k] && m[k] > 0 ? "best" : ""}">${f(m[k])}</td>`;
    return `<tr class="${c === "hybrid" ? "ours" : ""}"><td>${label}</td>
      ${cell("hit_rate_at_5", pct)}${cell("hit_rate_at_10", pct)}${cell("ndcg_at_5", fmt)}${cell("ndcg_at_10", fmt)}${cell("recall_at_50", pct)}
      <td>${typeof m.avg_llm_calls === "number" ? m.avg_llm_calls.toFixed(1) : "—"}</td><td>${typeof m.avg_seconds === "number" ? m.avg_seconds.toFixed(1) : "—"}</td></tr>`;
  }).join("");

  const v = M.vector || {}, h = M.hybrid || {};
  const verdict = $("results-verdict");
  if (typeof v.hit_rate_at_5 === "number" && typeof h.hit_rate_at_5 === "number") {
    const word = h.hit_rate_at_5 > v.hit_rate_at_5 ? "beat" : h.hit_rate_at_5 === v.hit_rate_at_5 ? "tied" : "did not beat";
    verdict.innerHTML = `<b>Adding the movie graph ${word} the text-similarity baseline</b> on “hit in top 5”: ${pct(h.hit_rate_at_5)} vs ${pct(v.hit_rate_at_5)}.
      The right new movie reached the candidate list for ${pct(h.recall_at_50)} vs ${pct(v.recall_at_50)}.`;
    verdict.hidden = false;
  }
  const p = data.provenance || {};
  const rc = data.candidate_recall_all_viewers || {};
  $("results-foot").innerHTML = [
    p.viewers ? `${p.viewers} real MovieLens test viewers` : "",
    p.model ? `model ${esc([].concat(p.model).join(", "))}` : "",
    typeof p.runs_with_fallback === "number" ? `${p.runs_with_fallback} runs used a backup rule` : "",
    rc.hybrid ? `Candidate recall over all ${rc.hybrid.viewers.toLocaleString()} eligible viewers (no AI): text ${pct(rc.vector?.recall_at_50)}, both ${pct(rc.hybrid?.recall_at_50)}, graph ${pct(rc.graph?.recall_at_50)}` : "",
  ].filter(Boolean).join(" · ");

  $("cases").innerHTML = (data.error_analysis || []).slice(0, 6).map((c) => `
    <div class="case"><h4>Viewer #${esc(c.user_id)} later loved: ${esc(c.ground_truth)}</h4>
      <div>Text only: ${c.vector_hit ? "✓ found" : "✗ missed"} — <span class="muted">${esc((c.vector_recommendations || []).slice(0, 3).join(", "))}</span></div>
      <div>Both: ${c.hybrid_hit ? "✓ found" : "✗ missed"} — <span class="muted">${esc((c.hybrid_recommendations || []).slice(0, 3).join(", "))}</span></div>
    </div>`).join("") || `<p class="muted">No examples yet.</p>`;
}

/* ---------------- Init ---------------- */
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.tab)));
$("ask").addEventListener("submit", (e) => { e.preventDefault(); executeRecommendation(); });
$("compare-select").addEventListener("change", loadComparison);
checkHealth();
loadScenarios();
setInterval(checkHealth, 15000);
