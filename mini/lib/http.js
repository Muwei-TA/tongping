// The only native transport adapter. Business authorization stays on the server.
const host = typeof wx !== 'undefined' ? wx : qq;
const config = require('./config');
const downloads = new Set();
function clearSession() {
  host.removeStorageSync('tp_session');
  downloads.forEach(path => host.getFileSystemManager().unlink({ filePath: path, fail() {} }));
  downloads.clear();
}
function headers() {
  const session = host.getStorageSync('tp_session');
  if (!session || session.expires_at * 1000 <= Date.now()) return {};
  return { Authorization: 'Bearer ' + session.token };
}
function api(path, method = 'GET', data) {
  return new Promise((resolve, reject) => host.request({
    url: config.apiBase + '/api/v1' + path, method, data, header: headers(), timeout: 15000,
    success(response) {
      if (response.statusCode >= 200 && response.statusCode < 300) return resolve(response.data);
      if (response.statusCode === 401) clearSession();
      reject(new Error(response.data && response.data.error ? response.data.error.message : '请求失败，请重新读取'));
    },
    fail() { reject(new Error('网络连接失败，请检查接口域名与网络；输入不会自动重试。')); }
  }));
}
function platformLogin() {
  return new Promise((resolve, reject) => host.login({
    success(result) { result.code ? resolve(result.code) : reject(new Error('未取得宿主登录凭证')); },
    fail() { reject(new Error('宿主登录未完成')); }
  })).then(code => api('/auth/code', 'POST', { provider: config.provider, code }));
}
function upload(club, filePath) {
  return new Promise((resolve, reject) => host.uploadFile({
    url: config.apiBase + '/api/v1/clubs/' + club + '/media', header: headers(), filePath, name: 'file',
    success(response) {
      try {
        const data = JSON.parse(response.data);
        if (response.statusCode !== 201) throw new Error(data.error ? data.error.message : '图片上传失败');
        resolve(data);
      } catch (error) { reject(error); }
    },
    fail() { reject(new Error('图片上传失败，请保留输入再试')); }
  }));
}
function image(id) {
  return new Promise((resolve, reject) => host.downloadFile({
    url: config.apiBase + '/api/v1/media/' + id, header: headers(),
    success(response) {
      if (response.statusCode !== 200) return reject(new Error('图片不可访问'));
      downloads.add(response.tempFilePath); resolve(response.tempFilePath);
    },
    fail() { reject(new Error('图片下载失败')); }
  }));
}
module.exports = { host, api, image, upload, platformLogin, clearSession };
