// import { useState, useEffect } from "react";
import React, { useRef } from "react"
import { render } from "react-dom"
import Excalidraw from "@excalidraw/excalidraw"
import { AppState, Gesture } from "@excalidraw/excalidraw/types/types"
import throttle from "lodash.throttle"
import ReconnectingWebSocket from "reconnectingwebsocket"

import "./style.css"
import { ExcalidrawElement } from "@excalidraw/excalidraw/types/element/types"
window.React = React

const defaultConfig = {
  SOCKET_URL: "",
  BROADCAST_RESOLUTION: 200,
}

const config: typeof defaultConfig = Object.assign(
  {},
  defaultConfig,
  JSON.parse(document.getElementById("excalidraw-config").innerText)
)

let ws = null

interface PointerUpdateProps {
  pointer: { x: number; y: number }
  button: "down" | "up"
  pointersMap: Gesture["pointers"]
}

function setupWebSocket() {
  ws = new ReconnectingWebSocket(config.SOCKET_URL)
}

function broadcastCursorMovement({ pointer }: PointerUpdateProps) {
  for (let key in pointer) {
    pointer[key] |= 0
  }
  ws && ws.send(JSON.stringify({ eventtype: "consolelog", pointer }))
}

function broadcastObjectUpdate(elements: readonly ExcalidrawElement[], appState: AppState) {
  console.log(elements)
  ws && ws.send(JSON.stringify({ eventtype: "consolelog", state: elements }))
}

function IndexPage() {
  let draw = useRef(null)
  return (
    <Excalidraw
      ref={draw}
      onPointerUpdate={throttle(broadcastCursorMovement, config.BROADCAST_RESOLUTION)}
      onChange={throttle(broadcastObjectUpdate, config.BROADCAST_RESOLUTION)}
      onCollabButtonClick={setupWebSocket}
    />
  )
}

render(<IndexPage />, document.getElementById("app"))
