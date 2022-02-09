module.exports = {
  // plugin from https://github.com/evanw/esbuild/issues/266
  name: "preact-compat",
  setup(build) {
    const path = require("path");
    const preact = path.join(
      process.cwd(),
      "node_modules",
      "preact",
      "compat",
      "dist",
      "compat.module.js"
    );

    build.onResolve({ filter: /^(react-dom|react)$/ }, (args) => {
      return { path: preact };
    });
  },
};
