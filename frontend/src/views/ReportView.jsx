import { useMemo, useState } from 'react'
import ThemeToggle from '../components/ThemeToggle.jsx'
import apiClient from '../api/client.js'

const getFilenameFromReport = (report) => {
  if (report?.report_path) return report.report_path.split('/').pop()
  if (report?.download_url) return report.download_url.split('/').pop()
  return null
}

export default function ReportView({ latestAnalysis }) {
  const [generating, setGenerating] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)

  const summary = latestAnalysis?.result?.summary
  const filename = useMemo(() => getFilenameFromReport(report), [report])
  const hasAnalysis = Boolean(latestAnalysis?.file && latestAnalysis?.result)

  const handleGenerateReport = async () => {
    if (!latestAnalysis?.file) {
      setError('Analyze an image first, then generate the report here.')
      return
    }

    setGenerating(true)
    setError(null)
    try {
      const result = await apiClient.generateReport(latestAnalysis.file)
      setReport(result)
    } catch (err) {
      setError(err?.message || 'Failed to generate report.')
    } finally {
      setGenerating(false)
    }
  }

  const handleDownloadReport = async () => {
    if (!filename) return

    setDownloading(true)
    setError(null)
    try {
      await apiClient.downloadReport(filename)
    } catch (err) {
      setError(err?.message || 'Failed to download report.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <section className="relative animate-fadeIn">
      <div className="absolute right-0 top-0">
        <ThemeToggle />
      </div>

      <div className="pt-6">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-[var(--text-primary)] to-[var(--text-secondary)] bg-clip-text text-transparent">
          Reports
        </h1>
        <p className="mt-2 text-sm text-[var(--text-muted)]">
          Generate and download the PDF for the latest analyzed tomato image.
        </p>

        <div className="mt-8 space-y-6">
          <div className="card-hover rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] p-6 shadow-lg">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-lg font-semibold text-[var(--text-primary)]">Latest Analysis</h3>
                <div className="mt-1 text-sm text-[var(--text-muted)]">
                  {hasAnalysis ? latestAnalysis.file.name : 'No image has been analyzed in this session.'}
                </div>
              </div>
              <button
                type="button"
                onClick={handleGenerateReport}
                disabled={!hasAnalysis || generating}
                className="btn btn-primary"
              >
                {generating ? 'Generating...' : 'Generate Report'}
              </button>
            </div>

            {summary && (
              <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
                <div className="rounded-lg bg-[var(--bg-card-hover)] p-4 text-center">
                  <div className="text-2xl font-bold text-[var(--accent-primary)]">{summary.total_tomatoes_detected}</div>
                  <div className="mt-1 text-xs text-[var(--text-muted)]">Total Tomatoes</div>
                </div>
                <div className="rounded-lg bg-[var(--bg-card-hover)] p-4 text-center">
                  <div className="text-2xl font-bold text-[var(--neon-blue)]">{summary.plucking_decisions?.should_pluck ?? 0}</div>
                  <div className="mt-1 text-xs text-[var(--text-muted)]">Should Pluck</div>
                </div>
                <div className="rounded-lg bg-[var(--bg-card-hover)] p-4 text-center">
                  <div className="text-2xl font-bold text-[var(--neon-orange)]">{summary.plucking_decisions?.should_not_pluck ?? 0}</div>
                  <div className="mt-1 text-xs text-[var(--text-muted)]">Don't Pluck</div>
                </div>
                <div className="rounded-lg bg-[var(--bg-card-hover)] p-4 text-center">
                  <div className="text-2xl font-bold text-[var(--text-primary)]">
                    {((summary.confidence_metrics?.average_overall_confidence ?? 0) * 100).toFixed(1)}%
                  </div>
                  <div className="mt-1 text-xs text-[var(--text-muted)]">Avg Confidence</div>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {report && (
            <div className="card-hover rounded-xl border border-[var(--border-color)] bg-[var(--bg-card)] p-6 shadow-lg">
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">Generated Report</h3>
              <div className="mt-2 text-sm text-[var(--text-muted)]">
                {filename || 'Report is ready.'}
              </div>
              <div className="mt-6 flex justify-end">
                <button
                  type="button"
                  onClick={handleDownloadReport}
                  disabled={!filename || downloading}
                  className="btn btn-secondary"
                >
                  {downloading ? 'Downloading...' : 'Download Report'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
