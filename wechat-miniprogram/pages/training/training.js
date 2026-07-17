const { loadSettings } = require('../../utils/settings')

function getApi() {
  return require('../../utils/api')
}

const SCORE_STATS_KEY = 'bridge_score_stats'
const OPENER_CATEGORY_OPTIONS = ['一阶定约', '强开叫', '阻击叫']
const OPENER_BIDS_BY_CATEGORY = {
  '一阶定约': ['随机', '1♣', '1♦', '1♥', '1♠', '1NT'],
  '强开叫': ['2♣', '2NT'],
  '阻击叫': ['随机', '2♦', '2♥', '2♠', '3♣', '3♦', '3♥', '3♠', '4♣', '4♦', '4♥', '4♠', '5♣', '5♦']
}

const STRAIN_ORDER = { '♣': 1, '♦': 2, '♥': 3, '♠': 4, 'NT': 5 }
const RESPONSE_BIDS = ['Pass', 'X', '1♦', '1♥', '1♠', '1NT', '2♣', '2♦', '2♥', '2♠', '2NT', '3♣', '3♦', '3♥', '3♠', '3NT', '4♥', '4♠', '5♣', '5♦']
const REBID_BIDS = ['Pass', '1♣', '1♦', '1♥', '1♠', '1NT', '2♣', '2♦', '2♥', '2♠', '2NT', '3♣', '3♦', '3♥', '3♠', '3NT', '4♣', '4♦', '4♥', '4♠', '4NT', '5♣', '5♦', '5♥', '5♠', '5NT']

function parseContractBid(bid) {
  if (!bid || bid.length < 2 || !/^\d/.test(bid)) return null
  const level = Number(bid[0])
  const strain = bid.slice(1)
  if (!(strain in STRAIN_ORDER)) return null
  return { level, strain }
}

function isLegalBidAfter(prevBid, bid) {
  if (bid === 'Pass') return true
  const prev = parseContractBid(prevBid)
  const next = parseContractBid(bid)
  if (!prev || !next) return false
  if (next.level > prev.level) return true
  if (next.level === prev.level) return STRAIN_ORDER[next.strain] > STRAIN_ORDER[prev.strain]
  return false
}

function legalResponseBidsForOpener(openerBid) {
  if (!openerBid || openerBid === '随机') return ['随机']
  return ['随机', ...RESPONSE_BIDS.filter(b => isLegalBidAfter(openerBid, b))]
}

function legalRebidBidsForResponse(responseBid) {
  if (!responseBid || responseBid === '随机') return ['随机']
  return ['随机', ...REBID_BIDS.filter(b => isLegalBidAfter(responseBid, b))]
}

Page({
  data: {
    mode: 'opening',
    modeText: '开叫训练',
    openerCategoryOptions: OPENER_CATEGORY_OPTIONS,
    openerCategoryIndex: 0,
    openerOptions: ['随机', '1♣', '1♦', '1♥', '1♠', '1NT'],
    openerIndex: 0,
    responseBidOptions: ['随机'],
    responseBidIndex: 0,
    openerRebidBidOptions: ['随机'],
    openerRebidBidIndex: 0,
    question: null,
    bidItems: [],
    bidGridClass: 'cols-4',
    selectedBid: 'Pass',
    selectedBidLegal: true,
    submitted: false,
    answer: null,
    feedbackTitle: '',
    loading: false,
    error: '',
    appVersion: '--',
    buildTime: '--',
    practicalProfile: '--',
    practicalProfileUpdated: false,
    total: 0,
    correct: 0,
    rate: '0.0',
    allTotal: 0,
    allCorrect: 0,
    allRate: '0.0'
  },

  onLoad(options) {
    const mode = ['opening', 'response', 'opener_rebid', 'responder_rebid'].indexOf(options.mode) >= 0 ? options.mode : 'opening'
    const openerCategoryOptions = this.getOpenerCategoryOptions(mode)
    const openerCategoryIndex = 0
    const openerOptions = this.getOpenerOptions(mode, openerCategoryOptions[openerCategoryIndex])
    const stats = this.getStoredStats()
    const modeStats = stats.byMode[mode] || { total: 0, correct: 0 }
    const allRate = stats.total ? (stats.correct / stats.total * 100).toFixed(1) : '0.0'
    const modeRate = modeStats.total ? (modeStats.correct / modeStats.total * 100).toFixed(1) : '0.0'
    this._loadToken = 0
    this.setData({
      mode,
      modeText: this.getModeText(mode),
      openerCategoryOptions,
      openerCategoryIndex,
      openerOptions,
      openerIndex: 0,
      responseBidOptions: ['随机'],
      responseBidIndex: 0,
      openerRebidBidOptions: ['随机'],
      openerRebidBidIndex: 0,
      total: modeStats.total,
      correct: modeStats.correct,
      rate: modeRate,
      allTotal: stats.total,
      allCorrect: stats.correct,
      allRate
    })
    this.refreshPracticalProfile()
    this.loadQuestion()
  },

  onShow() {
    this.refreshPracticalProfile(true)
    // Do not auto-reload questions here: onLoad already loads once,
    // and re-entering would re-trigger heavy search on WeChat.
  },

  loadQuestion() {
    const token = (this._loadToken || 0) + 1
    this._loadToken = token
    this.setData({ loading: true, error: '', submitted: false, answer: null, feedbackTitle: '', selectedBid: 'Pass' })

    const opener = this.data.openerOptions[this.data.openerIndex] || '随机'
    const openerCategory = this.data.openerCategoryOptions[this.data.openerCategoryIndex] || null
    const responseBid = this.data.responseBidOptions[this.data.responseBidIndex] || '随机'
    const openerRebidBid = this.data.openerRebidBidOptions[this.data.openerRebidBidIndex] || '随机'
    const payload = {
      mode: this.data.mode,
      opener_bid: opener === '随机' ? null : opener,
      opener_category: this.data.mode === 'opening' ? null : openerCategory,
      response_bid: responseBid === '随机' ? null : responseBid,
      opener_rebid_bid: openerRebidBid === '随机' ? null : openerRebidBid,
      settings: loadSettings()
    }

    getApi().createQuestion(payload).then((question) => {
      if (token !== this._loadToken) {
        return
      }
      const bidItems = question.choices.map((bid) => ({
        bid,
        legal: question.legal_choices.indexOf(bid) >= 0,
        strainClass: this.getBidStrainClass(bid)
      }))
      const auctionBids = this.parseAuctionBids(question.auction)
      this.setData({
        question,
        bidItems,
        auctionBids,
        bidGridClass: this.getBidGridClass(bidItems.length),
        selectedBidLegal: question.legal_choices.indexOf('Pass') >= 0,
        appVersion: question.app_version || '--',
        buildTime: question.build_time || '--',
        loading: false
      })
    }).catch((error) => {
      if (token !== this._loadToken) {
        return
      }
      this.setData({ loading: false, error: `出题失败：${error.message || error.errMsg || error}` })
    })
  },

  getPracticalProfileText() {
    const settings = loadSettings()
    const mode = settings.scoring_mode || 'IMP'
    const vulnText = settings.respect_vulnerability ? '考虑局况' : '不按局况调整'
    const agg = Number(settings.game_aggressiveness || 0)
    const aggText = `激进度 ${agg >= 0 ? '+' : ''}${agg}`
    return `${mode} | ${vulnText} | ${aggText}`
  },

  refreshPracticalProfile(notifyIfChanged = false) {
    const profile = this.getPracticalProfileText()
    const changed = this.data.practicalProfile !== '--' && this.data.practicalProfile !== profile
    this.setData({
      practicalProfile: profile,
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

  getStoredStats() {
    const fallback = {
      total: 0,
      correct: 0,
      byMode: {
        opening: { total: 0, correct: 0 },
        response: { total: 0, correct: 0 },
        opener_rebid: { total: 0, correct: 0 },
        responder_rebid: { total: 0, correct: 0 }
      }
    }
    try {
      const stats = wx.getStorageSync(SCORE_STATS_KEY)
      if (!stats || typeof stats !== 'object') {
        return fallback
      }
      const byMode = stats.byMode || {}
      return {
        total: Number(stats.total) || 0,
        correct: Number(stats.correct) || 0,
        byMode: {
          opening: byMode.opening || { total: 0, correct: 0 },
          response: byMode.response || { total: 0, correct: 0 },
          opener_rebid: byMode.opener_rebid || { total: 0, correct: 0 },
          responder_rebid: byMode.responder_rebid || { total: 0, correct: 0 }
        }
      }
    } catch (e) {
      return fallback
    }
  },

  saveStoredStats(stats) {
    try {
      wx.setStorageSync(SCORE_STATS_KEY, stats)
    } catch (e) {
      // Ignore local storage write failures on older devices.
    }
  },

  showScoreStats() {
    const modeText = this.getModeText(this.data.mode)
    wx.showModal({
      title: '统计分数',
      content: [
        `当前模式（${modeText}）`,
        `答题：${this.data.total} 题`,
        `正确：${this.data.correct} 题`,
        `正确率：${this.data.rate}%`,
        '',
        '全部模式累计',
        `答题：${this.data.allTotal} 题`,
        `正确：${this.data.allCorrect} 题`,
        `正确率：${this.data.allRate}%`
      ].join('\n'),
      showCancel: false,
      confirmText: '知道了',
      confirmColor: '#198754'
    })
  },

  getEmptyStats() {
    return {
      total: 0,
      correct: 0,
      byMode: {
        opening: { total: 0, correct: 0 },
        response: { total: 0, correct: 0 },
        opener_rebid: { total: 0, correct: 0 },
        responder_rebid: { total: 0, correct: 0 }
      }
    }
  },

  clearScoreStats() {
    wx.showModal({
      title: '确认清空统计',
      content: '将清空当前模式与全部模式的累计分数统计，是否继续？',
      confirmText: '继续',
      cancelText: '取消',
      confirmColor: '#dc3545',
      success: (firstRes) => {
        if (!firstRes.confirm) {
          return
        }
        wx.showModal({
          title: '二次确认',
          content: '此操作不可恢复，确认清空全部统计吗？',
          confirmText: '确认清空',
          cancelText: '返回',
          confirmColor: '#dc3545',
          success: (secondRes) => {
            if (!secondRes.confirm) {
              return
            }
            const empty = this.getEmptyStats()
            this.saveStoredStats(empty)
            this.setData({
              total: 0,
              correct: 0,
              rate: '0.0',
              allTotal: 0,
              allCorrect: 0,
              allRate: '0.0'
            })
            wx.showToast({
              title: '统计已清空',
              icon: 'success',
              duration: 1500
            })
          }
        })
      }
    })
  },

  getModeText(mode) {
    if (mode === 'response') {
      return '应叫训练'
    }
    if (mode === 'opener_rebid') {
      return '开叫者再叫训练'
    }
    if (mode === 'responder_rebid') {
      return '应叫者第二次应叫训练'
    }
    return '开叫训练'
  },

  onOpenerChange(event) {
    const openerIndex = Number(event.detail.value)
    const openerBid = this.data.openerOptions[openerIndex]
    const responseBidOptions = legalResponseBidsForOpener(openerBid)
    this.setData({
      openerIndex,
      responseBidOptions,
      responseBidIndex: 0,
      openerRebidBidOptions: ['随机'],
      openerRebidBidIndex: 0,
    })
    this.loadQuestion()
  },

  onOpenerCategoryChange(event) {
    const openerCategoryIndex = Number(event.detail.value)
    const category = this.data.openerCategoryOptions[openerCategoryIndex]
    this.setData({
      openerCategoryIndex,
      openerOptions: this.getOpenerOptions(this.data.mode, category),
      openerIndex: 0,
      responseBidOptions: ['随机'],
      responseBidIndex: 0,
      openerRebidBidOptions: ['随机'],
      openerRebidBidIndex: 0,
    })
    this.loadQuestion()
  },

  onResponseBidChange(event) {
    const responseBidIndex = Number(event.detail.value)
    const responseBid = this.data.responseBidOptions[responseBidIndex]
    const openerRebidBidOptions = legalRebidBidsForResponse(responseBid)
    this.setData({
      responseBidIndex,
      openerRebidBidOptions,
      openerRebidBidIndex: 0,
    })
    this.loadQuestion()
  },

  onOpenerRebidBidChange(event) {
    this.setData({ openerRebidBidIndex: Number(event.detail.value) })
    this.loadQuestion()
  },

  getOpenerCategoryOptions(mode) {
    if (mode === 'response' || mode === 'opener_rebid' || mode === 'responder_rebid') {
      return OPENER_CATEGORY_OPTIONS
    }
    return ['一阶定约']
  },

  getOpenerOptions(mode, category) {
    if (mode === 'response' || mode === 'opener_rebid' || mode === 'responder_rebid') {
      return OPENER_BIDS_BY_CATEGORY[category] || OPENER_BIDS_BY_CATEGORY['一阶定约']
    }
    return ['随机']
  },

  selectBid(event) {
    if (this.data.submitted) {
      return
    }
    const selectedBid = event.currentTarget.dataset.bid
    const selectedBidLegal = this.data.question.legal_choices.indexOf(selectedBid) >= 0
    this.setData({ selectedBid, selectedBidLegal })
  },

  getBidGridClass(count) {
    if (count >= 17) {
      return 'cols-6'
    }
    if (count >= 13) {
      return 'cols-5'
    }
    return 'cols-4'
  },

  getBidStrainClass(bid) {
    if (bid.indexOf('♣') >= 0) {
      return 'bid-club'
    }
    if (bid.indexOf('♦') >= 0) {
      return 'bid-diamond'
    }
    if (bid.indexOf('♥') >= 0) {
      return 'bid-heart'
    }
    if (bid.indexOf('♠') >= 0) {
      return 'bid-spade'
    }
    if (bid.indexOf('NT') >= 0) {
      return 'bid-nt'
    }
    return 'bid-pass'
  },

  parseAuctionBids(auctionStr) {
    const parts = auctionStr.split(/[-\s]+/)
    const bids = []
    let bidIndex = 0
    for (const part of parts) {
      const cleaned = part.trim()
      if (cleaned && cleaned !== 'Pass' && cleaned !== '?' && !cleaned.includes('叫')) {
        if (cleaned.match(/^\d[♣♦♥♠]/) || cleaned.match(/^\d\s*NT$/)) {
          bids.push({
            bid: cleaned,
            strainClass: this.getBidStrainClass(cleaned),
            position: bidIndex
          })
          bidIndex++
        }
      }
    }
    return bids
  },

  parseContract(bid) {
    const match = String(bid || '').trim().match(/^(\d)(♣|♦|♥|♠|NT)$/)
    if (!match) {
      return null
    }
    return {
      level: Number(match[1]),
      strain: match[2]
    }
  },

  getContextualRebidMeaning(bid, auctionBids) {
    const opening = this.parseContract(auctionBids[0] && auctionBids[0].bid)
    const response = this.parseContract(auctionBids[1] && auctionBids[1].bid)
    const rebid = this.parseContract(bid)
    if (!rebid || !opening || !response) {
      return '再叫：根据前序叫牌继续描述牌力与牌型'
    }

    const seq = `${auctionBids[0].bid}-${auctionBids[1].bid}`
    if (opening.strain === 'NT') {
      const responseBid = auctionBids[1] && auctionBids[1].bid
      if (responseBid === '2♣') {
        if (bid === '2♦') {
          return `在 ${seq} 后再叫 2♦：Stayman 否定叫，通常表示没有四张高花。`
        }
        if (bid === '2♥') {
          return `在 ${seq} 后再叫 2♥：Stayman 应答，通常表示有四张红心。`
        }
        if (bid === '2♠') {
          return `在 ${seq} 后再叫 2♠：Stayman 应答，通常表示有四张黑桃。`
        }
      }
      if (responseBid === '2♦') {
        if (bid === '2♥') {
          return `在 ${seq} 后再叫 2♥：接受红心转移，通常为标准完成转移。`
        }
      }
      if (responseBid === '2♥') {
        if (bid === '2♠') {
          return `在 ${seq} 后再叫 2♠：接受黑桃转移，通常为标准完成转移。`
        }
      }
      if (responseBid === '2NT' && bid === '3NT') {
        return `在 ${seq} 后再叫 3NT：接受邀局，确认无将进局。`
      }
      if (rebid.strain === 'NT') {
        return `在 ${seq} 后再叫 ${bid}：1NT 体系后续中的无将牌力描述或进程推进。`
      }
      return `在 ${seq} 后再叫 ${bid}：1NT 开叫后的约定叫进程（如 Stayman/转移后的应答）。`
    }

    if (rebid.strain === 'NT') {
      if (rebid.level === 1) {
        return `在 ${seq} 后再叫 1NT：约 12-14 HCP，均型最低限。`
      }
      if (rebid.level === 2) {
        return `在 ${seq} 后再叫 2NT：约 18-19 HCP，均型强牌。`
      }
      return `在 ${seq} 后再叫 ${bid}：通常显示均型进局或更强牌力。`
    }

    if (rebid.strain === opening.strain) {
      return `在 ${seq} 后重复开叫花色 ${bid}：通常 12-15 HCP，显示 6+ 张原开叫花色。`
    }
    if (rebid.strain === response.strain) {
      return `在 ${seq} 后再叫 ${bid} 支持应叫花色：通常 13+ HCP，约 3-4 张支持。`
    }
    return `在 ${seq} 后再叫新花 ${bid}：通常 12+ HCP，约 4+ 张该花色，用于描述第二套。`
  },

  getContextualResponseMeaning(bid, auctionBids) {
    const opening = this.parseContract(auctionBids[0] && auctionBids[0].bid)
    const response = this.parseContract(bid)
    if (!opening || !response) {
      return null
    }

    const seq = `${auctionBids[0].bid}-${bid}`
    if (opening.strain === 'NT') {
      if (bid === '2♣') {
        return `在 ${seq} 中，2♣ 是 Stayman，通常询问开叫方是否有四张高花。`
      }
      if (bid === '2♦') {
        return `在 ${seq} 中，2♦ 是红心转移，通常要求同伴转叫 2♥。`
      }
      if (bid === '2♥') {
        return `在 ${seq} 中，2♥ 是黑桃转移，通常要求同伴转叫 2♠。`
      }
      if (bid === '2NT') {
        return `在 ${seq} 中，2NT 通常是无将邀局，约 8-9 HCP。`
      }
      if (bid === '3NT') {
        return `在 ${seq} 中，3NT 通常是直接无将进局。`
      }
      return `在 ${seq} 中，这是 1NT 体系下的应叫，用于处理高花配合与定约层级。`
    }

    if (opening.strain === '♥' || opening.strain === '♠') {
      if (response.strain === opening.strain) {
        return `在 ${seq} 中，应叫同花通常表示支持同伴高花并按牌力分层。`
      }
      if (bid === '1NT') {
        return `在 ${seq} 中，1NT 通常是高花开叫后的半逼叫/逼叫一轮应叫。`
      }
    }

    if (opening.strain === '♣' || opening.strain === '♦') {
      if (response.level === 1 && (response.strain === '♥' || response.strain === '♠')) {
        return `在 ${seq} 中，一阶高花应叫通常显示 4 张高花并争取高花定约。`
      }
    }

    return null
  },

  getContextualResponder2Meaning(bid, auctionBids) {
    const opening = this.parseContract(auctionBids[0] && auctionBids[0].bid)
    const response = this.parseContract(auctionBids[1] && auctionBids[1].bid)
    const openerRebid = this.parseContract(auctionBids[2] && auctionBids[2].bid)
    const responder2 = this.parseContract(bid)
    if (!responder2 || !opening || !response || !openerRebid) {
      return '第二次应叫：根据前序叫牌选择邀局、进局或继续描述牌型'
    }

    const seq = `${auctionBids[0].bid}-${auctionBids[1].bid}-${auctionBids[2].bid}`
    if (opening.strain === 'NT') {
      const responseBid = auctionBids[1] && auctionBids[1].bid
      const openerRebidBid = auctionBids[2] && auctionBids[2].bid

      if (responseBid === '2♦' && openerRebidBid === '2♥') {
        if (bid === '2NT') {
          return `在 ${seq} 后再叫 2NT：转移完成后邀局，通常约 8-9 HCP。`
        }
        if (bid === '3NT') {
          return `在 ${seq} 后再叫 3NT：转移完成后直接无将进局。`
        }
        if (responder2.strain === '♥') {
          return `在 ${seq} 后再叫 ${bid}：红心转移完成后继续描述红心长度与牌力。`
        }
      }

      if (responseBid === '2♥' && openerRebidBid === '2♠') {
        if (bid === '2NT') {
          return `在 ${seq} 后再叫 2NT：转移完成后邀局，通常约 8-9 HCP。`
        }
        if (bid === '3NT') {
          return `在 ${seq} 后再叫 3NT：转移完成后直接无将进局。`
        }
        if (responder2.strain === '♠') {
          return `在 ${seq} 后再叫 ${bid}：黑桃转移完成后继续描述黑桃长度与牌力。`
        }
      }

      if (responseBid === '2♣') {
        if (bid === '2NT') {
          return `在 ${seq} 后再叫 2NT：Stayman 后无将邀局。`
        }
        if (bid === '3NT') {
          return `在 ${seq} 后再叫 3NT：Stayman 后确认无将进局。`
        }
        if (responder2.strain === '♥' || responder2.strain === '♠') {
          return `在 ${seq} 后再叫 ${bid}：Stayman 后确认高花配合并推进定约层级。`
        }
      }

      if (responder2.strain === 'NT') {
        return `在 ${seq} 后再叫 ${bid}：1NT 体系后续中以无将邀局/进局为主线。`
      }
      return `在 ${seq} 后再叫 ${bid}：1NT 开叫后续的结构化再叫，用于确认配合与定约层级。`
    }

    if (responder2.strain === 'NT') {
      if (openerRebid.strain === 'NT') {
        if (responder2.level === 2) {
          return `在 ${seq} 后应叫者再叫 2NT：约 10-12 HCP，邀请进局。`
        }
        if (responder2.level === 3) {
          return `在 ${seq} 后应叫者再叫 3NT：约 13+ HCP，确认无将进局。`
        }
      }
      return `在 ${seq} 后应叫者再叫 ${bid}：通常显示均型并推进到邀局/进局层级。`
    }

    if (responder2.strain === openerRebid.strain) {
      return `在 ${seq} 后应叫者再叫 ${bid} 支持开叫者再叫花色：通常 10+ HCP，约 3+ 张支持。`
    }
    if (responder2.strain === response.strain) {
      return `在 ${seq} 后应叫者重复原应叫花色 ${bid}：通常 10+ HCP，约 6+ 张该花色。`
    }
    if (responder2.strain === opening.strain) {
      return `在 ${seq} 后应叫者回到开叫花色 ${bid}：通常表示补充支持并竞争/邀局。`
    }
    return `在 ${seq} 后应叫者再叫新花 ${bid}：通常 10+ HCP，约 4+ 张该花色，继续描述牌型。`
  },

  getBidMeaning(bid, bidPosition, auctionBids) {
    const openingMeanings = {
      '1♣': '梅花开叫 - 12+ HCP，3张以上梅花',
      '1♦': '方片开叫 - 12+ HCP，3张以上方片',
      '1♥': '红心开叫 - 12+ HCP，5张以上红心',
      '1♠': '黑桃开叫 - 12+ HCP，5张以上黑桃',
      '1NT': '无将开叫 - 15-17 HCP，均型',
      '2♣': '强 2♣ - 22+ HCP',
      '2♦': '弱 2 - 6-11 HCP，6张方片',
      '2♥': '弱 2 - 6-11 HCP，6张红心',
      '2♠': '弱 2 - 6-11 HCP，6张黑桃',
      '2NT': '2NT 开叫 - 20-21 HCP，均型',
      '3♣': '预防性 - 6-10 HCP，7张梅花',
      '3♦': '预防性 - 6-10 HCP，7张方片',
      '3♥': '预防性 - 6-10 HCP，7张红心',
      '3♠': '预防性 - 6-10 HCP，7张黑桃',
      '3NT': '3NT 开叫 - 25-27 HCP，均型'
    }

    const responseMeanings = {
      '1♦': '新花应叫 - 6+ HCP，4张以上方片',
      '1♥': '新花应叫 - 6+ HCP，4张以上红心',
      '1♠': '新花应叫 - 6+ HCP，4张以上黑桃',
      '1NT': '1NT 应叫 - 6-9 HCP，均型',
      '2♣': '2/1 应叫 - 11+ HCP，4张梅花',
      '2♦': '2/1 应叫 - 11+ HCP，4张方片',
      '2♥': '2/1 应叫 - 11+ HCP，4张红心',
      '2♠': '2/1 应叫 - 11+ HCP，4张黑桃',
      '2NT': '2NT 应叫 - 11+ HCP，均型',
      '3♣': '支持邀局 - 11-12 HCP，4张梅花支持',
      '3♦': '支持邀局 - 11-12 HCP，4张方片支持',
      '3♥': '支持邀局 - 11-12 HCP，4张红心支持',
      '3♠': '支持邀局 - 11-12 HCP，4张黑桃支持',
      '3NT': '3NT 应叫 - 12+ HCP，均型',
      '4♥': '支持进局 - 13+ HCP，4张红心支持',
      '4♠': '支持进局 - 13+ HCP，4张黑桃支持'
    }

    const rebidMeanings = {
      '1NT': '再叫 1NT - 12-14 HCP，均型最低',
      '2♣': '再叫梅花 - 12-14 HCP，3张梅花',
      '2♦': '再叫方片 - 12-14 HCP，3张方片',
      '2♥': '支持高花 - 3-4张支持',
      '2♠': '支持高花 - 3-4张支持',
      '2NT': '再叫 2NT - 18-19 HCP，均型',
      '3♣': '支持邀局 - 15-17 HCP，5张梅花',
      '3♦': '支持邀局 - 15-17 HCP，5张方片',
      '3♥': '支持进局 - 13+ HCP，5张红心支持',
      '3♠': '支持进局 - 13+ HCP，5张黑桃支持',
      '3NT': '再叫 3NT - 16-18 HCP，均型',
      '4♥': '支持进局 - 13+ HCP，5张红心支持',
      '4♠': '支持进局 - 13+ HCP，5张黑桃支持',
      '4NT': '关键张问叫',
      '5♣': '长套进局 - 13+ HCP，6张梅花',
      '5♦': '长套进局 - 13+ HCP，6张方片'
    }

    const responder2Meanings = {
      '2NT': '邀局 - 10-12 HCP，邀请无将',
      '3NT': '进局 - 13+ HCP，无将进局',
      '3♣': '支持邀 - 10-12 HCP，4张梅花支持',
      '3♦': '支持邀 - 10-12 HCP，4张方片支持',
      '3♥': '支持进 - 13+ HCP，4张红心支持',
      '3♠': '支持进 - 13+ HCP，4张黑桃支持',
      '4♥': '支持进 - 13+ HCP，4张红心支持',
      '4♠': '支持进 - 13+ HCP，4张黑桃支持',
      '4NT': '关键张问叫',
      '5♣': '长套 - 13+ HCP，6张梅花',
      '5♦': '长套 - 13+ HCP，6张方片',
      '5♥': '竞争 - 高花长套',
      '5♠': '竞争 - 高花长套',
      '5NT': '小满贯邀 - 14+ HCP',
      '6NT': '小满贯 - 15+ HCP',
      '7NT': '大满贯 - 16+ HCP'
    }

    // 根据叫品的实际位置判断含义
    if (bidPosition === 0) {
      // 第 0 位：开叫
      return openingMeanings[bid] || '开叫叫品'
    } else if (bidPosition === 1) {
      // 第 1 位：应叫
      return this.getContextualResponseMeaning(bid, auctionBids || []) || responseMeanings[bid] || '应叫叫品'
    } else if (bidPosition === 2) {
      // 第 2 位：开叫者再叫
      return this.getContextualRebidMeaning(bid, auctionBids || []) || rebidMeanings[bid] || '再叫叫品'
    } else if (bidPosition === 3) {
      // 第 3 位：应叫者第二次应叫
      return this.getContextualResponder2Meaning(bid, auctionBids || []) || responder2Meanings[bid] || '第二次应叫'
    } else if (bidPosition % 2 === 0) {
      // 偶数位：开叫者再叫
      return this.getContextualRebidMeaning(bid, auctionBids || []) || rebidMeanings[bid] || '再叫叫品'
    } else {
      // 奇数位：应叫者应叫
      return this.getContextualResponder2Meaning(bid, auctionBids || []) || responder2Meanings[bid] || '应叫叫品'
    }
  },

  showBidMeaning(event) {
    const bid = event.currentTarget.dataset.bid
    const auctionBids = this.data.auctionBids
    const bidPosition = Number(event.currentTarget.dataset.index)
    const meaning = this.getBidMeaning(bid, bidPosition, auctionBids)
    wx.showModal({
      title: `叫品含义：${bid}`,
      content: meaning,
      showCancel: false,
      confirmText: '关闭',
      confirmColor: '#198754'
    })
  },

  async submitAnswer() {
    if (!this.data.question || this.data.submitted || !this.data.selectedBidLegal) {
      return
    }
    const recommendation = this.data.question.recommendation
    try {
      const answer = await getApi().checkAnswer({
        selected_bid: this.data.selectedBid,
        recommended_bid: recommendation.bid,
        acceptable_bids: this.data.question.acceptable_bids || [recommendation.bid],
        explanation: recommendation.explanation,
        rule_name: recommendation.rule_name
      })
      const stats = this.getStoredStats()
      const mode = this.data.mode
      const modeStats = stats.byMode[mode] || { total: 0, correct: 0 }

      modeStats.total += 1
      if (answer.correct) {
        modeStats.correct += 1
      }
      stats.byMode[mode] = modeStats
      stats.total += 1
      if (answer.correct) {
        stats.correct += 1
      }
      this.saveStoredStats(stats)

      const total = modeStats.total
      const correct = modeStats.correct
      const rate = total ? (correct / total * 100).toFixed(1) : '0.0'
      const allTotal = stats.total
      const allCorrect = stats.correct
      const allRate = allTotal ? (allCorrect / allTotal * 100).toFixed(1) : '0.0'
      const recommendedBidClass = this.getBidStrainClass(recommendation.bid)
      let feedbackTitle = '不太合适'
      if (answer.grade === 'primary' || this.data.selectedBid === recommendation.bid) {
        feedbackTitle = '正确'
      } else if (answer.grade === 'acceptable' || answer.correct) {
        feedbackTitle = '可接受次优'
      }
      this.setData({
        submitted: true,
        answer,
        feedbackTitle,
        recommendedBidClass,
        total,
        correct,
        rate,
        allTotal,
        allCorrect,
        allRate
      })
    } catch (error) {
      this.setData({ error: `提交失败：${error.message || error.errMsg || error}` })
    }
  }
})
