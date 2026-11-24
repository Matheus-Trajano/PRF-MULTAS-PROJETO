// Extrai um .rar para um diretório usando node-unrar-js (WASM, sem binário do sistema)
const { createExtractorFromData } = require('node-unrar-js');
const fs = require('fs');
const path = require('path');
(async () => {
  const [rarPath, outDir] = process.argv.slice(2);
  const data = fs.readFileSync(rarPath);
  const ex = await createExtractorFromData({ data });
  fs.mkdirSync(outDir, { recursive: true });
  let n = 0, skipped = 0;
  for (const f of ex.extract().files) {
    const name = f.fileHeader.name;
    if (name.endsWith('/') || f.fileHeader.packSize === 0) { skipped++; continue; }
    if (!f.extraction) { skipped++; continue; }
    const dest = path.join(outDir, path.basename(name));
    fs.writeFileSync(dest, f.extraction);
    n++;
  }
  console.log(`OK ${path.basename(rarPath)}: ${n} arquivos extraidos, ${skipped} entradas ignoradas -> ${outDir}`);
})().catch(e => { console.error('FALHA:', e.message); process.exit(1); });
