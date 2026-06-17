const app = getApp()

function request(path, method, data) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${app.globalData.apiBaseUrl}${path}`,
      method,
      data,
      dataType: 'json',
      header: {
        'content-type': 'application/json'
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
          return
        }
        reject(new Error(`接口错误：${res.statusCode}`))
      },
      fail(error) {
        reject(error)
      }
    })
  })
}

function createQuestion(payload) {
  return request('/api/question', 'POST', payload)
}

function checkAnswer(payload) {
  return request('/api/answer', 'POST', payload)
}

module.exports = {
  createQuestion,
  checkAnswer
}
