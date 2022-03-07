import ReconnectingWebSocket from "reconnectingwebsocket"

import Communicator, { CommunicatorMessage } from "./communicator"
import { ConfigProps } from "../types"
import { Dispatch, SetStateAction, useEffect, useState } from "react"

// #region message types
interface ResetScene {
  eventtype: "reset_scene"
  steps?: number
}

type ControlTypes = "start_replay" | "pause_replay" | "restart_replay"

interface ControlMessage {
  eventtype: ControlTypes
}

type ReplayMessage = CommunicatorMessage | ResetScene | ControlMessage
// #endregion message types

type ControlStates = "play" | "pause"

type ControlStateSetter = Dispatch<SetStateAction<ControlStates>>
type StepSetter = Dispatch<SetStateAction<number>>

/**
 * This Communicator is instantiated when we are in replay mode.
 */
export default class ReplayCommunicator extends Communicator {
  private _setControlState?: ControlStateSetter
  private _setCurrentStep?: StepSetter
  controlState: ControlStates = "pause"
  steps = 0

  constructor(config: ConfigProps, ws: ReconnectingWebSocket) {
    super(config, ws)
  }

  set controlStateSetter(setter: ControlStateSetter) {
    this._setControlState = setter
  }

  set currentStepSetter(setter: StepSetter) {
    this._setCurrentStep = setter
  }

  protected routeMessage<MsgType extends ReplayMessage>(message: MsgType) {
    if (["collaborator_change", "elements_changed", "full_sync"].indexOf(message.eventtype) > -1) {
      this._setCurrentStep?.((current) => current + 1)
    }
    let messageWasRouted = super.routeMessage(message as CommunicatorMessage)
    if (!messageWasRouted) {
      switch (message.eventtype) {
        case "reset_scene":
          this.resetScene(message.steps ?? 0)
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
  private resetScene(steps: number) {
    this.broadcastedVersions = new Map()
    this.excalidrawApi?.updateScene({ elements: [], commitToHistory: false })
    this.steps = steps
    this._setCurrentStep?.(0)
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
  useEffect(() => {
    communicator.controlStateSetter = setControlState
  }, [communicator])
  const sendControlState = (newState: ControlTypes) => {
    communicator.sendControlState(newState)
  }
  return [controlState, sendControlState]
}

/**
 * Replay progress state hook
 *
 * @param communicator
 * @returns the current progress in percent
 */
export function useReplayProgress(communicator: ReplayCommunicator): number {
  let [currentStep, setCurrentStep] = useState(0)
  useEffect(() => {
    communicator.currentStepSetter = setCurrentStep
  }, [communicator])
  return (currentStep / communicator.steps) * 100 || 0
}
