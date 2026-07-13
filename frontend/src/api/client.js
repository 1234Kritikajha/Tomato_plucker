const API_BASE_URL =
  (typeof process !== 'undefined' && process.env && process.env.REACT_APP_API_BASE_URL)
    ? process.env.REACT_APP_API_BASE_URL
    : 'http://localhost:8000/api'

class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('API request failed:', error)
      throw error
    }
  }

  async get(endpoint) {
    return this.request(endpoint, { method: 'GET' })
  }

  async post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async put(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' })
  }

  async upload(endpoint, formData) {
    const url = `${this.baseUrl}${endpoint}`
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Upload failed:', error)
      throw error
    }
  }

  async generateReport(file) {
    const formData = new FormData()
    formData.append('file', file)
    
    const url = `${this.baseUrl}/generate_report`
    
    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Report generation failed:', error)
      throw error
    }
  }

  async downloadReport(filename) {
    const url = `${this.baseUrl}/reports/download/${filename}`
    
    try {
      const response = await fetch(url)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
      
      return { success: true }
    } catch (error) {
      console.error('Download failed:', error)
      throw error
    }
  }

  // Model Management APIs
  async getModels() {
    return this.get('/models/list')
  }

  async getActiveModel() {
    return this.get('/models/active')
  }

  async rollbackModel(version) {
    return this.post('/models/rollback', { version })
  }

  async deleteModel(modelName) {
    return this.delete(`/models/${modelName}`)
  }

  async getModelInfo(modelName) {
    return this.get(`/models/info/${modelName}`)
  }

  // Metrics APIs
  async getMetricsSummary() {
    return this.get('/metrics/summary')
  }

  async getHistoricalMetrics(days = 7) {
    return this.get(`/metrics/historical?days=${days}`)
  }

  async getPerformanceMetrics() {
    return this.get('/metrics/performance')
  }

  async getRealtimeMetrics() {
    return this.get('/metrics/realtime')
  }

  // Prediction APIs
  async getPredictionHistory(limit = 10) {
    return this.get(`/predict/history?limit=${limit}`)
  }

  // Training APIs
  async startTraining(config) {
    return this.post('/train/start', config)
  }

  async getTrainingStatus() {
    return this.get('/train/status')
  }

  async stopTraining() {
    return this.post('/train/stop')
  }

  // Dataset APIs
  async getDatasetStats() {
    return this.get('/dataset/stats')
  }

  async uploadDataset(formData) {
    return this.upload('/dataset/upload', formData)
  }

  // Evaluation APIs
  async runEvaluation(modelVersion) {
    return this.post('/evaluation/run', { model_version: modelVersion })
  }

  async getEvaluationResults() {
    return this.get('/evaluation/results')
  }

  // Export APIs
  async exportData(format = 'csv') {
    return this.get(`/export/data?format=${format}`)
  }

  async exportModel(modelVersion) {
    return this.get(`/export/model?version=${modelVersion}`)
  }

  // System APIs
  async getSystemHealth() {
    return this.get('/health')
  }

  async getSystemLogs() {
    return this.get('/system/logs')
  }

  async getSystemConfig() {
    return this.get('/system/config')
  }

  async updateSystemConfig(config) {
    return this.put('/system/config', config)
  }
}

export const apiClient = new ApiClient(API_BASE_URL)
export default apiClient