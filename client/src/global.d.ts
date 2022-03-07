import { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types/types"

declare global {
  interface Window {
    draw?: React.RefObject<ExcalidrawImperativeAPI>
    EXCALIDRAW_ASSET_PATH?: string
  }
}
