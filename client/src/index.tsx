// import { useState, useEffect } from "react";
import React, { useRef } from "react"
import { render } from "react-dom"
import Excalidraw from "@excalidraw/excalidraw"
import { AppState, ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types/types"
import { ExcalidrawElement } from "@excalidraw/excalidraw/types/element/types"
import throttle from "lodash.throttle"
import { ConfigProps } from "./types"

import "./style.css"
import { getJsonScript } from "./utils"
import { CollabAPI } from "./collab/collaboration"

window.React = React

// #region init
const defaultConfig: ConfigProps = {
  BROADCAST_RESOLUTION: 150,
  ELEMENT_UPDATES_BEFORE_FULL_RESYNC: 50,
  INITIAL_DATA: [],
  SOCKET_URL: "",
  USER_COLOR: { background: "#aaa", stroke: "#444" },
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
// TODO: sync data over tabs and on window events? (see syncData() excalidraw.index ~353)
//       -> before unload, on blur, on visibility change, on hash change
// TODO: make libraries work
// TODO: make deletion work
// #endregion init

function IndexPage() {
  let draw = useRef<ExcalidrawImperativeAPI>(null)
  window.draw = draw

  let collabAPI = useRef(new CollabAPI(config, draw))

  const throttledBroadcastCursorMovement = throttle(
    collabAPI.current.broadcastCursorMovement.bind(collabAPI.current),
    config.BROADCAST_RESOLUTION
  )

  const throttledBroadcastObjectUpdate = throttle(
    collabAPI.current.broadcastElements.bind(collabAPI.current),
    config.BROADCAST_RESOLUTION,
    {
      leading: false,
      trailing: true,
    }
  )

  // function storeElements(elements: readonly ExcalidrawElement[]) {
  //   // TODO: persist locally and remotely
  // }

  // const throttledStoreElements = throttle(storeElements, config.ROOM_SAVE_FREQUENCY, {
  //   leading: false,
  //   trailing: true,
  // })

  function stateChanged(elements: readonly ExcalidrawElement[], appState: AppState) {
    // throttledStoreElements(elements)
    throttledBroadcastObjectUpdate(elements, appState)
    // diffElements(elements)
    // TODO: throttle function individually
  }

  return (
    <Excalidraw
      ref={draw}
      initialData={{ elements: config.INITIAL_DATA }}
      onPointerUpdate={throttledBroadcastCursorMovement}
      // onChange={throttle(stateChanged, config.BROADCAST_RESOLUTION, {
      //   leading: false,
      //   trailing: true,
      // })}
      onChange={stateChanged}
      // onCollabButtonClick={setupWebSocket}
      UIOptions={{
        canvasActions: {
          loadScene: false,
          clearCanvas: false,
        },
      }}
      autoFocus={true}
      handleKeyboardGlobally={true}
      langCode={config.LANGUAGE_CODE}
    />
  )
}

render(<IndexPage />, document.getElementById("app"))
