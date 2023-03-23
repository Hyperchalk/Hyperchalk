import { GaugeOptions } from "svg-gauge"
import { ReplayCommunicator } from "../communication"
import { useControlState, useReplayProgress } from "../communication/replay"
import Gauge from "./Gauge"
import React from "react"

const color = (val: number) => "green"

export default function ReplayControls({ communicator }: { communicator: ReplayCommunicator }) {
  const [controlState, sendControlState] = useControlState(communicator)
  const [current, duration] = useReplayProgress(communicator)
  const options: GaugeOptions = { color }

  return (
    <div className="replay-controls">
      {controlState == "play" ? (
        <button className="replay-controls__button" onClick={(e) => sendControlState("pause_replay")}>
          ⏸
        </button>
      ) : (
        <button className="replay-controls__button" onClick={(e) => sendControlState("start_replay")}>
          ▶️
        </button>
      )}
      <button className="replay-controls__button" onClick={(e) => sendControlState("restart_replay")}>
        ⏮
      </button>
      <Gauge className="replay-controls__progress" maxValue={duration} options={options} value={current} />
    </div>
  )
}
