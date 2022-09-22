import { ReactNode } from "react"
import React from "react"

interface IslandSectionProps {
  children: ReactNode
  className?: string
  title: string
}

export default function IslandSection({ children, className, title }: IslandSectionProps) {
  return (
    <section>
      <h2 className="visually-hidden">{title}</h2>
      <div
        className={"Island " + (className ?? "")}
        style={{ "--padding": "2" } as React.CSSProperties}
      >
        {children}
      </div>
    </section>
  )
}
