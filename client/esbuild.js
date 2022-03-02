#!/usr/bin/env node

// const preactCompatPlugin = require("./build/esbuild-preact-compat")
const copyDist = require("./build/copy-dist")

copyDist("static", "dist")
copyDist("node_modules/@excalidraw/excalidraw/dist/excalidraw-assets", "dist/excalidraw-assets")
copyDist(
  "node_modules/@excalidraw/excalidraw/dist/excalidraw-assets-dev",
  "dist/excalidraw-assets-dev"
)
require("esbuild")
  .build({
    entryPoints: ["src/index.tsx"],
    bundle: true,
    outfile: "dist/app.js",
    sourcemap: true,
    minify: true,
    define: {
      "process.env.NODE_ENV": "production",
      production: "production",
    },
    // plugins: [preactCompatPlugin],
  })
  .catch(() => process.exit(1))
