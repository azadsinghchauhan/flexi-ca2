/**
 * Automated News Topic Monitoring Using Agentic AI
 * Client-side Orchestrator & UI Interactions
 */

document.addEventListener("DOMContentLoaded", () => {
  initAlertActions();
  initTopicToggles();
  initReportCopy();
});

// ==============================================================================
// 12-Step Agent Pipeline Orchestrator (Vercel Timeout Prevention)
// ==============================================================================

const STEP_NAMES = [
  "1. Load Topic & Keywords",
  "2. Build Search Queries",
  "3. Fetch Articles (Tavily/Engine)",
  "4. Normalize Fields",
  "5. Relevance Pre-Check Score",
  "6. 3-Layer Deduplication",
  "7. Filter Stored DB Articles",
  "8. Groq AI Structured JSON Analysis",
  "9. Store Results in Database",
  "10. Recompute Topic Trends (7d vs 7d)",
  "11. Generate High-Importance Alerts",
  "12. Write Monitoring Audit Log"
];

let isMonitoringRunning = false;

window.startMonitoringPipeline = async function(singleTopicId = null) {
  if (isMonitoringRunning) return;
  isMonitoringRunning = true;

  const modal = document.getElementById("agentModalBackdrop");
  const modalTopicTitle = document.getElementById("modalActiveTopic");
  const modalProgressFill = document.getElementById("modalProgressFill");
  const modalStatusText = document.getElementById("modalStatusText");
  const stepsContainer = document.getElementById("modalPipelineSteps");
  const modalSummaryStats = document.getElementById("modalSummaryStats");
  const modalCloseBtn = document.getElementById("modalCloseBtn");

  if (!modal) return;

  // Show modal
  modal.classList.add("active");
  modalCloseBtn.style.display = "none";
  modalSummaryStats.style.display = "none";
  stepsContainer.innerHTML = "";
  modalProgressFill.style.width = "5%";
  modalStatusText.innerText = "Initializing Agent Orchestrator...";

  let topicsToRun = [];

  try {
    if (singleTopicId) {
      topicsToRun = [{ id: singleTopicId, name: `Topic #${singleTopicId}` }];
    } else {
      modalStatusText.innerText = "Querying active monitoring topics...";
      const res = await fetch("/api/topics/active");
      topicsToRun = await res.json();
    }

    if (!topicsToRun || topicsToRun.length === 0) {
      modalStatusText.innerText = "No active topics configured! Please add or seed topics first.";
      modalCloseBtn.style.display = "inline-flex";
      modalCloseBtn.innerText = "Close";
      modalCloseBtn.onclick = () => { modal.classList.remove("active"); isMonitoringRunning = false; };
      return;
    }

    let totalArticlesFound = 0;
    let totalProcessed = 0;
    let totalDuplicates = 0;
    let totalAlerts = 0;

    for (let tIndex = 0; tIndex < topicsToRun.length; tIndex++) {
      const topic = topicsToRun[tIndex];
      modalTopicTitle.innerText = `Monitoring Topic (${tIndex + 1}/${topicsToRun.length}): "${topic.name}"`;
      modalStatusText.innerText = `Executing 12-Step Agentic Pipeline for "${topic.name}"...`;
      
      // Render initial 12 pending steps in UI
      renderPendingSteps(stepsContainer);

      const progressPercent = Math.round(((tIndex) / topicsToRun.length) * 100) + 10;
      modalProgressFill.style.width = `${progressPercent}%`;

      // Animate steps simulating real-time step transition
      const stepInterval = simulateStepProgress(stepsContainer);

      // Call backend per-topic endpoint
      const response = await fetch(`/api/monitor/run-topic/${topic.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      clearInterval(stepInterval);
      const result = await response.json();

      if (result.success && result.steps) {
        renderCompletedSteps(stepsContainer, result.steps);
        totalArticlesFound += (result.articles_found || 0);
        totalProcessed += (result.articles_processed || 0);
        totalDuplicates += (result.duplicates_removed || 0);
        totalAlerts += (result.alerts_created || 0);
      } else {
        markStepsFailed(stepsContainer, result.error || "Agent execution failed");
      }

      // Small pause between topics
      if (tIndex < topicsToRun.length - 1) {
        modalStatusText.innerText = `Topic complete. Advancing to next topic in queue...`;
        await new Promise(r => setTimeout(r, 1200));
      }
    }

    // Pipeline Complete
    modalProgressFill.style.width = "100%";
    modalStatusText.innerText = `Agent Pipeline Completed Successfully!`;
    
    // Show summary badge counters
    modalSummaryStats.style.display = "grid";
    document.getElementById("modalStatFound").innerText = totalArticlesFound;
    document.getElementById("modalStatProcessed").innerText = totalProcessed;
    document.getElementById("modalStatDups").innerText = totalDuplicates;
    document.getElementById("modalStatAlerts").innerText = totalAlerts;

    modalCloseBtn.style.display = "inline-flex";
    modalCloseBtn.innerText = "View Results & Refresh";
    modalCloseBtn.onclick = () => {
      window.location.reload();
    };

  } catch (err) {
    console.error("Orchestrator error:", err);
    modalStatusText.innerText = `Agent Error: ${err.message}`;
    modalCloseBtn.style.display = "inline-flex";
    modalCloseBtn.innerText = "Dismiss";
    modalCloseBtn.onclick = () => {
      modal.classList.remove("active");
      isMonitoringRunning = false;
    };
  }
};

function renderPendingSteps(container) {
  container.innerHTML = "";
  STEP_NAMES.forEach((name, idx) => {
    const row = document.createElement("div");
    row.className = "pipeline-step-row";
    row.id = `modalStepRow_${idx + 1}`;
    row.innerHTML = `
      <div class="step-info">
        <span class="step-num">${idx + 1}</span>
        <span class="step-name">${name}</span>
      </div>
      <div class="step-meta" id="modalStepMeta_${idx + 1}">
        <span style="color: var(--text-muted);">Waiting...</span>
      </div>
    `;
    container.appendChild(row);
  });
}

function simulateStepProgress(container) {
  let cur = 1;
  return setInterval(() => {
    if (cur <= 12) {
      const row = document.getElementById(`modalStepRow_${cur}`);
      const meta = document.getElementById(`modalStepMeta_${cur}`);
      if (row) {
        row.className = "pipeline-step-row running";
        if (meta) meta.innerHTML = `<span style="color: var(--accent-cyan);">⚡ Running...</span>`;
      }
      if (cur > 1) {
        const prevRow = document.getElementById(`modalStepRow_${cur - 1}`);
        const prevMeta = document.getElementById(`modalStepMeta_${cur - 1}`);
        if (prevRow) prevRow.className = "pipeline-step-row success";
        if (prevMeta) prevMeta.innerHTML = `<span style="color: var(--accent-emerald);">✓ Done</span>`;
      }
      cur++;
    }
  }, 450);
}

function renderCompletedSteps(container, executedSteps) {
  executedSteps.forEach(step => {
    const row = document.getElementById(`modalStepRow_${step.step_number}`);
    const meta = document.getElementById(`modalStepMeta_${step.step_number}`);
    if (row && meta) {
      row.className = `pipeline-step-row ${step.status}`;
      const statusIcon = step.status === "success" ? "✓" : (step.status === "failed" ? "✕" : "!");
      const statusColor = step.status === "success" ? "var(--accent-emerald)" : "var(--accent-rose)";
      meta.innerHTML = `
        <span style="color: ${statusColor}; font-weight: 600;">${statusIcon} ${step.duration_ms}ms</span>
        <div style="font-size: 0.72rem; color: var(--text-secondary); max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${step.details}">
          ${step.details}
        </div>
      `;
    }
  });
}

function markStepsFailed(container, errMsg) {
  const meta = document.getElementById("modalStepMeta_1");
  if (meta) {
    meta.innerHTML = `<span style="color: var(--accent-rose);">Error: ${errMsg}</span>`;
  }
}

// ==============================================================================
// Alert Read Handler
// ==============================================================================
function initAlertActions() {
  document.querySelectorAll(".btn-mark-alert-read").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      const alertId = btn.dataset.alertId;
      if (!alertId) return;

      try {
        btn.disabled = true;
        btn.innerText = "Marking...";
        const res = await fetch(`/api/alerts/${alertId}/read`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
          const card = document.getElementById(`alertCard_${alertId}`);
          if (card) {
            card.style.opacity = "0.5";
            card.style.pointerEvents = "none";
          }
          btn.innerText = "Read ✓";
          // Decrement nav badge if present
          const navBadge = document.querySelector(".nav-badge");
          if (navBadge) {
            let count = parseInt(navBadge.innerText) || 0;
            if (count > 1) {
              navBadge.innerText = count - 1;
            } else {
              navBadge.remove();
            }
          }
        }
      } catch (err) {
        btn.disabled = false;
        btn.innerText = "Error";
      }
    });
  });
}

// ==============================================================================
// Topic Active Toggle Handler
// ==============================================================================
function initTopicToggles() {
  document.querySelectorAll(".topic-toggle-checkbox").forEach(toggle => {
    toggle.addEventListener("change", async () => {
      const topicId = toggle.dataset.topicId;
      if (!topicId) return;

      try {
        const res = await fetch(`/api/topics/${topicId}/toggle`, { method: "POST" });
        const data = await res.json();
        if (!data.success) {
          toggle.checked = !toggle.checked;
          alert("Could not toggle topic status.");
        }
      } catch (err) {
        toggle.checked = !toggle.checked;
        alert("Network error updating topic.");
      }
    });
  });
}

// ==============================================================================
// Report Markdown Copy
// ==============================================================================
function initReportCopy() {
  const copyBtn = document.getElementById("btnCopyMarkdownReport");
  if (!copyBtn) return;

  copyBtn.addEventListener("click", () => {
    const rawMd = document.getElementById("reportMarkdownSource");
    if (!rawMd) return;

    navigator.clipboard.writeText(rawMd.value).then(() => {
      const origText = copyBtn.innerHTML;
      copyBtn.innerHTML = "<span>✓ Copied to Clipboard!</span>";
      setTimeout(() => { copyBtn.innerHTML = origText; }, 2500);
    }).catch(err => {
      alert("Failed to copy markdown to clipboard.");
    });
  });
}
