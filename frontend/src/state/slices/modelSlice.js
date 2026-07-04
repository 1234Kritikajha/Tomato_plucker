import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  currentModel: 'tomato_model.keras',
  modelVersions: [],
  performance: {
    accuracy: 0,
    precision: 0,
    recall: 0,
    f1Score: 0,
  },
}

const modelSlice = createSlice({
  name: 'model',
  initialState,
  reducers: {
    setCurrentModel: (state, action) => {
      state.currentModel = action.payload
    },
    setModelVersions: (state, action) => {
      state.modelVersions = action.payload
    },
    setPerformance: (state, action) => {
      state.performance = { ...state.performance, ...action.payload }
    },
  },
})

export const { setCurrentModel, setModelVersions, setPerformance } = modelSlice.actions
export default modelSlice.reducer