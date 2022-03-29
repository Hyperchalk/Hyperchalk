interface Messages {
  "org.imsglobal.lti.close": {}
  "lti.frameResize": { height: number | string }
  "lti.removeBorder": {}
  "lti.scrollToTop": {}
}

// type Messages = ResizeFrame | ScrollToTop | RemoveBorder

export function dispatchLtiFrameMessage<T extends Messages = Messages, K extends keyof T = keyof T>(
  subject: K,
  data: T[K]
) {
  ;(window.parent || window.opener)?.postMessage(JSON.stringify({ subject, ...data }), "*")
}
