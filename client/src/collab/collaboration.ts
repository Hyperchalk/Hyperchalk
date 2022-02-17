import { isInvisiblySmallElement } from "@excalidraw/excalidraw"
import { ExcalidrawElement } from "@excalidraw/excalidraw/types/element/types"
import { AppState, Collaborator, ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types/types"
import { RefObject } from "react"
import ReconnectingWebSocket from "reconnectingwebsocket"
import { ConfigProps, PointerUpdateProps } from "../types"
import { BroadcastedExcalidrawElement, reconcileElements } from "./reconciliation"

enum WsState {
  CONNECTING = 0,
  OPEN = 1,
  CLOSING = 2,
  CLOSED = 3,
}

// user_room_id always gets patched into the change in the backend
type CollaboratorChange = { time?: string; userRoomId?: string } & Collaborator

interface CollaboratorChangeMessage {
  eventtype: "collaborator_change"
  changes: CollaboratorChange[]
}

interface ElementsChangedMessage {
  eventtype: "elements_changed" | "full_sync"
  elements: BroadcastedExcalidrawElement[]
  username: string
}

type RoutableMessage = CollaboratorChangeMessage | ElementsChangedMessage

function isSyncableElement(element: ExcalidrawElement): boolean {
  return !element.isDeleted && !isInvisiblySmallElement(element)
}

export class CollabAPI {
  private broadcastedVersions = new Map<string, number>()
  private ws: ReconnectingWebSocket
  private excalidrawApiRef: RefObject<ExcalidrawImperativeAPI>
  private meInfo: Collaborator
  private MAX_UPDATES_BEFORE_RESYNC: number
  private collaborators: Map<string, Collaborator> = new Map()

  constructor(config: ConfigProps, api: RefObject<ExcalidrawImperativeAPI>) {
    this.excalidrawApiRef = api
    this.ws = new ReconnectingWebSocket(config.SOCKET_URL)
    this.ws.addEventListener("message", (event) => this.routeMessage(JSON.parse(event.data)))
    this.ws.addEventListener("connecting", () => this.scheduleFullSync())
    this.meInfo = {
      username: config.USER_NAME,
      color: config.USER_COLOR,
    }
    this.scheduleBroadcastUserEntry(this.meInfo)
    this.MAX_UPDATES_BEFORE_RESYNC = config.ELEMENT_UPDATES_BEFORE_FULL_RESYNC
  }

  private routeMessage(message: RoutableMessage) {
    switch (message.eventtype) {
      case "collaborator_change":
        // if a buffer was sent, only the last change is relevant to this client
        this.receiveCollaboratorChange(message.changes[message.changes.length - 1])
        break
      case "elements_changed":
      case "full_sync":
        this.receiveElements(message.elements)
        break
    }
  }

  private get excalidrawApi() {
    return this.excalidrawApiRef.current
  }

  // #region broadcast elements
  private updateBroadcastedVersions(elements: readonly BroadcastedExcalidrawElement[]) {
    for (let index = 0; index < elements.length; index++) {
      let element = elements[index]
      this.broadcastedVersions.set(element.id, element.version)
    }
  }

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

  private elementsSyncBroadcastCounter = 0

  scheduleFullSync() {
    this.elementsSyncBroadcastCounter = 0
  }

  syncSuccess() {
    this.elementsSyncBroadcastCounter =
      (this.elementsSyncBroadcastCounter + 1) % this.MAX_UPDATES_BEFORE_RESYNC
  }

  broadcastElements(elements: readonly ExcalidrawElement[], appState: AppState) {
    // TODO: broadcast information about item deletion
    // IDEA: broadcast full sync on mouse up
    // TODO: avoid resending incoming reconceiled elements
    let toSync =
      this.elementsSyncBroadcastCounter == 0
        ? this.elementsToSync(elements, true)
        : this.elementsToSync(elements, false)

    // do a full sync after reconnect
    if (this.ws.readyState == WsState.OPEN) {
      if (!toSync.length) return
      this.ws.send(
        JSON.stringify({
          eventtype: this.elementsSyncBroadcastCounter == 0 ? "full_sync" : "elements_changed",
          elements: toSync,
          username: this.meInfo.username,
        } as ElementsChangedMessage)
      )
      this.updateBroadcastedVersions(toSync)
      this.syncSuccess()
    } else {
      // full resync after websocket failed once
      this.scheduleFullSync()
    }
  }

  // #endregion broadcast elements

  // #region receive elements
  receiveElements(remoteElements: readonly BroadcastedExcalidrawElement[]) {
    if (this.excalidrawApi) {
      let reconciledElements = reconcileElements(
        this.excalidrawApi?.getSceneElementsIncludingDeleted(),
        remoteElements,
        this.excalidrawApi?.getAppState()
      )
      this.excalidrawApi?.updateScene({ elements: reconciledElements, commitToHistory: false })
    }
  }
  // #endregion receive elements

  // #region cursor movements
  collaboratorChangeBuffer: CollaboratorChange[] = []

  scheduleBroadcastUserEntry(meInfo: Collaborator) {
    this.collaboratorChangeBuffer.push({
      time: new Date().toISOString(),
      ...meInfo,
    })
  }

  broadcastCursorMovement({ pointer, button, pointersMap }: PointerUpdateProps) {
    // don't send touch gestures
    if (pointersMap?.size ?? 0 > 1) return

    for (let key in pointer) {
      pointer[key as keyof typeof pointer] |= 0
    }

    this.collaboratorChangeBuffer.push({
      button,
      pointer,
      selectedElementIds: this.excalidrawApi?.getAppState().selectedElementIds,
      time: new Date().toISOString(),
      username: this.meInfo.username,
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

  receiveCollaboratorChange(change: CollaboratorChange) {
    let userRoomId = change.userRoomId!
    let collaborator = this.collaborators.get(userRoomId) ?? {}
    delete change.userRoomId
    delete change.time
    Object.assign(collaborator, change)

    this.excalidrawApi?.updateScene({ collaborators: new Map([[userRoomId, collaborator]]) })
    // TODO: should we really pass the whole map here?
  }
  // #endregion cursor movements
}
