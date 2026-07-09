Page({
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
