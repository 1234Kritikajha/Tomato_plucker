import React, { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

import PageShell from './components/layout/PageShell.jsx'

import LiveDetectionView from './views/LiveDetectionView.jsx'
import InferenceDashboardView from './views/InferenceDashboard.jsx'
import MonitoringView from './views/MonitoringView.jsx'
import SettingsView from './views/SettingsView.jsx'
import SystemLogsView from './views/SystemLogsView.jsx'
import ModelManagementView from './views/ModelManagementView.jsx'
import RetrainingView from './views/RetrainingView.jsx'
import TrainingMonitorView from './views/TrainingMonitorView.jsx'
import AnnotationsView from './views/AnnotationsView.jsx'
import LearningDatasetView from './views/LearningDatasetView.jsx'
import ActiveLearningView from './views/ActiveLearningView.jsx'
import UploadImageView from './views/UploadImageView.jsx'
import UploadVideoView from './views/UploadVideoView.jsx'
import AdminReviewQueueView from './views/AdminReviewQueueView.jsx'
import ReportView from './views/ReportView.jsx'

export default function App() {
  const [latestAnalysis, setLatestAnalysis] = useState(null)

  return (
    <PageShell>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<InferenceDashboardView />} />
        <Route path="/live" element={<LiveDetectionView />} />
        <Route path="/monitoring" element={<MonitoringView />} />
        <Route path="/settings" element={<SettingsView />} />
        <Route path="/system-logs" element={<SystemLogsView />} />
        <Route path="/models" element={<ModelManagementView />} />
        <Route path="/retraining" element={<RetrainingView />} />
        <Route path="/training-monitor" element={<TrainingMonitorView />} />
        <Route path="/annotations" element={<AnnotationsView />} />
        <Route path="/dataset" element={<LearningDatasetView />} />
        <Route path="/active-learning" element={<ActiveLearningView />} />
        <Route
          path="/upload-image"
          element={<UploadImageView onAnalysisComplete={setLatestAnalysis} />}
        />
        <Route path="/upload-video" element={<UploadVideoView />} />
        <Route path="/admin-review-queue" element={<AdminReviewQueueView />} />
        <Route path="/reports" element={<ReportView latestAnalysis={latestAnalysis} />} />
      </Routes>
    </PageShell>
  )
}
