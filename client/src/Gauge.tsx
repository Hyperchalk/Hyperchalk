/*

https://github.com/naikus/svg-gauge

The MIT License (MIT)

Copyright (c) 2016 Aniket Naik

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*/

import { useEffect, useRef } from "react"
import SvgGauge, { GaugeOptions, GaugeInstance } from "svg-gauge"

const Gauge = ({ value }: Props) => {
  const gaugeEl = useRef<HTMLDivElement>(null)
  const gaugeRef = useRef<GaugeInstance | null>(null)
  useEffect(() => {
    if (!gaugeRef.current) {
      if (!gaugeEl.current) return
      const options: GaugeOptions = { color: (value) => "green" }
      gaugeRef.current = SvgGauge(gaugeEl.current, options)
      gaugeRef.current?.setValue(1)
    }
    gaugeRef.current?.setValueAnimated(value, 1)
  }, [value])

  return (
    <div style={{ width: "40px", height: "40px" }}>
      <div ref={gaugeEl} />
    </div>
  )
}

interface Props {
  value: number
}

export default Gauge
