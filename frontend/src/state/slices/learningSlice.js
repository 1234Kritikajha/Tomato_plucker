import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  pendingSamples: [],
  trainingProgress: 0,
  isTraining: false,
  models: [],
}

const learningSlice = createSlice({
  name: 'learning',
  initialState,
  reducers: {
    setPendingSamples: (state, action) => {
      state.pendingSamples = action.payload
    },
    setTrainingProgress: (state, action) => {
      state.trainingProgress = action.payload
    },
    setTraining: (state, action) => {
      state.isTraining = action.payload
    },
    setModels: (state, action) => {
      state.models = action.payload
    },
  },
})

export const { setPendingSamples, setTrainingProgress, setTraining, setModels } = learningSlice.actions
export default learningSlice.reducer