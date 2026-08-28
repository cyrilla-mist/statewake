const fixtures = {
  return: {
    className: "return",
    eyebrow: "01 / RETURN",
    title: "Welcome back.",
    lede: "Your project may have moved while you were away.",
    supporting: "STATEWAKE checks whether the working state you left still matches the project now.",
    helper: "Check what still holds before you continue.",
    cta: "Re-enter Project",
    ctaState: "recover",
    note: "Calibrate the point you left. Then read what changed.",
  },
  recover: {
    className: "recover",
    eyebrow: "02 / RECOVER",
    title: "Your previous next step is no longer valid.",
    lede: "The project changed while you were away. Here’s what no longer holds—and what matters now.",
  },
  resume: {
    className: "resume",
    eyebrow: "03 / RESUME",
    title: "Working state recovered.",
    lede: "You are here.",
  },
  valid: {
    className: "valid",
    eyebrow: "04 / STILL ALIGNED",
    title: "You're still aligned.",
    lede: "Your trusted working state still matches the project now.",
    supporting: "Previous next action remains valid.",
  },
};

const app = document.querySelector("#app");
const tabs = [...document.querySelectorAll(".state-tab")];
const fixtureMode = new URLSearchParams(window.location.search).get("fixture") === "true";
const explicitApiBase = new URLSearchParams(window.location.search).get("api");
const apiBase = window.STATEWAKE_API_BASE || explicitApiBase || "";
let latestApiResponse = null;
let memoryCaptureState = "available";

document.querySelector("#mode-label").textContent = fixtureMode
  ? "re-entry / fixture fallback"
  : "re-entry / API mode";

function returnStateCards() {
  return `<div class="return-state-visual" aria-label="Project state comparison">
    <article class="state-card return-state-card return-state-card-current">
      <p class="card-kicker">Current project</p>
      <p class="return-state-status">Not checked yet</p>
      <p class="return-state-copy">Run Re-entry to compare the project against current evidence.</p>
    </article>
    <article class="state-card return-state-card return-state-card-trusted">
      <div class="return-state-heading">
        <p class="card-kicker">Last trusted state</p>
        <span class="return-state-trust"><i></i>Trusted</span>
      </div>
      <p class="return-state-checkpoint">CP-01</p>
      <dl>
        <div><dt>Direction</dt><dd>Feature A</dd></div>
        <div><dt>Next action</dt><dd>Finish Feature A integration</dd></div>
      </dl>
    </article>
  </div>`;
}

function button(label, state, className = "button") {
  return `<button class="${className}" data-state="${state}">${label}</button>`;
}

function returnScreen(data) {
  return `<section class="screen ${data.className}">
    <div class="copy-block">
      <p class="eyebrow">${data.eyebrow}</p>
      <h1>${data.title}</h1>
      <p class="lede">${data.lede}</p>
      <p class="supporting">${data.supporting}</p>
      <div class="actions"><button class="button" data-action="reenter">${data.cta}</button></div>
      <p class="helper">${data.helper}</p>
    </div>
    ${returnStateCards()}
  </section>`;
}

function recoverScreen(data) {
  const evidence = latestApiResponse?.evidence?.evidence;
  const evidenceMarkup = Array.isArray(evidence) && evidence.length
    ? evidence.map((item) => `<li><span class="evidence-kind">${escapeHtml(item.kind || "Evidence")}</span><span>${escapeHtml(item.summary || item.description || JSON.stringify(item))}</span></li>`).join("")
    : `<li><span class="evidence-kind">Commit</span><span>Experimental Feature B implementation entered the project history.</span></li>
       <li><span class="evidence-kind">Route/config</span><span>Feature A left the active demo flow; Feature B is the current implementation path.</span></li>
       <li><span class="evidence-kind">README</span><span>The walkthrough now describes the current demo path.</span></li>
       <li><span class="evidence-kind">Open issue</span><span>Cloud Run deployment blocks the hosted demo.</span></li>`;
  return `<section class="screen ${data.className}">
    <div class="recover-main">
      <p class="eyebrow">${data.eyebrow}</p>
      <h1>${data.title}</h1>
      <p class="lede">${data.lede}</p>
      <div class="recover-state-cards">
        <article class="state-card recover-state-card recover-trusted-card">
          <p class="card-kicker">Last trusted state</p>
          <p class="recover-checkpoint">CP-01</p>
          <dl>
            <div><dt>Direction</dt><dd>Feature A</dd></div>
            <div><dt>Priority</dt><dd>Technical depth</dd></div>
            <div><dt>Next action</dt><dd>Finish Feature A integration</dd></div>
          </dl>
          <span class="recover-status"><i></i>Trusted</span>
        </article>
        <article class="state-card recover-state-card recover-reality-card">
          <p class="card-kicker">Current reality</p>
          <dl>
            <div><dt>Implementation</dt><dd>Feature A left the active demo flow</dd></div>
            <div><dt>Current path</dt><dd>Feature B is the CURRENT IMPLEMENTATION PATH</dd></div>
            <div><dt>Deployment</dt><dd class="blocked">Cloud Run blocks the hosted demo</dd></div>
          </dl>
        </article>
      </div>
      <section class="comparison" aria-label="What changed">
        <p class="section-kicker">What changed</p>
        <div class="changed-grid">
          <div><p class="compare-label">When you left</p><p>Direction · Feature A</p><p>Priority · Technical depth</p><p>Next action · Finish Feature A integration</p></div>
          <div><p class="compare-label">Current reality</p><p>Feature A left the active demo flow</p><p>Feature B is the CURRENT IMPLEMENTATION PATH</p><p>Cloud Run deployment blocks the hosted demo</p><p>Presentation polish is non-material</p></div>
        </div>
      </section>
      <section class="what-matters glass" aria-label="What matters now">
        <p class="section-kicker">What matters now</p>
        <ul class="signal-list">
          <li><strong>Blocker</strong><span>Cloud Run deployment blocks the hosted demo</span></li>
          <li><strong>No longer valid</strong><span>Finish Feature A integration</span></li>
          <li><strong>Current implementation path</strong><span>Feature B</span></li>
          <li><strong>Presentation</strong><span>Non-material</span></li>
        </ul>
      </section>
    </div>
    <aside class="decision-rail">
      <section class="why-stop glass"><p class="section-kicker">Why STATEWAKE stopped</p><p>Protected project direction cannot be replaced from observed evidence alone.</p><p>A replacement direction still needs your authority.</p></section>
      <div class="decision glass">
        <p class="compare-label">Decision gate</p>
        <h2>The project moved away from Feature A. Which direction should I use to rebuild your Resume State?</h2>
        <div class="actions">
          <button class="button signal" data-action="resolution">Move forward with Feature B</button>
          <button class="button secondary" data-action="defer">Keep my previous direction</button>
          <button class="text-button" data-evidence>Show evidence</button>
          <button class="text-button" data-action="defer">Decide later</button>
        </div>
      </div>
      <div class="evidence glass" data-evidence-panel><h3>Why STATEWAKE thinks this changed</h3><ul class="evidence-list">${evidenceMarkup}</ul></div>
    </aside>
  </section>`;
}

function resumeScreen(data) {
  const committed = latestApiResponse?.resume_state;
  const state = committed || latestApiResponse?.trusted_state || {
    direction: "Feature B",
    priority: "Demo clarity",
    current_next_action: "Resolve Cloud Run deployment failure",
    checkpoint_id: "CP-02",
  };
  const doFirst = state.do_first || state.current_next_action;
  const checkpoint = state.checkpoint_id;
  return `<section class="screen ${data.className}">
    <div class="resume-main">
      <p class="eyebrow">${data.eyebrow}</p>
      <h1>${data.title}</h1>
      <p class="lede">${data.lede}</p>
      <div class="actions">${button("Resume Project", "resume")}</div>
      <div class="state-card glass resume-artifact">
      <div class="artifact-heading">
        <div><p class="card-kicker">Resume State</p><p class="artifact-title">A verified point of continuation</p></div>
        <span class="artifact-checkpoint">${escapeHtml(checkpoint)}</span>
      </div>
      <dl>
        <div><dt>Direction</dt><dd>${escapeHtml(state.direction)}</dd></div>
        <div><dt>Priority</dt><dd>${escapeHtml(state.priority)}</dd></div>
        <div><dt>Do First</dt><dd>${escapeHtml(doFirst)}</dd></div>
        <div><dt>Ignore for Now</dt><dd>${escapeHtml(state.ignore_for_now || "Feature A integration")}</dd></div>
      </dl>
      <span class="checkpoint">Committed continuation point</span>
      </div>
      <section class="what-changed glass resume-changes"><p class="section-kicker">What changed</p><div class="changed-grid"><div><p class="compare-label">Direction</p><p>Feature A → Feature B</p></div><div><p class="compare-label">Priority</p><p>Technical depth → Demo clarity</p></div><div><p class="compare-label">Next action</p><p>Finish Feature A integration<br>→ Resolve Cloud Run deployment failure</p></div></div></section>
      <div class="memory-capture glass">
      <p class="card-kicker">For next time <span class="optional-label">Optional</span></p>
      <p>Suggested rule: Experimental implementation alone does not establish approved scope without explicit confirmation.</p>
      ${memoryCaptureState === "saved"
        ? `<p class="memory-saved">Saved for future re-entry.</p>`
        : `<div class="memory-actions"><button class="button secondary" data-action="save-memory">Save for future re-entry</button><button class="text-button" data-action="dismiss-memory">Not now</button></div>`}
      </div>
    </div>
  </section>`;
}

function validScreen(data) {
  const state = latestApiResponse?.trusted_state || {
    direction: "Feature B",
    priority: "Demo clarity",
    current_next_action: "Resolve Cloud Run deployment failure",
    checkpoint_id: "CP-02",
  };
  const appliedRule = latestApiResponse?.applied_memory?.find(
    (memory) => memory.memory_type === "interpretation_rule",
  );
  return `<section class="screen ${data.className}">
    <div class="valid-main">
      <p class="eyebrow">${data.eyebrow}</p>
      <h1>${data.title}</h1>
      <p class="lede">${data.lede}</p>
      <p class="validation-complete">Validation complete. <span>No recovery required.</span></p>
      <p class="quiet-line">${data.supporting}</p>
      <div class="actions">${button("Resume Project", "resume")}</div>
      <div class="state-card glass valid-artifact">
      <p class="card-kicker">Still aligned</p>
      <p class="valid-checkpoint">${escapeHtml(state.checkpoint_id)}</p>
      <dl>
        <div><dt>Direction</dt><dd>${escapeHtml(state.direction)}</dd></div>
        <div><dt>Priority</dt><dd>${escapeHtml(state.priority || "Demo clarity")}</dd></div>
        <div><dt>Next Action</dt><dd>${escapeHtml(state.current_next_action)}</dd></div>
      </dl>
      <span class="valid-status"><i></i>Valid · No new checkpoint created.</span>
      </div>
      <section class="what-changed glass valid-evidence"><p class="section-kicker">New evidence</p><div class="evidence-summary"><p><strong>Feature C</strong><span>Experimental prototype</span></p><p><strong>Cloud Run blocker</strong><span>Still open</span></p>${appliedRule ? `<p><strong>Applied collaboration rule</strong><span>${escapeHtml(appliedRule.summary)}</span></p>` : `<p><strong>Applied collaboration rule</strong><span>Experimental implementation ≠ approved scope</span></p>`}</div></section>
      <p class="aligned-message">Nothing consequential changed your trusted continuation point.</p>
    </div>
  </section>`;
}

function render(state = "return") {
  const data = fixtures[state] || fixtures.return;
  if (state === "recover") app.innerHTML = recoverScreen(data);
  else if (state === "resume") app.innerHTML = resumeScreen(data);
  else if (state === "valid") app.innerHTML = validScreen(data);
  else app.innerHTML = returnScreen(data);

  tabs.forEach((tab) => tab.classList.toggle("is-active", tab.dataset.state === state));
  document.querySelectorAll("[data-state]").forEach((control) => {
    control.addEventListener("click", () => {
      const nextState = control.dataset.state;
      window.location.hash = nextState;
    });
  });
  const reenter = document.querySelector('[data-action="reenter"]');
  if (reenter && !fixtureMode) reenter.addEventListener("click", requestReentry);
  const resolution = document.querySelector('[data-action="resolution"]');
  if (resolution && !fixtureMode) resolution.addEventListener("click", requestResolution);
  const defer = document.querySelector('[data-action="defer"]');
  if (defer && !fixtureMode) defer.addEventListener("click", requestDefer);
  const saveMemory = document.querySelector('[data-action="save-memory"]');
  if (saveMemory) saveMemory.addEventListener("click", requestSaveMemory);
  const dismissMemory = document.querySelector('[data-action="dismiss-memory"]');
  if (dismissMemory) dismissMemory.addEventListener("click", () => {
    memoryCaptureState = "dismissed";
    render("resume");
  });
  const evidenceToggle = document.querySelector("[data-evidence]");
  const evidencePanel = document.querySelector("[data-evidence-panel]");
  if (evidenceToggle && evidencePanel) {
    evidenceToggle.addEventListener("click", () => {
      evidencePanel.classList.toggle("is-open");
      evidenceToggle.textContent = evidencePanel.classList.contains("is-open") ? "Hide evidence" : "Show evidence";
    });
  }
}

async function requestSaveMemory() {
  const control = document.querySelector('[data-action="save-memory"]');
  if (fixtureMode) {
    memoryCaptureState = "saved";
    render("resume");
    return;
  }
  control.disabled = true;
  control.textContent = "Saving…";
  try {
    const response = await fetch(`${apiBase}/api/reentry/memory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: latestApiResponse?.trusted_state?.project_id || "statewake-demo",
        confirmed: true,
      }),
    });
    if (!response.ok) throw new Error(`Memory was not saved (${response.status})`);
    memoryCaptureState = "saved";
    render("resume");
  } catch (error) {
    control.disabled = false;
    control.textContent = "Save for future re-entry";
    control.insertAdjacentHTML("afterend", `<p class="helper api-error">${escapeHtml(error.message)}</p>`);
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[character]));
}

async function requestReentry() {
  const control = document.querySelector('[data-action="reenter"]');
  control.disabled = true;
  control.textContent = "Checking trusted state…";
  try {
    const response = await fetch(`${apiBase}/api/reentry`, { method: "POST" });
    if (!response.ok) throw new Error(`API request failed (${response.status})`);
    latestApiResponse = await response.json();
    const validity = latestApiResponse.validity;
    if (validity.overall_validity === "VALID") window.location.hash = "valid";
    else if (latestApiResponse.resume_state) window.location.hash = "resume";
    else window.location.hash = "recover";
  } catch (error) {
    control.disabled = false;
    control.textContent = "Re-enter Project";
    control.insertAdjacentHTML("afterend", `<p class="helper api-error">${escapeHtml(error.message)}</p>`);
  }
}

async function requestResolution() {
  const control = document.querySelector('[data-action="resolution"]');
  control.disabled = true;
  control.textContent = "Checking authorization…";
  try {
    const response = await fetch(`${apiBase}/api/reentry/resolution`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: latestApiResponse?.authorization?.project_id || "statewake-demo",
        session_id: latestApiResponse?.authorization?.session_id,
        expected_state_version: latestApiResponse?.authorization?.expected_state_version || latestApiResponse?.trusted_state?.stateVersion || 1,
        approved_resolution_id: "MOVE_FORWARD_WITH_B",
      }),
    });
    if (!response.ok) throw new Error(`Resolution was not accepted (${response.status})`);
    latestApiResponse = await response.json();
    window.location.hash = latestApiResponse.resume_state ? "resume" : "recover";
  } catch (error) {
    control.disabled = false;
    control.textContent = "Move forward with Feature B";
    control.insertAdjacentHTML("afterend", `<p class="helper api-error">${escapeHtml(error.message)}</p>`);
  }
}

async function requestDefer() {
  const controls = [...document.querySelectorAll('[data-action="defer"]')];
  controls.forEach((control) => {
    control.disabled = true;
    control.textContent = "Preserving trusted state…";
  });
  try {
    const response = await fetch(`${apiBase}/api/reentry/resolution`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: latestApiResponse?.authorization?.project_id || "statewake-demo",
        session_id: latestApiResponse?.authorization?.session_id,
        expected_state_version: latestApiResponse?.authorization?.expected_state_version || latestApiResponse?.trusted_state?.stateVersion || 1,
        approved_resolution_id: "DEFER",
      }),
    });
    if (!response.ok) throw new Error(`Decision was not accepted (${response.status})`);
    latestApiResponse = await response.json();
    window.location.hash = "return";
  } catch (error) {
    controls.forEach((control) => {
      control.disabled = false;
      control.textContent = "Decide later";
    });
    controls[0]?.insertAdjacentHTML("afterend", `<p class="helper api-error">${escapeHtml(error.message)}</p>`);
  }
}

function stateFromHash() {
  return window.location.hash.replace("#", "") || "return";
}

window.addEventListener("hashchange", () => render(stateFromHash()));
render(stateFromHash());
