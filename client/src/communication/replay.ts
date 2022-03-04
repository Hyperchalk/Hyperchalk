import ReconnectingWebSocket from "reconnectingwebsocket"

import Communicator, { CommunicatorMessage } from "./communicator"
import { ConfigProps } from "../types"
import { Dispatch, SetStateAction, useState } from "react"

// #region message types
interface ResetScene {
  eventtype: "reset_scene"
}

type ControlTypes = "start_replay" | "pause_replay" | "restart_replay"

interface ControlMessage {
  eventtype: ControlTypes
}

type ReplayMessage = CommunicatorMessage | ResetScene | ControlMessage
// #endregion message types

type ControlStates = "play" | "pause"

type ControlStateSetter = Dispatch<SetStateAction<ControlStates>>

/**
 * This Communicator is instantiated when we are in replay mode.
 */
export default class ReplayCommunicator extends Communicator {
  private _setControlState?: ControlStateSetter
  controlState: ControlStates = "play"

  constructor(config: ConfigProps, ws: ReconnectingWebSocket) {
    super(config, ws)
  }

  set controlStateSetter(setter: ControlStateSetter) {
    this._setControlState = setter
  }

  protected routeMessage<MsgType extends ReplayMessage>(message: MsgType) {
    let messageWasRouted = super.routeMessage(message as CommunicatorMessage)
    if (!messageWasRouted) {
      switch (message.eventtype) {
        case "reset_scene":
          this.resetScene()
          return true
        case "start_replay":
          this._setControlState?.("play")
          return true
        case "pause_replay":
          this._setControlState?.("pause")
          return true
      }
    }
    return false
  }

  /**
   * Resets the scene. This is only for replay mode.
   */
  private resetScene() {
    this.broadcastedVersions = new Map()
    this.excalidrawApi?.updateScene({ elements: [], commitToHistory: false })
  }

  sendControlState(eventtype: ControlTypes) {
    this.ws.send(JSON.stringify({ eventtype }))
  }
}

/**
 * React hook to communicate control button presses to the server
 *
 * @param communicator an instance of ReplayCommunicator that will send control requests
 * @returns custom hook
 */
export function useControlState(
  communicator: ReplayCommunicator
): [ControlStates, (newState: ControlTypes) => void] {
  const [controlState, setControlState] = useState<ControlStates>(communicator.controlState)
  communicator.controlStateSetter = setControlState
  const sendControlState = (newState: ControlTypes) => {
    communicator.sendControlState(newState)
  }
  return [controlState, sendControlState]
}
