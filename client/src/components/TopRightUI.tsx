import React from "react"
import QRCode from "./QRCode"

export default function TopRightUI() {
  return (
    <div className="topright Island App-toolbar" style={{ "--padding": 1 } as any}>
      <label className="topright__toggle topright__qr replay-controls__button" htmlFor="qr-toggle">
        <img className="topright__icon" src="/static/qr.svg" width="24" height="24" />
        <span className="topright__label visually-hidden">Show QR Code</span>
      </label>
      <input className="topright__toggle-input visually-hidden" type="checkbox" id="qr-toggle" />
      <QRCode link={window.location.href} />
    </div>
  )
}
