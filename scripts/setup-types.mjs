import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';

// Pin both the revision and content for identical local and CI diagnostics.
const revision = 'f703392df78b5fba5e8f9f1ad0b1cb6d3def9736';
const digest = 'a080c34acaef287db4e920f7ae5cd6d0389a26498b2ecc2005c8377ac69318cb';
const response = await fetch(
  `https://raw.githubusercontent.com/yazi-rs/plugins/${revision}/types.yazi/main.lua`,
  { signal: AbortSignal.timeout(30000) },
);
if (!response.ok) throw new Error(`Type download failed: HTTP ${response.status}`);
const source = Buffer.from(await response.arrayBuffer());
if (createHash('sha256').update(source).digest('hex') !== digest) {
  throw new Error('Yazi type checksum mismatch');
}
const directory = new URL('../.dev/types/', import.meta.url);
await mkdir(directory, { recursive: true });
// Mark definitions as metadata so they cannot resolve as a plugin module.
await writeFile(new URL('yazi.lua', directory), Buffer.concat([
  Buffer.from('---@meta _\n'), source,
]));
console.log(`Yazi types ready (${revision})`);
