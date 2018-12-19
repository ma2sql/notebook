import C from './constants'

export const color = (state={}, action) => {
  switch (action.type) {
    case C.ADD_COLOR:
      return {
        id: action.id,
        title: action.title,
        color: action.color,
        timestamp: action.timestamp,
        rating: 0
      }
    case C.RATE_COLOR:
      return (state.id !== action.id) ?
        state:
        {
          ...state,
          rating: action.rating
        }
    default:
      return state
  }
}

export const colors = (state={}, action) => {
  switch (action.type) {
    case C.ADD_COLOR:
      return [
        ...state,
        color({}, action)
      ]
    case C.RATE_COLOR:
      return state.map(
        c => color(c, action)
      )
    case C.REMOVE_COLOR:
      return state.filter(
        c => c.id !== action.id
      )
    default:
      return state
  }
}

export const sort = (state="SORTED_BY_DATE", action) => {
  return ""
}

const action = {
  type: "ADD_COLOR",
  id: "4243e1p0-9abl-4e90-95p4-8001l8yf3036",
  color: "#0000FF",
  title: "큰 파랑",
  timestamp: "Thu Mar 10 2016 01:11:12 GMT-0800 (PST)"
}
