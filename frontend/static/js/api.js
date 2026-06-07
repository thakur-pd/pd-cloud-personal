/* ============================================================
   PD Cloud Personal — API client
   ============================================================ */
window.PD = window.PD || {};

PD.getCookie = function (name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
};

PD.api = async function (path, opts = {}) {
  const headers = Object.assign(
    { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    opts.headers || {}
  );
  const csrf = PD.getCookie('csrf_token');
  if (csrf) headers['X-CSRF-Token'] = csrf;

  const res = await fetch(path, {
    method: opts.method || 'GET',
    headers,
    credentials: 'same-origin',
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });

  let payload;
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) payload = await res.json();
  else payload = await res.text();

  if (!res.ok) {
    const msg = (payload && payload.detail) ? payload.detail : (typeof payload === 'string' ? payload : 'Request failed');
    const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    err.status = res.status;
    err.payload = payload;
    throw err;
  }
  return payload;
};

PD.upload = async function (path, formData) {
  const headers = {};
  const csrf = PD.getCookie('csrf_token');
  if (csrf) headers['X-CSRF-Token'] = csrf;
  const res = await fetch(path, {
    method: 'POST',
    headers,
    credentials: 'same-origin',
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || 'Upload failed');
  }
  return await res.json();
};
