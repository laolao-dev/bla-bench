import { copyFileSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { basename, extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const sourceUrl = new URL('../bla/dist/engine/benchmark.js', import.meta.url);
const source = readFileSync(sourceUrl, 'utf8');
const prefix = source.slice(0, source.indexOf('export async function runShowcaseBenchmark'))
  .replace(/(from ")([.][^"]+)(")/g, (_, open, path, close) => open + '../bla/dist/engine/' + path.replace(/^\.\//, '') + close);
const blocks = [...source.matchAll(/\/\/ (\d+)\. [^\n]+\n(?:\s*\/\/[^\n]*\n)*\s*(?:if \(isNodeSqliteAvailable\(\)\) )?\{([\s\S]*?)const res = protectTarget\(\{ inputPath: (\w+),[^\n]+\n[\s\S]*?cases\.push\(buildCaseResult\("([^"]+)", "([^"]+)"/g)];
if (blocks.length !== 16 || blocks.some((block, index) => Number(block[1]) !== index + 1)) {
  throw new Error(`Unexpected benchmark cases: ${blocks.map(block => block[1]).join(', ')}`);
}
const generated = new URL('./original-builders.mjs', import.meta.url);
const body = blocks.map(([, number, setup, artifact, id, title]) => {
  const metadata = JSON.stringify({ number: Number(number), id, title });
  return `{const tempDir = fixtureDir(${JSON.stringify(id)}); ${setup} results.push({...${metadata}, path: ${artifact}});}`;
}).join('\n');
writeFileSync(generated, `${prefix}\nexport default function(fixtureDir) {const results=[];\n${body}\nreturn results;}`);
const { default: buildOriginals } = await import(generated);
const fixtures = buildOriginals(id => {
  const path = fileURLToPath(new URL(`../fixtures/${id}/`, import.meta.url));
  mkdirSync(path, { recursive: true });
  return path;
}).map(item => ({ ...item, format: extname(item.path), size: statSync(item.path).size }));
const selected = fixtures.filter(item => item.format === '.js').sort((first, second) => first.size - second.size)[0];
const target = fileURLToPath(new URL(`../targets/${selected.id}/original/`, import.meta.url));
mkdirSync(target, { recursive: true });
copyFileSync(selected.path, join(target, basename(selected.path)));
const lines = [
  '# BLA 官方未加固样本', '',
  'BLA 3.6.0，提交 `8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`。',
  '来源：`bla/src/engine/benchmark.ts`。官方 CLI 把原件写到临时目录后删除；下表是用各案例 `protectTarget` 前的原始构造代码重新生成的持久副本，不含加固产物。',
  `最小 JavaScript 原件：${selected.id}（${selected.size} 字节）。已复制到 \`targets/${selected.id}/original/${basename(selected.path)}\`。`,
];
const table = (title, items) => ['', `## ${title}`, '', '| # | 名称 | 格式 | 路径（相对 bla-bench） | 大小（字节） |', '|---:|---|---|---|---:|', ...items.map(item => `| ${item.number} | ${item.title} | \`${item.format}\` | \`fixtures/${item.id}/${basename(item.path)}\` | ${item.size} |`)];
lines.push(...table('前 14 项', fixtures.slice(0, 14)), ...table('当前版本额外的第 15、16 项', fixtures.slice(14)));
writeFileSync(new URL('../samples.md', import.meta.url), `${lines.join('\n')}\n`);
console.log(`${selected.id}: ${selected.size} bytes; ${fixtures.length} original fixtures`);
