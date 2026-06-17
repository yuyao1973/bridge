const { loadSettings, saveSettings, resetSettings } = require('../../utils/settings')

Page({
  data: {
    settings: {},
    oneNtRanges: ['14-16', '15-17', '16-18'],
    oneNtIndex: 1,
    openingMinOptions: [11, 12, 13],
    openingMinIndex: 1,
    strongTwoOptions: [21, 22, 23],
    strongTwoIndex: 1,
    twoOverOneOptions: [11, 12, 13],
    twoOverOneIndex: 1,
    forcingNtRanges: ['5-11', '6-10', '6-11', '7-11', '6-12'],
    forcingNtIndex: 2,
    simpleRaiseMaxOptions: [8, 9, 10],
    simpleRaiseMaxIndex: 1,
    limitRaiseRanges: ['10-12', '11-12'],
    limitRaiseIndex: 0,
    bergenWeakMaxOptions: [8, 9, 10],
    bergenWeakMaxIndex: 1,
    negativeDoubleMinOptions: [6, 7, 8],
    negativeDoubleMinIndex: 0,
    forcingNtLabels: ['半逼叫', '逼叫一轮'],
    forcingNtLabelIndex: 0,
    scoringModes: ['IMP', 'MP'],
    scoringModeIndex: 0,
    aggressivenessOptions: [-1, 0, 1],
    aggressivenessIndex: 1
  },

  onLoad() {
    this.load()
  },

  load() {
    const settings = loadSettings()
    const oneNtValue = `${settings.one_nt_min}-${settings.one_nt_max}`
    const forcingNtValue = `${settings.forcing_nt_min_hcp}-${settings.forcing_nt_max_hcp}`
    const limitRaiseValue = `${settings.responder_limit_raise_min ?? 10}-${settings.responder_limit_raise_max ?? 12}`
    this.setData({
      settings,
      oneNtIndex: Math.max(0, this.data.oneNtRanges.indexOf(oneNtValue)),
      openingMinIndex: Math.max(0, this.data.openingMinOptions.indexOf(settings.opening_min_hcp)),
      strongTwoIndex: Math.max(0, this.data.strongTwoOptions.indexOf(settings.strong_two_club_min)),
      twoOverOneIndex: Math.max(0, this.data.twoOverOneOptions.indexOf(settings.two_over_one_min_hcp)),
      forcingNtIndex: Math.max(0, this.data.forcingNtRanges.indexOf(forcingNtValue)),
      simpleRaiseMaxIndex: Math.max(0, this.data.simpleRaiseMaxOptions.indexOf(settings.responder_simple_raise_max ?? 9)),
      limitRaiseIndex: Math.max(0, this.data.limitRaiseRanges.indexOf(limitRaiseValue)),
      bergenWeakMaxIndex: Math.max(0, this.data.bergenWeakMaxOptions.indexOf(settings.responder_bergen_weak_max ?? 9)),
      negativeDoubleMinIndex: Math.max(0, this.data.negativeDoubleMinOptions.indexOf(settings.negative_double_min_hcp ?? 6)),
      forcingNtLabelIndex: Math.max(0, this.data.forcingNtLabels.indexOf(settings.forcing_nt_label)),
      scoringModeIndex: Math.max(0, this.data.scoringModes.indexOf(settings.scoring_mode || 'IMP')),
      aggressivenessIndex: Math.max(0, this.data.aggressivenessOptions.indexOf(settings.game_aggressiveness ?? 0))
    })
  },

  updateSettings(patch) {
    this.setData({ settings: Object.assign({}, this.data.settings, patch) })
  },

  onOneNtChange(event) {
    const index = Number(event.detail.value)
    const [min, max] = this.data.oneNtRanges[index].split('-').map(Number)
    this.setData({ oneNtIndex: index })
    this.updateSettings({ one_nt_min: min, one_nt_max: max })
  },

  onOpeningMinChange(event) {
    const index = Number(event.detail.value)
    this.setData({ openingMinIndex: index })
    this.updateSettings({ opening_min_hcp: this.data.openingMinOptions[index] })
  },

  onStrongTwoChange(event) {
    const index = Number(event.detail.value)
    this.setData({ strongTwoIndex: index })
    this.updateSettings({ strong_two_club_min: this.data.strongTwoOptions[index] })
  },

  onTwoOverOneChange(event) {
    const index = Number(event.detail.value)
    this.setData({ twoOverOneIndex: index })
    this.updateSettings({ two_over_one_min_hcp: this.data.twoOverOneOptions[index] })
  },

  onForcingNtRangeChange(event) {
    const index = Number(event.detail.value)
    const [min, max] = this.data.forcingNtRanges[index].split('-').map(Number)
    this.setData({ forcingNtIndex: index })
    this.updateSettings({ forcing_nt_min_hcp: min, forcing_nt_max_hcp: max })
  },

  onSimpleRaiseMaxChange(event) {
    const index = Number(event.detail.value)
    this.setData({ simpleRaiseMaxIndex: index })
    this.updateSettings({ responder_simple_raise_max: this.data.simpleRaiseMaxOptions[index] })
  },

  onLimitRaiseRangeChange(event) {
    const index = Number(event.detail.value)
    const [min, max] = this.data.limitRaiseRanges[index].split('-').map(Number)
    this.setData({ limitRaiseIndex: index })
    this.updateSettings({ responder_limit_raise_min: min, responder_limit_raise_max: max })
  },

  onBergenWeakMaxChange(event) {
    const index = Number(event.detail.value)
    this.setData({ bergenWeakMaxIndex: index })
    this.updateSettings({ responder_bergen_weak_max: this.data.bergenWeakMaxOptions[index] })
  },

  onNegativeDoubleMinChange(event) {
    const index = Number(event.detail.value)
    this.setData({ negativeDoubleMinIndex: index })
    this.updateSettings({ negative_double_min_hcp: this.data.negativeDoubleMinOptions[index] })
  },

  onForcingNtLabelChange(event) {
    const index = Number(event.detail.value)
    this.setData({ forcingNtLabelIndex: index })
    this.updateSettings({ forcing_nt_label: this.data.forcingNtLabels[index] })
  },

  onScoringModeChange(event) {
    const index = Number(event.detail.value)
    this.setData({ scoringModeIndex: index })
    this.updateSettings({ scoring_mode: this.data.scoringModes[index] })
  },

  onAggressivenessChange(event) {
    const index = Number(event.detail.value)
    this.setData({ aggressivenessIndex: index })
    this.updateSettings({ game_aggressiveness: this.data.aggressivenessOptions[index] })
  },

  onSwitchChange(event) {
    const key = event.currentTarget.dataset.key
    this.updateSettings({ [key]: event.detail.value })
  },

  save() {
    saveSettings(this.data.settings)
    wx.showToast({ title: '已保存', icon: 'success' })
  },

  reset() {
    resetSettings()
    this.load()
    wx.showToast({ title: '已恢复默认', icon: 'success' })
  }
})
