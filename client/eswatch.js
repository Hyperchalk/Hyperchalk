#!/usr/bin/env node

// const preactCompatPlugin = require("./build/esbuild-preact-compat")
const copyDist = require("./build/copy-dist")

copyDist("static", "dist")
copyDist("node_modules/@excalidraw/excalidraw/dist/excalidraw-assets", "dist/excalidraw-assets")
copyDist(
  "node_modules/@excalidraw/excalidraw/dist/excalidraw-assets-dev",
  "dist/excalidraw-assets-dev"
)

const basicconf = {
  bundle: true,
  entryPoints: ["src/app.tsx"],
  format: "esm",
  outdir: "dist/",
  sourcemap: true,
  splitting: true,
}

require("esbuild")
  .serve(
    {
      servedir: "dist",
      host: "localhost",
      port: 8080,
    },
    { ...basicconf }
  )
  .then((server) => {
    // Call "stop" on the web server to stop serving
    console.log(`Serving on http://${server.host}:${server.port}`)
  })

require("esbuild")
  .build({
    ...basicconf,
    watch: {
      onRebuild(error, result) {
        // copyDist("static", "dist")
        // copyDist(
        //   "node_modules/@excalidraw/excalidraw/dist/excalidraw-assets",
        //   "dist/excalidraw-assets"
        // )
        // copyDist(
        //   "node_modules/@excalidraw/excalidraw/dist/excalidraw-assets-dev",
        //   "dist/excalidraw-assets-dev"
        // )
        if (error) console.error("watch build failed:", error)
        else console.log("watch build succeeded:", result)
      },
    },
    // plugins: [preactCompatPlugin],
  })
  .then((server) => {
    // Call "stop" on the web server to stop serving
    console.log("watching...")
  })
