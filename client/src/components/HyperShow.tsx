import React, { RefObject, useCallback, useState } from "react"
import IslandSection from "./IslandSection"
import { Droppable, Draggable, DragDropContext, DropResult } from "react-beautiful-dnd"
import { ExcalidrawElement } from "@excalidraw/excalidraw/types/element/types"
import { AppState, ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types/types"
import { ApiRef } from "../types"

interface DraggableElements {
  elements: ExcalidrawElement[]
  id: string
}

interface ListItemProps {
  item: DraggableElements
  index: number
  rm: (idx: number) => void
  show: (elements: ExcalidrawElement[]) => void
}

function ListItem({ item, index, rm, show }: ListItemProps) {
  return (
    <Draggable draggableId={item.id} index={index}>
      {(provided) => (
        <li {...provided.draggableProps} {...provided.dragHandleProps} ref={provided.innerRef}>
          {item.elements.map((e) => (
            <div key={e.id}>
              {e.type} {e.id.slice(0, 5)}
            </div>
          ))}
          <button className="zIndexButton" title="Remove Focus Object" onClick={() => rm(index)}>
            ➖
          </button>
          <button
            className="zIndexButton"
            title="Remove Focus Object"
            onClick={() => show(item.elements)}
          >
            👁
          </button>
        </li>
      )}
    </Draggable>
  )
}

/**
 * Typeguard to ensure the imperative API is available
 */
function apiOrThrow(apiRef: RefObject<ExcalidrawImperativeAPI>) {
  if (apiRef.current === null) throw new Error("api is null")
  return apiRef.current
}

// TODO: remove list items when they are deleted from the board
const usedElements = new WeakSet<ExcalidrawElement>()

interface HyperShowProps {
  appState: AppState
  apiRef: ApiRef
}

export default function HyperShow({ apiRef, appState }: HyperShowProps) {
  // list of elements that are to be centered when the show goes on
  const [items, setItems] = useState<DraggableElements[]>([])

  // TODO: register event listener for arrow events
  // TODO: persist state
  // TODO: improve UI so we know what elements are meant. e.g. with screenshots / exports?

  function onDragEnd(result: DropResult) {
    const { source, destination } = result
    if (!destination || destination.index == source.index) return
    const newItems = [...items]
    newItems.splice(source.index, 1)
    newItems.splice(destination.index, 0, items[source.index])
    setItems(newItems)
  }

  function addSelectedElement() {
    let api = apiOrThrow(apiRef)
    let elements = api
      .getSceneElements()
      .filter((el) => Object.keys(appState.selectedElementIds).indexOf(el.id) > -1)
    if (elements.length) {
      setItems([...items, { elements, id: "" + Date.now() }])
    }
  }

  function removeElement(index: number) {
    let newItems = [...items]
    newItems.splice(index, 1)
    setItems(newItems)
  }

  function showElements(elements: ExcalidrawElement[]) {
    let api = apiOrThrow(apiRef)
    api.scrollToContent(elements)
  }

  return (
    <IslandSection className="App-menu__left panelColumn " title="Hypershow presentation">
      <fieldset>
        <legend>Focus Objects</legend>
        <div className="buttonList">
          <button className="zIndexButton" title="Add Focus Object" onClick={addSelectedElement}>
            ➕
          </button>
        </div>
      </fieldset>
      <DragDropContext onDragEnd={onDragEnd}>
        <Droppable droppableId="hypershow">
          {(provided) => (
            <ul {...provided.droppableProps} ref={provided.innerRef} className="hypershow__list">
              {items.map((item, index) => (
                <ListItem
                  item={item}
                  index={index}
                  rm={removeElement}
                  show={showElements}
                  key={item.id}
                />
              ))}
              {provided.placeholder}
            </ul>
          )}
        </Droppable>
      </DragDropContext>
    </IslandSection>
  )
}
