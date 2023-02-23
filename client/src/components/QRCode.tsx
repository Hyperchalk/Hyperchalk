import qr from "qrcode-generator"
import React, { useMemo } from "react"

export default function QRCode({ link }: { link: string }) {
  const qrCode = useMemo(() => {
    const qrCode = qr(0, "L")
    qrCode.addData(link)
    qrCode.make()
    return qrCode.createDataURL(10, 1)
  }, [link])

  return <img src={qrCode} style={{ margin: ".5rem" }} />
}
