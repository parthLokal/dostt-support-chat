const API_BASE = "";
const TOKEN_KEY = "dostt_admin_token";
const NAME_KEY = "dostt_admin_name";

const $loginScreen = document.getElementById("loginScreen");
const $dashboard = document.getElementById("dashboard");
const $loginEmail = document.getElementById("loginEmail");
const $loginPassword = document.getElementById("loginPassword");
const $loginError = document.getElementById("loginError");
const $adminName = document.getElementById("adminName");
const $statusFilter = document.getElementById("statusFilter");
const $ticketRows = document.getElementById("ticketRows");
const $emptyState = document.getElementById("emptyState");
const $detailOverlay = document.getElementById("detailOverlay");
const $detailBody = document.getElementById("detailBody");

function token() { return localStorage.getItem(TOKEN_KEY); }

async function authedFetch(path, opts = {}) {
  const res = await fetch(API_BASE + path, {
    ...opts,
    headers: { ...(opts.headers || {}), Authorization: `Bearer ${token()}` },
  });
  if (res.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    showLogin();
    throw new Error("Session expired");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

function showLogin() {
  $loginScreen.hidden = false;
  $dashboard.hidden = true;
}
function showDashboard() {
  $loginScreen.hidden = true;
  $dashboard.hidden = false;
  $adminName.textContent = localStorage.getItem(NAME_KEY) || "";
  loadTickets();
}

document.getElementById("loginBtn").addEventListener("click", async () => {
  $loginError.hidden = true;
  try {
    const res = await fetch(API_BASE + "/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: $loginEmail.value, password: $loginPassword.value }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || "Login failed");
    }
    const body = await res.json();
    localStorage.setItem(TOKEN_KEY, body.token);
    localStorage.setItem(NAME_KEY, body.name);
    showDashboard();
  } catch (err) {
    $loginError.textContent = err.message;
    $loginError.hidden = false;
  }
});

document.getElementById("logoutBtn").addEventListener("click", () => {
  localStorage.removeItem(TOKEN_KEY);
  showLogin();
});
document.getElementById("refreshBtn").addEventListener("click", loadTickets);
$statusFilter.addEventListener("change", loadTickets);
document.getElementById("closeDetail").addEventListener("click", () => { $detailOverlay.hidden = true; });

function fmtDate(iso) {
  const d = new Date(iso + "Z");
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function slaCell(ticket) {
  if (!ticket.sla_due_at) return "—";
  const dueMs = new Date(ticket.sla_due_at + "Z").getTime();
  const isOpen = ticket.status !== "resolved" && ticket.status !== "closed";
  const overdue = isOpen && dueMs < Date.now();
  const label = fmtDate(ticket.sla_due_at);
  return overdue ? `<span class="sla-overdue">${label} (overdue)</span>` : label;
}

async function loadTickets() {
  const qs = $statusFilter.value ? `?status=${$statusFilter.value}` : "";
  let tickets;
  try {
    tickets = await authedFetch(`/api/admin/tickets${qs}`);
  } catch (err) {
    return;
  }
  $ticketRows.innerHTML = "";
  $emptyState.hidden = tickets.length > 0;
  tickets.forEach((ticket) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>#${ticket.id}</td>
      <td>${escapeHtml(ticket.category)}</td>
      <td>${escapeHtml(ticket.sub_category)}</td>
      <td><span class="status-pill status-${ticket.status}">${ticket.status.replace("_", " ")}</span></td>
      <td>${escapeHtml(ticket.escalation_team || "—")}</td>
      <td>${ticket.callback_requested ? "Yes" : "No"}</td>
      <td>${ticket.refund_checked ? escapeHtml(ticket.refund_rule_label || "checked") : "—"}</td>
      <td>${ticket.real_ticket_id ? `#${ticket.real_ticket_id}` : "—"}</td>
      <td>${slaCell(ticket)}</td>
      <td>${fmtDate(ticket.created_at)}</td>
    `;
    tr.addEventListener("click", () => openDetail(ticket));
    $ticketRows.appendChild(tr);
  });
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function openDetail(ticket) {
  $detailBody.innerHTML = `
    <div class="detail-body">
      <div class="field"><div class="label">Ticket</div><div class="value ticket-title">#${ticket.id} — ${escapeHtml(ticket.category)} / ${escapeHtml(ticket.sub_category)}</div></div>
      <div class="field"><div class="label">Description (EN)</div><div class="value">${escapeHtml(ticket.description_en)}</div></div>
      <div class="field"><div class="label">Original language description</div><div class="value">${escapeHtml(ticket.description)}</div></div>
      <div class="field"><div class="label">Escalation team</div><div class="value">${escapeHtml(ticket.escalation_team || "—")}</div></div>
      <div class="field"><div class="label">Callback requested</div><div class="value">${ticket.callback_requested ? "Yes" : "No"}</div></div>
      <div class="field"><div class="label">Update status</div>
        <select id="statusSelect">
          <option value="in_progress" ${ticket.status === "in_progress" ? "selected" : ""}>In Progress</option>
          <option value="resolved" ${ticket.status === "resolved" ? "selected" : ""}>Resolved</option>
          <option value="closed" ${ticket.status === "closed" ? "selected" : ""}>Closed</option>
        </select>
      </div>
      <div class="field"><div class="label">Note</div><textarea id="statusNote" placeholder="Optional note for the history log"></textarea></div>
      <button id="saveStatusBtn" class="primary-btn" style="width:100%">Save status</button>
      <div class="field" style="margin-top:16px"><div class="label">History</div>
        ${ticket.history.map((h) => `<div class="history-item">${fmtDate(h.changed_at)} — <strong>${h.status}</strong> by ${escapeHtml(h.changed_by)}${h.note ? " — " + escapeHtml(h.note) : ""}</div>`).join("")}
      </div>
    </div>
  `;
  document.getElementById("saveStatusBtn").addEventListener("click", async () => {
    const status = document.getElementById("statusSelect").value;
    const note = document.getElementById("statusNote").value;
    try {
      await authedFetch(`/api/admin/tickets/${ticket.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status, note: note || null }),
      });
      $detailOverlay.hidden = true;
      loadTickets();
    } catch (err) {
      alert(err.message);
    }
  });
  $detailOverlay.hidden = false;
}

if (token()) showDashboard();
else showLogin();
