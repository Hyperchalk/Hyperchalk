import { AppState, ExcalidrawImperativeAPI } from "@excalidraw/excalidraw/types/types"
import React, { lazy, ReactChild, RefObject, Suspense, useState } from "react"
import IslandSection from "./IslandSection"

const LazyHyperShow = lazy(() => import("./HyperShow"))

type ToolIconProps = { children: ReactChild; title: string } & { [key: string]: any }

function ToolIcon({ title, children, ...props }: ToolIconProps) {
  return (
    <label
      title={title}
      className="ToolIcon_type_button ToolIcon_size_medium ToolIcon_type_button--show ToolIcon"
    >
      <input type="radio" className="ToolIcon_type_radio ToolIcon_size_medium" {...props} />
      <span className="ToolIcon__icon">{children}</span>
    </label>
  )
}

interface TopRightUIProps {
  isMobile: boolean
  appState: AppState
  apiRef: RefObject<ExcalidrawImperativeAPI>
}

export default function TopRightUI({ isMobile, appState, apiRef }: TopRightUIProps) {
  const [panel, setPanel] = useState<"hypershow" | null>(null)

  return (
    <div className="Stack Stack_vertical" style={{ "--gap": 4 } as React.CSSProperties}>
      <IslandSection title="Hyperchalk functions">
        <div className="Stack Stack_vertical">
          <div
            className="Stack Stack_horizontal"
            style={{ "--gap": 1, justifyContent: "space-between" } as React.CSSProperties}
          >
            <ToolIcon
              title="create Hypershow-presentation"
              name="hypershow"
              onChange={() => setPanel("hypershow")}
              checked={panel == "hypershow"}
            >
              🖼
            </ToolIcon>
            {panel != null ? (
              <ToolIcon
                title="close panel"
                name="close-hyperchalk-panel"
                onClick={() => setPanel(null)}
              >
                ❌
              </ToolIcon>
            ) : null}
          </div>
        </div>
      </IslandSection>
      <Suspense
        fallback={
          <IslandSection title="Loading">
            <span>Loading...</span>
          </IslandSection>
        }
      >
        {panel == "hypershow" ? <LazyHyperShow apiRef={apiRef} appState={appState} /> : null}
      </Suspense>
    </div>
  )
}
