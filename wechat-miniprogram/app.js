function loadLocalConfig() {
  try {
    return require('./config/local.js')
  } catch (error) {
    return {
      cloudEnv: '',
      useCloudBackend: false,
      cloudApiBaseUrl: ''
    }
  }
}

const localConfig = loadLocalConfig()
const cloudEnv = String(localConfig.cloudEnv || '').trim()
const useCloudBackend = Boolean(localConfig.useCloudBackend && cloudEnv)

App({
  onLaunch() {
    if (!useCloudBackend || !wx.cloud || typeof wx.cloud.init !== 'function') {
      this.globalData.useCloudBackend = false
      return
    }

    try {
      wx.cloud.init({
        env: cloudEnv,
        traceUser: true
      })
      this.globalData.useCloudBackend = true
    } catch (error) {
      // If cloud init fails in simulator, keep app bootable with local API fallback.
      this.globalData.useCloudBackend = false
    }
  },
  globalData: {
    cloudEnv,
    useCloudBackend,
    apiBaseUrl: 'http://127.0.0.1:8001',
    cloudApiBaseUrl: String(localConfig.cloudApiBaseUrl || '').trim()
  }
})
