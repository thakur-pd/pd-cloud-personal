/* ============================================================
   PD Cloud Personal — Tiny UI helpers (toasts, modals, counters)
   ============================================================ */
window.PD = window.PD || {};

PD.toast = function (msg, type = 'ok') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.toggle('error', type === 'error');
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3200);
};

PD.openModal = function (title, html) {
  document.getElementById('modalTitle').textContent = title;
  document.getElementById('modalBody').innerHTML = html;
  document.getElementById('modal').classList.add('show');
};

PD.closeModal = function () {
  document.getElementById('modal').classList.remove('show');
};

PD.fmtBytes = function (b) {
  if (!b) return '0 B';
  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
  return `${b.toFixed(b < 10 ? 2 : 1)} ${u[i]}`;
};

PD.fmtRate = function (b) {
  return PD.fmtBytes(b) + '/s';
};

PD.fmtDate = function (s) {
  if (!s) return '—';
  const d = new Date(s);
  return d.toLocaleString();
};

// Animate a number from current value to target
PD.animateValue = function (el, target, suffix = '', duration = 600) {
  if (!el) return;
  const start = parseFloat(el.dataset.value || '0');
  const startTime = performance.now();
  el.dataset.value = target;
  function step(now) {
    const t = Math.min(1, (now - startTime) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    const cur = start + (target - start) * eased;
    el.textContent = (Math.round(cur * 10) / 10).toFixed(target % 1 === 0 ? 0 : 1) + suffix;
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
};

PD.escapeHtml = function (s) {
  return (s ?? '').toString()
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
};

PD.statusBadge = function (status) {
  return `<span class="badge-pd ${status}">${status}</span>`;
};

PD.confirm = function (message) {
  return new Promise((resolve) => {
    PD.openModal('Confirm', `
      <p style="color:var(--text-muted);margin-bottom:18px">${PD.escapeHtml(message)}</p>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button class="btn-pd ghost" id="cnfNo">Cancel</button>
        <button class="btn-pd danger" id="cnfYes">Confirm</button>
      </div>
    `);
    document.getElementById('cnfYes').onclick = () => { PD.closeModal(); resolve(true); };
    document.getElementById('cnfNo').onclick  = () => { PD.closeModal(); resolve(false); };
  });
};
