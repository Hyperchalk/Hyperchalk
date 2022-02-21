// import { useState, useEffect } from "react";
import React, { useCallback, useRef } from "react"
import { render } from "react-dom"
import Excalidraw, { serializeAsJSON } from "@excalidraw/excalidraw"
import { ExcalidrawImperativeAPI, LibraryItems } from "@excalidraw/excalidraw/types/types"
import { ConfigProps } from "./types"

import "./style.css"
import { getJsonScript } from "./utils"
import { CollabAPI } from "./collab/collaboration"
import { useEventListener } from "./hooks/useEventListener"
import { reconcileElements } from "./collab/reconciliation"
import { ImportedDataState } from "@excalidraw/excalidraw/types/data/types"

window.React = React

const defaultConfig: ConfigProps = {
  BROADCAST_RESOLUTION: 150,
  ELEMENT_UPDATES_BEFORE_FULL_RESYNC: 50,
  INITIAL_DATA: [],
  SOCKET_URL: "",
  USER_NAME: "",
  LANGUAGE_CODE: "en-US",
}

const config: ConfigProps = Object.assign({}, defaultConfig, getJsonScript("excalidraw-config"))

let params = new URLSearchParams(window.location.search.slice(1))
let hash = new URLSearchParams(window.location.hash.slice(1))

function updateHashParams(name: string, value: string) {
  hash.set(name, value)
  window.location.hash = hash.toString()
}

// TODO: if a library was added, load it and update the URL hash
// TODO: debounced save_room executions. they are only
//       sent to the server and will not be broadcasted.

function saveLibrary(items: LibraryItems) {
  localStorage.setItem("_library", JSON.stringify(items))
}

function loadLibrary(): LibraryItems {
  return JSON.parse(localStorage.getItem("_library") ?? "[]")
}

let localData: ImportedDataState = JSON.parse(localStorage.getItem(params.get("room")!) ?? "{}")

let importedAppState = Object.assign(
  { editingElement: null, resizingElement: null, draggingElement: null },
  localData?.appState ?? {}
)

let initialData = {
  elements: reconcileElements(localData?.elements ?? [], config.INITIAL_DATA, importedAppState),
  appState: importedAppState,
  libraryItems: loadLibrary(),
}

let collabAPI = new CollabAPI(config)

function IndexPage() {
  let draw = useRef<ExcalidrawImperativeAPI>(null)
  collabAPI.excalidrawApiRef = draw
  window.draw = draw

  const saveStateToLocalStorage = useCallback(() => {
    // if an element is deleted and the user closes the tab before it can sync to the
    // server, the deleted element will be restored on reload, because we do not save
    // deleted elements. is this a problem? how correct do we have to be here?
    const elements = draw.current?.getSceneElements() ?? []
    const appState = draw.current?.getAppState() ?? {}
    localStorage.setItem(params.get("room")!, serializeAsJSON(elements, appState))
  }, [draw])

  useEventListener("blur", saveStateToLocalStorage, window)
  useEventListener("hashchange", saveStateToLocalStorage, window)
  useEventListener("beforeunload", saveStateToLocalStorage, window)
  useEventListener("visibilitychange", saveStateToLocalStorage, document)
  // TODO: debounced or throttled save on change

  return (
    <Excalidraw
      ref={draw}
      initialData={initialData}
      onPointerUpdate={collabAPI.broadcastCursorMovement}
      onChange={collabAPI.broadcastElements}
      UIOptions={{
        canvasActions: {
          loadScene: false,
          clearCanvas: false,
        },
      }}
      autoFocus={true}
      handleKeyboardGlobally={true}
      langCode={config.LANGUAGE_CODE}
      onLibraryChange={saveLibrary}
    />
  )
}

render(<IndexPage />, document.getElementById("app"))
