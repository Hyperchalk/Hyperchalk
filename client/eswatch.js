#!/usr/bin/env node

// const preactCompatPlugin = require("./build/esbuild-preact-compat")
const copyDist = require("./build/copy-dist")

copyDist("static", "dist")

require("esbuild")
  .serve(
    {
      servedir: "dist",
      host: "localhost",
    },
    {
      entryPoints: ["src/index.tsx"],
      bundle: true,
      outfile: "dist/app.js",
      sourcemap: true,
      // plugins: [preactCompatPlugin],
    }
  )
  .then((server) => {
    // Call "stop" on the web server to stop serving
    console.log(`Serving on http://${server.host}:${server.port}`)
  })

require("esbuild")
  .build({
    entryPoints: ["src/index.tsx"],
    bundle: true,
    outfile: "dist/app.js",
    sourcemap: true,
    watch: {
      onRebuild(error, result) {
        if (error) console.error("watch build failed:", error)
        else console.log("watch build succeeded:", result)
      },
    }, // plugins: [preactCompatPlugin],
  })
  .then((server) => {
    // Call "stop" on the web server to stop serving
    console.log("watching...")
  })
