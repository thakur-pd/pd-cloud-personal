/* ============================================================
   PD Cloud Personal — Page renderers
   Each page exports an async render(container) and may return
   a cleanup() function to stop intervals when navigating away.
   ============================================================ */
window.PD = window.PD || {};
PD.Pages = {};

/* ---------------------------------------------------------- */
/*  DASHBOARD                                                 */
/* ---------------------------------------------------------- */
PD.Pages.dashboard = {
  title: 'Dashboard',
  async render(c) {
    c.innerHTML = `
      <div class="row g-3 mb-3">
        ${stat('cpu', 'CPU', 'cpu', 'bi-cpu')}
        ${stat('ram', 'Memory', 'memory', 'bi-memory')}
        ${stat('disk', 'Disk', 'hdd', 'bi-hdd')}
        ${stat('net', 'Network', 'arrow-down-up', 'bi-arrow-down-up')}
      </div>

      <div class="row g-3 mb-3">
        <div class="col-12 col-md-3">
          <div class="card-pd">
            <div class="label" style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em;font-weight:600;">Uptime</div>
            <div style="font-size:18px;font-weight:700;margin-top:4px;" id="dUptime">—</div>
            <div style="color:var(--text-muted);font-size:12px;" id="dBoot">—</div>
          </div>
        </div>
        <div class="col-12 col-md-3">
          <div class="card-pd">
            <div class="label" style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em;font-weight:600;">System Load</div>
            <div style="font-size:18px;font-weight:700;margin-top:4px;" id="dLoad">—</div>
            <div style="color:var(--text-muted);font-size:12px;">1m / 5m / 15m</div>
          </div>
        </div>
        <div class="col-12 col-md-3">
          <div class="card-pd">
            <div class="label" style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em;font-weight:600;">Applications</div>
            <div style="font-size:18px;font-weight:700;margin-top:4px;"><span id="dAppsRun">0</span> / <span id="dAppsTotal">0</span></div>
            <div style="color:var(--text-muted);font-size:12px;">running / total</div>
          </div>
        </div>
        <div class="col-12 col-md-3">
          <div class="card-pd">
            <div class="label" style="font-size:11px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em;font-weight:600;">CPU Cores</div>
            <div style="font-size:18px;font-weight:700;margin-top:4px;" id="dCores">—</div>
            <div style="color:var(--text-muted);font-size:12px;" id="dFreq">—</div>
          </div>
        </div>
      </div>

      <div class="row g-3">
        <div class="col-12 col-lg-8">
          <div class="card-pd">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
              <h6 style="margin:0;font-weight:700">Live Performance</h6>
              <span style="color:var(--text-muted);font-size:12px;">last 60s</span>
            </div>
            <div style="height:240px"><canvas id="liveChart"></canvas></div>
          </div>
        </div>
        <div class="col-12 col-lg-4">
          <div class="card-pd" style="height:100%">
            <h6 style="margin:0 0 12px;font-weight:700">Recent Activity</h6>
            <div id="recentAct" style="max-height:240px;overflow-y:auto"></div>
          </div>
        </div>
      </div>

      <div class="row g-3 mt-1">
        <div class="col-12">
          <div class="card-pd">
            <h6 style="margin:0 0 12px;font-weight:700">Recent Logs</h6>
            <div id="recentLogs" style="font-family:'JetBrains Mono',monospace;font-size:12.5px;max-height:240px;overflow-y:auto;background:var(--bg-soft);padding:12px;border-radius:8px;"></div>
          </div>
        </div>
      </div>
    `;

    // Live chart
    const ctx = document.getElementById('liveChart').getContext('2d');
    const history = { labels: [], cpu: [], ram: [], disk: [] };
    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: history.labels,
        datasets: [
          { label: 'CPU %',  data: history.cpu,  borderColor: '#10b981', backgroundColor: 'rgba(16,185,129,.15)', fill: true, tension: .35, pointRadius: 0, borderWidth: 2 },
          { label: 'RAM %',  data: history.ram,  borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,.10)', fill: true, tension: .35, pointRadius: 0, borderWidth: 2 },
          { label: 'Disk %', data: history.disk, borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,.08)', fill: true, tension: .35, pointRadius: 0, borderWidth: 2 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        scales: { y: { min: 0, max: 100, ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,.15)' } },
                  x: { ticks: { color: '#94a3b8', maxTicksLimit: 6 }, grid: { display: false } } },
        plugins: { legend: { labels: { color: '#64748b', boxWidth: 12 } } },
      },
    });

    const refresh = async () => {
      try {
        const d = await PD.api('/api/system/dashboard');
        PD.animateValue(document.querySelector('#stat-cpu .value'),  d.system.cpu.percent, '%');
        PD.animateValue(document.querySelector('#stat-ram .value'),  d.system.ram.percent, '%');
        PD.animateValue(document.querySelector('#stat-disk .value'), d.system.disk.percent, '%');
        document.querySelector('#stat-net .value').textContent = PD.fmtRate(d.system.network.rx_rate);
        document.querySelector('#stat-net .sub').textContent = '↑ ' + PD.fmtRate(d.system.network.tx_rate);

        document.querySelector('#stat-cpu .sub').textContent = d.system.cpu.count + ' cores @ ' + Math.round(d.system.cpu.freq) + 'MHz';
        document.querySelector('#stat-ram .sub').textContent = PD.fmtBytes(d.system.ram.used) + ' / ' + PD.fmtBytes(d.system.ram.total);
        document.querySelector('#stat-disk .sub').textContent = PD.fmtBytes(d.system.disk.used) + ' / ' + PD.fmtBytes(d.system.disk.total);

        document.getElementById('dUptime').textContent = d.system.uptime.pretty;
        document.getElementById('dBoot').textContent = 'Booted ' + PD.fmtDate(d.system.uptime.boot_time);
        document.getElementById('dLoad').textContent =
          `${d.system.load['1m'].toFixed(2)} · ${d.system.load['5m'].toFixed(2)} · ${d.system.load['15m'].toFixed(2)}`;
        document.getElementById('dAppsRun').textContent = d.apps.running;
        document.getElementById('dAppsTotal').textContent = d.apps.total;
        document.getElementById('dCores').textContent = d.system.cpu.count + ' logical';
        document.getElementById('dFreq').textContent = (d.system.cpu.physical || '?') + ' physical';

        // Chart push
        const ts = new Date().toLocaleTimeString().split(' ')[0];
        history.labels.push(ts);
        history.cpu.push(d.system.cpu.percent);
        history.ram.push(d.system.ram.percent);
        history.disk.push(d.system.disk.percent);
        if (history.labels.length > 30) {
          history.labels.shift(); history.cpu.shift(); history.ram.shift(); history.disk.shift();
        }
        chart.update('none');

        // Activity
        document.getElementById('recentAct').innerHTML = d.activities.map(a => `
          <div style="display:flex;gap:10px;padding:8px 0;border-bottom:1px solid var(--border-soft);">
            <i class="bi ${a.success ? 'bi-check-circle text-success' : 'bi-x-circle text-danger'}" style="font-size:14px;margin-top:3px;color:${a.success ? 'var(--mint-500)' : '#ef4444'}"></i>
            <div style="flex:1;min-width:0">
              <div style="font-size:13px;font-weight:600;">${PD.escapeHtml(a.action)} <span style="color:var(--text-muted);font-weight:400">${PD.escapeHtml(a.target || '')}</span></div>
              <div style="color:var(--text-faint);font-size:11px;">${PD.fmtDate(a.at)} · ${PD.escapeHtml(a.ip || '')}</div>
            </div>
          </div>
        `).join('') || '<div style="color:var(--text-muted);font-size:13px;">No activity yet.</div>';

        // Logs
        document.getElementById('recentLogs').innerHTML = (d.logs.length ?
          d.logs.map(l => `<div><span style="color:var(--text-faint)">${PD.fmtDate(l.at)}</span> [${l.level}] ${PD.escapeHtml(l.message)}</div>`).join('')
          : '<span style="color:var(--text-muted)">No recent logs.</span>');
      } catch (e) { console.warn(e); }
    };

    await refresh();
    const interval = setInterval(refresh, 3000);
    return () => { clearInterval(interval); chart.destroy(); };
  },
};

function stat(id, label, _ico, biIcon) {
  return `
    <div class="col-6 col-md-3">
      <div class="card-pd stat-card" id="stat-${id}">
        <div class="icon"><i class="bi ${biIcon}"></i></div>
        <div class="label">${label}</div>
        <div class="value" data-anim>—</div>
        <div class="sub">loading…</div>
      </div>
    </div>`;
}

/* ---------------------------------------------------------- */
/*  MONITORING                                                */
/* ---------------------------------------------------------- */
PD.Pages.monitoring = {
  title: 'Monitoring',
  async render(c) {
    c.innerHTML = `
      <div class="row g-3">
        ${['cpu','ram','disk','net'].map(k => `
          <div class="col-12 col-md-6">
            <div class="card-pd">
              <h6 style="margin:0 0 8px;font-weight:700;text-transform:capitalize;">${k} usage</h6>
              <div style="height:200px"><canvas id="mc-${k}"></canvas></div>
            </div>
          </div>`).join('')}
      </div>
      <div class="card-pd mt-3">
        <h6 style="margin:0 0 10px;font-weight:700;">Top Processes</h6>
        <div id="procTable"></div>
      </div>
    `;
    const charts = {};
    const series = { cpu: [], ram: [], disk: [], net: [] };
    const labels = [];
    const mk = (id, color, label) => new Chart(document.getElementById('mc-' + id), {
      type: 'line',
      data: { labels, datasets: [{ label, data: series[id], borderColor: color, backgroundColor: color + '22', fill: true, tension: .3, pointRadius: 0, borderWidth: 2 }] },
      options: { responsive: true, maintainAspectRatio: false, animation: false,
        scales: { y: { beginAtZero: true }, x: { ticks: { maxTicksLimit: 6 } } },
        plugins: { legend: { display: false } } },
    });
    charts.cpu = mk('cpu', '#10b981', 'CPU %');
    charts.ram = mk('ram', '#3b82f6', 'RAM %');
    charts.disk= mk('disk', '#f59e0b', 'Disk %');
    charts.net = mk('net', '#8b5cf6', 'Net B/s');

    const refresh = async () => {
      try {
        const s = await PD.api('/api/system/snapshot');
        const ts = new Date().toLocaleTimeString().split(' ')[0];
        labels.push(ts); if (labels.length > 30) labels.shift();
        series.cpu.push(s.cpu.percent); if (series.cpu.length > 30) series.cpu.shift();
        series.ram.push(s.ram.percent); if (series.ram.length > 30) series.ram.shift();
        series.disk.push(s.disk.percent); if (series.disk.length > 30) series.disk.shift();
        series.net.push(Math.round((s.network.rx_rate + s.network.tx_rate) / 1024)); if (series.net.length > 30) series.net.shift();
        Object.values(charts).forEach(ch => ch.update('none'));

        const svcs = await PD.api('/api/system/services');
        document.getElementById('procTable').innerHTML = `
          <table class="table-pd">
            <thead><tr><th>PID</th><th>Name</th><th>User</th><th>CPU %</th></tr></thead>
            <tbody>${svcs.slice(0, 12).map(p => `
              <tr><td>${p.pid}</td><td>${PD.escapeHtml(p.name || '')}</td><td>${PD.escapeHtml(p.username || '')}</td><td>${(p.cpu_percent || 0).toFixed(1)}</td></tr>
            `).join('')}</tbody>
          </table>`;
      } catch (e) {}
    };
    await refresh();
    const i = setInterval(refresh, 4000);
    return () => { clearInterval(i); Object.values(charts).forEach(ch => ch.destroy()); };
  },
};

/* ---------------------------------------------------------- */
/*  APPLICATIONS                                              */
/* ---------------------------------------------------------- */
PD.Pages.apps = {
  title: 'Applications',
  async render(c) {
    c.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;gap:8px;flex-wrap:wrap">
        <p style="color:var(--text-muted);margin:0">Deploy and control your Python, Node, PHP, Docker and static apps.</p>
        <button class="btn-pd primary" id="btnNewApp"><i class="bi bi-plus-lg"></i> New App</button>
      </div>
      <div class="card-pd p-0" style="overflow:hidden">
        <table class="table-pd">
          <thead><tr><th>Name</th><th>Type</th><th>Port</th><th>Status</th><th>Updated</th><th></th></tr></thead>
          <tbody id="appsBody"><tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:30px">Loading…</td></tr></tbody>
        </table>
      </div>
    `;
    const refresh = async () => {
      const apps = await PD.api('/api/apps');
      document.getElementById('appsBody').innerHTML = apps.length ? apps.map(a => `
        <tr>
          <td><strong>${PD.escapeHtml(a.name)}</strong>${a.domain ? `<br><small style="color:var(--text-muted)">${PD.escapeHtml(a.domain)}</small>` : ''}</td>
          <td><span class="badge-pd info">${a.app_type}</span></td>
          <td>${a.port || '—'}</td>
          <td>${PD.statusBadge(a.status)}</td>
          <td><small style="color:var(--text-muted)">${PD.fmtDate(a.updated_at)}</small></td>
          <td style="text-align:right;white-space:nowrap">
            <button class="btn-pd small ghost" data-act="start" data-id="${a.id}" title="Start"><i class="bi bi-play-fill"></i></button>
            <button class="btn-pd small ghost" data-act="stop" data-id="${a.id}" title="Stop"><i class="bi bi-stop-fill"></i></button>
            <button class="btn-pd small ghost" data-act="restart" data-id="${a.id}" title="Restart"><i class="bi bi-arrow-clockwise"></i></button>
            <button class="btn-pd small ghost" data-act="logs" data-id="${a.id}" title="Logs"><i class="bi bi-card-text"></i></button>
            <button class="btn-pd small ghost" data-act="deploy" data-id="${a.id}" title="Deploy"><i class="bi bi-cloud-upload"></i></button>
            <button class="btn-pd small danger" data-act="delete" data-id="${a.id}" title="Delete"><i class="bi bi-trash"></i></button>
          </td>
        </tr>
      `).join('') : `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:30px">No applications yet. Click <strong>New App</strong>.</td></tr>`;
    };

    document.getElementById('btnNewApp').onclick = () => {
      PD.openModal('Create Application', `
        <form id="newAppForm">
          <div class="row g-2">
            <div class="col-md-6"><label class="form-label">Name</label><input class="form-control" id="na_name" required pattern="[a-zA-Z0-9_\\-]+"></div>
            <div class="col-md-6"><label class="form-label">Type</label>
              <select class="form-select" id="na_type">
                <option value="python">Python</option><option value="flask">Flask</option>
                <option value="django">Django</option><option value="fastapi">FastAPI</option>
                <option value="node">Node.js</option><option value="php">PHP</option>
                <option value="static">Static</option>
              </select>
            </div>
            <div class="col-md-6"><label class="form-label">Port</label><input type="number" class="form-control" id="na_port" placeholder="8000"></div>
            <div class="col-md-6"><label class="form-label">Domain (optional)</label><input class="form-control" id="na_domain" placeholder="myapp.example.com"></div>
            <div class="col-12"><label class="form-label">Startup command (optional — uses sensible default if blank)</label>
              <input class="form-control" id="na_cmd" placeholder="e.g. uvicorn main:app --host 0.0.0.0 --port 8000"></div>
            <div class="col-md-8"><label class="form-label">Git URL (optional)</label><input class="form-control" id="na_git" placeholder="https://github.com/user/repo.git"></div>
            <div class="col-md-4"><label class="form-label">Branch</label><input class="form-control" id="na_branch" value="main"></div>
            <div class="col-12"><label class="form-label">Env vars (KEY=VALUE per line)</label>
              <textarea class="form-control" id="na_env" rows="3"></textarea></div>
          </div>
          <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:18px">
            <button type="button" class="btn-pd ghost" onclick="PD.closeModal()">Cancel</button>
            <button class="btn-pd primary"><i class="bi bi-check2"></i> Create</button>
          </div>
        </form>
      `);
      document.getElementById('newAppForm').onsubmit = async (e) => {
        e.preventDefault();
        const env = {};
        document.getElementById('na_env').value.split('\n').forEach(l => {
          const [k, ...v] = l.split('='); if (k.trim()) env[k.trim()] = v.join('=').trim();
        });
        try {
          await PD.api('/api/apps', { method: 'POST', body: {
            name: document.getElementById('na_name').value,
            app_type: document.getElementById('na_type').value,
            startup_command: document.getElementById('na_cmd').value,
            env_vars: env,
            port: parseInt(document.getElementById('na_port').value) || null,
            domain: document.getElementById('na_domain').value || null,
            git_url: document.getElementById('na_git').value || null,
            git_branch: document.getElementById('na_branch').value || 'main',
            auto_restart: true,
          }});
          PD.toast('App created');
          PD.closeModal();
          refresh();
        } catch (err) { PD.toast(err.message, 'error'); }
      };
    };

    c.addEventListener('click', async (e) => {
      const btn = e.target.closest('button[data-act]'); if (!btn) return;
      const id = btn.dataset.id; const act = btn.dataset.act;
      try {
        if (act === 'start')   { await PD.api(`/api/apps/${id}/start`,   { method: 'POST' }); PD.toast('Started'); }
        else if (act === 'stop')   { await PD.api(`/api/apps/${id}/stop`,    { method: 'POST' }); PD.toast('Stopped'); }
        else if (act === 'restart'){ await PD.api(`/api/apps/${id}/restart`, { method: 'POST' }); PD.toast('Restarted'); }
        else if (act === 'logs')   { const d = await PD.api(`/api/apps/${id}/logs?lines=300`); PD.openModal('Logs', `<pre style="background:#0b1220;color:#d1fae5;padding:14px;border-radius:10px;max-height:60vh;overflow:auto;font-size:12px">${PD.escapeHtml(d.logs || '(empty)')}</pre>`); return; }
        else if (act === 'deploy') {
          PD.openModal('Deploy', `
            <div class="mb-3">
              <h6>From Git</h6>
              <button class="btn-pd primary" id="depGit"><i class="bi bi-github"></i> Git Pull / Clone</button>
            </div>
            <hr>
            <div>
              <h6>From ZIP</h6>
              <input type="file" id="depZip" accept=".zip" class="form-control mb-2">
              <button class="btn-pd primary" id="depZipBtn"><i class="bi bi-file-zip"></i> Upload &amp; Extract</button>
            </div>`);
          document.getElementById('depGit').onclick = async () => {
            try { await PD.api(`/api/apps/${id}/deploy/git`, { method: 'POST' }); PD.toast('Git deploy started'); PD.closeModal(); }
            catch (err) { PD.toast(err.message, 'error'); }
          };
          document.getElementById('depZipBtn').onclick = async () => {
            const f = document.getElementById('depZip').files[0]; if (!f) return PD.toast('Pick a file', 'error');
            const fd = new FormData(); fd.append('file', f);
            try { await PD.upload(`/api/apps/${id}/deploy/zip`, fd); PD.toast('ZIP deployed'); PD.closeModal(); }
            catch (err) { PD.toast(err.message, 'error'); }
          };
          return;
        }
        else if (act === 'delete') {
          if (!(await PD.confirm('Delete this app and all its files? This cannot be undone.'))) return;
          await PD.api(`/api/apps/${id}`, { method: 'DELETE' }); PD.toast('Deleted');
        }
        refresh();
      } catch (err) { PD.toast(err.message, 'error'); }
    });

    await refresh();
  },
};

/* ---------------------------------------------------------- */
/*  DOCKER                                                    */
/* ---------------------------------------------------------- */
PD.Pages.docker = {
  title: 'Docker',
  async render(c) {
    c.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;gap:8px;flex-wrap:wrap;">
        <p style="margin:0;color:var(--text-muted)">Manage containers and Docker Compose stacks.</p>
        <div>
          <button class="btn-pd ghost" id="btnComp"><i class="bi bi-layers"></i> Compose</button>
          <button class="btn-pd primary" id="btnRun"><i class="bi bi-play-circle"></i> Run Container</button>
        </div>
      </div>
      <div id="dockerStatus" style="margin-bottom:10px"></div>
      <div class="card-pd p-0" style="overflow:hidden">
        <table class="table-pd">
          <thead><tr><th>Name</th><th>Image</th><th>Status</th><th>Ports</th><th></th></tr></thead>
          <tbody id="contBody"><tr><td colspan="5" style="padding:30px;text-align:center;color:var(--text-muted)">Loading…</td></tr></tbody>
        </table>
      </div>
    `;
    const refresh = async () => {
      try {
        const status = await PD.api('/api/docker/status');
        if (!status.available) {
          document.getElementById('dockerStatus').innerHTML =
            `<div class="card-pd" style="border-left:4px solid #f59e0b">⚠ Docker engine not available on host. Install with: <code>sudo apt install docker.io</code></div>`;
          document.getElementById('contBody').innerHTML = '';
          return;
        }
        const conts = await PD.api('/api/docker/containers');
        document.getElementById('contBody').innerHTML = conts.length ? conts.map(c => `
          <tr>
            <td><strong>${PD.escapeHtml(c.name)}</strong><br><small style="color:var(--text-muted)">${c.id}</small></td>
            <td>${PD.escapeHtml(c.image)}</td>
            <td>${PD.statusBadge(c.status === 'running' ? 'running' : 'stopped')}</td>
            <td>${Object.keys(c.ports || {}).join(', ') || '—'}</td>
            <td style="text-align:right;white-space:nowrap">
              <button class="btn-pd small ghost" data-act="start" data-id="${c.id}"><i class="bi bi-play-fill"></i></button>
              <button class="btn-pd small ghost" data-act="stop" data-id="${c.id}"><i class="bi bi-stop-fill"></i></button>
              <button class="btn-pd small ghost" data-act="restart" data-id="${c.id}"><i class="bi bi-arrow-clockwise"></i></button>
              <button class="btn-pd small ghost" data-act="logs" data-id="${c.id}"><i class="bi bi-card-text"></i></button>
              <button class="btn-pd small danger" data-act="remove" data-id="${c.id}"><i class="bi bi-trash"></i></button>
            </td>
          </tr>`).join('') : `<tr><td colspan="5" style="padding:30px;text-align:center;color:var(--text-muted)">No containers.</td></tr>`;
      } catch (e) { console.warn(e); }
    };

    c.addEventListener('click', async (e) => {
      const btn = e.target.closest('button[data-act]'); if (!btn) return;
      const id = btn.dataset.id, act = btn.dataset.act;
      try {
        if (act === 'logs') {
          const d = await PD.api(`/api/docker/containers/${id}/logs?tail=300`);
          PD.openModal('Container logs', `<pre style="background:#0b1220;color:#d1fae5;padding:14px;border-radius:10px;max-height:60vh;overflow:auto;font-size:12px">${PD.escapeHtml(d.logs)}</pre>`); return;
        }
        if (act === 'remove' && !(await PD.confirm('Remove this container?'))) return;
        const method = act === 'remove' ? 'DELETE' : 'POST';
        const url = act === 'remove' ? `/api/docker/containers/${id}` : `/api/docker/containers/${id}/${act}`;
        await PD.api(url, { method });
        PD.toast(act + 'ed');
        refresh();
      } catch (err) { PD.toast(err.message, 'error'); }
    });

    document.getElementById('btnRun').onclick = () => {
      PD.openModal('Run container', `
        <form id="dockRun">
          <div class="mb-2"><label class="form-label">Image</label><input class="form-control" id="dr_img" placeholder="nginx:alpine" required></div>
          <div class="mb-2"><label class="form-label">Name</label><input class="form-control" id="dr_name"></div>
          <div class="mb-2"><label class="form-label">Ports (host:container per line, e.g. 8080:80)</label><textarea class="form-control" id="dr_ports" rows="2"></textarea></div>
          <div class="mb-2"><label class="form-label">Env (KEY=VAL per line)</label><textarea class="form-control" id="dr_env" rows="2"></textarea></div>
          <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:14px">
            <button type="button" class="btn-pd ghost" onclick="PD.closeModal()">Cancel</button>
            <button class="btn-pd primary">Run</button>
          </div>
        </form>`);
      document.getElementById('dockRun').onsubmit = async (e) => {
        e.preventDefault();
        const ports = {}, env = {};
        document.getElementById('dr_ports').value.split('\n').forEach(l => {
          const [h, cp] = l.split(':'); if (h && cp) ports[`${cp.trim()}/tcp`] = h.trim();
        });
        document.getElementById('dr_env').value.split('\n').forEach(l => {
          const [k, ...v] = l.split('='); if (k.trim()) env[k.trim()] = v.join('=').trim();
        });
        try {
          await PD.api('/api/docker/containers', { method: 'POST', body: {
            image: document.getElementById('dr_img').value,
            name: document.getElementById('dr_name').value || null,
            ports, env, volumes: {}, command: null, restart: 'unless-stopped',
          }});
          PD.toast('Container started'); PD.closeModal(); refresh();
        } catch (err) { PD.toast(err.message, 'error'); }
      };
    };

    document.getElementById('btnComp').onclick = () => {
      PD.openModal('Docker Compose', `
        <form id="compForm">
          <div class="mb-2"><label class="form-label">Stack name</label><input class="form-control" id="cmp_name" required></div>
          <div class="mb-2"><label class="form-label">docker-compose.yml</label>
            <textarea class="form-control" id="cmp_yaml" rows="14" style="font-family:'JetBrains Mono',monospace;font-size:12px"></textarea>
          </div>
          <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:14px">
            <button type="button" class="btn-pd ghost" onclick="PD.closeModal()">Cancel</button>
            <button class="btn-pd primary">Up -d</button>
          </div>
        </form>`);
      document.getElementById('compForm').onsubmit = async (e) => {
        e.preventDefault();
        try {
          await PD.api('/api/docker/compose/up', { method: 'POST', body: {
            name: document.getElementById('cmp_name').value,
            compose_yaml: document.getElementById('cmp_yaml').value,
          }});
          PD.toast('Compose up'); PD.closeModal(); refresh();
        } catch (err) { PD.toast(err.message, 'error'); }
      };
    };

    await refresh();
    const i = setInterval(refresh, 6000);
    return () => clearInterval(i);
  },
};

/* ---------------------------------------------------------- */
/*  DATABASES                                                 */
/* ---------------------------------------------------------- */
PD.Pages.databases = {
  title: 'Databases',
  async render(c) {
    c.innerHTML = `
      <p style="color:var(--text-muted)">Run queries against SQLite files or a PostgreSQL DSN.</p>
      <div class="card-pd">
        <div class="row g-2">
          <div class="col-md-12">
            <label class="form-label">Connection</label>
            <input class="form-control" id="dbDsn" value="/var/lib/pdcloud/pdcloud.db" placeholder="/path/to/file.db   or   postgresql://user:pass@host/db">
          </div>
          <div class="col-md-12">
            <label class="form-label">SQL</label>
            <textarea class="form-control" id="dbSql" rows="6" style="font-family:'JetBrains Mono',monospace;font-size:13px">SELECT name FROM sqlite_master WHERE type='table';</textarea>
          </div>
          <div class="col-md-12" style="text-align:right">
            <button class="btn-pd primary" id="runSql"><i class="bi bi-play-fill"></i> Run</button>
          </div>
        </div>
      </div>
      <div class="card-pd mt-3" id="dbResult"><div style="color:var(--text-muted)">Results will appear here.</div></div>
    `;
    document.getElementById('runSql').onclick = async () => {
      try {
        const r = await PD.api('/api/db/query', { method: 'POST', body: {
          database: document.getElementById('dbDsn').value,
          sql: document.getElementById('dbSql').value,
        }});
        if (!r.columns.length) {
          document.getElementById('dbResult').innerHTML = `<div>OK · rowcount: ${r.rowcount}</div>`;
          return;
        }
        const head = r.columns.map(c => `<th>${PD.escapeHtml(c)}</th>`).join('');
        const body = r.rows.map(row => `<tr>${row.map(v => `<td>${PD.escapeHtml(String(v ?? ''))}</td>`).join('')}</tr>`).join('');
        document.getElementById('dbResult').innerHTML = `<div style="overflow:auto"><table class="table-pd"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>
          <div style="color:var(--text-muted);margin-top:8px;font-size:12px">${r.rowcount} rows</div>`;
      } catch (err) { PD.toast(err.message, 'error'); }
    };
  },
};

/* ---------------------------------------------------------- */
/*  FILE MANAGER                                              */
/* ---------------------------------------------------------- */
PD.Pages.files = {
  title: 'File Manager',
  async render(c) {
    let cwd = '';
    c.innerHTML = `
      <div class="card-pd">
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
          <button class="btn-pd ghost" id="fmUp"><i class="bi bi-arrow-90deg-up"></i></button>
          <input class="form-control" id="fmPath" value="" placeholder="/" style="flex:1;min-width:200px">
          <button class="btn-pd ghost" id="fmGo">Go</button>
          <button class="btn-pd ghost" id="fmMk"><i class="bi bi-folder-plus"></i> New folder</button>
          <label class="btn-pd primary" style="margin:0">
            <i class="bi bi-upload"></i> Upload
            <input type="file" id="fmUpload" hidden multiple>
          </label>
        </div>
        <div id="fmList"></div>
      </div>
    `;
    const load = async (path) => {
      cwd = path;
      document.getElementById('fmPath').value = '/' + path;
      try {
        const entries = await PD.api('/api/files/list?path=' + encodeURIComponent(path));
        document.getElementById('fmList').innerHTML = entries.length ? entries.map(e => `
          <div class="file-row" data-path="${PD.escapeHtml(e.path)}" data-isdir="${e.is_dir}">
            <div class="ico ${e.is_dir ? 'folder' : ''}"><i class="bi ${e.is_dir ? 'bi-folder-fill' : 'bi-file-earmark'}"></i></div>
            <div style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${PD.escapeHtml(e.name)}</div>
            <div class="size">${e.is_dir ? '' : PD.fmtBytes(e.size)}</div>
            <button class="btn-pd small ghost" data-act="dl"><i class="bi bi-download"></i></button>
            <button class="btn-pd small ghost" data-act="rn"><i class="bi bi-pencil"></i></button>
            ${e.name.toLowerCase().endsWith('.zip') ? `<button class="btn-pd small ghost" data-act="ex" title="Extract"><i class="bi bi-file-zip"></i></button>` : ''}
            <button class="btn-pd small danger" data-act="del"><i class="bi bi-trash"></i></button>
          </div>`).join('') : '<div style="color:var(--text-muted);padding:18px;text-align:center">Empty.</div>';
      } catch (err) { PD.toast(err.message, 'error'); }
    };

    document.getElementById('fmGo').onclick = () => load(document.getElementById('fmPath').value.replace(/^\/+/, ''));
    document.getElementById('fmUp').onclick = () => { const p = cwd.split('/').slice(0, -1).join('/'); load(p); };
    document.getElementById('fmMk').onclick = () => {
      const name = prompt('Folder name?'); if (!name) return;
      PD.api('/api/files/mkdir', { method: 'POST', body: { path: cwd, name } })
        .then(() => { PD.toast('Created'); load(cwd); })
        .catch(e => PD.toast(e.message, 'error'));
    };
    document.getElementById('fmUpload').onchange = async (e) => {
      for (const f of e.target.files) {
        const fd = new FormData(); fd.append('file', f);
        try { await PD.upload('/api/files/upload?path=' + encodeURIComponent(cwd), fd); }
        catch (err) { PD.toast(err.message, 'error'); }
      }
      PD.toast('Uploaded'); load(cwd);
    };

    c.addEventListener('click', async (e) => {
      const row = e.target.closest('.file-row'); if (!row) return;
      const p = row.dataset.path; const isdir = row.dataset.isdir === 'true';
      const actBtn = e.target.closest('button[data-act]');
      if (actBtn) {
        e.stopPropagation();
        const act = actBtn.dataset.act;
        try {
          if (act === 'dl') { window.location.href = '/api/files/download?path=' + encodeURIComponent(p); return; }
          if (act === 'rn') {
            const newName = prompt('New name?', p.split('/').pop()); if (!newName) return;
            await PD.api('/api/files/rename', { method: 'POST', body: { path: p, new_name: newName } });
            PD.toast('Renamed'); load(cwd); return;
          }
          if (act === 'del') {
            if (!(await PD.confirm('Delete ' + p + ' ?'))) return;
            await PD.api('/api/files/delete?path=' + encodeURIComponent(p), { method: 'DELETE' });
            PD.toast('Deleted'); load(cwd); return;
          }
          if (act === 'ex') {
            await PD.api('/api/files/extract?path=' + encodeURIComponent(p), { method: 'POST' });
            PD.toast('Extracted'); load(cwd); return;
          }
        } catch (err) { PD.toast(err.message, 'error'); }
        return;
      }
      if (isdir) { load(p); return; }
      // Edit file
      try {
        const r = await PD.api('/api/files/read?path=' + encodeURIComponent(p));
        PD.openModal('Edit: ' + p, `
          <textarea id="edTxt" class="form-control" rows="18" style="font-family:'JetBrains Mono',monospace;font-size:12.5px">${PD.escapeHtml(r.content)}</textarea>
          <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:12px">
            <button class="btn-pd ghost" onclick="PD.closeModal()">Close</button>
            <button class="btn-pd primary" id="edSave"><i class="bi bi-save"></i> Save</button>
          </div>
        `);
        document.getElementById('edSave').onclick = async () => {
          try {
            await PD.api('/api/files/write', { method: 'POST', body: {
              path: p, content: document.getElementById('edTxt').value,
            }});
            PD.toast('Saved'); PD.closeModal();
          } catch (err) { PD.toast(err.message, 'error'); }
        };
      } catch (err) { PD.toast(err.message, 'error'); }
    });

    await load('');
  },
};

/* ---------------------------------------------------------- */
/*  TERMINAL                                                  */
/* ---------------------------------------------------------- */
PD.Pages.terminal = {
  title: 'Terminal',
  async render(c) {
    c.innerHTML = `
      <p style="color:var(--text-muted)">Restricted single-command runner — audit-logged. Destructive commands are blocked.</p>
      <div class="terminal" id="term"></div>
      <div style="display:flex;gap:8px;align-items:center">
        <span style="color:var(--mint-600);font-weight:700;font-family:'JetBrains Mono',monospace">$</span>
        <input class="terminal-input" id="termIn" placeholder="Type a command and press Enter (e.g. ls -la)">
      </div>
    `;
    const term = document.getElementById('term');
    const inp = document.getElementById('termIn');
    const print = (cls, txt) => { const div = document.createElement('div'); if (cls) div.className = cls; div.textContent = txt; term.appendChild(div); term.scrollTop = term.scrollHeight; };

    print('prompt', '$ welcome');
    print('', 'PD Cloud Personal terminal. Working directory is restricted to /var/lib/pdcloud/apps');
    try {
      const h = await PD.api('/api/terminal/history?limit=10');
      h.reverse().forEach(x => print('', '· ' + x.command));
    } catch {}

    const history = [];
    let idx = -1;

    inp.addEventListener('keydown', async (e) => {
      if (e.key === 'ArrowUp')   { if (history.length && idx < history.length - 1) { idx++; inp.value = history[history.length - 1 - idx]; } e.preventDefault(); }
      else if (e.key === 'ArrowDown') { if (idx > 0) { idx--; inp.value = history[history.length - 1 - idx]; } else { idx = -1; inp.value = ''; } e.preventDefault(); }
      else if (e.key === 'Enter') {
        const cmd = inp.value.trim(); if (!cmd) return;
        history.push(cmd); idx = -1; inp.value = '';
        print('prompt', '$ ' + cmd);
        try {
          const r = await PD.api('/api/terminal/exec', { method: 'POST', body: { command: cmd } });
          print(r.exit_code === 0 ? '' : 'err', r.output || '(no output)');
        } catch (err) { print('err', err.message); }
      }
    });
    inp.focus();
  },
};

/* ---------------------------------------------------------- */
/*  BACKUPS                                                   */
/* ---------------------------------------------------------- */
PD.Pages.backups = {
  title: 'Backups',
  async render(c) {
    c.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px">
        <p style="margin:0;color:var(--text-muted)">Nightly snapshots run at 03:00 UTC. Create one now anytime.</p>
        <button class="btn-pd primary" id="newBak"><i class="bi bi-cloud-arrow-up"></i> Backup Now</button>
      </div>
      <div class="card-pd p-0" style="overflow:hidden">
        <table class="table-pd">
          <thead><tr><th>Name</th><th>Kind</th><th>Size</th><th>Created</th><th></th></tr></thead>
          <tbody id="bakBody"><tr><td colspan="5" style="padding:30px;text-align:center;color:var(--text-muted)">Loading…</td></tr></tbody>
        </table>
      </div>`;
    const refresh = async () => {
      const list = await PD.api('/api/backups');
      document.getElementById('bakBody').innerHTML = list.length ? list.map(b => `
        <tr><td><strong>${PD.escapeHtml(b.name)}</strong></td>
            <td><span class="badge-pd info">${b.kind}</span></td>
            <td>${PD.fmtBytes(b.size)}</td>
            <td>${PD.fmtDate(b.created_at)}</td>
            <td style="text-align:right;white-space:nowrap">
              <a class="btn-pd small ghost" href="/api/backups/${b.id}/download"><i class="bi bi-download"></i></a>
              <button class="btn-pd small danger" data-act="del" data-id="${b.id}"><i class="bi bi-trash"></i></button>
            </td></tr>`).join('')
        : `<tr><td colspan="5" style="padding:30px;text-align:center;color:var(--text-muted)">No backups yet.</td></tr>`;
    };
    document.getElementById('newBak').onclick = async () => {
      try { await PD.api('/api/backups/panel', { method: 'POST' }); PD.toast('Backup created'); refresh(); }
      catch (e) { PD.toast(e.message, 'error'); }
    };
    c.addEventListener('click', async (e) => {
      const b = e.target.closest('button[data-act="del"]'); if (!b) return;
      if (!(await PD.confirm('Delete backup?'))) return;
      try { await PD.api('/api/backups/' + b.dataset.id, { method: 'DELETE' }); PD.toast('Deleted'); refresh(); }
      catch (err) { PD.toast(err.message, 'error'); }
    });
    await refresh();
  },
};

/* ---------------------------------------------------------- */
/*  ACTIVITY                                                  */
/* ---------------------------------------------------------- */
PD.Pages.activity = {
  title: 'Activity Log',
  async render(c) {
    c.innerHTML = `
      <div class="card-pd p-0" style="overflow:hidden">
        <table class="table-pd">
          <thead><tr><th>When</th><th>Action</th><th>Target</th><th>IP</th><th>Result</th></tr></thead>
          <tbody id="actBody"><tr><td colspan="5" style="padding:30px;text-align:center;color:var(--text-muted)">Loading…</td></tr></tbody>
        </table>
      </div>`;
    const d = await PD.api('/api/system/dashboard');
    document.getElementById('actBody').innerHTML = d.activities.map(a => `
      <tr><td>${PD.fmtDate(a.at)}</td><td><strong>${PD.escapeHtml(a.action)}</strong></td>
          <td>${PD.escapeHtml(a.target || '')}</td><td>${PD.escapeHtml(a.ip || '')}</td>
          <td>${a.success ? '<span class="badge-pd running">ok</span>' : '<span class="badge-pd crashed">fail</span>'}</td></tr>`).join('');
  },
};

/* ---------------------------------------------------------- */
/*  SETTINGS                                                  */
/* ---------------------------------------------------------- */
PD.Pages.settings = {
  title: 'Settings',
  async render(c) {
    c.innerHTML = `
      <div class="row g-3">
        <div class="col-12 col-md-6">
          <div class="card-pd">
            <h6 style="font-weight:700">Change Password</h6>
            <form id="pwForm">
              <div class="mb-2"><label class="form-label">Current</label><input type="password" class="form-control" id="pw_cur" required></div>
              <div class="mb-2"><label class="form-label">New (min 10)</label><input type="password" class="form-control" id="pw_new" minlength="10" required></div>
              <button class="btn-pd primary"><i class="bi bi-shield-lock"></i> Update</button>
            </form>
          </div>
        </div>
        <div class="col-12 col-md-6">
          <div class="card-pd">
            <h6 style="font-weight:700">Telegram Notifications</h6>
            <form id="tgForm">
              <div class="mb-2"><label class="form-label">Bot token</label><input class="form-control" id="tg_token" placeholder="123456:ABC…"></div>
              <div class="mb-2"><label class="form-label">Chat ID</label><input class="form-control" id="tg_chat" placeholder="123456789"></div>
              <button class="btn-pd primary"><i class="bi bi-save"></i> Save</button>
              <button type="button" class="btn-pd ghost" id="tgTest"><i class="bi bi-send"></i> Send test</button>
            </form>
          </div>
        </div>
      </div>`;
    document.getElementById('pwForm').onsubmit = async (e) => {
      e.preventDefault();
      try { await PD.api('/api/auth/change-password', { method: 'POST', body: {
        current_password: document.getElementById('pw_cur').value,
        new_password: document.getElementById('pw_new').value,
      }}); PD.toast('Password updated'); e.target.reset(); }
      catch (err) { PD.toast(err.message, 'error'); }
    };
    document.getElementById('tgForm').onsubmit = async (e) => {
      e.preventDefault();
      try { await PD.api('/api/notifications/telegram', { method: 'POST', body: {
        bot_token: document.getElementById('tg_token').value,
        chat_id: document.getElementById('tg_chat').value,
      }}); PD.toast('Saved'); }
      catch (err) { PD.toast(err.message, 'error'); }
    };
    document.getElementById('tgTest').onclick = async () => {
      try { const r = await PD.api('/api/notifications/telegram/test', { method: 'POST' }); PD.toast(r.message, r.ok ? 'ok' : 'error'); }
      catch (err) { PD.toast(err.message, 'error'); }
    };
  },
};
