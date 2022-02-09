const fs = require("fs")
const path = require("path")

module.exports = function copyDist(from, to) {
  fs.mkdirSync(to, { recursive: true })
  let files = fs.readdirSync(from)
  for (file of files) {
    fs.copyFileSync(path.join(from, file), path.join(to, file))
  }
}
