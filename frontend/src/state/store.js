import { configureStore } from '@reduxjs/toolkit'
import uiReducer from './slices/uiSlice'
import inferenceReducer from './slices/inferenceSlice'
import learningReducer from './slices/learningSlice'
import modelReducer from './slices/modelSlice'

export const store = configureStore({
  reducer: {
    ui: uiReducer,
    inference: inferenceReducer,
    learning: learningReducer,
    model: modelReducer,
  },
})

export default store