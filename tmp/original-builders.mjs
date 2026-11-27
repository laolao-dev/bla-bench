import { createHash } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import vm from "node:vm";
import { BLA_IDENTITY } from "../bla/dist/identity.js";
import { getDatabaseSyncClass, isNodeSqliteAvailable } from "../bla/dist/core/sqlite-runtime.js";
import { packAsarBuffer, unpackAsarBuffer } from "../bla/dist/shields/formats/asar.js";
import { buildSampleSqliteDatabase } from "../bla/dist/shields/formats/sqlite.js";
import { buildSafetensorsBuffer, validateSafetensorsBuffer } from "../bla/dist/shields/formats/model.js";
import { buildMappedGoFlutterElfFixture } from "../bla/dist/shields/formats/go-flutter-exhaustion.js";
import { inspectAndroidDex } from "../bla/dist/shields/formats/mobile-game.js";
import { inspectErlangBeam } from "../bla/dist/shields/formats/erlang-beam.js";
import { inspectEvmBytecode } from "../bla/dist/shields/formats/evm-bytecode.js";
import { inspectPcapCapture } from "../bla/dist/shields/formats/pcap-capture.js";
import { inspectGpuPtx } from "../bla/dist/shields/formats/gpu-ptx.js";
import { parseGgufLayout, readGgufStringKv } from "../bla/dist/shields/formats/gguf-layout.js";
import { auditTarget } from "../bla/dist/engine/auditor.js";
import { protectTarget } from "../bla/dist/engine/protector.js";
/**
 * Showcase 1: DX-Ball Sound-Pan Calculation (Directly countering REA's #1 README Showcase!)
 */
const DX_BALL_SOURCE = `
function clampPan(panValue) {
  if (panValue < -10000) return -10000;
  if (panValue > 10000) return 10000;
  return panValue | 0;
}

function calculateSoundPan(paddleX, ballX, screenWidth) {
  const center = screenWidth >> 1;
  const delta = (ballX - center) * 18;
  const weighted = delta + ((paddleX - center) >> 2);
  return clampPan(weighted);
}

module.exports = { calculateSoundPan, clampPan };
`;
/**
 * Showcase 2: Notion Electron Clipboard Bridge (Directly countering REA's #2 README Showcase!)
 */
const NOTION_PRELOAD_SOURCE = `
const { contextBridge, ipcRenderer } = require("electron");

function exposeNotionClipboardBridge() {
  contextBridge.exposeInMainWorld("notionClipboard", {
    readRichBlocks: () => ipcRenderer.invoke("notion:clipboard:read-rich"),
    writeRichBlocks: (blocks) => ipcRenderer.invoke("notion:clipboard:write-rich", blocks),
    syncSelection: (range) => ipcRenderer.send("notion:clipboard:selection-sync", range),
  });
}

module.exports = { exposeNotionClipboardBridge };
`;
const NOTION_MAIN_SOURCE = `
const { ipcMain } = require("electron");

function registerNotionClipboardHandlers(store) {
  ipcMain.handle("notion:clipboard:read-rich", async () => {
    const res = await fetch("/api/v1/clipboard/blocks");
    return store.get("lastBlocks") || [];
  });
  ipcMain.handle("notion:clipboard:write-rich", async (_event, blocks) => {
    store.set("lastBlocks", blocks);
    return { ok: true, count: blocks.length };
  });
}

module.exports = { registerNotionClipboardHandlers };
`;
/**
 * Showcase 3: Enterprise Offline License & Entitlement Validator
 */
const LICENSE_VALIDATOR_SOURCE = `
function computeLicenseChecksum(serialKey, productCode) {
  let hash = 0x811c9dc5;
  const combined = serialKey + ":" + productCode + ":enterprise-v4";
  for (let i = 0; i < combined.length; i++) {
    hash ^= combined.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash;
}

function validateEnterpriseLicense(serialKey, productCode, expectedChecksum) {
  if (!serialKey || !serialKey.startsWith("ENT-")) return { valid: false, tier: "none" };
  const actual = computeLicenseChecksum(serialKey, productCode);
  return {
    valid: actual === (expectedChecksum >>> 0),
    tier: actual === (expectedChecksum >>> 0) ? "enterprise-unlimited" : "invalid",
    checksum: actual,
  };
}

module.exports = { computeLicenseChecksum, validateEnterpriseLicense };
`;
/**
 * Showcase 4b: entitlement string table — the JavaScript-strings profile REA
 * charges through `primitive-bytes`, `primitive-candidates`, `alias-selections`
 * and `getter-expansion`.
 */
const JS_STRINGS_SOURCE = `
const ENTITLEMENT_LABELS = Object.freeze(${JSON.stringify(Array.from({ length: 64 }, (_, i) => `entitlement_pro_${i}_${"x".repeat(24)}`))});

function resolveEntitlement(code) {
  const idx = ((code | 0) >>> 0) % ENTITLEMENT_LABELS.length;
  return ENTITLEMENT_LABELS[idx];
}

module.exports = { resolveEntitlement, labelCount: ENTITLEMENT_LABELS.length };
`;
/**
 * Showcase 4: Minimal Valid WebAssembly Crypto Module (`add(a, b)` & `mix(x)` exported)
 */
function buildSampleWasmModule() {
    // Valid WASM binary exporting `computeDigest(i32, i32) -> i32`
    return Buffer.from([
        0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00, // magic + version 1
        // Section 1: Type section (1 func type: (i32, i32) -> i32)
        0x01, 0x07, 0x01, 0x60, 0x02, 0x7f, 0x7f, 0x01, 0x7f,
        // Section 3: Function section (1 function of type 0)
        0x03, 0x02, 0x01, 0x00,
        // Section 7: Export section ("computeDigest" -> func 0)
        0x07, 0x11, 0x01, 0x0d,
        0x63, 0x6f, 0x6d, 0x70, 0x75, 0x74, 0x65, 0x44, 0x69, 0x67, 0x65, 0x73, 0x74,
        0x00, 0x00,
        // Section 10: Code section (local.get 0, local.get 1, i32.xor, i32.const 42, i32.add, end)
        0x0a, 0x0c, 0x01, 0x0a, 0x00, 0x20, 0x00, 0x20, 0x01, 0x73, 0x41, 0x2a, 0x6a, 0x0b,
    ]);
}
/**
 * Showcase 5: ELF64 with mapped `.go.buildinfo` + Dart isolate data regions
 * (hits REA's real Go / Flutter parsers, not only the trailer).
 */
function buildSampleElf64Binary() {
    return buildMappedGoFlutterElfFixture();
}
function runCommonJsModule(code) {
    const mod = { exports: {} };
    const sandbox = {
        module: mod,
        exports: mod.exports,
        require: (id) => {
            if (id === "electron") {
                return {
                    contextBridge: { exposeInMainWorld: () => undefined },
                    ipcRenderer: { invoke: () => Promise.resolve([]), send: () => undefined },
                    ipcMain: { handle: () => undefined, on: () => undefined },
                };
            }
            return {};
        },
        fetch: () => Promise.resolve({ json: () => ({}) }),
        process: { pid: 1234 },
        Math,
        Object,
        Array,
        String,
        Number,
        Boolean,
        Map,
        Set,
        Buffer,
    };
    vm.runInNewContext(code, sandbox, { timeout: 5000 });
    return mod.exports;
}
function runElectronAsarClipboardHarness(preloadCode, mainCode, virtualFiles = new Map()) {
    let exposedKey = "";
    let exposedApi = {};
    const handlers = new Map();
    const sentEvents = [];
    const electronMock = {
        contextBridge: {
            exposeInMainWorld: (key, api) => {
                exposedKey = key;
                exposedApi = api;
            },
        },
        ipcRenderer: {
            invoke: (channel, ...args) => {
                const handler = handlers.get(channel);
                return handler ? handler({}, ...args) : Promise.resolve([]);
            },
            send: (channel, payload) => {
                sentEvents.push({ channel, payload });
            },
        },
        ipcMain: {
            handle: (channel, fn) => {
                handlers.set(channel, fn);
            },
            on: () => undefined,
        },
    };
    const fsMock = {
        readFileSync: (filePath, encoding) => {
            const base = String(filePath).split(/[\\/]/).pop() ?? String(filePath);
            const buf = virtualFiles.get(base) ?? virtualFiles.get(String(filePath));
            if (!buf) {
                return readFileSync(filePath, encoding);
            }
            return encoding ? buf.toString(encoding) : buf;
        },
    };
    const pathMock = {
        join: (...parts) => parts.join("/"),
        resolve: (...parts) => parts.join("/"),
        dirname: (p) => p.split("/").slice(0, -1).join("/") || ".",
    };
    const makeSandbox = (mod) => ({
        module: mod,
        exports: mod.exports,
        __dirname: "/asar",
        __filename: "/asar/index.js",
        require: (id) => {
            if (id === "electron")
                return electronMock;
            if (id === "fs" || id === "node:fs")
                return fsMock;
            if (id === "path" || id === "node:path")
                return pathMock;
            return {};
        },
        fetch: () => Promise.resolve({ json: () => ({}) }),
        process: { pid: 1234 },
        Math,
        Object,
        Array,
        String,
        Number,
        Boolean,
        Map,
        Set,
        Buffer,
    });
    const mainMod = { exports: {} };
    vm.runInNewContext(mainCode, makeSandbox(mainMod), { timeout: 5000 });
    const preloadMod = { exports: {} };
    vm.runInNewContext(preloadCode, makeSandbox(preloadMod), { timeout: 5000 });
    const storeMap = new Map();
    const store = {
        get: (k) => storeMap.get(k),
        set: (k, v) => storeMap.set(k, v),
    };
    const regFn = typeof mainMod.exports.registerNotionClipboardHandlers === "function"
        ? mainMod.exports.registerNotionClipboardHandlers
        : Object.values(mainMod.exports).find((v) => typeof v === "function");
    if (regFn)
        regFn(store);
    const exposeFn = typeof preloadMod.exports.exposeNotionClipboardBridge === "function"
        ? preloadMod.exports.exposeNotionClipboardBridge
        : Object.values(preloadMod.exports).find((v) => typeof v === "function");
    if (exposeFn)
        exposeFn();
    return {
        exposedKey,
        bridgeMethods: Object.keys(exposedApi).sort(),
        handlersRegistered: handlers.size,
    };
}
/**
 * Fixed seed for the showcase run. Without it every run mints a fresh project
 * seed (`generateProjectSeed`), so the emitted decoys — and therefore the
 * reported token/cost amplification — change from one run to the next.
 */
const BENCHMARK_SHOWCASE_SEED = "bla-benchmark-showcase-v1";
/**
 * Runs the Counter-REA Showcase Benchmark (`bla benchmark`), including BEAM/EVM/PCAP/PTX.
 *
 * `seed` overrides the fixed showcase seed; the default keeps the published
 * aggregate reproducible so it can be guarded by a test.
 */

export default function(fixtureDir) {const results=[];
{const tempDir = fixtureDir("dx-ball"); 
            const srcPath = join(tempDir, "dx-ball-sound-pan.js");
            const outPath = join(tempDir, "dx-ball-sound-pan.shielded.js");
            writeFileSync(srcPath, DX_BALL_SOURCE, "utf8");
             results.push({...{"number":1,"id":"dx-ball","title":"DX-Ball Sound-Pan Calculation"}, path: srcPath});}
{const tempDir = fixtureDir("notion-electron"); 
            const asarPath = join(tempDir, "notion-clipboard.asar");
            const outAsarPath = join(tempDir, "notion-clipboard.shielded.asar");
            const rawAsar = packAsarBuffer([
                {
                    relativePath: "package.json",
                    content: Buffer.from(JSON.stringify({ name: "notion-clipboard", main: "main.js" }), "utf8"),
                },
                { relativePath: "preload.js", content: Buffer.from(NOTION_PRELOAD_SOURCE, "utf8") },
                { relativePath: "main.js", content: Buffer.from(NOTION_MAIN_SOURCE, "utf8") },
            ]);
            writeFileSync(asarPath, rawAsar);
             results.push({...{"number":2,"id":"notion-electron","title":"Notion Electron Clipboard Bridge (.asar)"}, path: asarPath});}
{const tempDir = fixtureDir("license-guard"); 
            const srcPath = join(tempDir, "license-validator.js");
            const outPath = join(tempDir, "license-validator.shielded.js");
            writeFileSync(srcPath, LICENSE_VALIDATOR_SOURCE, "utf8");
             results.push({...{"number":3,"id":"license-guard","title":"Enterprise License & Crypto Validator"}, path: srcPath});}
{const tempDir = fixtureDir("wasm-core"); 
            const wasmPath = join(tempDir, "crypto-core.wasm");
            const outWasmPath = join(tempDir, "crypto-core.shielded.wasm");
            const rawWasm = buildSampleWasmModule();
            writeFileSync(wasmPath, rawWasm);
             results.push({...{"number":4,"id":"wasm-core","title":"WebAssembly Crypto Kernel (.wasm)"}, path: wasmPath});}
{const tempDir = fixtureDir("native-elf"); 
            const elfPath = join(tempDir, "enclave-daemon.elf");
            const outElfPath = join(tempDir, "enclave-daemon.shielded.elf");
            const origElf = buildSampleElf64Binary();
            writeFileSync(elfPath, origElf);
             results.push({...{"number":5,"id":"native-elf","title":"Native ELF64 Rust/Go/Electron/Dart Binary"}, path: elfPath});}
{const tempDir = fixtureDir("sqlite-db"); 
            const dbPath = join(tempDir, "entitlements.sqlite");
            const outDbPath = join(tempDir, "entitlements.shielded.sqlite");
            writeFileSync(dbPath, buildSampleSqliteDatabase());
             results.push({...{"number":6,"id":"sqlite-db","title":"Local SQLite Entitlement Database (.sqlite)"}, path: dbPath});}
{const tempDir = fixtureDir("safetensors-model"); 
            const modelPath = join(tempDir, "proprietary-weights.safetensors");
            const outModelPath = join(tempDir, "proprietary-weights.shielded.safetensors");
            const tensorWeights = Buffer.alloc(32);
            for (let i = 0; i < 8; i++) {
                tensorWeights.writeFloatLE((i + 1) * 0.25, i * 4);
            }
            const rawModel = buildSafetensorsBuffer({
                encoder_proj: { dtype: "F32", shape: [2, 2], data_offsets: [0, 16] },
                layer_norm_weight: { dtype: "F32", shape: [4], data_offsets: [16, 32] },
            }, tensorWeights);
            writeFileSync(modelPath, rawModel);
             results.push({...{"number":7,"id":"safetensors-model","title":"Proprietary Edge AI Model (.safetensors)"}, path: modelPath});}
{const tempDir = fixtureDir("android-dex"); 
            const dexPath = join(tempDir, "classes.dex");
            const outDexPath = join(tempDir, "classes.shielded.dex");
            const appDescriptor = Buffer.from("Lcom/enterprise/vault/LicenseVerifier;\0verifyOfflineSignature\0", "utf8");
            const baseDex = Buffer.alloc(112 + appDescriptor.length, 0);
            baseDex.write("dex\n035\0", 0, "ascii");
            baseDex.writeUInt32LE(baseDex.length, 32);
            baseDex.writeUInt32LE(112, 36);
            baseDex.writeUInt32LE(0x12345678, 40);
            appDescriptor.copy(baseDex, 112);
            writeFileSync(dexPath, baseDex);
             results.push({...{"number":8,"id":"android-dex","title":"Android Dalvik Bytecode (classes.dex)"}, path: dexPath});}
{const tempDir = fixtureDir("apple-plist"); 
            const plistPath = join(tempDir, "Info.plist");
            const outPlistPath = join(tempDir, "Info.shielded.plist");
            const origPlist = [
                `<?xml version="1.0" encoding="UTF-8"?>`,
                `<plist version="1.0"><dict>`,
                `  <key>CFBundleIdentifier</key><string>com.bla.desktop</string>`,
                `  <key>CFBundleShortVersionString</key><string>3.2.3</string>`,
                `  <key>CFBundleExecutable</key><string>bla-daemon</string>`,
                `</dict></plist>`,
            ].join("\n");
            writeFileSync(plistPath, origPlist, "utf8");
             results.push({...{"number":9,"id":"apple-plist","title":"Apple Bundle PropertyList (Info.plist)"}, path: plistPath});}
{const tempDir = fixtureDir("dotnet-managed"); 
            const dllPath = join(tempDir, "EnterpriseVault.dll");
            const outDllPath = join(tempDir, "EnterpriseVault.shielded.dll");
            const clrMetadataSym = Buffer.from("EnterpriseVault.Core.LicenseGuard\0VerifyOfflineLease\0", "utf8");
            const peClr = Buffer.alloc(160 + clrMetadataSym.length, 0);
            peClr.write("MZ", 0, "ascii");
            peClr.writeUInt32LE(0x40, 0x3c);
            peClr.write("PE\0\0", 0x40, "ascii");
            peClr.write("BSJB", 96, "ascii");
            clrMetadataSym.copy(peClr, 160);
            writeFileSync(dllPath, peClr);
             results.push({...{"number":10,"id":"dotnet-managed","title":".NET Managed CLR Assembly (.dll)"}, path: dllPath});}
{const tempDir = fixtureDir("erlang-beam"); 
            const beamPath = join(tempDir, "enclave_guard.beam");
            const outBeamPath = join(tempDir, "enclave_guard.shielded.beam");
            const chunk = (name, body) => {
                const pad = (4 - (body.length % 4)) % 4;
                const hdr = Buffer.alloc(8);
                hdr.write(name, 0, "latin1");
                hdr.writeUInt32BE(body.length, 4);
                return Buffer.concat([hdr, body, Buffer.alloc(pad)]);
            };
            const atomNames = ["bench_mod", "module_info", "start"];
            const atomParts = [Buffer.alloc(4)];
            atomParts[0].writeUInt32BE(atomNames.length);
            for (const n of atomNames) {
                const enc = Buffer.from(n, "utf8");
                atomParts.push(Buffer.from([enc.length]), enc);
            }
            const codeBody = Buffer.alloc(20);
            codeBody.writeUInt32BE(16, 0);
            codeBody.writeUInt32BE(0, 4);
            codeBody.writeUInt32BE(169, 8);
            codeBody.writeUInt32BE(4, 12);
            codeBody.writeUInt32BE(2, 16);
            const expBody = Buffer.alloc(16);
            expBody.writeUInt32BE(1, 0);
            expBody.writeUInt32BE(2, 4);
            expBody.writeUInt32BE(0, 8);
            expBody.writeUInt32BE(1, 12);
            const codeChunk = chunk("Code", codeBody);
            const expChunk = chunk("ExpT", expBody);
            const form = Buffer.concat([
                Buffer.from("BEAM", "latin1"),
                chunk("AtU8", Buffer.concat(atomParts)),
                codeChunk,
                expChunk,
            ]);
            const beamFixture = Buffer.concat([
                Buffer.from("FOR1", "latin1"),
                (() => {
                    const b = Buffer.alloc(4);
                    b.writeUInt32BE(form.length);
                    return b;
                })(),
                form,
            ]);
            writeFileSync(beamPath, beamFixture);
             results.push({...{"number":11,"id":"erlang-beam","title":"Erlang/OTP BEAM Module (.beam)"}, path: beamPath});}
{const tempDir = fixtureDir("evm-bytecode"); 
            const evmPath = join(tempDir, "Vault.evm");
            const outEvmPath = join(tempDir, "Vault.shielded.evm");
            // Realistic Solidity dispatcher runtime bytecode:
            // PUSH1 0x80 PUSH1 0x40 MSTORE CALLDATASIZE ISZERO PUSH1 0x1b JUMPI
            // PUSH1 0x00 CALLDATALOAD PUSH1 0xe0 SHR DUP1 PUSH4 0x67e408a7 EQ PUSH1 0x20 JUMPI
            // JUMPDEST STOP JUMPDEST PUSH1 0x2a PUSH1 0x00 MSTORE PUSH1 0x20 PUSH1 0x00 RETURN
            const origEvm = Buffer.from("60806040523615601b5760003560e01c806367e408a7146020575b005b602a60005260206000f3", "hex");
            writeFileSync(evmPath, origEvm);
             results.push({...{"number":12,"id":"evm-bytecode","title":"EVM Contract Bytecode (Solidity metadata)"}, path: evmPath});}
{const tempDir = fixtureDir("pcap-capture"); 
            const pcapPath = join(tempDir, "enclave-traffic.pcap");
            const outPcapPath = join(tempDir, "enclave-traffic.shielded.pcap");
            const hdr = Buffer.alloc(24);
            hdr.writeUInt32LE(0xa1b2c3d4, 0);
            hdr.writeUInt16LE(2, 4);
            hdr.writeUInt16LE(4, 6);
            hdr.writeUInt32LE(65535, 16);
            hdr.writeUInt32LE(1, 20);
            // Include an initial application Ethernet/IPv4/UDP packet record (46 bytes frame)
            const appFrame = Buffer.alloc(46, 0x41);
            appFrame[12] = 0x08;
            appFrame[13] = 0x00;
            const recHdr = Buffer.alloc(16);
            recHdr.writeUInt32LE(1700000000, 0);
            recHdr.writeUInt32LE(125, 4);
            recHdr.writeUInt32LE(appFrame.length, 8);
            recHdr.writeUInt32LE(appFrame.length, 12);
            const origPcap = Buffer.concat([hdr, recHdr, appFrame]);
            writeFileSync(pcapPath, origPcap);
             results.push({...{"number":13,"id":"pcap-capture","title":"libpcap Network Capture (.pcap)"}, path: pcapPath});}
{const tempDir = fixtureDir("gpu-ptx"); 
            const ptxPath = join(tempDir, "enclave_kernel.ptx");
            const outPtxPath = join(tempDir, "enclave_kernel.shielded.ptx");
            const origPtx = [
                `.version 7.5`,
                `.target sm_70`,
                `.address_size 64`,
                ``,
                `.visible .entry real_kernel(.param .u64 real_kernel_param_0)`,
                `{`,
                `  .reg .b64 %rd<3>;`,
                `  .reg .f32 %f<3>;`,
                `  ld.param.u64 %rd1, [real_kernel_param_0];`,
                `  ld.global.f32 %f1, [%rd1];`,
                `  add.f32 %f2, %f1, 0f3F800000;`,
                `  st.global.f32 [%rd1], %f2;`,
                `  ret;`,
                `}`,
                ``,
            ].join("\n");
            writeFileSync(ptxPath, origPtx, "utf8");
             results.push({...{"number":14,"id":"gpu-ptx","title":"NVIDIA PTX Text Module (.ptx)"}, path: ptxPath});}
{const tempDir = fixtureDir("javascript-strings"); 
            const stringsPath = join(tempDir, "entitlement-labels.js");
            const outStringsPath = join(tempDir, "entitlement-labels.shielded.js");
            writeFileSync(stringsPath, JS_STRINGS_SOURCE, "utf8");
             results.push({...{"number":15,"id":"javascript-strings","title":"JavaScript Entitlement String Table (.js)"}, path: stringsPath});}
{const tempDir = fixtureDir("gguf-model"); 
            const ggufPath = join(tempDir, "tensorless.gguf");
            const outGgufPath = join(tempDir, "tensorless.shielded.gguf");
            const gguf = Buffer.alloc(24);
            gguf.write("GGUF", 0, "ascii");
            gguf.writeUInt32LE(3, 4);
            gguf.writeBigUInt64LE(0n, 8);
            gguf.writeBigUInt64LE(0n, 16);
            writeFileSync(ggufPath, gguf);
             results.push({...{"number":16,"id":"gguf-model","title":"GGUF Model Metadata (.gguf)"}, path: ggufPath});}
return results;}