import { ExcalidrawElement } from "@excalidraw/excalidraw/types/element/types"
import { AppState, Collaborator, ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types/types"
import { RefObject, Dispatch, SetStateAction, useState, useRef } from "react"
import ReconnectingWebSocket from "reconnectingwebsocket"

import { BroadcastedExcalidrawElement, ConfigProps, PointerUpdateProps } from "../types"
import { reconcileElements } from "../reconciliation"
import { noop } from "../utils"

// #region message types
// userRoomId always gets patched into the change in the backend
export type CollaboratorChange = { time?: string; userRoomId?: string } & Collaborator

export interface CollaboratorChangeMessage {
  eventtype: "collaborator_change"
  changes: CollaboratorChange[]
}

export interface ElementsChangedMessage {
  eventtype: "elements_changed" | "full_sync"
  elements: BroadcastedExcalidrawElement[]
}

export type CommunicatorMessage = CollaboratorChangeMessage | ElementsChangedMessage
// #endregion message types

export type ConnectionStates = "CONNECTED" | "DISCONNECTED"

export default class Communicator {
  protected ws: ReconnectingWebSocket
  protected config: ConfigProps

  protected _excalidrawApiRef?: RefObject<ExcalidrawImperativeAPI>
  private _setConnectionState?: Dispatch<SetStateAction<ConnectionStates>>
  private _connectionState: ConnectionStates = "CONNECTED"

  // #region methods for excalidraw props

  broadcastCursorMovement: (collaborator: PointerUpdateProps) => void = noop
  broadcastElements: (elements: readonly ExcalidrawElement[], appState: AppState) => void = noop
  saveRoom: () => void = noop

  // #endregion methods for excalidraw props

  /**
   * Setup the WebSocket to use and configure the collaboration api.
   *
   * @param config configuration for the excalidraw room
   */
  constructor(config: ConfigProps, ws: ReconnectingWebSocket) {
    // collaborator setup
    this.config = config

    // websocket setup
    this.ws = ws

    this.ws.addEventListener("message", (event) => {
      this.routeMessage(JSON.parse(event.data))
    })

    // code 3000 is sent when a disconnect happens due to an authentication error.
    this.ws.addEventListener("connecting", (event) => {
      event.code == 3000 && this.ws.close()
    })
  }

  // #region component communication
  /**
   * This needs to be called when the excalidraw component is set up!
   */
  set excalidrawApiRef(apiRef: RefObject<ExcalidrawImperativeAPI>) {
    this._excalidrawApiRef = apiRef
  }

  /**
   * Helper to access the excalidraw api more easily
   */
  protected get excalidrawApi() {
    if (!this._excalidrawApiRef) {
      throw new Error("The excalidrawApiRef has not been set yet.")
    }
    return this._excalidrawApiRef.current
  }

  set connectionStateSetter(setter: typeof this._setConnectionState) {
    this._setConnectionState = setter
  }

  get connectionState() {
    return this._connectionState
  }
  // #endregion component communication

  // #region message hadling
  /**
   * Looks up which message type (`eventtype`) was sent by the
   * backend and calls the appropriate method to process it.
   *
   * @param message message sent by a collaborator
   *
   * @returns is the message was routed
   */
  protected routeMessage<MsgType extends CommunicatorMessage>(message: MsgType): boolean {
    switch (message.eventtype) {
      case "collaborator_change":
        // if a buffer was sent, only the last change and any
        // additional information is relevant to this client
        this.receiveCollaboratorChange(
          message.changes.reduce((acc, current) => Object.assign(acc, current), {})
        )
        return true
      case "elements_changed":
      case "full_sync":
        this.receiveElements(message.elements)
        return true
      default:
        return false
    }
  }

  /**
   * Ends the collaboration session by closing the websocket.
   *
   * Code 3000 means "unauthorized".
   */
  protected endCollaboration() {
    console.warn("not logged in aborting session")
    this.ws.close(3000)
    this._connectionState = "DISCONNECTED"
    this._setConnectionState?.(this._connectionState)
  }

  // #endregion message hadling

  // #region element changes
  protected broadcastedVersions = new Map<string, number>()

  /**
   * Store the versions of the elements when they were broadcasted, so it can
   * be determined which elements need to be send on the next broadcast call.
   *
   * @param elements elements on the current canvas
   */
  protected updateBroadcastedVersions(elements: readonly BroadcastedExcalidrawElement[]) {
    for (let index = 0; index < elements.length; index++) {
      let element = elements[index]
      this.broadcastedVersions.set(element.id, element.version)
    }
  }

  /**
   * Receive broadcasted elements from other clients.
   *
   * @param remoteElements elements that changed remotely. This can also be a full element set
   *                       if a remote client triggerd a full sync.
   */
  private receiveElements(remoteElements: readonly BroadcastedExcalidrawElement[]) {
    if (this.excalidrawApi) {
      let reconciledElements = reconcileElements(
        this.excalidrawApi?.getSceneElementsIncludingDeleted(),
        remoteElements,
        this.excalidrawApi?.getAppState()
      )
      this.updateBroadcastedVersions(reconciledElements)
      this.excalidrawApi?.updateScene({ elements: reconciledElements, commitToHistory: false })
    }
  }

  // #endregion element changes

  // #region collaborator awareness
  protected collaborators: Map<string, Collaborator> = new Map()

  /**
   * Receives the content of other clients {@link Communicator#_broadcastCursorMovement}.
   *
   * @param change an update to the collaborators
   * @returns information about the collaborator for internal usage
   */
  protected receiveCollaboratorChange(change: CollaboratorChange) {
    let userRoomId = change.userRoomId!
    let isKnownCollaborator = this.collaborators.has(userRoomId)
    let collaborator = this.collaborators.get(userRoomId) ?? {}
    delete change.userRoomId
    delete change.time
    Object.assign(collaborator, change)
    this.collaborators.set(userRoomId, collaborator)

    this.excalidrawApi?.updateScene({ collaborators: this.collaborators })

    return { isKnownCollaborator }
  }
  // #endregion collaborator awareness
}

export function useConnectionState(communicator: Communicator) {
  const [connectionState, setConnectionState] = useState<ConnectionStates>(
    communicator.connectionState
  )
  communicator.connectionStateSetter = setConnectionState
  return connectionState
}

export function useCommunicatorExcalidrawRef(communicator: Communicator) {
  const ref = useRef<ExcalidrawImperativeAPI>(null)
  communicator.excalidrawApiRef = ref
  return ref
}
