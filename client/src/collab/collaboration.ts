import { isInvisiblySmallElement } from "@excalidraw/excalidraw"
import { ExcalidrawElement } from "@excalidraw/excalidraw/types/element/types"
import { AppState, Collaborator, ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types/types"
import throttle from "lodash.throttle"
import { RefObject } from "react"
import ReconnectingWebSocket from "reconnectingwebsocket"

import { BroadcastedExcalidrawElement, ConfigProps, PointerUpdateProps, WsState } from "../types"
import { reconcileElements } from "./reconciliation"

// #region message types
// userRoomId always gets patched into the change in the backend
type CollaboratorChange = { time?: string; userRoomId?: string } & Collaborator

interface CollaboratorChangeMessage {
  eventtype: "collaborator_change"
  changes: CollaboratorChange[]
}

interface ElementsChangedMessage {
  eventtype: "elements_changed" | "full_sync"
  elements: BroadcastedExcalidrawElement[]
}

interface CollaboratorLeftMessage {
  eventtype: "collaborator_left"
  collaborator: CollaboratorChange
}

type RoutableMessage = CollaboratorChangeMessage | ElementsChangedMessage | CollaboratorLeftMessage
// #endregion message types

function isSyncableElement(element: ExcalidrawElement): boolean {
  return !isInvisiblySmallElement(element)
}

export class CollabAPI {
  private ws: ReconnectingWebSocket

  private _excalidrawApiRef?: RefObject<ExcalidrawImperativeAPI>

  // #region methods for excalidraw props

  broadcastCursorMovement: (collaborator: PointerUpdateProps) => void
  broadcastElements: (elements: readonly ExcalidrawElement[], appState: AppState) => void

  // #endregion methods for excalidraw props

  /**
   * Setup the WebSocket to use and configure the collaboration api.
   *
   * @param config configuration for the excalidraw room
   */
  constructor(config: ConfigProps) {
    // websocket setup
    this.ws = new ReconnectingWebSocket(config.SOCKET_URL)
    this.ws.addEventListener("message", (event) => this.routeMessage(JSON.parse(event.data)))
    this.ws.addEventListener("connecting", () => this.scheduleFullSync())
    this.ws.addEventListener("open", () => this.broadcastCollaboratorChange(this.meInfo))

    // collaborator setup
    this.meInfo = {
      username: config.USER_NAME,
      color: config.USER_COLOR,
    }
    this.MAX_UPDATES_BEFORE_RESYNC = config.ELEMENT_UPDATES_BEFORE_FULL_RESYNC

    // methods for direct usage by excalidraw component
    this.broadcastCursorMovement = throttle(
      this._broadcastCursorMovement.bind(this),
      config.BROADCAST_RESOLUTION
    )
    this.broadcastElements = throttle(
      this._broadcastElements.bind(this),
      config.BROADCAST_RESOLUTION,
      {
        leading: false,
        trailing: true,
      }
    )
  }

  // #region excalidraw access
  /**
   * This needs to be called when the excalidraw component is set up!
   */
  set excalidrawApiRef(apiRef: RefObject<ExcalidrawImperativeAPI>) {
    this._excalidrawApiRef = apiRef
  }

  /**
   * Helper to access the excalidraw api more easily
   */
  private get excalidrawApi() {
    if (!this._excalidrawApiRef) {
      throw new Error("The excalidrawApiRef has not been set yet.")
    }
    return this._excalidrawApiRef.current
  }
  // #endregion excalidraw access

  /**
   * Looks up which message type (`eventtype`) was sent by the
   * backend and calls the appropriate method to process it.
   *
   * @param message message sent by a collaborator
   */
  private routeMessage(message: RoutableMessage) {
    switch (message.eventtype) {
      case "collaborator_change":
        // if a buffer was sent, only the last change and any
        // additional information is relevant to this client
        this.receiveCollaboratorChange(
          message.changes.reduce((acc, current) => Object.assign(acc, current), {})
        )
        break
      case "elements_changed":
      case "full_sync":
        this.receiveElements(message.elements)
        break
      case "collaborator_left":
        this.receiveCollaboratorLeft(message.collaborator)
        break
    }
  }

  // #region element changes
  private broadcastedVersions = new Map<string, number>()

  /**
   * Store the versions of the elements when they were broadcasted, so it can
   * be determined which elements need to be send on the next broadcast call.
   *
   * @param elements elements on the current canvas
   */
  private updateBroadcastedVersions(elements: readonly BroadcastedExcalidrawElement[]) {
    for (let index = 0; index < elements.length; index++) {
      let element = elements[index]
      this.broadcastedVersions.set(element.id, element.version)
    }
  }

  /**
   * Determines which elements shall be broadcasted.
   *
   * @param elements all elements on the current canvas
   * @param syncAll sync all elements that are syncable
   * @returns the elements to be broadcasted
   */
  private elementsToSync(elements: readonly ExcalidrawElement[], syncAll = false) {
    let toSync: BroadcastedExcalidrawElement[] = []
    for (let index = 0; index < elements.length; index++) {
      let element = elements[index]
      let shouldElementSync =
        isSyncableElement(element) &&
        (syncAll ||
          !this.broadcastedVersions.has(element.id) ||
          element.version > this.broadcastedVersions.get(element.id)!)

      if (shouldElementSync) {
        toSync.push({
          ...elements[index],
          // z-index info for the reconciler
          parent: index === 0 ? "^" : elements[index - 1]?.id,
        })
      }
    }
    return toSync
  }

  private MAX_UPDATES_BEFORE_RESYNC: number
  private elementsSyncBroadcastCounter = 0

  /**
   * Resets the sync counter, thus triggering a full sync on the next elements broadcast.
   */
  private scheduleFullSync() {
    this.elementsSyncBroadcastCounter = 0
  }

  /**
   * Increases / resets the sync counter to its next value.
   */
  private syncSuccess() {
    this.elementsSyncBroadcastCounter =
      (this.elementsSyncBroadcastCounter + 1) % this.MAX_UPDATES_BEFORE_RESYNC
  }

  /**
   * Sends the elements to the other clients that changed since the last broadcast. Every
   * {@link CollabAPI#MAX_UPDATES_BEFORE_RESYNC} syncs will send all elements (ful sync).
   * This method should only be called through its throttle wrapper which is the method
   * {@link CollabAPI#broadcastElements} (without the `_`).
   *
   * @param elements the current elements on the canvas
   * @param appState excalidraw's app state
   */
  private _broadcastElements(elements: readonly ExcalidrawElement[], appState: AppState) {
    let doFullSync = this.elementsSyncBroadcastCounter == 0
    let toSync = doFullSync
      ? this.elementsToSync(elements, true)
      : this.elementsToSync(elements, false)

    // do a full sync after reconnect
    if (this.ws.readyState == WsState.OPEN) {
      if (!toSync.length) return

      this.ws.send(
        JSON.stringify({
          eventtype: doFullSync ? "full_sync" : "elements_changed",
          elements: toSync,
        } as ElementsChangedMessage)
      )
      this.updateBroadcastedVersions(toSync)
      this.syncSuccess()

      // FIXME: why is the cursor position not send if elements are being dragged?
      // if (appState.cursorButton == "down") {
      //   this._broadcastCursorMovement({  })
      // }
    } else {
      // full resync after websocket failed once
      this.scheduleFullSync()
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
  private meInfo: Collaborator
  private collaborators: Map<string, Collaborator> = new Map()

  private collaboratorChangeBuffer: CollaboratorChange[] = []

  // TODO: broadcast idle state
  // IDEA: remove all collaborators on connection loss

  /**
   * Sends the current cursor to the backend so it can be braodcasted to the other clients. It
   * is prefixed with an underscore so a throttled version of the method can be exposed to the
   * outside under the same name.
   *
   * @param param0 the updated cursor of this client
   */
  private _broadcastCursorMovement({ pointer, button, pointersMap }: PointerUpdateProps) {
    // don't send touch gestures
    if (pointersMap?.size ?? 0 > 1) return

    for (let key in pointer) {
      pointer[key as keyof typeof pointer] |= 0
    }

    this.broadcastCollaboratorChange({
      button,
      pointer,
      selectedElementIds: this.excalidrawApi?.getAppState().selectedElementIds,
    })
  }

  /**
   * Broadcast information about the collaborator that controls this instance.
   *
   * @param collaborator the collaborator info to send
   */
  private broadcastCollaboratorChange(collaborator: CollaboratorChange) {
    this.collaboratorChangeBuffer.push({
      time: new Date().toISOString(),
      username: this.meInfo.username,
      ...collaborator,
    })

    if (this.ws.readyState == WsState.OPEN) {
      this.ws.send(
        JSON.stringify({
          eventtype: "collaborator_change",
          changes: this.collaboratorChangeBuffer,
        } as CollaboratorChangeMessage)
      )
      this.collaboratorChangeBuffer = []
    }
  }

  /**
   * Receives the content of other clients {@link CollabAPI#_broadcastCursorMovement}.
   * @param change an update to the collaborators
   */
  private receiveCollaboratorChange(change: CollaboratorChange) {
    let userRoomId = change.userRoomId!
    let isKnownCollaborator = this.collaborators.has(userRoomId)
    let collaborator = this.collaborators.get(userRoomId) ?? {}
    delete change.userRoomId
    delete change.time
    Object.assign(collaborator, change)
    this.collaborators.set(userRoomId, collaborator)

    this.excalidrawApi?.updateScene({ collaborators: this.collaborators })

    if (!isKnownCollaborator) {
      this.broadcastEverything()
    }
  }

  /**
   * Remove a collaborater's pointer if they left the room.
   *
   * This is one of the rare instances where the message is
   * not generated by another client, but by the backend.
   *
   * @param param0 The changed collaborator
   */
  private receiveCollaboratorLeft({ userRoomId }: CollaboratorChange) {
    this.collaborators.delete(userRoomId!)
    this.excalidrawApi?.updateScene({ collaborators: this.collaborators })
  }
  // #endregion collaborator awareness

  /**
   * Broadcast all elements and the collaborator info.
   */
  private broadcastEverything() {
    if (this.excalidrawApi) {
      this.scheduleFullSync()
      this._broadcastElements(
        this.excalidrawApi.getSceneElements(),
        this.excalidrawApi.getAppState()
      )
    }
    this.broadcastCollaboratorChange(this.meInfo)
  }
}
