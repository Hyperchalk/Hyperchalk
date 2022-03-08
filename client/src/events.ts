// #region event system

export type EventMap = Record<string, any>
export type EventKey<T> = keyof T & string
export type EventHandler<T, K extends EventKey<T>> = (event: T[K]) => void

export interface EventEmitter<T extends EventMap> {
  on<K extends EventKey<T>>(eventName: K, handler: EventHandler<T, K>): void
  off<K extends EventKey<T>>(eventName: K, handler: EventHandler<T, K>): void
  emit<K extends EventKey<T>>(eventName: K, event: T[K]): void
}
