# TODO - Tomato Plucker (Backend + Frontend Sync, Camera, Upload/Report, Data Augmentation, Training)

## A) Root-cause analysis tasks (Backend/Frontend sync + broken flows)
1. [ ] Confirm frontend→backend base URL:
   - `frontend/src/api/client.js` uses default `http://localhost:8000/api`.
   - Verify every frontend API call matches backend mount paths (all endpoints should be under `/api/...`).
2. [ ] Fix any endpoint mismatches:
   - Check `generateReport()` and `downloadReport()` paths.
   - Ensure frontend is calling:
     - `POST /api/predict` (for analysis)
     - `POST /api/generate_report` (for report generation)
     - `GET /api/reports/download/{filename}` (for report download)
3. [ ] Verify server routers are correctly mounted:
   - `backend/app/main.py` includes `predict_router` with `prefix="/api"`.
   - Ensure no other router file duplicates/overrides the same endpoints.
4. [ ] Verify frontend state wiring:
   - Upload/analyze response handling should store “latest analyzed image + latest response” in state.
   - Sidebar “Report” link should use that stored state (not a missing/old variable).
5. [ ] Log actual network calls:
   - Use browser Network tab to capture failed requests (404/500/CORS).
   - Ensure request payload key names match backend expectations (e.g., `formData.append('file', file)`).

## B) Upload → Analysis → (Remove old report generation) → Sidebar Report flow
6. [ ] Locate current sidebar/report implementation:
   - Inspect `frontend/src/App.jsx` routing + sidebar component (find the route for Report).
   - Inspect `frontend/src/views/InferenceDashboard.jsx` and `frontend/src/views/MonitoringView.jsx` for any existing “report generation” during upload.
7. [ ] Remove report generation from upload/analyze path:
   - Upload/analyze should only call prediction (`POST /api/predict`) and update UI with `detections` + `summary`.
8. [ ] Implement sidebar Report navigation to generate report:
   - On clicking sidebar “Report” link, render report page.
   - Add a “Generate Report” button that calls:
     - `apiClient.generateReport(latestAnalyzedFile)` OR (if backend requires upload file) re-upload the same image from client state.
9. [ ] Add functional “Report download” button on report page:
   - After report generation returns `download_url` (or `{ report_path, download_url }`), show a bottom button:
     - “Download Report”
   - On click call `apiClient.downloadReport(filename)` OR directly open `download_url`.
10. [ ] Ensure report page works without full page refresh:
   - If user reloads, fallback gracefully (disable generate/download until a new analysis exists).

## C) Camera functionality + UI theming (Front/Rear switch styling)
11. [ ] Ensure camera works in your environment:
   - `frontend/src/utils/cameraCapture.js` requires HTTPS (or localhost).
   - If you run frontend behind a non-HTTPS URL, camera capture will fail.
12. [ ] Fix front/rear camera switching:
   - Ensure `facingMode` state updates (`environment` ⇄ `user`).
   - When switching while not running, selection should apply to next start.
   - If you want instant switch while running, implement stop+restart on facingMode change.
13. [ ] Make buttons match card background for dark/light modes:
   - In `frontend/src/views/LiveDetectionView.jsx`, update the dropdown/options button classes so they inherit/align with card background.
   - Implement explicit theme-aware backgrounds:
     - dark mode: use `dark:bg-[your-card-bg]` and correct border/text
     - light mode: use `bg-[your-card-bg]` and correct border/text
14. [ ] Ensure overlay/canvas stays aligned:
   - Validate canvas sizing uses actual rendered video box size (object-fit cover).

## D) Dataset building (2k images per class from internet) + augmentation to 50k–60k per class
15. [ ] Define dataset classes + folder structure:
   - Decide class names used by YOLO model.
   - Create `backend/storage/dataset/raw/` and `backend/storage/dataset/organized/` (or project pipeline equivalents).
16. [ ] Download ~2,000 images per class from internet:
   - Create script/pipeline step that fetches images (with rate limits) into `raw/{class}/`.
17. [ ] Data cleaning:
   - Remove corrupted images / wrong formats.
   - Deduplicate via hash (sha256).
18. [ ] Annotation strategy:
   - If you have annotation sources, convert to YOLO format.
   - Otherwise, integrate/prepare labeling pipeline.
19. [ ] Augmentation to reach 50k–60k images per class:
   - Use deterministic augmentation set (rotation, crop, brightness/contrast, blur, noise, perspective, random erasing, etc.).
   - Ensure bounding boxes are transformed correctly for YOLO labels.
20. [ ] Generate YOLO training split:
   - Create `train/val/test` for each class.
   - Verify label counts match images count.
21. [ ] Sanity checks:
   - Visualize random samples with bboxes after augmentation.
   - Ensure no empty/invalid labels.

## E) Train model
22. [ ] Configure training:
   - Update YOLO training config (epochs, batch size, img size, learning rate, augmentation flags).
   - Ensure correct paths to augmented dataset.
23. [ ] Train:
   - Run existing training entry points (e.g., `backend/tools/train_model.py` or YOLO training script used in repo).
24. [ ] Evaluate:
   - Run evaluation step and generate metrics/summary.
25. [ ] Export/activate model:
   - Save best checkpoint to `backend/storage/models/`.
   - Update model loader logic if required.

## F) End-to-end verification (UI + backend + model)
26. [ ] Backend smoke test:
   - `POST /api/predict` with a known image.
   - Confirm response contains `detections` and `summary`.
27. [ ] Report smoke test:
   - Call `POST /api/generate_report` with same image.
   - Confirm `GET /api/reports/download/{filename}` returns PDF.
28. [ ] Frontend workflow test:
   - Upload → inference results show.
   - Sidebar Report link → generate report → download button works.
29. [ ] Live camera test:
   - Start camera works.
   - Front/Rear switch works.
   - Overlay bounding boxes render consistently.

## G) Final “done” criteria
30. [ ] Backend and frontend flows are synced (no broken navigation/API mismatches).
31. [ ] Report generation happens only from sidebar Report page.
32. [ ] Report download button at bottom of report page is functional.
33. [ ] Camera is functional and UI matches dark/light mode card background.
34. [ ] Dataset: ~2k raw images/class + augmented to 50k–60k/class.
35. [ ] Model trains successfully and inference uses the updated model.


