/**
 * MIT License
 *
 * Copyright (c) 2020 Excalidraw
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

import { ExcalidrawElement } from "@excalidraw/excalidraw/types/element/types"
import { AppState } from "@excalidraw/excalidraw/types/types"

export type ReconciledElements = readonly ExcalidrawElement[] & {
  _brand: "reconciledElements"
}

export type BroadcastedExcalidrawElement = ExcalidrawElement & {
  parent?: string
}

function shouldDiscardRemoteElement(
  localAppState: AppState,
  local: ExcalidrawElement | undefined,
  remote: BroadcastedExcalidrawElement
): boolean {
  if (
    local &&
    // local element is being edited
    (local.id === localAppState.editingElement?.id ||
      local.id === localAppState.resizingElement?.id ||
      local.id === localAppState.draggingElement?.id ||
      // local element is newer
      local.version > remote.version ||
      // resolve conflicting edits deterministically by taking the one with
      // the lowest versionNonce
      (local.version === remote.version && local.versionNonce < remote.versionNonce))
  ) {
    return true
  }
  return false
}

function getElementsMapWithIndex<T extends ExcalidrawElement>(elements: readonly T[]) {
  return elements.reduce(
    (
      acc: {
        [key: string]: [element: T, index: number] | undefined
      },
      element: T,
      idx
    ) => {
      acc[element.id] = [element, idx]
      return acc
    },
    {}
  )
}

export function reconcileElements(
  localElements: readonly ExcalidrawElement[],
  remoteElements: readonly BroadcastedExcalidrawElement[],
  localAppState: AppState
): ReconciledElements {
  const localElementsData = getElementsMapWithIndex<ExcalidrawElement>(localElements)

  const reconciledElements: ExcalidrawElement[] = localElements.slice()

  const duplicates = new WeakMap<ExcalidrawElement, true>()

  let cursor = 0
  let offset = 0

  let remoteElementIdx = -1
  for (const remoteElement of remoteElements) {
    remoteElementIdx++

    const local = localElementsData[remoteElement.id]

    if (shouldDiscardRemoteElement(localAppState, local?.[0], remoteElement)) {
      if (remoteElement.parent) {
        delete remoteElement.parent
      }

      continue
    }

    if (local) {
      // mark for removal since it'll be replaced with the remote element
      duplicates.set(local[0], true)
    }

    // parent may not be defined in case the remote client is running an older
    // excalidraw version
    const parent = remoteElement.parent || remoteElements[remoteElementIdx - 1]?.id || null

    if (parent != null) {
      delete remoteElement.parent

      // ^ indicates the element is the first in elements array
      if (parent === "^") {
        offset++
        if (cursor === 0) {
          reconciledElements.unshift(remoteElement)
          localElementsData[remoteElement.id] = [remoteElement, cursor - offset]
        } else {
          reconciledElements.splice(cursor + 1, 0, remoteElement)
          localElementsData[remoteElement.id] = [remoteElement, cursor + 1 - offset]
          cursor++
        }
      } else {
        let idx = localElementsData[parent] ? localElementsData[parent]![1] : null
        if (idx != null) {
          idx += offset
        }
        if (idx != null && idx >= cursor) {
          reconciledElements.splice(idx + 1, 0, remoteElement)
          offset++
          localElementsData[remoteElement.id] = [remoteElement, idx + 1 - offset]
          cursor = idx + 1
        } else if (idx != null) {
          reconciledElements.splice(cursor + 1, 0, remoteElement)
          offset++
          localElementsData[remoteElement.id] = [remoteElement, cursor + 1 - offset]
          cursor++
        } else {
          reconciledElements.push(remoteElement)
          localElementsData[remoteElement.id] = [
            remoteElement,
            reconciledElements.length - 1 - offset,
          ]
        }
      }
      // no parent z-index information, local element exists → replace in place
    } else if (local) {
      reconciledElements[local[1]] = remoteElement
      localElementsData[remoteElement.id] = [remoteElement, local[1]]
      // otherwise push to the end
    } else {
      reconciledElements.push(remoteElement)
      localElementsData[remoteElement.id] = [remoteElement, reconciledElements.length - 1 - offset]
    }
  }

  const ret: readonly ExcalidrawElement[] = reconciledElements.filter(
    (element) => !duplicates.has(element)
  )

  return ret as ReconciledElements
}
