// import { useState, useEffect } from "react";
import { render } from "react-dom";
import * as React from "react"
import Excalidraw from "@excalidraw/excalidraw"

window.React = React

// function IndexPage() {
//   const [Comp, setComp] = useState(null);
//   useEffect(() => {
//     import("@excalidraw/excalidraw").then((comp) => setComp(comp.default));
//   }, []);
//   return <>{Comp && <Comp />}</>;
// }

// render(<IndexPage/>, document.getElementById("app"))
render(<Excalidraw/>, document.getElementById("app"))

import "./style.css"
