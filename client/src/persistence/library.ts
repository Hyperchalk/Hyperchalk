import { ExcalidrawImperativeAPI, LibraryItems } from "@excalidraw/excalidraw/types/types"
import { RefObject, useCallback } from "react"

import { getLocalStorageJson, setLocalStorageJson } from "../utils"

const _library = "_library"
const _addLibraries = "_addLibraries"

export function saveLibrary(items: LibraryItems) {
  setLocalStorageJson(_library, items)
}

export function loadLibrary(): LibraryItems {
  return getLocalStorageJson(_library, [])
}

/**
 * A react hook which loads libraries from urls supplied via localStorage.
 *
 * @param apiRef api ref to the excalidraw api
 * @returns hook for loading libraries
 */
export function useLoadLibraries(apiRef: RefObject<ExcalidrawImperativeAPI>) {
  return useCallback(() => {
    let urls: string[] = getLocalStorageJson(_addLibraries, [])
    if (apiRef.current) {
      for (let url of urls) {
        apiRef.current.updateLibrary({
          libraryItems: new Promise<Blob>(async (resolve, reject) => {
            try {
              const request = await fetch(decodeURIComponent(url))
              const blob = await request.blob()
              resolve(blob)
            } catch (error: any) {
              reject(error)
            }
          }),
          prompt: true,
          merge: true,
          defaultStatus: "published",
          openLibraryMenu: true,
        })
      }
      setLocalStorageJson(_addLibraries, [])
    }
  }, [apiRef])
}
