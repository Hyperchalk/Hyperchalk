import { useRef, useState } from "react"
import ReconnectingWebSocket from "reconnectingwebsocket"

import { ConfigProps } from "../types"
import { useEventEmitter } from "../hooks/useEventEmitter"
import Communicator, {
  CollaboratorChange,
  CommunicatorEventMap,
  CommunicatorMessage,
} from "./communicator"

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

  // needed to remove stale cursors
  private collaboratorUpdate = 0
  private lastCollaboratorUpdate = new Map<string, number>()

  protected receiveCollaboratorChange(change: CollaboratorChange): {
    isKnownCollaborator: boolean
  } {
    // remove collaborators after not updating for 30 collaborator update steps
    this.collaboratorUpdate += 1
    change.userRoomId && this.lastCollaboratorUpdate.set(change.userRoomId, this.collaboratorUpdate)
    for (let collaboratorId of this.collaborators.keys()) {
      let lastUpdate = this.lastCollaboratorUpdate.get(collaboratorId) ?? 0
      if (this.collaboratorUpdate - lastUpdate >= 30) {
        this.collaborators.delete(collaboratorId)
      }
    }

    return super.receiveCollaboratorChange(change)
  }

  /**
   * Resets the scene. This is only for replay mode.
   */
  private resetScene(duration: number) {
    this.broadcastedElementsVersions = new Map()
    this.collaborators = new Map()
    this.collaboratorUpdate = 0
    this.lastCollaboratorUpdate = new Map()
    this.excalidrawApi?.updateScene({
      collaborators: this.collaborators,
      elements: [],
      commitToHistory: false,
    })
    this.duration = duration
    this.emit("reset", { duration })
  }

  sendControlState(eventtype: ControlTypes) {
    this.ws.send(JSON.stringify({ eventtype }))
  }
}

// #region hooks

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

// #endregion hooks
