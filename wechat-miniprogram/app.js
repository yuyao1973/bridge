App({
  onLaunch() {
    if (!wx.cloud || typeof wx.cloud.init !== 'function') {
      this.globalData.useCloudBackend = false
      return
    }

    try {
      wx.cloud.init({
        env: 'cloud1-d3g942xe37289a824',
        traceUser: true
      })
    } catch (error) {
      // If cloud init fails in simulator, keep app bootable with local API fallback.
      this.globalData.useCloudBackend = false
    }
  },
  globalData: {
    // Cloud backend is preferred; keep local API for development fallback.
    cloudEnv: 'cloud1-d3g942xe37289a824',
    useCloudBackend: true,
    apiBaseUrl: 'http://127.0.0.1:8001',
    cloudApiBaseUrl: ''
  }
})
