// HTTP transport only. Session credentials never enter localStorage.
let token = '';
export function setToken(value) { token = value; }
export function hasToken() { return Boolean(token); }
export async function request(path, options = {}) {
  const headers = { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers };
  let body = options.body;
  if (body && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(body);
  }
  let response;
  try { response = await fetch(`/api/v1${path}`, { ...options, headers, body, credentials: 'omit' }); }
  catch { throw new Error('网络连接失败。请保留输入，恢复连接后再试。'); }
  if (!response.ok) {
    const data = await response.json();
    const error = new Error(data.error?.message || `请求失败 (${response.status})`);
    error.status = response.status;
    throw error;
  }
  if (response.status === 204) return null;
  return options.binary ? response.blob() : response.json();
}
