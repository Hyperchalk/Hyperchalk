// import { useState, useEffect } from "react";
import React from "react"
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
import { dispatchLtiFrameMessage } from "./lti"

window.React = React

// moodle makes the frame very small. I don't know if other LMS do this as well. When the
// LTI Message Handler plugin is installed, this will resize the frame to an appropriate
// size. See https://moodle.org/plugins/ltisource_message_handler
const resize90vh = () => dispatchLtiFrameMessage("lti.frameResize", { height: "90vh" })
resize90vh()
window.addEventListener("resize", resize90vh)

const defaultConfig: ConfigProps = {
  BROADCAST_RESOLUTION: 150,
  ELEMENT_UPDATES_BEFORE_FULL_RESYNC: 50,
  IS_REPLAY_MODE: false,
  LANGUAGE_CODE: "en-US",
  ROOM_NAME: "_default",
  SAVE_ROOM_MAX_WAIT: 15000,
  SOCKET_URL: "",
  USER_NAME: "",
}

const config: ConfigProps = { ...defaultConfig, ...getJsonScript("excalidraw-config") }
const msg: Record<string, string> = { ...getJsonScript("custom-messages") }

const initialData = config.IS_REPLAY_MODE
  ? getInitialReplayData()
  : getInitialData(config.ROOM_NAME)

const ws = new ReconnectingWebSocket(config.SOCKET_URL)
let communicator = config.IS_REPLAY_MODE
  ? new ReplayCommunicator(config, ws)
  : new CollaborationCommunicator(config, ws)

function IndexPage() {
  let draw = useCommunicatorExcalidrawRef(communicator)
  let connectionState = useConnectionState(communicator)
  window.draw = draw

  const saveStateToLocalStorage = config.IS_REPLAY_MODE
    ? noop
    : useSaveState(draw, config.ROOM_NAME)

  const loadEnqueuedLibraries = useLoadLibraries(draw)

  useEventListener("blur", saveStateToLocalStorage, window)
  useEventListener("focus", loadEnqueuedLibraries, window)
  useEventListener("hashchange", saveStateToLocalStorage, window)
  useEventListener("beforeunload", saveStateToLocalStorage, window)
  useEventListener("visibilitychange", saveStateToLocalStorage, document)

  return connectionState == "CONNECTED" ? (
    <div className="excalidraw">
      <Excalidraw
        ref={draw}
        initialData={initialData}
        onPointerUpdate={communicator.broadcastCursorMovement}
        onChange={communicator.broadcastElements}
        UIOptions={{
          canvasActions: {
            loadScene: false,
            clearCanvas: false,
          },
        }}
        viewModeEnabled={config.IS_REPLAY_MODE}
        autoFocus={true}
        handleKeyboardGlobally={true}
        langCode={config.LANGUAGE_CODE}
        onLibraryChange={saveLibrary}
        libraryReturnUrl={config.LIBRARY_RETURN_URL}
      />
      {config.IS_REPLAY_MODE && (
        <ReplayControls communicator={communicator as ReplayCommunicator} />
      )}
    </div>
  ) : (
    <p style={{ margin: "1rem" }}>{msg.NOT_LOGGED_IN}</p>
  )
}

render(<IndexPage />, document.getElementById("app"))
