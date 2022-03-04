import { AppState, ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types/types"
import { ImportedDataState } from "@excalidraw/excalidraw/types/data/types"
import { serializeAsJSON } from "@excalidraw/excalidraw"
import { RefObject, useCallback } from "react"

import { BroadcastedExcalidrawElement } from "../types"
import { getJsonScript } from "../utils"
import { getLocalStorageJson } from "../utils"
import { reconcileElements } from "../reconciliation"
import { loadLibrary } from "./library"

/**
 * Get initial data for the room by merging the data from localStorage
 * and the remote data which is supplied by the server via the room html
 * (JSON script with ID `#initial-data`).
 *
 * @param roomName room name to get initial data for
 * @returns initial data for the room
 */
export function getInitialData(roomName: string): ImportedDataState {
  let elementsFromServer: BroadcastedExcalidrawElement[] = getJsonScript("initial-data", [])

  let localState: ImportedDataState = getLocalStorageJson(roomName)
  let localElements = localState?.elements ?? []
  let localAppState = {
    editingElement: null,
    resizingElement: null,
    draggingElement: null,
    ...localState?.appState,
  }

  return {
    elements: reconcileElements(localElements, elementsFromServer, localAppState),
    appState: localAppState,
    libraryItems: loadLibrary(),
  }
}

/**
 * @returns initial data for replay mode
 */
export function getInitialReplayData(): ImportedDataState {
  return {}
}

/**
 * A react hook which saves the state of the current room.
 *
 * @param apiRef a ref tot he excalidraw API
 * @param roomName room name to save a state for
 * @returns hook
 */
export function useSaveState(apiRef: RefObject<ExcalidrawImperativeAPI>, roomName: string) {
  return useCallback(() => {
    // if an element is deleted and the user closes the tab before it can sync to the
    // server, the deleted element will be restored on reload, because we do not save
    // deleted elements. is this a problem? how correct do we have to be here?
    const elements = apiRef.current?.getSceneElements() ?? []
    const appState: Partial<AppState> = { ...apiRef.current?.getAppState() }
    delete appState.collaborators
    localStorage.setItem(roomName, serializeAsJSON(elements, appState))
  }, [apiRef])
}
