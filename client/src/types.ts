import { ExcalidrawElement } from "@excalidraw/excalidraw/types/element/types"
import { AppState, Gesture } from "@excalidraw/excalidraw/types/types"

export type BroadcastedExcalidrawElement = ExcalidrawElement & {
  parent?: string
}

export type ReconciliationAppState = Pick<
  AppState,
  "editingElement" | "resizingElement" | "draggingElement"
>

export interface Pointer {
  x: number
  y: number
}

export interface PointerUpdateProps {
  pointer: Pointer
  button: "down" | "up"
  pointersMap?: Gesture["pointers"]
}

export interface UserColor {
  background: string
  stroke: string
}

export interface ConfigProps {
  BROADCAST_RESOLUTION: number
  ELEMENT_UPDATES_BEFORE_FULL_RESYNC: number
  INITIAL_DATA: BroadcastedExcalidrawElement[]
  SOCKET_URL: string
  USER_COLOR?: UserColor
  USER_NAME: string
  LANGUAGE_CODE: string
}

export enum WsState {
  CONNECTING = 0,
  OPEN = 1,
  CLOSING = 2,
  CLOSED = 3,
}