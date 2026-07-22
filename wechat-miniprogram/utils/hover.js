/** 真悬停辅助：PC / 支持鼠标的环境用 mouseenter；模拟器主要靠 CSS :hover。 */

function onHoverEnter(e) {
  const key = e.currentTarget.dataset.hover
  if (key == null || key === '') return
  if (this.data.hoverKey === String(key)) return
  this.setData({ hoverKey: String(key) })
}

function onHoverLeave(e) {
  const key = e.currentTarget.dataset.hover
  if (key != null && key !== '' && this.data.hoverKey !== String(key)) return
  if (!this.data.hoverKey) return
  this.setData({ hoverKey: '' })
}

module.exports = {
  onHoverEnter,
  onHoverLeave
}
