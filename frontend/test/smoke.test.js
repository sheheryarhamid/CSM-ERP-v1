const fs = require('fs')
const path = require('path')

function fail(msg){
  console.error('SMOKE TEST FAIL:', msg)
  process.exit(2)
}

const indexPath = path.join(__dirname, '..', 'index.html')
if(!fs.existsSync(indexPath)) fail('index.html not found')
const content = fs.readFileSync(indexPath, 'utf8')
if(!/Central ERP Hub/.test(content)) fail('expected app title not found in index.html')
console.log('SMOKE TEST OK')
process.exit(0)
