import { createReadStream } from 'node:fs';
import { createInterface } from 'node:readline';
import * as pagefind from 'pagefind';
import { fileURLToPath } from 'node:url';

const recordsPath = new URL('../build/search-records.jsonl', import.meta.url);
const outputPath = fileURLToPath(new URL('../site/pagefind/', import.meta.url));
function check(result) {
  if (result.errors?.length) throw new Error(result.errors.join('\n'));
  return result;
}
const { index } = check(await pagefind.createIndex({
  forceLanguage: 'de',
  includeCharacters: '+#_',
  writePlayground: false,
  // Bundle post snippets so Pages does not have to sync one file per result.
  maxFragments: 512,
}));
if (!index) throw new Error('Pagefind could not create an index');
let count = 0;
try {
  const lines = createInterface({ input: createReadStream(recordsPath), crlfDelay: Infinity });
  for await (const line of lines) {
    if (!line.trim()) continue;
    check(await index.addCustomRecord(JSON.parse(line)));
    count++;
    if (count % 2000 === 0) console.log(`Search index: ${count} records`);
  }
  if (!count) throw new Error('No searchable records were supplied');
  check(await index.writeFiles({ outputPath }));
  console.log(`Search index complete: ${count} records`);
} finally {
  await index.deleteIndex();
  await pagefind.close();
}
