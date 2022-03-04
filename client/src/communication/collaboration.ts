import { isInvisiblySmallElement } from "@excalidraw/excalidraw"
import { ExcalidrawElement } from "@excalidraw/excalidraw/types/element/types"
import { AppState, Collaborator } from "@excalidraw/excalidraw/types/types"
import { debounce, throttle } from "lodash"
import ReconnectingWebSocket from "reconnectingwebsocket"

import { BroadcastedExcalidrawElement, ConfigProps, PointerUpdateProps, WsState } from "../types"

import Communicator, {
  CollaboratorChange,
  CollaboratorChangeMessage,
  CommunicatorMessage,
  ElementsChangedMessage,
} from "./communicator"

// #region message types
interface CollaboratorLeftMessage {
  eventtype: "collaborator_left"
  collaborator: CollaboratorChange
}

interface LoginRequired {
  eventtype: "login_required"
}

type CollaborationMessage = CommunicatorMessage | CollaboratorLeftMessage | LoginRequired
// #endregion message types

function isSyncableElement(element: ExcalidrawElement): boolean {
  return !isInvisiblySmallElement(element)
}

/**
 * This Communicator is instantiated when we are in collaboration mode.
 */
export default class CollaborationCommunicator extends Communicator {
  constructor(config: ConfigProps, ws: ReconnectingWebSocket) {
    super(config, ws)

    this.meInfo = {
      username: config.USER_NAME,
      color: config.USER_COLOR,
    }

    // WebSocket setup
    this.ws.addEventListener("open", () => {
      this.broadcastCollaboratorChange(this.meInfo)
    })

    this.ws.addEventListener("connecting", () => {
      this.scheduleFullSync()
    })

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

    this.saveRoom = debounce(this._saveRoom.bind(this), 5000, {
      leading: false,
      trailing: true,
      maxWait: config.SAVE_ROOM_MAX_WAIT,
    })
  }

  // #region message handling
  protected routeMessage<MsgType extends CollaborationMessage>(message: MsgType) {
    let messageWasRouted = super.routeMessage(message as CommunicatorMessage)
    if (!messageWasRouted) {
      switch (message.eventtype) {
        case "collaborator_left":
          this.receiveCollaboratorLeft(message.collaborator)
          return true
        case "login_required":
          this.endCollaboration()
          return true
      }
    }
    return false
  }
  // #endregion message handling

  // #region element changes
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
      (this.elementsSyncBroadcastCounter + 1) % this.config.ELEMENT_UPDATES_BEFORE_FULL_RESYNC
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
      ? this.elementsToSync(elements, /* syncAll */ true)
      : this.elementsToSync(elements, /* syncAll */ false)

    // do a full sync after reconnect
    if (this.ws.readyState == WsState.OPEN) {
      // FIXME: see issue #1
      // https://gitlab.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application/-/issues/1
      this.saveRoom()

      // don't send an update if there is nothing to sync.
      // e.g. the case after another client sent an update
      if (!toSync.length) return

      this.ws.send(
        JSON.stringify({
          eventtype: doFullSync ? "full_sync" : "elements_changed",
          elements: toSync,
        } as ElementsChangedMessage)
      )
      this.updateBroadcastedVersions(toSync)
      this.syncSuccess()

      // FIXME: why is the cursor position not send if elements are being dragged? see issue #2
      // https://gitlab.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application/-/issues/2
      // if (appState.cursorButton == "down") {
      //   this._broadcastCursorMovement({  })
      // }
    } else {
      // full resync after websocket failed once
      this.scheduleFullSync()
    }
  }
  // #endregion element changes

  // #region collaborator awareness
  private meInfo: Collaborator
  private collaboratorChangeBuffer: CollaboratorChange[] = []

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
   * If a new collaborator enters in collaboration mode, we do a full sync.
   *
   * @param change change that happened to a collaborator
   * @returns information about the collaborator for internal usage
   */
  protected receiveCollaboratorChange(change: CollaboratorChange): {
    isKnownCollaborator: boolean
  } {
    let { isKnownCollaborator } = super.receiveCollaboratorChange(change)
    if (!isKnownCollaborator) {
      this.broadcastEverything()
    }
    return { isKnownCollaborator }
  }

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
  // #region collaborator awareness

  // #region backend communication
  private _saveRoom() {
    this.ws.send(
      JSON.stringify({
        eventtype: "save_room",
        elements: this.excalidrawApi?.getSceneElements() ?? [],
      })
    )
  }
  // #endregion backend communication
}
