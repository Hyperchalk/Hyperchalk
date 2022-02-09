#!/usr/bin/env node

const preactCompatPlugin = require("./build/esbuild-preact-compat")
const copyDist = require("./build/copy-dist")

copyDist("static", "dist")

require("esbuild")
  .build({
    entryPoints: ["src/index.tsx"],
    bundle: true,
    outfile: "dist/app.js",
    sourcemap: true,
    minify: true,
    // plugins: [preactCompatPlugin],
  })
  .catch(() => process.exit(1))
