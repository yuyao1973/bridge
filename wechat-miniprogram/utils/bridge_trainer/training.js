const {
  OPENING_BIDS,
  REBID_BIDS,
  RESPONSE_BIDS,
  RESPONDER_REBID_BIDS,
  defaultRuleSettings,
  legal_response_bids,
  legal_rebid_bids,
  legal_responder_rebid_bids,
  parse_contract_bid,
  recommend_opening,
  recommend_opener_rebid,
  recommend_responder_rebid,
  recommend_response,
} = require('./bidding')
const { deal, new_deck, sort_hand } = require('./cards')
const { evaluate_hand } = require('./evaluator')
const { PythonRandom } = require('./random')

const ONE_LEVEL_OPENINGS = new Set(['1♣', '1♦', '1♥', '1♠', '1NT'])
const STRONG_OPENINGS = new Set(['2♣', '2NT'])
const PREEMPT_OPENINGS = new Set([
  '2♦', '2♥', '2♠', '3♣', '3♦', '3♥', '3♠',
  '4♣', '4♦', '4♥', '4♠', '5♣', '5♦',
])
const SUPPORTED_FILTER_OPENINGS = new Set()
ONE_LEVEL_OPENINGS.forEach(function (bid) { SUPPORTED_FILTER_OPENINGS.add(bid) })
STRONG_OPENINGS.forEach(function (bid) { SUPPORTED_FILTER_OPENINGS.add(bid) })
PREEMPT_OPENINGS.forEach(function (bid) { SUPPORTED_FILTER_OPENINGS.add(bid) })

// Hard caps for WeChat JS thread / simulator watchdog.
const DEFAULT_SEARCH_ATTEMPTS = 25
const OPENING_FILTER_SEARCH_ATTEMPTS = 40
const RESPONSE_FILTER_SEARCH_ATTEMPTS = 50
const REBID_FILTER_SEARCH_ATTEMPTS = 60
const DIRECTED_OPENER_REBID_SEARCH_ATTEMPTS = 80
const DIRECTED_RESPONDER_REBID_SEARCH_ATTEMPTS = 80
const TARGETED_OPENER_ATTEMPTS = 15
const TARGETED_RESPONDER_ATTEMPTS = 10
// Cap "should Pass" opening deals (below opening strength and no weak/preempt).
const OPENING_PASS_MAX_RATE = 0.09
const OPENING_PASS_RATE_DENOM = 100
const OPENING_PASS_RATE_NUM = 9
const OPENING_DEAL_SEARCH_ATTEMPTS = 50

const DIRECTED_OPENER_REBID_SEQUENCES = new Set([
  '1NT|2♣',
  '1NT|2♦',
  '1NT|2♥',
  '2NT|3♣',
  '2NT|3♦',
  '2NT|3♥',
  '1♥|2NT',
  '1♠|2NT',
])

const DIRECTED_RESPONDER_REBID_SEQUENCES = new Set([
  '1NT|2♣|2♦',
  '1NT|2♣|2♥',
  '1NT|2♣|2♠',
  '1NT|2♦|2♥',
  '1NT|2♥|2♠',
  '1♥|2NT|4♥',
  '1♠|2NT|4♠',
])

function openerRebidSeqKey(openerBid, responseBid) {
  return openerBid + '|' + responseBid
}

function responderRebidSeqKey(openerBid, responseBid, openerRebidBid) {
  return openerBid + '|' + responseBid + '|' + openerRebidBid
}

function createTrainingQuestion(fields) {
  return Object.assign({
    position: '南',
    auction: '第一家开叫',
    opener_bid: null,
    response_bid: null,
    opener_rebid_bid: null,
  }, fields || {})
}

function isBalancedNtOpening(evaluation, settings, ntLevel) {
  if (ntLevel === 1) {
    return evaluation.balanced && settings.one_nt_min <= evaluation.hcp && evaluation.hcp <= settings.one_nt_max
  }
  if (ntLevel === 2) {
    return evaluation.balanced && evaluation.hcp >= 20 && evaluation.hcp <= 21
  }
  return false
}

function matchesCommonOpenerRebidPrefilter(
  openerBid,
  responseBid,
  openerEvaluation,
  responderEvaluation,
  settings,
) {
  if (openerBid == null || responseBid == null) {
    return true
  }

  const responderLengths = responderEvaluation.lengths
  const openerLengths = openerEvaluation.lengths

  if (openerBid === '1NT' && responseBid === '2♣') {
    return isBalancedNtOpening(openerEvaluation, settings, 1) && responderEvaluation.hcp >= 8 && (
      responderLengths.H >= 4 || responderLengths.S >= 4
    )
  }
  if (openerBid === '1NT' && responseBid === '2♦') {
    return isBalancedNtOpening(openerEvaluation, settings, 1) && settings.transfers_enabled && responderLengths.H >= 5
  }
  if (openerBid === '1NT' && responseBid === '2♥') {
    return isBalancedNtOpening(openerEvaluation, settings, 1) && settings.transfers_enabled && responderLengths.S >= 5
  }
  if (openerBid === '2NT' && responseBid === '3♣') {
    return isBalancedNtOpening(openerEvaluation, settings, 2) && (
      responderLengths.H >= 4 || responderLengths.S >= 4
    )
  }
  if (openerBid === '2NT' && responseBid === '3♦') {
    return isBalancedNtOpening(openerEvaluation, settings, 2) && settings.transfers_enabled && responderLengths.H >= 5
  }
  if (openerBid === '2NT' && responseBid === '3♥') {
    return isBalancedNtOpening(openerEvaluation, settings, 2) && settings.transfers_enabled && responderLengths.S >= 5
  }
  if (openerBid === '1♥' && responseBid === '2NT') {
    return settings.jacoby_2nt_enabled && openerLengths.H >= 5 && responderLengths.H >= 4 && responderEvaluation.hcp >= 12
  }
  if (openerBid === '1♠' && responseBid === '2NT') {
    return settings.jacoby_2nt_enabled && openerLengths.S >= 5 && responderLengths.S >= 4 && responderEvaluation.hcp >= 12
  }

  return true
}

function matchesCommonResponderRebidPrefilter(
  openerBid,
  responseBid,
  openerRebidBid,
  openerEvaluation,
  responderEvaluation,
  settings,
) {
  if (openerBid == null || responseBid == null) {
    return true
  }

  const responderLengths = responderEvaluation.lengths
  const openerLengths = openerEvaluation.lengths

  if (openerBid === '1NT' && responseBid === '2♣') {
    if (!(isBalancedNtOpening(openerEvaluation, settings, 1) && responderEvaluation.hcp >= 8 && (responderLengths.H >= 4 || responderLengths.S >= 4))) {
      return false
    }
    if (openerRebidBid === '2♥') {
      return openerLengths.H >= 4
    }
    if (openerRebidBid === '2♠') {
      return openerLengths.H < 4 && openerLengths.S >= 4
    }
    if (openerRebidBid === '2♦') {
      return openerLengths.H < 4 && openerLengths.S < 4
    }
    return true
  }

  if (openerBid === '1NT' && responseBid === '2♦') {
    return (
      isBalancedNtOpening(openerEvaluation, settings, 1)
      && settings.transfers_enabled
      && responderLengths.H >= 5
      && (openerRebidBid == null || openerRebidBid === '2♥')
    )
  }

  if (openerBid === '1NT' && responseBid === '2♥') {
    return (
      isBalancedNtOpening(openerEvaluation, settings, 1)
      && settings.transfers_enabled
      && responderLengths.S >= 5
      && (openerRebidBid == null || openerRebidBid === '2♠')
    )
  }

  if (openerBid === '1♥' && responseBid === '2NT') {
    if (!(settings.jacoby_2nt_enabled && openerLengths.H >= 5 && responderLengths.H >= 4 && responderEvaluation.hcp >= 12)) {
      return false
    }
    return openerRebidBid !== '4♥' || openerLengths.H >= 5
  }

  if (openerBid === '1♠' && responseBid === '2NT') {
    if (!(settings.jacoby_2nt_enabled && openerLengths.S >= 5 && responderLengths.S >= 4 && responderEvaluation.hcp >= 12)) {
      return false
    }
    return openerRebidBid !== '4♠' || openerLengths.S >= 5
  }

  return true
}

function searchAttemptBudget({
  openerBid = null,
  responseBid = null,
  openerRebidBid = null,
} = {}) {
  let attempts = DEFAULT_SEARCH_ATTEMPTS
  if (openerBid != null) {
    attempts = Math.max(attempts, OPENING_FILTER_SEARCH_ATTEMPTS)
  }
  if (responseBid != null) {
    attempts = Math.max(attempts, RESPONSE_FILTER_SEARCH_ATTEMPTS)
  }
  if (openerRebidBid != null) {
    attempts = Math.max(attempts, REBID_FILTER_SEARCH_ATTEMPTS)
  }
  return attempts
}

function directedSequenceAttemptBudget({
  openerBid = null,
  responseBid = null,
  openerRebidBid = null,
} = {}) {
  let attempts = searchAttemptBudget({ openerBid, responseBid, openerRebidBid })
  if (openerBid != null && responseBid != null) {
    if (openerRebidBid == null && DIRECTED_OPENER_REBID_SEQUENCES.has(openerRebidSeqKey(openerBid, responseBid))) {
      attempts = Math.max(attempts, DIRECTED_OPENER_REBID_SEARCH_ATTEMPTS)
    }
    if (openerRebidBid != null && DIRECTED_RESPONDER_REBID_SEQUENCES.has(responderRebidSeqKey(openerBid, responseBid, openerRebidBid))) {
      attempts = Math.max(attempts, DIRECTED_RESPONDER_REBID_SEARCH_ATTEMPTS)
    }
  }
  return attempts
}

function iterRolePairs(hands, prioritizeSequence, defaultOpener, defaultResponder) {
  // Always single pair on miniprogram to avoid 12x search blowups.
  return [[hands[defaultOpener], hands[defaultResponder]]]
}

function dealTargeted() {
  // Disabled on miniprogram: nested search freezes the WeChat simulator watchdog.
  return null
}

function getSequenceConstraints(openerBid, responseBid, openerRebidBid, settings) {
  if (openerBid == null || responseBid == null) {
    return null
  }

  function nt1(hand) {
    const ev = evaluate_hand(hand)
    return ev.balanced && settings.one_nt_min <= ev.hcp && ev.hcp <= settings.one_nt_max
  }

  function nt1NoMajor(hand) {
    const ev = evaluate_hand(hand)
    return ev.balanced && settings.one_nt_min <= ev.hcp && ev.hcp <= settings.one_nt_max && ev.lengths.H < 4 && ev.lengths.S < 4
  }

  function nt1FourHearts(hand) {
    const ev = evaluate_hand(hand)
    return ev.balanced && settings.one_nt_min <= ev.hcp && ev.hcp <= settings.one_nt_max && ev.lengths.H >= 4
  }

  function nt1FourSpadesNoHearts(hand) {
    const ev = evaluate_hand(hand)
    return ev.balanced && settings.one_nt_min <= ev.hcp && ev.hcp <= settings.one_nt_max && ev.lengths.S >= 4 && ev.lengths.H < 4
  }

  function nt2(hand) {
    const ev = evaluate_hand(hand)
    return ev.balanced && ev.hcp >= 20 && ev.hcp <= 21
  }

  function staymanResponder(hand) {
    const ev = evaluate_hand(hand)
    return ev.hcp >= 8 && (ev.lengths.H >= 4 || ev.lengths.S >= 4)
  }

  function transferHeartsResponder(hand) {
    return evaluate_hand(hand).lengths.H >= 5
  }

  function transferSpadesResponder(hand) {
    return evaluate_hand(hand).lengths.S >= 5
  }

  function hearts5Opener(hand) {
    const ev = evaluate_hand(hand)
    return ev.lengths.H >= 5 && ev.hcp >= 12 && ev.hcp <= 21
  }

  function spades5Opener(hand) {
    const ev = evaluate_hand(hand)
    return ev.lengths.S >= 5 && ev.hcp >= 12 && ev.hcp <= 21
  }

  function jacobyHeartsResponder(hand) {
    const ev = evaluate_hand(hand)
    return ev.hcp >= 12 && ev.lengths.H >= 4
  }

  function jacobySpadesResponder(hand) {
    const ev = evaluate_hand(hand)
    return ev.hcp >= 12 && ev.lengths.S >= 4
  }

  if (openerRebidBid == null) {
    if (openerBid === '1NT' && responseBid === '2♣') {
      return [nt1, staymanResponder]
    }
    if (openerBid === '1NT' && responseBid === '2♦' && settings.transfers_enabled) {
      return [nt1, transferHeartsResponder]
    }
    if (openerBid === '1NT' && responseBid === '2♥' && settings.transfers_enabled) {
      return [nt1, transferSpadesResponder]
    }
    if (openerBid === '2NT' && responseBid === '3♣') {
      return [nt2, staymanResponder]
    }
    if (openerBid === '2NT' && responseBid === '3♦' && settings.transfers_enabled) {
      return [nt2, transferHeartsResponder]
    }
    if (openerBid === '2NT' && responseBid === '3♥' && settings.transfers_enabled) {
      return [nt2, transferSpadesResponder]
    }
    if (openerBid === '1♥' && responseBid === '2NT' && settings.jacoby_2nt_enabled) {
      return [hearts5Opener, jacobyHeartsResponder]
    }
    if (openerBid === '1♠' && responseBid === '2NT' && settings.jacoby_2nt_enabled) {
      return [spades5Opener, jacobySpadesResponder]
    }
  } else {
    if (openerBid === '1NT' && responseBid === '2♣') {
      if (openerRebidBid === '2♦') {
        return [nt1NoMajor, staymanResponder]
      }
      if (openerRebidBid === '2♥') {
        return [nt1FourHearts, staymanResponder]
      }
      if (openerRebidBid === '2♠') {
        return [nt1FourSpadesNoHearts, staymanResponder]
      }
    }
    if (openerBid === '1NT' && responseBid === '2♦' && settings.transfers_enabled) {
      return [nt1, transferHeartsResponder]
    }
    if (openerBid === '1NT' && responseBid === '2♥' && settings.transfers_enabled) {
      return [nt1, transferSpadesResponder]
    }
    if (openerBid === '1♥' && responseBid === '2NT' && settings.jacoby_2nt_enabled) {
      return [hearts5Opener, jacobyHeartsResponder]
    }
    if (openerBid === '1♠' && responseBid === '2NT' && settings.jacoby_2nt_enabled) {
      return [spades5Opener, jacobySpadesResponder]
    }
  }

  return null
}

function buildOpeningQuestion(seed, settings) {
  const hands = deal(seed)
  const hand = hands.S
  const evaluation = evaluate_hand(hand)
  const vulnerability = chooseVulnerability(seed)
  const recommendation = recommend_opening(evaluation, settings, vulnerability)
  return createTrainingQuestion({
    hand,
    evaluation,
    recommendation,
    vulnerability,
    choices: OPENING_BIDS,
    legal_choices: OPENING_BIDS,
    acceptable_bids: buildAcceptableBids(
      recommendation.bid,
      OPENING_BIDS,
      'opening',
    ),
    mode: '开叫训练',
  })
}

function generateOpeningQuestion(seed = null, settings = null) {
  const resolvedSettings = settings || defaultRuleSettings()
  const baseSeed = seed != null ? seed : Math.floor(Math.random() * 1000000000) + 1
  const preferPass = (Math.abs(Math.floor(baseSeed)) % OPENING_PASS_RATE_DENOM) < OPENING_PASS_RATE_NUM

  let fallback = null
  if (preferPass) {
    for (let offset = 0; offset < OPENING_DEAL_SEARCH_ATTEMPTS; offset += 1) {
      const question = buildOpeningQuestion(baseSeed + offset, resolvedSettings)
      if (fallback === null) {
        fallback = question
      }
      if (question.recommendation.bid === 'Pass') {
        return question
      }
    }
    return fallback
  }

  for (let offset = 0; offset < OPENING_DEAL_SEARCH_ATTEMPTS; offset += 1) {
    const question = buildOpeningQuestion(baseSeed + offset, resolvedSettings)
    if (fallback === null) {
      fallback = question
    }
    if (question.recommendation.bid !== 'Pass') {
      return question
    }
  }
  return fallback
}

function generateResponseQuestion(
  seed = null,
  openerBid = null,
  settings = null,
  openerCategory = null,
) {
  const resolvedSettings = settings || defaultRuleSettings()
  const supportedOpenings = supportedOpeningsForCategory(openerCategory)
  let resolvedOpenerBid = openerBid
  if (resolvedOpenerBid != null && !supportedOpenings.has(resolvedOpenerBid)) {
    resolvedOpenerBid = null
  }
  const baseSeed = seed != null ? seed : 1
  const attempts = searchAttemptBudget({ openerBid: resolvedOpenerBid })

  for (let offset = 0; offset < attempts; offset += 1) {
    const hands = deal(baseSeed + offset)
    const vulnerability = chooseVulnerability(baseSeed + offset)
    const openerEvaluation = evaluate_hand(hands.N)
    const openerRecommendation = recommend_opening(openerEvaluation, resolvedSettings, vulnerability)
    if (!supportedOpenings.has(openerRecommendation.bid)) {
      continue
    }
    if (resolvedOpenerBid != null && openerRecommendation.bid !== resolvedOpenerBid) {
      continue
    }

    const hand = hands.S
    const evaluation = evaluate_hand(hand)
    const recommendation = recommend_response(openerRecommendation.bid, evaluation, resolvedSettings, vulnerability)
    const legalChoices = legal_response_bids(openerRecommendation.bid)
    return createTrainingQuestion({
      hand,
      evaluation,
      recommendation,
      vulnerability,
      choices: RESPONSE_BIDS,
      legal_choices: legalChoices,
      acceptable_bids: buildAcceptableBids(
        recommendation.bid,
        legalChoices,
        'response',
        openerRecommendation.bid,
      ),
      mode: '应叫训练',
      auction: `${openerRecommendation.bid}-?`,
      opener_bid: openerRecommendation.bid,
    })
  }

  return generateOpeningQuestion(seed, resolvedSettings)
}

function generateOpenerRebidQuestion(
  seed = null,
  settings = null,
  openerBid = null,
  openerCategory = null,
  responseBid = null,
) {
  const resolvedSettings = settings || defaultRuleSettings()
  const supportedOpenings = supportedOpeningsForCategory(openerCategory)
  let resolvedOpenerBid = openerBid
  let resolvedResponseBid = responseBid
  if (resolvedOpenerBid != null && !supportedOpenings.has(resolvedOpenerBid)) {
    resolvedOpenerBid = null
  }
  if (resolvedOpenerBid != null && resolvedResponseBid != null && !legal_response_bids(resolvedOpenerBid).includes(resolvedResponseBid)) {
    resolvedResponseBid = null
  }
  const baseSeed = seed != null ? seed : 1
  const attempts = directedSequenceAttemptBudget({ openerBid: resolvedOpenerBid, responseBid: resolvedResponseBid })
  const prioritizeSequence = resolvedOpenerBid != null && resolvedResponseBid != null

  if (prioritizeSequence) {
    const constraints = getSequenceConstraints(resolvedOpenerBid, resolvedResponseBid, null, resolvedSettings)
    if (constraints != null) {
      const [openerC, responderC] = constraints
      const targeted = dealTargeted(openerC, responderC, baseSeed)
      if (targeted != null) {
        const [openerHand, responderHand] = targeted
        const vuln = chooseVulnerability(baseSeed)
        const openerEval = evaluate_hand(openerHand)
        const openRec = recommend_opening(openerEval, resolvedSettings, vuln)
        if (openRec.bid === resolvedOpenerBid) {
          const respEval = evaluate_hand(responderHand)
          const respRec = recommend_response(openRec.bid, respEval, resolvedSettings, vuln)
          if (respRec.bid === resolvedResponseBid) {
            const rebidRec = recommend_opener_rebid(
              openRec.bid,
              respRec.bid,
              openerEval,
              resolvedSettings,
              vuln,
            )
            const legalChoices = legal_rebid_bids(respRec.bid)
            return createTrainingQuestion({
              hand: openerHand,
              evaluation: openerEval,
              recommendation: rebidRec,
              vulnerability: vuln,
              choices: REBID_BIDS,
              legal_choices: legalChoices,
              acceptable_bids: buildAcceptableBids(
                rebidRec.bid,
                legalChoices,
                'opener_rebid',
                openRec.bid,
                respRec.bid,
              ),
              mode: '开叫者再叫训练',
              auction: `${openRec.bid}-${respRec.bid}-? `,
              opener_bid: openRec.bid,
              response_bid: respRec.bid,
            })
          }
        }
      }
    }
  }

  for (let offset = 0; offset < attempts; offset += 1) {
    const hands = deal(baseSeed + offset)
    const vulnerability = chooseVulnerability(baseSeed + offset)
    for (const [openerHand, responderHand] of iterRolePairs(hands, prioritizeSequence, 'S', 'N')) {
      const openerEvaluation = evaluate_hand(openerHand)
      const openingRecommendation = recommend_opening(openerEvaluation, resolvedSettings, vulnerability)
      if (!supportedOpenings.has(openingRecommendation.bid)) {
        continue
      }
      if (resolvedOpenerBid != null && openingRecommendation.bid !== resolvedOpenerBid) {
        continue
      }

      const responderEvaluation = evaluate_hand(responderHand)
      if (!matchesCommonOpenerRebidPrefilter(
        resolvedOpenerBid,
        resolvedResponseBid,
        openerEvaluation,
        responderEvaluation,
        resolvedSettings,
      )) {
        continue
      }
      const responseRecommendation = recommend_response(
        openingRecommendation.bid,
        responderEvaluation,
        resolvedSettings,
        vulnerability,
      )
      if (responseRecommendation.bid === 'Pass' && !PREEMPT_OPENINGS.has(openingRecommendation.bid)) {
        continue
      }
      if (resolvedResponseBid != null && responseRecommendation.bid !== resolvedResponseBid) {
        continue
      }

      const recommendation = recommend_opener_rebid(
        openingRecommendation.bid,
        responseRecommendation.bid,
        openerEvaluation,
        resolvedSettings,
        vulnerability,
      )
      const legalChoices = legal_rebid_bids(responseRecommendation.bid)
      return createTrainingQuestion({
        hand: openerHand,
        evaluation: openerEvaluation,
        recommendation,
        vulnerability,
        choices: REBID_BIDS,
        legal_choices: legalChoices,
        acceptable_bids: buildAcceptableBids(
          recommendation.bid,
          legalChoices,
          'opener_rebid',
          openingRecommendation.bid,
          responseRecommendation.bid,
        ),
        mode: '开叫者再叫训练',
        auction: `${openingRecommendation.bid}-${responseRecommendation.bid}-? `,
        opener_bid: openingRecommendation.bid,
        response_bid: responseRecommendation.bid,
      })
    }
  }

  if (resolvedResponseBid != null) {
    return generateOpenerRebidQuestion(
      seed,
      resolvedSettings,
      resolvedOpenerBid,
      openerCategory,
      null,
    )
  }

  return generateResponseQuestion(seed, resolvedOpenerBid, resolvedSettings, openerCategory)
}

function generateResponderRebidQuestion(
  seed = null,
  settings = null,
  openerBid = null,
  openerCategory = null,
  responseBid = null,
  openerRebidBid = null,
) {
  const resolvedSettings = settings || defaultRuleSettings()
  const supportedOpenings = supportedOpeningsForCategory(openerCategory)
  let resolvedOpenerBid = openerBid
  let resolvedResponseBid = responseBid
  let resolvedOpenerRebidBid = openerRebidBid
  if (resolvedOpenerBid != null && !supportedOpenings.has(resolvedOpenerBid)) {
    resolvedOpenerBid = null
  }
  if (resolvedOpenerBid != null && resolvedResponseBid != null && !legal_response_bids(resolvedOpenerBid).includes(resolvedResponseBid)) {
    resolvedResponseBid = null
  }
  if (resolvedResponseBid != null && resolvedOpenerRebidBid != null && !legal_rebid_bids(resolvedResponseBid).includes(resolvedOpenerRebidBid)) {
    resolvedOpenerRebidBid = null
  }
  const baseSeed = seed != null ? seed : 1
  const attempts = directedSequenceAttemptBudget({
    openerBid: resolvedOpenerBid,
    responseBid: resolvedResponseBid,
    openerRebidBid: resolvedOpenerRebidBid,
  })
  const prioritizeSequence = resolvedOpenerBid != null && resolvedResponseBid != null && resolvedOpenerRebidBid != null

  if (prioritizeSequence) {
    const constraints = getSequenceConstraints(
      resolvedOpenerBid,
      resolvedResponseBid,
      resolvedOpenerRebidBid,
      resolvedSettings,
    )
    if (constraints != null) {
      const [openerC, responderC] = constraints
      const targeted = dealTargeted(openerC, responderC, baseSeed)
      if (targeted != null) {
        const [openerHand, responderHand] = targeted
        const vuln = chooseVulnerability(baseSeed)
        const openerEval = evaluate_hand(openerHand)
        const respEval = evaluate_hand(responderHand)
        const openRec = recommend_opening(openerEval, resolvedSettings, vuln)
        if (openRec.bid === resolvedOpenerBid) {
          const respRec = recommend_response(openRec.bid, respEval, resolvedSettings, vuln)
          if (respRec.bid === resolvedResponseBid) {
            const rebidRec = recommend_opener_rebid(
              openRec.bid,
              respRec.bid,
              openerEval,
              resolvedSettings,
              vuln,
            )
            if (rebidRec.bid === resolvedOpenerRebidBid) {
              const finalRec = recommend_responder_rebid(
                openRec.bid,
                respRec.bid,
                rebidRec.bid,
                respEval,
                resolvedSettings,
                vuln,
              )
              const legalChoices = legal_responder_rebid_bids(rebidRec.bid)
              return createTrainingQuestion({
                hand: responderHand,
                evaluation: respEval,
                recommendation: finalRec,
                vulnerability: vuln,
                choices: RESPONDER_REBID_BIDS,
                legal_choices: legalChoices,
                acceptable_bids: buildAcceptableBids(
                  finalRec.bid,
                  legalChoices,
                  'responder_rebid',
                  openRec.bid,
                  respRec.bid,
                  rebidRec.bid,
                ),
                mode: '应叫者第二次应叫训练',
                auction: `${openRec.bid}-Pass-${respRec.bid}-Pass-${rebidRec.bid}-Pass-? `,
                opener_bid: openRec.bid,
                response_bid: respRec.bid,
                opener_rebid_bid: rebidRec.bid,
              })
            }
          }
        }
      }
    }
  }

  for (let offset = 0; offset < attempts; offset += 1) {
    const hands = deal(baseSeed + offset)
    const vulnerability = chooseVulnerability(baseSeed + offset)
    for (const [openerHand, responderHand] of iterRolePairs(hands, prioritizeSequence, 'N', 'S')) {
      const openerEvaluation = evaluate_hand(openerHand)
      const responderEvaluation = evaluate_hand(responderHand)

      if (!matchesCommonResponderRebidPrefilter(
        resolvedOpenerBid,
        resolvedResponseBid,
        resolvedOpenerRebidBid,
        openerEvaluation,
        responderEvaluation,
        resolvedSettings,
      )) {
        continue
      }

      const openingRecommendation = recommend_opening(openerEvaluation, resolvedSettings, vulnerability)
      if (!supportedOpenings.has(openingRecommendation.bid)) {
        continue
      }
      if (resolvedOpenerBid != null && openingRecommendation.bid !== resolvedOpenerBid) {
        continue
      }

      const responseRecommendation = recommend_response(
        openingRecommendation.bid,
        responderEvaluation,
        resolvedSettings,
        vulnerability,
      )
      if (responseRecommendation.bid === 'Pass') {
        continue
      }
      if (resolvedResponseBid != null && responseRecommendation.bid !== resolvedResponseBid) {
        continue
      }

      const openerRebidRecommendation = recommend_opener_rebid(
        openingRecommendation.bid,
        responseRecommendation.bid,
        openerEvaluation,
        resolvedSettings,
        vulnerability,
      )
      if (openerRebidRecommendation.bid === 'Pass') {
        continue
      }
      if (resolvedOpenerRebidBid != null && openerRebidRecommendation.bid !== resolvedOpenerRebidBid) {
        continue
      }

      const recommendation = recommend_responder_rebid(
        openingRecommendation.bid,
        responseRecommendation.bid,
        openerRebidRecommendation.bid,
        responderEvaluation,
        resolvedSettings,
        vulnerability,
      )
      const legalChoices = legal_responder_rebid_bids(openerRebidRecommendation.bid)
      return createTrainingQuestion({
        hand: responderHand,
        evaluation: responderEvaluation,
        recommendation,
        vulnerability,
        choices: RESPONDER_REBID_BIDS,
        legal_choices: legalChoices,
        acceptable_bids: buildAcceptableBids(
          recommendation.bid,
          legalChoices,
          'responder_rebid',
          openingRecommendation.bid,
          responseRecommendation.bid,
          openerRebidRecommendation.bid,
        ),
        mode: '应叫者第二次应叫训练',
        auction: `${openingRecommendation.bid}-Pass-${responseRecommendation.bid}-Pass-${openerRebidRecommendation.bid}-Pass-? `,
        opener_bid: openingRecommendation.bid,
        response_bid: responseRecommendation.bid,
        opener_rebid_bid: openerRebidRecommendation.bid,
      })
    }
  }

  if (resolvedOpenerRebidBid != null) {
    return generateResponderRebidQuestion(
      seed,
      resolvedSettings,
      resolvedOpenerBid,
      openerCategory,
      resolvedResponseBid,
      null,
    )
  }

  if (resolvedResponseBid != null) {
    return generateResponderRebidQuestion(
      seed,
      resolvedSettings,
      resolvedOpenerBid,
      openerCategory,
      null,
      null,
    )
  }

  return generateResponseQuestion(seed, null, resolvedSettings, openerCategory)
}

function supportedOpeningsForCategory(openerCategory) {
  if (openerCategory === '一阶定约') {
    return new Set(ONE_LEVEL_OPENINGS)
  }
  if (openerCategory === '强开叫') {
    return new Set(STRONG_OPENINGS)
  }
  if (openerCategory === '阻击叫') {
    return new Set(PREEMPT_OPENINGS)
  }
  return new Set(SUPPORTED_FILTER_OPENINGS)
}

function chooseVulnerability(seed = null) {
  const options = ['双方无局', '南北有局', '东西有局', '双方有局']
  if (seed == null) {
    return options[Math.floor(Math.random() * options.length)]
  }
  return options[seed % options.length]
}

function buildAcceptableBids(
  recommendedBid,
  legalChoices,
  mode,
  openerBid = null,
  responseBid = null,
  openerRebidBid = null,
) {
  const accepted = []
  if (legalChoices.includes(recommendedBid)) {
    accepted.push(recommendedBid)
  }
  if (recommendedBid === 'Pass') {
    return accepted.length ? accepted : ['Pass']
  }

  const recommendedContract = parse_contract_bid(recommendedBid)
  if (recommendedContract == null) {
    return accepted.length ? accepted : [recommendedBid]
  }

  const [recLevel, recStrain] = recommendedContract
  const openerContract = openerBid ? parse_contract_bid(openerBid) : null
  const responseContract = responseBid ? parse_contract_bid(responseBid) : null
  const openerRebidContract = openerRebidBid ? parse_contract_bid(openerRebidBid) : null

  function addIfLegal(bid) {
    if (legalChoices.includes(bid) && !accepted.includes(bid)) {
      accepted.push(bid)
    }
  }

  if (mode === 'opening') {
    if (recommendedBid === '1♣' || recommendedBid === '1♦') {
      addIfLegal('1♣')
      addIfLegal('1♦')
    }
    if (recommendedBid === '1♥' || recommendedBid === '1♠') {
      const other = recommendedBid === '1♥' ? '1♠' : '1♥'
      addIfLegal(other)
    }
    if (recommendedBid === '2NT' || recommendedBid === '3NT') {
      addIfLegal('2NT')
      addIfLegal('3NT')
    }
  } else if (mode === 'response') {
    if (openerBid === '1NT' && (recommendedBid === '2NT' || recommendedBid === '3NT')) {
      addIfLegal('2NT')
      addIfLegal('3NT')
    }

    if (openerBid === '1♥' && (recommendedBid === '3♦' || recommendedBid === '3♣')) {
      addIfLegal('3♣')
      addIfLegal('3♦')
      addIfLegal('2♥')
    }

    if (openerContract && (openerContract[1] === '♥' || openerContract[1] === '♠') && recStrain === openerContract[1]) {
      addIfLegal(`${Math.max(2, recLevel - 1)}${recStrain}`)
      addIfLegal(`${Math.min(4, recLevel + 1)}${recStrain}`)
    }
  } else if (mode === 'opener_rebid') {
    if (recLevel === 1 && (recStrain === '♣' || recStrain === '♦' || recStrain === '♥' || recStrain === '♠')) {
      addIfLegal('1NT')
    }

    if (
      recLevel === 4
      && openerContract != null
      && responseBid === '2NT'
      && openerContract[0] === 1
      && recStrain === openerContract[1]
    ) {
      addIfLegal('3NT')
    }

    if (
      recLevel === 2
      && (recStrain === '♣' || recStrain === '♦' || recStrain === '♥' || recStrain === '♠')
      && openerContract != null
      && openerContract[0] === 1
      && (openerContract[1] === '♥' || openerContract[1] === '♠')
    ) {
      addIfLegal(`2${openerContract[1]}`)
    }

    if (
      recommendedBid === '1NT'
      && openerContract != null
      && responseContract != null
      && openerContract[0] === 1
      && responseContract[0] === 1
    ) {
      addIfLegal('2♣')
      addIfLegal('2♦')
    }

    if (
      recLevel === 2
      && (recStrain === '♣' || recStrain === '♦' || recStrain === '♥' || recStrain === '♠')
      && openerContract != null
      && responseContract != null
      && openerContract[0] === 1
      && responseContract[0] === 1
    ) {
      addIfLegal('1NT')
    }

    if (recStrain === 'NT') {
      if (recommendedBid === '1NT') {
        addIfLegal('2NT')
      } else if (recommendedBid === '2NT') {
        addIfLegal('1NT')
        addIfLegal('3NT')
      } else if (recommendedBid === '3NT') {
        addIfLegal('2NT')
      }
    }

    if (responseContract && recStrain === responseContract[1]) {
      addIfLegal(`${Math.max(2, recLevel - 1)}${recStrain}`)
      addIfLegal(`${recLevel + 1}${recStrain}`)
    }

    if (openerContract && recStrain === openerContract[1]) {
      addIfLegal(`${Math.max(2, recLevel - 1)}${recStrain}`)
      addIfLegal(`${recLevel + 1}${recStrain}`)
    }
  } else if (mode === 'responder_rebid') {
    if (openerRebidContract && openerRebidContract[1] === 'NT' && (recommendedBid === '2NT' || recommendedBid === '3NT')) {
      addIfLegal('2NT')
      addIfLegal('3NT')
    }

    if (responseContract && recStrain === responseContract[1]) {
      addIfLegal(`${Math.max(responseContract[0], recLevel - 1)}${recStrain}`)
      addIfLegal(`${recLevel + 1}${recStrain}`)
    }

    if (openerRebidContract && recStrain === openerRebidContract[1]) {
      addIfLegal(`${Math.max(openerRebidContract[0], recLevel - 1)}${recStrain}`)
      addIfLegal(`${recLevel + 1}${recStrain}`)
    }
  }

  if (accepted.length < 2) {
    const neighbors = []
    for (const bid of legalChoices) {
      if (accepted.includes(bid) || bid === 'Pass') {
        continue
      }
      const contract = parse_contract_bid(bid)
      if (contract == null) {
        continue
      }
      const [level, strain] = contract
      if (strain === recStrain && Math.abs(level - recLevel) === 1) {
        neighbors.push(bid)
      }
    }

    neighbors.sort((a, b) => {
      const aLevel = parse_contract_bid(a)[0]
      const bLevel = parse_contract_bid(b)[0]
      return Math.abs(aLevel - recLevel) - Math.abs(bLevel - recLevel)
    })
    for (const bid of neighbors) {
      if (!accepted.includes(bid)) {
        accepted.push(bid)
      }
      if (accepted.length >= 2) {
        break
      }
    }
  }

  return accepted.length ? accepted : [recommendedBid]
}

module.exports = {
  ONE_LEVEL_OPENINGS,
  STRONG_OPENINGS,
  PREEMPT_OPENINGS,
  SUPPORTED_FILTER_OPENINGS,
  DEFAULT_SEARCH_ATTEMPTS,
  OPENING_FILTER_SEARCH_ATTEMPTS,
  RESPONSE_FILTER_SEARCH_ATTEMPTS,
  REBID_FILTER_SEARCH_ATTEMPTS,
  DIRECTED_OPENER_REBID_SEARCH_ATTEMPTS,
  DIRECTED_RESPONDER_REBID_SEARCH_ATTEMPTS,
  DIRECTED_OPENER_REBID_SEQUENCES,
  DIRECTED_RESPONDER_REBID_SEQUENCES,
  createTrainingQuestion,
  isBalancedNtOpening,
  matchesCommonOpenerRebidPrefilter,
  matchesCommonResponderRebidPrefilter,
  searchAttemptBudget,
  directedSequenceAttemptBudget,
  iterRolePairs,
  dealTargeted,
  getSequenceConstraints,
  generateOpeningQuestion,
  generateResponseQuestion,
  generateOpenerRebidQuestion,
  generateResponderRebidQuestion,
  supportedOpeningsForCategory,
  chooseVulnerability,
  buildAcceptableBids,
}
