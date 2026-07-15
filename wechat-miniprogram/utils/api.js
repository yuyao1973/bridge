const app = getApp()

function requestHttp(path, method, data) {
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

function requestCloudContainer(path, method, data) {
  return new Promise((resolve, reject) => {
    const cloud = wx.cloud
    if (!cloud || typeof cloud.callContainer !== 'function') {
      reject(new Error('当前基础库不支持云托管 callContainer'))
      return
    }

    cloud.callContainer({
      config: {
        env: app.globalData.cloudEnv,
        path,
        method,
        header: {
          'content-type': 'application/json'
        }
      },
      data,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
          return
        }
        reject(new Error(`云托管接口错误：${res.statusCode}`))
      },
      fail(error) {
        reject(error)
      }
    })
  })
}

function request(path, method, data) {
  if (!app.globalData.useCloudBackend) {
    return requestHttp(path, method, data)
  }

  return requestCloudContainer(path, method, data).catch(() => {
    if (app.globalData.cloudApiBaseUrl) {
      return new Promise((resolve, reject) => {
        wx.request({
          url: `${app.globalData.cloudApiBaseUrl}${path}`,
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
            reject(new Error(`云托管公网接口错误：${res.statusCode}`))
          },
          fail(error) {
            reject(error)
          }
        })
      })
    }

    // Final fallback for local development.
    return requestHttp(path, method, data)
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
