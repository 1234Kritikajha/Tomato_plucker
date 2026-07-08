import ThemeToggle from '../components/ThemeToggle.jsx'
import { useState } from 'react'
import apiClient from '../api/client.js'

export default function UploadImageView() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [generatingReport, setGeneratingReport] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [error, setError] = useState(null)

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      setSelectedFile(file)
      setError(null)
      setAnalysisResult(null)
    }
  }

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError('Please select an image first')
      return
    }

    setAnalyzing(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const result = await apiClient.upload('/predict', formData)
      setAnalysisResult(result)
    } catch (err) {
      setError('Failed to analyze image. Please try again.')
      console.error(err)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleGenerateReport = async () => {
    if (!selectedFile) {
      setError('Please select an image first')
      return
    }

    setGeneratingReport(true)
    setError(null)

    try {
      const result = await apiClient.generateReport(selectedFile)
      
      if (result.status === 'success') {
        // Download the report
        await apiClient.downloadReport(result.report_path)
        alert('Report generated and downloaded successfully!')
      }
    } catch (err) {
      setError('Failed to generate report. Please try again.')
      console.error(err)
    } finally {
      setGeneratingReport(false)
    }
  }

  return (
    <section className="relative">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-[var(--text-primary)] to-[var(--text-secondary)] bg-clip-text text-transparent">
          Upload Image for Analysis
        </h1>
        <p className="mt-2 text-sm text-[var(--text-muted)]">
          Upload tomato images for AI-powered ripeness and condition analysis
        </p>

        <div className="mt-8 space-y-6">
          {/* Upload Section */}
          <div className="card-hover rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Upload Image</h3>
            
            <div className="border-2 border-dashed border-[var(--border-color)] rounded-xl p-8 text-center hover:border-[var(--accent-primary)] transition-colors">
              <input
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className="cursor-pointer block"
              >
                <div className="text-5xl mb-3">📁</div>
                <div className="text-sm font-medium text-[var(--text-secondary)]">
                  {selectedFile ? selectedFile.name : 'Click to upload or drag and drop'}
                </div>
                <div className="text-xs text-[var(--text-muted)] mt-1">
                  JPG, PNG, WebP supported (max 10MB)
                </div>
              </label>
            </div>

            <div className="flex gap-4 mt-4">
              <button
                onClick={handleAnalyze}
                disabled={!selectedFile || analyzing}
                className="btn btn-primary flex-1"
              >
                {analyzing ? 'Analyzing...' : 'Analyze Image'}
              </button>
              
              <button
                onClick={handleGenerateReport}
                disabled={!selectedFile || generatingReport}
                className="btn btn-secondary flex-1"
              >
                {generatingReport ? 'Generating...' : 'Generate Report'}
              </button>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-600 dark:text-red-400">
              <div className="font-medium">Error</div>
              <div className="text-sm mt-1">{error}</div>
            </div>
          )}

          {/* Analysis Results */}
          {analysisResult && (
            <div className="space-y-6">
              {/* Summary Section */}
              <div className="card-hover rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] p-6 shadow-lg">
                <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Analysis Summary</h3>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center p-4 rounded-lg bg-[var(--bg-card-hover)]">
                    <div className="text-2xl font-bold text-[var(--accent-primary)]">
                      {analysisResult.summary.total_tomatoes_detected}
                    </div>
                    <div className="text-xs text-[var(--text-muted)] mt-1">Total Tomatoes</div>
                  </div>
                  
                  <div className="text-center p-4 rounded-lg bg-[var(--bg-card-hover)]">
                    <div className="text-2xl font-bold text-[var(--neon-blue)]">
                      {analysisResult.summary.plucking_decisions.should_pluck}
                    </div>
                    <div className="text-xs text-[var(--text-muted)] mt-1">Should Pluck</div>
                  </div>
                  
                  <div className="text-center p-4 rounded-lg bg-[var(--bg-card-hover)]">
                    <div className="text-2xl font-bold text-[var(--neon-orange)]">
                      {analysisResult.summary.plucking_decisions.should_not_pluck}
                    </div>
                    <div className="text-xs text-[var(--text-muted)] mt-1">Don't Pluck</div>
                  </div>
                  
                  <div className="text-center p-4 rounded-lg bg-[var(--bg-card-hover)]">
                    <div className="text-2xl font-bold text-[var(--text-primary)]">
                      {(analysisResult.summary.confidence_metrics.average_overall_confidence * 100).toFixed(1)}%
                    </div>
                    <div className="text-xs text-[var(--text-muted)] mt-1">Avg Confidence</div>
                  </div>
                </div>

                {/* Ripeness Distribution */}
                <div className="mt-6">
                  <h4 className="text-sm font-medium text-[var(--text-secondary)] mb-3">Ripeness Distribution</h4>
                  <div className="flex gap-4">
                    {Object.entries(analysisResult.summary.ripeness_distribution).map(([key, value]) => (
                      <div key={key} className="flex-1">
                        <div className="text-xs text-[var(--text-muted)]">{key}</div>
                        <div className="text-lg font-semibold text-[var(--text-primary)]">{value}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Condition Distribution */}
                <div className="mt-6">
                  <h4 className="text-sm font-medium text-[var(--text-secondary)] mb-3">Condition Distribution</h4>
                  <div className="flex gap-4">
                    {Object.entries(analysisResult.summary.condition_distribution).map(([key, value]) => (
                      <div key={key} className="flex-1">
                        <div className="text-xs text-[var(--text-muted)]">{key}</div>
                        <div className="text-lg font-semibold text-[var(--text-primary)]">{value}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Detailed Detection Results */}
              <div className="card-hover rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] p-6 shadow-lg">
                <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Detection Details</h3>
                
                <div className="space-y-4">
                  {analysisResult.detections.map((detection) => (
                    <div
                      key={detection.id}
                      className={`p-4 rounded-lg border ${
                        detection.plucking_decision.should_pluck
                          ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)]/10'
                          : 'border-[var(--border-color)] bg-[var(--bg-card-hover)]'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <div className="font-semibold text-[var(--text-primary)]">
                            {detection.bounding_box.label}
                          </div>
                          <div className="text-xs text-[var(--text-muted)] mt-1">
                            Bounding Box: x={detection.bounding_box.x.toFixed(0)}, y={detection.bounding_box.y.toFixed(0)}, 
                            w={detection.bounding_box.width.toFixed(0)}, h={detection.bounding_box.height.toFixed(0)}
                          </div>
                        </div>
                        <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                          detection.plucking_decision.should_pluck
                            ? 'bg-[var(--accent-primary)] text-black'
                            : 'bg-[var(--border-color)] text-[var(--text-muted)]'
                        }`}>
                          {detection.plucking_decision.should_pluck ? '🟢 PLUCKABLE' : '🔴 SKIP'}
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <div className="text-xs text-[var(--text-muted)]">Ripeness</div>
                          <div className="font-medium text-[var(--text-primary)]">
                            {detection.classification.ripeness}
                            <span className="text-[var(--text-muted)]"> ({(detection.classification.ripeness_confidence * 100).toFixed(1)}%)</span>
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-[var(--text-muted)]">Condition</div>
                          <div className="font-medium text-[var(--text-primary)]">
                            {detection.classification.condition}
                            <span className="text-[var(--text-muted)]"> ({(detection.classification.condition_confidence * 100).toFixed(1)}%)</span>
                          </div>
                        </div>
                      </div>

                      <div className="mt-3 text-xs text-[var(--text-muted)]">
                        {detection.plucking_decision.reason}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Quality Assessment */}
              <div className="card-hover rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] p-6 shadow-lg">
                <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Quality Assessment</h3>
                
                <div className="grid grid-cols-3 gap-4">
                  <div className="text-center p-4 rounded-lg bg-green-500/10 border border-green-500/30">
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {analysisResult.summary.quality_assessment.high_quality_tomatoes}
                    </div>
                    <div className="text-xs text-[var(--text-muted)] mt-1">High Quality</div>
                  </div>
                  
                  <div className="text-center p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
                    <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                      {analysisResult.summary.quality_assessment.medium_quality_tomatoes}
                    </div>
                    <div className="text-xs text-[var(--text-muted)] mt-1">Medium Quality</div>
                  </div>
                  
                  <div className="text-center p-4 rounded-lg bg-red-500/10 border border-red-500/30">
                    <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                      {analysisResult.summary.quality_assessment.low_quality_tomatoes}
                    </div>
                    <div className="text-xs text-[var(--text-muted)] mt-1">Low Quality</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}