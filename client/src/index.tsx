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
// TODO: persist locally and remotely
// #endregion init

let collabAPI = new CollabAPI(config)

function IndexPage() {
  let draw = useRef<ExcalidrawImperativeAPI>(null)
  collabAPI.excalidrawApiRef = draw

  return (
    <Excalidraw
      ref={draw}
      initialData={{ elements: config.INITIAL_DATA }}
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
    />
  )
}

render(<IndexPage />, document.getElementById("app"))
