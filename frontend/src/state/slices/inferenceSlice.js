import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  detections: [],
  isProcessing: false,
  currentImage: null,
  stats: {
    totalDetections: 0,
    ripeHealthy: 0,
    avgConfidence: 0,
  },
}

const inferenceSlice = createSlice({
  name: 'inference',
  initialState,
  reducers: {
    setDetections: (state, action) => {
      state.detections = action.payload
    },
    setProcessing: (state, action) => {
      state.isProcessing = action.payload
    },
    setCurrentImage: (state, action) => {
      state.currentImage = action.payload
    },
    updateStats: (state, action) => {
      state.stats = { ...state.stats, ...action.payload }
    },
  },
})

export const { setDetections, setProcessing, setCurrentImage, updateStats } = inferenceSlice.actions
export default inferenceSlice.reducer