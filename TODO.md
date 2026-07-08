# Tomato Plucker - Connection Task Progress

- [x] Inspect backend routers for metrics endpoints used by dashboards

- [x] Update frontend MonitoringView to call:
  - [x] GET /api/metrics/summary
  - [x] GET /api/metrics/realtime
- [x] Update frontend InferenceDashboard to call:
  - [x] GET /api/metrics/summary
  - [x] GET /api/metrics/performance
  - [x] GET /api/metrics/historical?days=1

- [x] Ensure API client base URL matches backend (uses existing http://192.168.0.152:8000/api)
- [ ] Manual testing steps:
  - [ ] Start backend
  - [ ] Start frontend
  - [ ] Verify /live
  - [ ] Verify /monitoring shows live metrics
  - [ ] Verify /dashboard shows real metrics

