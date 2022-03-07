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

declare module "svg-gauge" {
  export interface GaugeInstance {
    setMaxValue: (max: number) => void
    setValue: (val: number) => void
    setValueAnimated: (val: number, duration: number) => void
    getValue: () => number
  }

  export interface GaugeOptions {
    /** The angle in degrees to start the dial
     * @default 135
     */
    dialStartAngle?: number
    /** The angle in degrees to end the dial. This MUST be less than dialStartAngle
     * @default 45
     */
    dialEndAngle?: number
    /** The radius of the gauge
     * @default 40
     */
    radius?: number
    /** The minimum value for the gauge. This can be a negative value
     * @default 0
     */
    min?: number
    /** The maximum value for the gauge
     * @default 100
     */
    max?: number
    /** Getter for the label that will be rendered in the center. */
    label?: (currentValue: number) => string
    /** Whether to show the value at the center of the gauge
     * @default true
     */
    showValue?: boolean
    /** The CSS class of the gauge
     * @default 'gauge'
     */
    gaugeClass?: string
    /** The CSS class of the gauge's dial
     * @default 'dial'
     */
    dialClass?: string
    /** The CSS class of the gauge's fill
     * @default 'value'
     */
    valueDialClass?: string
    /** The CSS class of the gauge's text
     * @default '(value-text)'
     */
    valueClass?: string
    /** An optional function that can return a color for current value
     */
    color?: (currentValue: number) => string
    /** An optional string that specifies the crop region
     * @default '(0 0 100 100)'
     */
    viewBox?: string
  }

  /**
   * Creates a Gauge instance.
   * @param {Element} element The DOM into which to render the gauge
   * @param {GaugeOptions} options The gauge options
   */
  const createInstance: (element: Element, options?: GaugeOptions) => GaugeInstance

  export default createInstance
}
