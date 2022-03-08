import { useRef, useState } from "react"
import ReconnectingWebSocket from "reconnectingwebsocket"

import { ConfigProps } from "../types"
import { useEventEmitter } from "../hooks/useEventEmitter"
import Communicator, { CommunicatorEventMap, CommunicatorMessage } from "./communicator"

// #region message types
interface ResetScene {
  eventtype: "reset_scene"
  duration?: number
}

type ControlTypes = "start_replay" | "pause_replay" | "restart_replay"

interface ControlMessage {
  eventtype: ControlTypes
}

type ReplayMessage = CommunicatorMessage | ResetScene | ControlMessage
// #endregion message types

type ControlStates = "play" | "pause"

export interface ReplayCommunicatorEventMap extends CommunicatorEventMap {
  controlStateChanged: { state: ControlStates }
  reset: { duration: number }
}

/**
 * This Communicator is instantiated when we are in replay mode.
 */
export default class ReplayCommunicator extends Communicator<ReplayCommunicatorEventMap> {
  controlState: ControlStates = "pause"
  duration = 0

  constructor(config: ConfigProps, ws: ReconnectingWebSocket) {
    super(config, ws)
  }

  protected routeMessage<MsgType extends ReplayMessage>(message: MsgType) {
    let messageWasRouted = super.routeMessage(message as CommunicatorMessage)
    if (!messageWasRouted) {
      switch (message.eventtype) {
        case "reset_scene":
          this.resetScene(message.duration ?? 0)
          return true
        case "start_replay":
          this.emit("controlStateChanged", { state: "play" })
          return true
        case "pause_replay":
          this.emit("controlStateChanged", { state: "pause" })
          return true
      }
    }
    return false
  }

  /**
   * Resets the scene. This is only for replay mode.
   */
  private resetScene(duration: number) {
    this.broadcastedVersions = new Map()
    this.excalidrawApi?.updateScene({ elements: [], commitToHistory: false })
    this.duration = duration
    this.emit("reset", { duration })
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
  useEventEmitter(communicator, "controlStateChanged", (event) => {
    setControlState(event.state)
  })
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
export function useReplayProgress(communicator: ReplayCommunicator): [number, number] {
  let [duration, setDuration] = useState(0)
  let [time, setTime] = useState(0)
  let interval = useRef<number | null>(null)

  let stop = () => {
    interval.current !== null && clearInterval(interval.current)
  }

  const start = () => {
    interval.current = setInterval(() => {
      setTime((time) => time + 1)
    }, 1000)
    return stop
  }

  useEventEmitter(communicator, "reset", (event) => {
    setTime(0)
    const durationSecs = Math.ceil(event.duration / 1000)
    // add a 8th of the duration to compensate submission irregularities
    // TODO: submit remaining time on server side
    setDuration(durationSecs + Math.ceil(durationSecs / 8))
  })

  useEventEmitter(communicator, "controlStateChanged", ({ state }) => {
    if (state == "play") {
      start()
    } else {
      stop()
    }
  })

  return [time, duration]
}
