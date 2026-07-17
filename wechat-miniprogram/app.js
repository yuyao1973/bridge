App({
  onLaunch() {
    // 默认使用本地离线引擎，无需云开发或 API 后端。
    this.globalData.useOfflineEngine = true
    this.globalData.useCloudBackend = false
  },
  globalData: {
    useOfflineEngine: true,
    cloudEnv: '',
    useCloudBackend: false,
    apiBaseUrl: 'http://127.0.0.1:8001',
    cloudApiBaseUrl: ''
  }
})
