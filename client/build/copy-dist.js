const fs = require("fs")
const path = require("path")

function copyFolderRecursiveSync(source, target) {
  if (fs.lstatSync(source).isDirectory()) {
    fs.mkdirSync(target, { recursive: true })
    let files = fs.readdirSync(source)
    for (let file of files) {
      let curSource = path.join(source, file)
      let curTarget = path.join(target, file)
      copyFolderRecursiveSync(curSource, curTarget)
    }
  } else {
    fs.copyFileSync(source, target)
  }
}

module.exports = copyFolderRecursiveSync
