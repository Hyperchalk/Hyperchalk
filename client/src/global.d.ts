import { ExcalidrawImperativeAPI } from "@excalidraw/excalidraw-next/types/types"

declare global {
  interface Window {
    draw?: React.RefObject<ExcalidrawImperativeAPI>
    EXCALIDRAW_ASSET_PATH?: string
  }
}
