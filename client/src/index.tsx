// import { useState, useEffect } from "react";
import React, { useCallback, useEffect } from "react"
import { render } from "react-dom"
import Excalidraw from "@excalidraw/excalidraw"

import { ConfigProps } from "./types"
import { getJsonScript, noop } from "./utils"
import { CollaborationCommunicator, ReplayCommunicator } from "./communication"
import { useEventListener } from "./hooks/useEventListener"
import { getInitialData, getInitialReplayData, useSaveState } from "./persistance/initial"
import ReconnectingWebSocket from "reconnectingwebsocket"
import { saveLibrary, useLoadLibraries } from "./persistance/library"

import "./style.css"
import { useCommunicatorExcalidrawRef, useConnectionState } from "./communication/communicator"
import ReplayControls from "./components/ReplayControls"
import TopRightUI from "./components/TopRightUI"
import { dispatchLtiFrameMessage } from "./lti"
import { EventKey } from "./events"

window.React = React

// welcome messages for dev tools
console.log(
  [
    "%cWelcome Developer!",
    "%c\n\nTo hook into the Excalidraw API, you can use 'window.draw.current'. ",
    "For documentation on what's available there, have a look at ",
    "https://github.com/excalidraw/excalidraw/tree/master/src/packages/excalidraw",
  ].join(""),
  "color: palevioletred; font-size: xx-large",
  "color: inherit; font-size: inherit"
)

// moodle makes the frame very small. I don't know if other LMS do this as well. When the
// LTI Message Handler plugin is installed, this will resize the frame to an appropriate
// size. See https://moodle.org/plugins/ltisource_message_handler
const adjustFrameHeight = () => dispatchLtiFrameMessage("lti.frameResize", { height: "calc(100vh - 75px)" })
adjustFrameHeight()
window.addEventListener("resize", adjustFrameHeight)

const defaultConfig: ConfigProps = {
  BROADCAST_RESOLUTION_THROTTLE_MSEC: 150,
  ELEMENT_UPDATES_BEFORE_FULL_RESYNC: 50,
  IS_REPLAY_MODE: false,
  LANGUAGE_CODE: "en-US",
  // When you set the MAX_FILE_SIZE_B64, please be aware that
  // your servers upload limit should be slightly higher due to
  // the metadata that is also attached when uploading a file.
  MAX_FILE_SIZE_B64: 5_000_000,
  MAX_RETRY_WAIT_MSEC: 300_000,
  ROOM_NAME: "_default",
  SAVE_ROOM_MAX_WAIT_MSEC: 15_000,
  SHOW_QR_CODE: true,
  SOCKET_URL: "",
  UPLOAD_RETRY_TIMEOUT_MSEC: 1_000,
  USER_NAME: "",
}

const config: ConfigProps = { ...defaultConfig, ...getJsonScript("excalidraw-config") }
const msg: Record<string, string> = getJsonScript("custom-messages")

const initialData = config.IS_REPLAY_MODE ? getInitialReplayData() : getInitialData(config.ROOM_NAME)

const ws = new ReconnectingWebSocket(config.SOCKET_URL)
let communicator = config.IS_REPLAY_MODE
  ? new ReplayCommunicator(config, ws)
  : new CollaborationCommunicator(config, ws, initialData.files ?? {})

type WindowEK = EventKey<WindowEventMap>
type DocEK = EventKey<DocumentEventMap>

function IndexPage() {
  let draw = useCommunicatorExcalidrawRef(communicator)
  let connectionState = useConnectionState(communicator)
  useEffect(() => {
    window.draw = draw
  }, [draw])

  const saveStateToLocalStorage = config.IS_REPLAY_MODE ? useCallback(noop, []) : useSaveState(draw, config.ROOM_NAME)

  const saveToServerImmediately = config.IS_REPLAY_MODE
    ? useCallback(noop, [])
    : useCallback(() => (communicator as CollaborationCommunicator).saveRoomImmediately(), [communicator])

  const loadEnqueuedLibraries = useLoadLibraries(draw)

  useEventListener<WindowEventMap, WindowEK>(window, "focus", loadEnqueuedLibraries)
  useEventListener<WindowEventMap, WindowEK>(window, "blur", saveStateToLocalStorage)
  useEventListener<WindowEventMap, WindowEK>(window, "hashchange", saveStateToLocalStorage)
  useEventListener<WindowEventMap, WindowEK>(window, "beforeunload", saveStateToLocalStorage)
  useEventListener<WindowEventMap, WindowEK>(window, "beforeunload", saveToServerImmediately)
  useEventListener<DocumentEventMap, DocEK>(document, "visibilitychange", saveStateToLocalStorage)

  return connectionState == "CONNECTED" ? (
    <div className="excalidraw">
      <Excalidraw
        ref={draw}
        initialData={initialData}
        onPointerUpdate={communicator.broadcastCursorMovement}
        onChange={communicator.broadcastElements}
        UIOptions={{
          canvasActions: {
            loadScene: !!config.USER_IS_STAFF,
            clearCanvas: false,
          },
        }}
        viewModeEnabled={config.IS_REPLAY_MODE}
        autoFocus={true}
        handleKeyboardGlobally={true}
        langCode={config.LANGUAGE_CODE}
        onLibraryChange={saveLibrary}
        libraryReturnUrl={config.LIBRARY_RETURN_URL}
        renderTopRightUI={TopRightUI(config)}
      />
      {config.IS_REPLAY_MODE && <ReplayControls communicator={communicator as ReplayCommunicator} />}
    </div>
  ) : (
    <p style={{ margin: "1rem" }}>{msg.NOT_LOGGED_IN}</p>
  )
}

render(<IndexPage />, document.getElementById("app"))
