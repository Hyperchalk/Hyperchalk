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
  return JSON.parse(document.getElementById(id)?.innerText ?? JSON.stringify(init))
}

export function getLocalStorageJson(key: string, init = {}) {
  return JSON.parse(localStorage.getItem(key) ?? JSON.stringify(init))
}

export function setLocalStorageJson(key: string, value: any) {
  localStorage.setItem(key, JSON.stringify(value))
}

export function noop() {}
