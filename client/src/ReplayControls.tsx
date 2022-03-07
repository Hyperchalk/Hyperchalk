import { ReplayCommunicator } from "./communication"
import { useControlState, useReplayProgress } from "./communication/replay"
import Gauge from "./Gauge"

export default function ReplayControls({ communicator }: { communicator: ReplayCommunicator }) {
  const [controlState, sendControlState] = useControlState(communicator)
  const replayProgress = useReplayProgress(communicator)

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
      <Gauge value={replayProgress} />
    </div>
  )
}
