const STORAGE_KEY = 'bridge_rule_settings'

const defaultSettings = {
  opening_min_hcp: 12,
  one_nt_min: 15,
  one_nt_max: 17,
  strong_two_club_min: 22,
  weak_two_enabled: true,
  august_2nt_enabled: true,
  stayman_enabled: true,
  transfers_enabled: true,
  jacoby_2nt_enabled: true,
  bergen_raises_enabled: true,
  two_over_one_min_hcp: 12,
  forcing_nt_min_hcp: 6,
  forcing_nt_max_hcp: 11,
  responder_simple_raise_max: 9,
  responder_limit_raise_min: 10,
  responder_limit_raise_max: 12,
  responder_bergen_weak_max: 9,
  splinter_enabled: true,
  responder_splinter_min_hcp: 11,
  responder_splinter_max_hcp: 15,
  forcing_nt_label: '半逼叫',
  scoring_mode: 'IMP',
  respect_vulnerability: true,
  game_aggressiveness: 0
}

function loadSettings() {
  return Object.assign({}, defaultSettings, wx.getStorageSync(STORAGE_KEY) || {})
}

function saveSettings(settings) {
  wx.setStorageSync(STORAGE_KEY, Object.assign({}, defaultSettings, settings))
}

function resetSettings() {
  wx.setStorageSync(STORAGE_KEY, defaultSettings)
  return Object.assign({}, defaultSettings)
}

module.exports = {
  defaultSettings,
  loadSettings,
  saveSettings,
  resetSettings
}
