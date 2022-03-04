import { ReplayCommunicator } from "./communication"
import { useControlState } from "./communication/replay"

export default function ReplayControls({ communicator }: { communicator: ReplayCommunicator }) {
  const [controlState, sendControlState] = useControlState(communicator)

  return (
    <div className="replay-controls">
      {controlState == "play" ? (
        <button
          className="replay-controls__button"
          onClick={(e) => sendControlState("pause_replay")}
        >
          ⏸
        </button>
      ) : (
        <button
          className="replay-controls__button"
          onClick={(e) => sendControlState("start_replay")}
        >
          ▶️
        </button>
      )}
      <button
        className="replay-controls__button"
        onClick={(e) => sendControlState("restart_replay")}
      >
        ⏮
      </button>
    </div>
  )
}
