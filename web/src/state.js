export const STATUS = {
  EMPTY: 'empty',
  FETCHING: 'fetching',
  READY: 'ready',
  ERROR: 'error',
}

export const initialState = {
  status: STATUS.EMPTY,
  files: [],
  activeId: null,
  preview: null,
  message: '',
  error: '',
  previewLoading: false,
}

export function reducer(state, action) {
  switch (action.type) {
    case 'files/loaded':
      return { ...state, files: action.files }

    case 'preview/loading':
      return { ...state, activeId: action.id, previewLoading: true, error: '' }

    case 'preview/loaded':
      return {
        ...state,
        activeId: action.preview.id,
        preview: action.preview,
        previewLoading: false,
      }

    case 'preview/clear':
      return { ...state, activeId: null, preview: null, previewLoading: false }

    case 'fetch/start':
      return { ...state, status: STATUS.FETCHING, message: 'Fetching…', error: '' }

    case 'fetch/error':
      return { ...state, status: STATUS.ERROR, message: '', error: action.error }

    case 'fetch/success':
      return {
        ...state,
        status: STATUS.READY,
        message: action.message,
        error: '',
        files: action.files,
        activeId: action.preview.id,
        preview: action.preview,
        previewLoading: false,
      }

    default:
      return state
  }
}
