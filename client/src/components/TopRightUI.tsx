import React from "react"
import type { ConfigProps } from "../types"
import QRCode from "./QRCode"

export default function TopRightUI(config: ConfigProps) {
  const showTopRightUI = config.SHOW_QR_CODE // extend this condition if you add more top right UI elements

  if (!showTopRightUI) return () => null

  return () => (
    <div className="topright Island App-toolbar" style={{ "--padding": 1 } as any}>
      {config.SHOW_QR_CODE ? (
        <>
          <label className="topright__toggle topright__qr replay-controls__button" htmlFor="qr-toggle">
            <img className="topright__icon" src="/static/qr.svg" width="24" height="24" />
            <span className="topright__label visually-hidden">Show QR Code</span>
          </label>
          <input className="topright__toggle-input visually-hidden" type="checkbox" id="qr-toggle" />
          <QRCode link={window.location.href} />
        </>
      ) : null}
    </div>
  )
}
