import { isInvisiblySmallElement } from "@excalidraw/excalidraw"
import { ExcalidrawElement } from "@excalidraw/excalidraw/types/element/types"
import {
  AppState,
  BinaryFileData,
  BinaryFiles,
  Collaborator,
} from "@excalidraw/excalidraw/types/types"
import debounce from "lodash/debounce"
import throttle from "lodash/throttle"
import ReconnectingWebSocket from "reconnectingwebsocket"

import { BroadcastedExcalidrawElement, ConfigProps, PointerUpdateProps, WsState } from "../types"
import { apiRequestInit, getJsonScript } from "../utils"

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

interface FilesAddedMessage {
  eventtype: "files_added"
  fileids: string[]
}

interface FilesMissingMessage {
  eventtype: "files_missing"
  missing: string[]
}

interface LoginRequired {
  eventtype: "login_required"
}

type CollaborationMessage =
  | CommunicatorMessage
  | CollaboratorLeftMessage
  | LoginRequired
  | FilesAddedMessage
  | FilesMissingMessage
// #endregion message types

function isSyncableElement(element: ExcalidrawElement): boolean {
  return !isInvisiblySmallElement(element)
}

class UnknownFilesError extends Error {
  unknownFileIds?: string[]
}

/**
 * This Communicator is instantiated when we are in collaboration mode.
 */
export default class CollaborationCommunicator extends Communicator {
  constructor(config: ConfigProps, ws: ReconnectingWebSocket, loadedFiles: BinaryFiles) {
    super(config, ws)

    this.meInfo = {
      username: config.USER_NAME,
      color: config.USER_COLOR,
    }

    this.updateUploadedFileIDs(Object.keys(loadedFiles))

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
      config.BROADCAST_RESOLUTION_THROTTLE_MSEC
    )

    this.broadcastElements = throttle(
      this._broadcastElementsAndUploadFiles.bind(this),
      config.BROADCAST_RESOLUTION_THROTTLE_MSEC,
      {
        leading: false,
        trailing: true,
      }
    )

    this.saveRoom = debounce(this.saveRoomImmediately.bind(this), 5000, {
      leading: false,
      trailing: true,
      maxWait: config.SAVE_ROOM_MAX_WAIT_MSEC,
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
        case "files_added":
          this.receiveFiles(message.fileids)
          return true
        case "files_missing":
          this.sendFiles(message.missing.filter((id) => !this.uploadingFileIds.has(id)))
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
          !this.broadcastedElementsVersions.has(element.id) ||
          element.version > this.broadcastedElementsVersions.get(element.id)!)

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

  private uploadedFileIds = new Set<string>()
  private uploadingFileIds = new Set<string>()

  /**
   * Get a url for a file to upload or download.
   *
   * @param fileId the files id
   * @returns a url for the file with the given id
   */
  private fileUrl(fileId: string) {
    return this.config.FILE_URL_TEMPLATE!.replace("FILE_ID", fileId)
  }

  private nextTryTimeout(nextTryExponentMinusOne: number) {
    return Math.min(
      this.config.UPLOAD_RETRY_TIMEOUT_MSEC * Math.pow(2, nextTryExponentMinusOne + 1),
      this.config.MAX_RETRY_WAIT_MSEC
    )
  }

  /**
   * Update the set of broadcasted files.
   *
   * @param newlySyncedFiles files that just have been synced
   */
  private updateUploadedFileIDs(newlySyncedFileIds: string[]) {
    for (let index = 0; index < newlySyncedFileIds.length; index++) {
      this.uploadedFileIds.add(newlySyncedFileIds[index])
      this.uploadingFileIds.delete(newlySyncedFileIds[index])
    }
  }

  /**
   * Update the set of files that are currently uploading.
   *
   * @param uploadingFileIds the Ids of the files for which an upload was just started
   */
  private startUploadingFileIDs(uploadingFileIds: string[]) {
    for (let index = 0; index < uploadingFileIds.length; index++) {
      this.uploadingFileIds.add(uploadingFileIds[index])
    }
  }

  /**
   * Receive files via WebSocket.
   *
   * This is not needed in {@link Communicator} because the
   * other modes will have all files available from the start.
   *
   * @param files files received over socket
   */
  private async receiveFiles(files: string[], nextTryExponentMinusOne = -1) {
    // construct requests. only files that are yet unknown are to be downloaded
    const fileRequests = files
      .filter((id) => !this.uploadedFileIds.has(id))
      .map((id) => fetch(this.fileUrl(id), apiRequestInit("GET")))

    // prevent files from being re-uploaded after this function finishes
    this.updateUploadedFileIDs(files)

    // TODO: what to do if api is not loaded yet? does this ever happen?

    // download the files and add them to the scene if the download succeeded.
    // success is defined as:
    // 1. the download promise settled
    // 2. the return status was 200. maybe this has to change in the future.
    const settledPromises = await Promise.allSettled(fileRequests)
    const succeededBinaryFileData = settledPromises
      .filter((p) => p.status == "fulfilled")
      .map((p) => (p as PromiseFulfilledResult<Response>).value)
      .filter((r) => r.status == 200)
      .map((r) => r.json() as Promise<BinaryFileData>)
    const downloadedFiles = await Promise.all(succeededBinaryFileData)
    this.excalidrawApi?.addFiles(downloadedFiles)

    // retry downloading failed IDs after a timeout elapsed
    const downloadedFileIds = downloadedFiles.map((f) => f.id as string)
    const downloadFailedIds = files.filter((id) => !downloadedFileIds.includes(id))
    if (downloadFailedIds.length) {
      setTimeout(() => {
        this.receiveFiles(downloadFailedIds, nextTryExponentMinusOne + 1)
      }, this.nextTryTimeout(nextTryExponentMinusOne))
    }
  }

  /**
   * sends files with given ids to the server
   *
   * If the upload fails, the client just does exponential retries, ignoring all failure reasons.
   * An upload is considered to have failed, if it has a non-200 status code!
   *
   * @param fileIds file ids to sned to the server
   * @param nextTryExponentMinusOne if uploads fail, this will determine when the next try starts
   */
  private async sendFiles(fileIds: string[], nextTryExponentMinusOne = -1) {
    // uploading files need to be locked for another upload so a new upload will
    // not be triggered on every new change while the upload is still ongoing
    this.startUploadingFileIDs(fileIds)

    // make new PUT requests for all new and wait till they are settled.
    const files = this.excalidrawApi?.getFiles() ?? {}
    const fileRequests = Object.entries(files)
      .filter(([id, file]) => fileIds.includes(id))
      .map(([id, file]) => fetch(this.fileUrl(id), apiRequestInit("PUT", file)))
    const settledPromises = await Promise.allSettled(fileRequests)

    // for now, we only filter for succeeded uploads. success is defined as:
    // 1. the upload promise settled
    // 2. the return status was 200. maybe this has to change in the future.
    const succeededFileInfo = settledPromises
      .filter((p) => p.status == "fulfilled")
      .map((p) => (p as PromiseFulfilledResult<Response>).value)
      .filter((r) => r.status == 200)
      .map((r) => r.json() as Promise<{ id: string }>)
    const succeededIds = (await Promise.all(succeededFileInfo)).map((f) => f.id)
    this.updateUploadedFileIDs(succeededIds)

    // notify the other clients about the added files
    if (succeededIds.length) {
      this.ws.send(
        JSON.stringify({
          eventtype: "files_added",
          fileids: succeededIds,
        } as FilesAddedMessage)
      )
    }

    // retry uploading failed IDs after a timeout elapsed
    const uploadFailedIds = fileIds.filter((id) => id in files && !succeededIds.includes(id))
    if (uploadFailedIds.length) {
      setTimeout(() => {
        this.sendFiles(uploadFailedIds, nextTryExponentMinusOne + 1)
      }, this.nextTryTimeout(nextTryExponentMinusOne))
    }

    const unknownFiles = fileIds.filter((id) => !(id in files))
    if (unknownFiles.length) {
      const err = new UnknownFilesError("Unknown files were requested for sending.")
      err.unknownFileIds = unknownFiles
      throw err
    }
  }

  /**
   * Get unsynced files.
   *
   * **Warning:** don't change files without changing their IDs. Files are assumed to me immutable.
   *
   * @param files files in the scene
   * @returns [[IDs of files that are not synced yet], [IDs of files that are too large to sync]]
   */
  private filesToSync(files: BinaryFiles): [string[], string[]] {
    const tooLarge = Object.keys(files).filter(
      (id) => files[id].dataURL.length > this.config.MAX_FILE_SIZE_B64
    )
    const toSync = Object.keys(files).filter(
      (id) =>
        !this.uploadedFileIds.has(id) &&
        !this.uploadingFileIds.has(id) &&
        files[id].dataURL.length <= this.config.MAX_FILE_SIZE_B64
    )
    return [toSync, tooLarge]
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
  private elementSyncSuccess() {
    this.elementsSyncBroadcastCounter =
      (this.elementsSyncBroadcastCounter + 1) % this.config.ELEMENT_UPDATES_BEFORE_FULL_RESYNC
  }

  /**
   * Sends the elements to the other clients that changed since the last broadcast. Every
   * {@link ConfigProps#ELEMENT_UPDATES_BEFORE_FULL_RESYNC} syncs will send all elements (ful sync).
   * This method should only be called through its throttle wrapper which is the method
   * {@link Communicator#broadcastElements} (without the `_`).
   *
   * @param elements the current elements on the canvas
   * @param appState excalidraw's app state
   * @param files files that were added to the scene
   */
  private _broadcastElementsAndUploadFiles(
    elements: readonly ExcalidrawElement[],
    appState: AppState,
    files: BinaryFiles
  ) {
    let doFullSync = this.elementsSyncBroadcastCounter == 0
    let elementsToSync = doFullSync
      ? this.elementsToSync(elements, /* syncAll */ true)
      : this.elementsToSync(elements, /* syncAll */ false)
    let [filesToSync, tooLarge] = this.filesToSync(files)

    // delete files that are too large and stop the broadcast if there are any.
    // FIXME: appearantly excalidraw does not expect anyone to do this. this will throw an
    //        unhandled promise to the terminal. everything will still work file though.
    //        So this is not a problem of high priority.
    if (tooLarge.length) {
      let newElements = elements.filter(
        (e) => e.type != "image" || e.fileId == null || !tooLarge.includes(e.fileId)
      )
      for (let fileId in files) {
        if (tooLarge.includes(fileId)) delete files[fileId]
      }
      const msg: Record<string, string> = getJsonScript("custom-messages")
      this.excalidrawApi?.setToastMessage(msg["FILE_TOO_LARGE"])
      this.excalidrawApi?.updateScene({ elements: newElements })
      return
    }

    // do a full sync after reconnect
    if (this.ws.readyState == WsState.OPEN) {
      // FIXME: performance; see issue #1
      // https://gitlab.tba-hosting.de/lpa-aflek-alice/excalidraw-lti-application/-/issues/1
      this.saveRoom()

      // don't send an update if there is nothing to sync.
      // e.g. the case after another client sent an update
      if (elementsToSync.length) {
        this.ws.send(
          JSON.stringify({
            eventtype: doFullSync ? "full_sync" : "elements_changed",
            elements: elementsToSync,
          } as ElementsChangedMessage)
        )
        this.updateBroadcastedElementsVersions(elementsToSync)
        this.elementSyncSuccess()
      }

      // upload all missing files, then send a message.
      if (filesToSync.length) {
        this.sendFiles(filesToSync)
      }

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
      this._broadcastElementsAndUploadFiles(
        this.excalidrawApi.getSceneElements(),
        this.excalidrawApi.getAppState(),
        this.excalidrawApi.getFiles()
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
  public saveRoomImmediately() {
    // the server will request missing files when it detects any.
    this.ws.send(
      JSON.stringify({
        eventtype: "save_room",
        elements: this.excalidrawApi?.getSceneElementsIncludingDeleted() ?? [],
      })
    )
  }
  // #endregion backend communication
}
