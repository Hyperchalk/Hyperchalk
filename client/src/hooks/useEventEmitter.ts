import { useEffect, useRef } from "react"
import { EventEmitter, EventKey, EventMap, EventHandler } from "../events"

/**
 * Use an event emitter as a hook.
 *
 * @param eventName event name to subscribe to
 * @param handler event handler
 * @param emitter event emitter for adding the event listener to.
 */
export function useEventEmitter<T extends EventMap, K extends EventKey<T>>(
  emitter: EventEmitter<T>,
  eventName: K,
  handler: EventHandler<T, K>
) {
  // Create a ref that stores handler
  const savedHandler = useRef<typeof handler>()

  // Update ref.current value if handler changes.
  // This allows our effect below to always get latest handler
  // without us needing to pass it in effect deps array and
  // potentially cause effect to re-run every render.
  useEffect(() => {
    savedHandler.current = handler
  }, [handler])

  useEffect(
    () => {
      const isSupported = emitter && emitter.on
      if (!isSupported) return

      // Create event listener that calls handler function stored in ref
      const eventListener = (event: any) => savedHandler.current?.(event)

      // Add event listener
      emitter.on(eventName, eventListener)

      // Remove event listener on cleanup
      return () => {
        emitter.off(eventName, eventListener)
      }
    },
    [eventName, emitter] // Re-run if eventName or element changes
  )
}
