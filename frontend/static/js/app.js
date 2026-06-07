/* ============================================================
   PD Cloud Personal — Application bootstrap & router
   ============================================================ */
(function () {
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => document.querySelectorAll(s);

  // ----- Theme -----
  const themeKey = 'pdcloud_theme';
  const setTheme = (t) => {
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem(themeKey, t);
    const icon = $('#themeToggle i');
    if (icon) icon.className = t === 'dark' ? 'bi bi-sun' : 'bi bi-moon-stars';
  };
  setTheme(localStorage.getItem(themeKey) || 'light');

  // ----- Auth flow -----
  async function checkAuth() {
    try { return await PD.api('/api/auth/me'); }
    catch { return null; }
  }

  function showLogin() {
    $('#loginScreen').style.display = 'grid';
    $('#appLayout').style.display = 'none';
  }
  function showApp(user) {
    $('#loginScreen').style.display = 'none';
    $('#appLayout').style.display = 'grid';
    $('#currentUser').textContent = user.username;
  }

  // ----- Router -----
  let cleanup = null;
  async function navigate(name) {
    const page = PD.Pages[name]; if (!page) return;
    if (cleanup) { try { cleanup(); } catch {} cleanup = null; }
    $('#pageTitle').textContent = page.title;
    $$('.sidebar .nav-link').forEach(n => n.classList.toggle('active', n.dataset.page === name));
    const container = $('#content');
    container.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-muted)"><i class="bi bi-arrow-clockwise" style="font-size:24px"></i><div style="margin-top:8px">Loading…</div></div>';
    try {
      cleanup = await page.render(container) || null;
    } catch (err) {
      container.innerHTML = `<div class="card-pd" style="border-left:4px solid #ef4444"><strong>Error:</strong> ${PD.escapeHtml(err.message)}</div>`;
    }
    if (window.innerWidth < 900) $('#sidebar').classList.remove('open');
    location.hash = '#' + name;
  }

  // ----- Event wiring -----
  function wire() {
    $('#themeToggle').onclick = () => setTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    $('#menuToggle').onclick = () => $('#sidebar').classList.toggle('open');
    $$('.sidebar .nav-link[data-page]').forEach(n => n.onclick = () => navigate(n.dataset.page));
    $('#logoutBtn').onclick = async () => {
      try { await PD.api('/api/auth/logout', { method: 'POST' }); } catch {}
      location.reload();
    };
    // Close modal on backdrop click
    $('#modal').addEventListener('click', (e) => { if (e.target.id === 'modal') PD.closeModal(); });
  }

  $('#loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const err = $('#loginError'); err.style.display = 'none';
    try {
      await PD.api('/api/auth/login', { method: 'POST', body: {
        username: $('#loginUser').value, password: $('#loginPass').value,
      }});
      const me = await checkAuth();
      if (me) { showApp(me); wire(); navigate('dashboard'); }
    } catch (e2) {
      err.textContent = e2.message || 'Login failed';
      err.style.display = 'block';
    }
  });

  // ----- Boot -----
  (async () => {
    const me = await checkAuth();
    if (me) {
      showApp(me); wire();
      const initial = (location.hash || '#dashboard').slice(1);
      navigate(PD.Pages[initial] ? initial : 'dashboard');
    } else {
      showLogin();
    }
  })();
})();
