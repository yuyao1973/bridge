const { APP_VERSION, getBuildTime } = require('../../utils/version')
const { loadSettings } = require('../../utils/settings')
const { onHoverEnter, onHoverLeave } = require('../../utils/hover')

Page({
  data: {
    appVersion: APP_VERSION,
    buildTime: '--',
    practicalProfile: '--',
    practicalProfileUpdated: false,
    hoverKey: ''
  },

  onHoverEnter,
  onHoverLeave,

  onLoad() {
    this.refreshMeta()
  },

  onShow() {
    this.refreshMeta(true)
  },

  getPracticalProfileText() {
    const settings = loadSettings()
    const mode = settings.scoring_mode || 'IMP'
    const vulnText = settings.respect_vulnerability ? '考虑局况' : '不按局况调整'
    const agg = Number(settings.game_aggressiveness || 0)
    const aggText = `激进度 ${agg >= 0 ? '+' : ''}${agg}`
    return `${mode} | ${vulnText} | ${aggText}`
  },

  refreshMeta(notifyIfChanged = false) {
    const profile = this.getPracticalProfileText()
    const changed = this.data.practicalProfile !== '--' && this.data.practicalProfile !== profile
    this.setData({
      practicalProfile: profile,
      buildTime: getBuildTime(),
      appVersion: APP_VERSION,
      practicalProfileUpdated: notifyIfChanged && changed
    })

    if (notifyIfChanged && changed) {
      wx.showToast({
        title: '实战参数已更新',
        icon: 'none',
        duration: 1200
      })
      setTimeout(() => {
        this.setData({ practicalProfileUpdated: false })
      }, 1400)
    }
  },

  startOpening() {
    wx.navigateTo({ url: '/pages/training/training?mode=opening' })
  },

  startResponse() {
    wx.navigateTo({ url: '/pages/training/training?mode=response' })
  },

  startOpenerRebid() {
    wx.navigateTo({ url: '/pages/training/training?mode=opener_rebid' })
  },

  startResponderRebid() {
    wx.navigateTo({ url: '/pages/training/training?mode=responder_rebid' })
  },

  exitAppWithCleanup() {
    wx.showModal({
      title: '退出确认',
      content: '将清除本地缓存（规则设置与统计等）并退出小程序，是否继续？',
      confirmText: '退出',
      cancelText: '取消',
      confirmColor: '#dc3545',
      success: (res) => {
        if (!res.confirm) {
          return
        }
        this.clearCacheAndExit()
      }
    })
  },

  clearCacheAndExit() {
    wx.showLoading({ title: '正在退出...' })
    wx.clearStorage({
      success: () => {
        wx.hideLoading()
        this.exitMiniProgramSafely()
      },
      fail: () => {
        wx.hideLoading()
        this.exitMiniProgramSafely()
      }
    })
  },

  exitMiniProgramSafely() {
    if (typeof wx.exitMiniProgram === 'function') {
      wx.exitMiniProgram({
        fail: () => {
          wx.showToast({
            title: '当前环境不支持直接退出',
            icon: 'none',
            duration: 1600
          })
          wx.reLaunch({ url: '/pages/index/index' })
        }
      })
      return
    }

    wx.showToast({
      title: '已清缓存，请手动关闭小程序',
      icon: 'none',
      duration: 1800
    })
    wx.reLaunch({ url: '/pages/index/index' })
  },

  openSettings() {
    wx.navigateTo({ url: '/pages/settings/settings' })
  }
})
