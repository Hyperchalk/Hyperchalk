// #region crypto
/**
 * i.e. 0-255 -> '00'-'ff'
 * from https://stackoverflow.com/a/27747377
 * @param dec decimal number to convert to hex string
 */
//
function dec2hex(dec: number) {
  return dec < 10 ? "0" + String(dec) : dec.toString(16)
}

/**
 * Generate a securely random string
 * from https://stackoverflow.com/a/27747377
 * @param len length to the string
 */
export function generateRandomString(len?: number) {
  const arr = new Uint8Array((len || 40) / 2)
  window.crypto.getRandomValues(arr)
  return Array.from(arr, dec2hex).join("")
}
// #endregion crypto

export function getJsonScript(id: string, init = {}) {
  return JSON.parse(document.getElementById(id)?.textContent ?? JSON.stringify(init))
}

export function getLocalStorageJson(key: string, init = {}) {
  return JSON.parse(localStorage.getItem(key) ?? JSON.stringify(init))
}

export function setLocalStorageJson(key: string, value: any) {
  localStorage.setItem(key, JSON.stringify(value))
}

export function noop() {}

export function assignAndReturn<T, S extends keyof T = keyof T>(o: T, attr: S, val: T[S]) {
  o[attr] = val
  return o
}

/**
 * Get all cookies as an object.
 * @returns all cookies with cookie names as keys.
 */
export function getAllCookies() {
  let pairs = document.cookie.split(";").map((pair) => pair.trim().split("=") as [string, string])
  return pairs.reduce(
    (o, [k, v]) => assignAndReturn(o, k, decodeURIComponent(v)),
    {} as Record<string, string>
  )
}

/**
 * Get a specific cookie's value.
 * @param name the cookie name
 * @returns the value
 */
export function getCookie(name: string) {
  return getAllCookies()[name]
}

/**
 * Sets a cookie on this document.
 * @param name the cookies name
 * @param value the value of the cookie
 * @param max_age the maximum age of the cookie in seconds. default is two days.
 */
export function setCookie(name: string, value: string, max_age = 172800) {
  document.cookie = `${name}=${encodeURIComponent(value)}; max-age=${max_age}`
}

const readOnlyMethods = new Set(["GET", "OPTIONS", "HEAD"])

/**
 * Creates a `RequestInit` that includes everything that's needed to call the REST API.
 * @param data the data to POST/PUT/PATCH/DELETE to the API
 * @param method the HTTP method you want to use. defaults to `'POST'`.
 * @param additional any custom parameters for the `RequestInit`. Defaults to `{}`.
 * @returns a `RequestInit` object to use in your `fetch()` call
 */
export function apiRequestInit(
  method: string,
  data: any = undefined,
  additional: RequestInit = {},
  headers: HeadersInit = {}
): RequestInit {
  let init: RequestInit = {
    method,
    credentials: "same-origin",
    headers: new Headers(
      readOnlyMethods.has(method)
        ? { ...headers }
        : {
            "X-CSRFTOKEN": getCookie("csrftoken"),
            "Content-Type": "application/json; charset=utf8",
            ...headers,
          }
    ),
    ...additional,
  }
  if (data !== undefined) init.body = new Blob([JSON.stringify(data)], { type: "application/json" })
  return init
}
