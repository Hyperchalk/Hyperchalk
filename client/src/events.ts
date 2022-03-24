// #region event emitter

export type EventMap = Record<string, any>
export type EventKey<T> = keyof T & string
export type EventHandler<T, K extends EventKey<T>> = (event: T[K]) => void

export interface EventEmitter<T extends EventMap> {
  on<K extends EventKey<T>>(eventName: K, handler: EventHandler<T, K>): void
  off<K extends EventKey<T>>(eventName: K, handler: EventHandler<T, K>): void
  emit<K extends EventKey<T>>(eventName: K, event: T[K]): void
}

// #endregion event emitter

// #region event target

export interface EventHandlerObject<T, K extends EventKey<T>> {
  handleEvent: (event: T[K]) => void
}

export type EventHandlerOrEventHandlerObject<T, K extends EventKey<T>> =
  | EventHandler<T, K>
  | EventHandlerObject<T, K>

export interface StrongEventTarget<
  T extends EventMap,
  K extends EventKey<T>,
  H extends EventHandlerOrEventHandlerObject<T, K> = EventHandlerOrEventHandlerObject<T, K>
> {
  addEventListener(eventName: K, handler: H): void
  addEventListener(eventName: K, handler: H, options: AddEventListenerOptions): void
  addEventListener(eventName: K, handler: H, useCapture: boolean): void
  removeEventListener(eventName: K, handler: H): void
  removeEventListener(eventName: K, handler: H, options: EventListenerOptions): void
  removeEventListener(eventName: K, handler: H, useCapture: boolean): void
  dispatchEvent?<E extends T[K]>(event: E): void
}

export function isEventListenerObject<T extends EventMap, K extends EventKey<T> = EventKey<T>>(
  handler: EventHandlerOrEventHandlerObject<T, K> | null | undefined
): handler is EventHandlerObject<T, K> {
  return !!handler && "handleEvent" in handler
}

export function isEventListener<T extends EventMap, K extends EventKey<T> = EventKey<T>>(
  handler: EventHandlerOrEventHandlerObject<T, K> | null | undefined
): handler is EventHandler<T, K> {
  return !!handler && typeof handler == "function"
}

// #endregion event target
