const { host, clearSession } = require('./lib/http');
App({
  globalData: { club: '', profile: null },
  onLaunch() {
    const session = host.getStorageSync('tp_session');
    if (session && session.expires_at * 1000 <= Date.now()) clearSession();
  }
});
