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

  openSettings() {
    wx.navigateTo({ url: '/pages/settings/settings' })
  }
})
