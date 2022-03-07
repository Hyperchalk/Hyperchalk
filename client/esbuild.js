#!/usr/bin/env node

// const preactCompatPlugin = require("./build/esbuild-preact-compat")
const copyDist = require("./build/copy-dist")
const fs = require("fs")

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
    metafile: true,
    treeShaking: true,
    define: {
      "process.env.NODE_ENV": "'production'",
      production: "'production'",
    },
    // plugins: [preactCompatPlugin],
  })
  .then((result) => {
    fs.writeFileSync("dist/meta.json", JSON.stringify(result.metafile))
  })
  .catch(() => process.exit(1))
