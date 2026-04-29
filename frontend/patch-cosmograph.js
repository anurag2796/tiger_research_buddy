const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, 'node_modules', '@cosmograph', 'cosmograph', 'cosmograph', 'managers', 'licensing-manager.js');

if (fs.existsSync(filePath)) {
  let content = fs.readFileSync(filePath, 'utf8');
  content = content.replace(
    'import e from"@/cosmograph/style.module.css";',
    'const e = { attribution: "cosmograph-attribution" };'
  );
  content = content.replace(
    'import e from "@/cosmograph/style.module.css";',
    'const e = { attribution: "cosmograph-attribution" };'
  );
  fs.writeFileSync(filePath, content, 'utf8');
  console.log('Patched Cosmograph licensing-manager.js');
} else {
  console.log('Could not find Cosmograph licensing-manager.js');
}
