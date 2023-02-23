import { useEffect, useRef } from "react"
import SvgGauge, { GaugeOptions, GaugeInstance } from "svg-gauge"
import React from "react"

/**
 * Gauge component based on svg-gauge.
 *
 * @param {Props} props value, wrapper class name and gauge options. options cannot be updated after
 *        instanciation
 * @returns Gauge component
 */
const Gauge = ({ value, className, options, maxValue }: Props) => {
  const gaugeEl = useRef<HTMLDivElement>(null)
  const gaugeRef = useRef<GaugeInstance | null>(null)
  useEffect(() => {
    if (!gaugeRef.current) {
      if (!gaugeEl.current) return
      gaugeRef.current = SvgGauge(gaugeEl.current, { ...options })
      gaugeRef.current?.setValue(0)
    }
    gaugeRef.current?.setMaxValue(maxValue)
    gaugeRef.current?.setValueAnimated(value, 1)
  }, [value, maxValue])

  return (
    <div className={className}>
      <div ref={gaugeEl} />
    </div>
  )
}

interface Props {
  className?: string
  maxValue: number
  options?: GaugeOptions
  value: number
}

export default Gauge
