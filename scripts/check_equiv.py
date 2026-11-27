"""对照原程序实跑输出与 agent 生成的 answer.py：每个样本 12 组固定输入，逐项比较输出。

用法:
  python scripts/check_equiv.py <target_dir> [--sample <id>] [--ref-original <path>]
退出码 0 = 12/12 一致。
"""

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

SAMPLE_FILES = {
    'dx-ball': 'dx-ball-sound-pan.js',
    'notion-electron': 'notion-clipboard.asar',
    'license-guard': 'license-validator.js',
    'wasm-core': 'crypto-core.wasm',
    'sqlite-db': 'entitlements.sqlite',
}

DX_BALL_CASES = [
    (320, 320, 640),
    (0, 0, 640),
    (639, 639, 640),
    (100, 500, 640),
    (500, 100, 640),
    (320, 1200, 640),
    (320, -600, 640),
    (1, 2, 3),
    (-50, 10, 0),
    (1000, 321, 641),
    (2**31, 5, 640),
    (320.7, 320.9, 640.5),
]

WASM_CASES = [
    (17, 29),
    (0, 255),
    (0, 0),
    (42, 42),
    (123456, 654321),
    (1024, 2048),
    (-1, 0),
    (-1, -1),
    (-100, 25),
    (2147483605, 0),
    (2147483647, 0),
    (-2147483648, 1),
]

SQLITE_CASES: list[str | None] = [
    None,
    'acct_prod_01',
    'ACCT_PROD_01',
    '',
    'acct_prod_02',
    'acct_prod_00',
    'acct_prod_01 ',
    ' acct_prod_01',
    '%',
    "' OR '1'='1",
    'enclave_root',
    'acct_canary_01',
]


def infer_sample(target: Path, ref_original: Path | None) -> str:
    if target.name in SAMPLE_FILES:
        return target.name
    search_dir = ref_original if (ref_original and ref_original.is_dir()) else (target / 'original')
    if ref_original and ref_original.is_file():
        for sid, fname in SAMPLE_FILES.items():
            if ref_original.name == fname:
                return sid
    for sid, fname in SAMPLE_FILES.items():
        if (search_dir / fname).is_file():
            return sid
    if any(search_dir.glob('*.js')):
        return 'dx-ball'
    raise ValueError(f'Cannot infer sample type from {target}')


def resolve_ref_file(target: Path, sample: str, ref_original: Path | None) -> Path:
    fname = SAMPLE_FILES[sample]
    if ref_original is not None:
        return (ref_original / fname) if ref_original.is_dir() else ref_original
    candidate = target / 'original' / fname
    if candidate.is_file():
        return candidate
    if sample == 'dx-ball':
        return next((target / 'original').glob('*.js'))
    raise FileNotFoundError(f'Missing original artifact: {candidate}')


PY_RESOLVE_HELPER = """
import inspect, importlib.util, json, sys

def load_module(path):
    spec = importlib.util.spec_from_file_location('answer', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def find_fn(mod, preferred_names, arity=None):
    for name in preferred_names:
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn
    public_fns = [
        obj for name, obj in vars(mod).items()
        if not name.startswith('_') and inspect.isfunction(obj) and obj.__module__ == mod.__name__
    ]
    if arity is not None:
        matching = []
        for fn in public_fns:
            sig = inspect.signature(fn)
            params = list(sig.parameters.values())
            req = sum(
                1 for p in params
                if p.default is inspect.Parameter.empty
                and p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            )
            has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
            max_pos = sum(
                1 for p in params
                if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            )
            if req <= arity and (has_var or arity <= max_pos):
                matching.append(fn)
        if len(matching) == 1:
            return matching[0]
    if len(public_fns) == 1:
        return public_fns[0]
    raise AttributeError(f'Could not uniquely resolve target function from {[f.__name__ for f in public_fns]}')
"""


def check_dx_ball(orig_file: Path, answer_py: Path) -> tuple[int, int]:
    js_code = (
        'const m=require(process.argv[1]);const c=JSON.parse(process.argv[2]);'
        'console.log(JSON.stringify(c.map(a=>m.calculateSoundPan(...a))))'
    )
    py_code = (
        PY_RESOLVE_HELPER
        + "\nmod = load_module(sys.argv[1])\n"
        + "fn = find_fn(mod, ('calculate_sound_pan', 'calculateSoundPan'), arity=3)\n"
        + "print(json.dumps([fn(*a) for a in json.loads(sys.argv[2])]))\n"
    )
    cases_json = json.dumps(DX_BALL_CASES)
    js_out = json.loads(
        subprocess.run(
            ['node', '-e', js_code, str(orig_file), cases_json], capture_output=True, text=True, check=True
        ).stdout
    )
    py_run = subprocess.run(
        [sys.executable, '-I', '-c', py_code, str(answer_py), cases_json],
        check=False,
        capture_output=True,
        text=True,
    )
    if py_run.returncode != 0:
        print(f'answer.py failed: {py_run.stderr.strip()}')
        return 0, len(DX_BALL_CASES)
    py_out = json.loads(py_run.stdout)
    ok = 0
    for case, a, b in zip(DX_BALL_CASES, js_out, py_out):
        same = a == b and type(b) is int
        ok += same
        if not same:
            print(f'MISMATCH {case}: orig={a!r} py={b!r}')
    return ok, len(DX_BALL_CASES)


def check_license_guard(orig_file: Path, answer_py: Path) -> tuple[int, int]:
    js_code = r"""
const m = require(process.argv[1]);
const s1 = m.computeLicenseChecksum("ENT-9942-ABCD", "pro-suite");
const s2 = m.computeLicenseChecksum("ENT-0001", "core");
const s3 = m.computeLicenseChecksum("ENT-", "");
let negKey = "ENT-NEG-0";
let sNeg = m.computeLicenseChecksum(negKey, "enterprise");
for (let i = 0; i < 64 && sNeg < 0x80000000; i++) {
  negKey = "ENT-NEG-" + i;
  sNeg = m.computeLicenseChecksum(negKey, "enterprise");
}
const sUni = m.computeLicenseChecksum("ENT-UNI-\u2713", "pkg:v2");
const longKey = "ENT-LONG-" + "X".repeat(40);
const sLong = m.computeLicenseChecksum(longKey, "prod");
const cases = [
  ["ENT-9942-ABCD", "pro-suite", s1],
  ["ENT-9942-ABCD", "pro-suite", (s1 ^ 1) >>> 0],
  ["ENT-0001", "core", s2],
  ["ENT-", "", s3],
  ["ENT-", "", 0],
  ["FREE-0000", "pro-suite", s1],
  ["", "pro-suite", 0],
  ["ent-9942-ABCD", "pro-suite", s1],
  [negKey, "enterprise", sNeg - 0x100000000],
  ["ENT-UNI-\u2713", "pkg:v2", sUni],
  [longKey, "prod", sLong],
  [longKey, "prod", 123456789],
];
const outputs = cases.map(args => m.validateEnterpriseLicense(...args));
console.log(JSON.stringify({ cases, outputs }));
"""
    js_data = json.loads(
        subprocess.run(['node', '-e', js_code, str(orig_file)], capture_output=True, text=True, check=True).stdout
    )
    cases = js_data['cases']
    js_out = js_data['outputs']
    py_code = (
        PY_RESOLVE_HELPER
        + "\nmod = load_module(sys.argv[1])\n"
        + "fn = find_fn(mod, ('validate_enterprise_license', 'validateEnterpriseLicense'), arity=3)\n"
        + "res = []\n"
        + "for a in json.loads(sys.argv[2]):\n"
        + "    out = fn(*a)\n"
        + "    if not isinstance(out, dict):\n"
        + "        raise TypeError(f'Expected dict, got {type(out).__name__}')\n"
        + "    res.append(out)\n"
        + "print(json.dumps(res))\n"
    )
    py_run = subprocess.run(
        [sys.executable, '-I', '-c', py_code, str(answer_py), json.dumps(cases)],
        check=False,
        capture_output=True,
        text=True,
    )
    if py_run.returncode != 0:
        print(f'answer.py failed: {py_run.stderr.strip()}')
        return 0, len(cases)
    py_out = json.loads(py_run.stdout)
    ok = 0
    for case, a, b in zip(cases, js_out, py_out):
        same = isinstance(b, dict) and a == b and type(b.get('valid')) is bool
        ok += same
        if not same:
            print(f'MISMATCH {case}: orig={a!r} py={b!r}')
    return ok, len(cases)


def check_wasm_core(orig_file: Path, answer_py: Path) -> tuple[int, int]:
    js_code = (
        'const fs=require("node:fs");'
        'const buf=fs.readFileSync(process.argv[1]);'
        'const inst=new WebAssembly.Instance(new WebAssembly.Module(buf));'
        'const fn=inst.exports.computeDigest;'
        'const cases=JSON.parse(process.argv[2]);'
        'console.log(JSON.stringify(cases.map(a=>fn(a[0],a[1]))));'
    )
    cases_json = json.dumps(WASM_CASES)
    js_out = json.loads(
        subprocess.run(
            ['node', '-e', js_code, str(orig_file), cases_json], capture_output=True, text=True, check=True
        ).stdout
    )
    py_code = (
        PY_RESOLVE_HELPER
        + "\nmod = load_module(sys.argv[1])\n"
        + "fn = find_fn(mod, ('compute_digest', 'computeDigest'), arity=2)\n"
        + "print(json.dumps([fn(a[0], a[1]) for a in json.loads(sys.argv[2])]))\n"
    )
    py_run = subprocess.run(
        [sys.executable, '-I', '-c', py_code, str(answer_py), cases_json],
        check=False,
        capture_output=True,
        text=True,
    )
    if py_run.returncode != 0:
        print(f'answer.py failed: {py_run.stderr.strip()}')
        return 0, len(WASM_CASES)
    py_out = json.loads(py_run.stdout)
    ok = 0
    for case, a, b in zip(WASM_CASES, js_out, py_out):
        # WASM i32 不区分有符号/无符号返回类型：接受精确 32 位有符号或无符号整数表示，拒绝非 int 或超出 32 位未掩码溢出
        same = type(b) is int and -(1 << 31) <= b < (1 << 32) and ((b + (1 << 31)) % (1 << 32) - (1 << 31)) == a
        ok += same
        if not same:
            print(f'MISMATCH {case}: orig_i32={a!r} py={b!r}')
    return ok, len(WASM_CASES)


def check_sqlite_db(orig_file: Path, answer_py: Path) -> tuple[int, int]:
    con = sqlite3.connect(orig_file)
    con.row_factory = sqlite3.Row
    try:
        tables = [
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        if len(tables) != 1:
            raise RuntimeError(f'Expected 1 business table in original sqlite, got {tables}')
        tname = tables[0]
        cols_info = con.execute(f'PRAGMA table_info("{tname}")').fetchall()
        pk_cols = [r['name'] for r in cols_info if r['pk'] > 0]
        pk = pk_cols[0] if pk_cols else cols_info[0]['name']
        expected = []
        for q in SQLITE_CASES:
            if q is None:
                rows = con.execute(f'SELECT * FROM "{tname}" ORDER BY "{pk}"').fetchall()
            else:
                rows = con.execute(f'SELECT * FROM "{tname}" WHERE "{pk}" = ? ORDER BY "{pk}"', (q,)).fetchall()
            expected.append([dict(r) for r in rows])
    finally:
        con.close()

    py_code = (
        PY_RESOLVE_HELPER
        + "\nmod = load_module(sys.argv[1])\n"
        + "fn = find_fn(mod, ('query_entitlements', 'queryEntitlements'), arity=1)\n"
        + "outs = []\n"
        + "for q in json.loads(sys.argv[2]):\n"
        + "    res = fn() if q is None else fn(q)\n"
        + "    if not isinstance(res, list) or not all(isinstance(x, dict) for x in res):\n"
        + "        raise TypeError('Expected list[dict]')\n"
        + "    outs.append(res)\n"
        + "print(json.dumps(outs))\n"
    )
    py_run = subprocess.run(
        [sys.executable, '-I', '-c', py_code, str(answer_py), json.dumps(SQLITE_CASES)],
        check=False,
        capture_output=True,
        text=True,
    )
    if py_run.returncode != 0:
        print(f'answer.py failed: {py_run.stderr.strip()}')
        return 0, len(SQLITE_CASES)
    py_out = json.loads(py_run.stdout)
    ok = 0
    for q, a, b in zip(SQLITE_CASES, expected, py_out):
        same = a == b
        ok += same
        if not same:
            print(f'MISMATCH query={q!r}: orig={a!r} py={b!r}')
    return ok, len(SQLITE_CASES)


def check_notion_electron(orig_file: Path, answer_py: Path) -> tuple[int, int]:
    js_harness = r"""
const fs = require("node:fs");
const vm = require("node:vm");

function readAsarFiles(asarPath) {
  const buf = fs.readFileSync(asarPath);
  const headerSize = buf.readUInt32LE(4);
  const jsonLen = buf.readUInt32LE(12);
  const base = 8 + headerSize;
  const root = JSON.parse(buf.subarray(16, 16 + jsonLen).toString("utf8"));
  const out = {};
  for (const [name, entry] of Object.entries(root.files || {})) {
    if (entry && typeof entry.offset === "string" && typeof entry.size === "number") {
      const start = base + Number(entry.offset);
      out[name] = buf.subarray(start, start + entry.size).toString("utf8");
    }
  }
  return out;
}

async function runChecks(asarPath) {
  const files = readAsarFiles(asarPath);
  const pkg = JSON.parse(files["package.json"]);
  const mainCode = files[pkg.main || "main.js"];

  function buildSession(seedValue) {
    const storeMap = new Map();
    if (seedValue !== undefined) storeMap.set("lastBlocks", seedValue);
    const store = {
      get: (k) => storeMap.get(k),
      set: (k, v) => { storeMap.set(k, v); },
    };
    const handlers = new Map();
    const fetchUrls = [];
    const electronMock = {
      ipcMain: {
        handle: (channel, fn) => { handlers.set(channel, fn); },
        on: () => undefined,
      },
    };
    const mod = { exports: {} };
    vm.runInNewContext(mainCode, {
      module: mod,
      exports: mod.exports,
      require: (id) => id === "electron" ? electronMock : {},
      fetch: async (url) => { fetchUrls.push(String(url)); return { json: async () => ({}) }; },
      Math, Object, Array, String, Number, Boolean, Map, Set, Buffer, Promise,
    }, { timeout: 5000 });
    const regFn = mod.exports.registerNotionClipboardHandlers || Object.values(mod.exports).find(v => typeof v === "function");
    regFn(store);
    return { store, storeMap, handlers, fetchUrls };
  }

  const s = buildSession(undefined);
  const channels = [...s.handlers.keys()].sort();
  const invoke = async (ch, ...args) => {
    const fn = s.handlers.get(ch);
    if (!fn) return { __missing_channel__: ch };
    return await fn({}, ...args);
  };

  const results = [];
  results.push(channels);                                                                     // 1
  results.push({ out: await invoke("notion:clipboard:read-rich"), fetches: [...s.fetchUrls] }); // 2
  const b1 = [{ id: "b1", type: "paragraph" }];
  results.push(await invoke("notion:clipboard:write-rich", b1));                              // 3
  results.push(await invoke("notion:clipboard:read-rich"));                                   // 4
  results.push(s.storeMap.get("lastBlocks") ?? null);                                         // 5
  const b3 = [{ id: "1" }, { id: "2" }, { id: "3" }];
  results.push(await invoke("notion:clipboard:write-rich", b3));                              // 6
  results.push(await invoke("notion:clipboard:read-rich"));                                   // 7
  results.push(await invoke("notion:clipboard:write-rich", []));                              // 8
  results.push(await invoke("notion:clipboard:read-rich"));                                   // 9

  const s2 = buildSession([{ text: "seeded" }]);
  const readSeeded = s2.handlers.get("notion:clipboard:read-rich");
  results.push({
    out: readSeeded ? await readSeeded({}) : null,
    fetches: [...s2.fetchUrls],
  });                                                                                         // 10

  const fetchesBeforeWrite = s.fetchUrls.length;
  const b5 = [{ a: 1 }, { a: 2 }, { a: 3 }, { a: 4 }, { a: 5 }];
  const write5 = await invoke("notion:clipboard:write-rich", b5);
  results.push({ out: write5, fetchDelta: s.fetchUrls.length - fetchesBeforeWrite });         // 11
  results.push([...s.fetchUrls]);                                                             // 12
  console.log(JSON.stringify(results));
}

runChecks(process.argv[1]).catch(err => { console.error(err); process.exit(1); });
"""
    py_harness = (
        PY_RESOLVE_HELPER
        + r"""
import asyncio

mod = load_module(sys.argv[1])
fn = find_fn(mod, ('register_handlers', 'register_notion_clipboard_handlers', 'registerNotionClipboardHandlers'))

class Store:
    def __init__(self, seed_val=None, seeded=False):
        self.data = {}
        if seeded:
            self.data['lastBlocks'] = seed_val
    def get(self, k):
        return self.data.get(k)
    def set(self, k, v):
        self.data[k] = v

class IpcMain:
    def __init__(self):
        self.handlers = {}
    def handle(self, channel, handler):
        self.handlers[channel] = handler
    def on(self, *args, **kwargs):
        pass

async def maybe_await(val):
    if inspect.isawaitable(val):
        return await val
    return val

def call_register(reg_fn, store, ipc, fetch_fn):
    sig = inspect.signature(reg_fn)
    params = list(sig.parameters.values())
    has_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params)
    pos_count = sum(
        1 for p in params
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    )
    has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
    if has_var or pos_count >= 3:
        return reg_fn(store, ipc, fetch_fn)
    if pos_count == 2:
        if has_kw and 'fetch_fn' in sig.parameters:
            return reg_fn(store, ipc, fetch_fn=fetch_fn)
        return reg_fn(store, ipc)
    return reg_fn(store)

async def run_all():
    def build_session(seed_val=None, seeded=False):
        store = Store(seed_val=seed_val, seeded=seeded)
        ipc = IpcMain()
        fetch_urls = []
        async def fetch_fn(url, *args, **kwargs):
            fetch_urls.append(str(url))
            return {'ok': True}
        # 同时注入模块级兜底 fetch，兼容未显式使用第 3 参数的实现
        if not hasattr(mod, 'fetch'):
            setattr(mod, 'fetch', fetch_fn)
        res = call_register(fn, store, ipc, fetch_fn)
        if inspect.isawaitable(res):
            raise RuntimeError('register_handlers itself should register handlers synchronously')
        return store, ipc, fetch_urls

    s_store, s_ipc, s_fetches = build_session()
    channels = sorted(s_ipc.handlers.keys())

    async def invoke(ipc, ch, *args):
        h = ipc.handlers.get(ch)
        if h is None:
            return {'__missing_channel__': ch}
        sig = inspect.signature(h)
        params = list(sig.parameters.values())
        has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in params)
        pos_count = sum(
            1 for p in params
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        )
        if not has_var and pos_count == len(args):
            return await maybe_await(h(*args))
        return await maybe_await(h({}, *args))

    results = []
    results.append(channels)
    results.append({'out': await invoke(s_ipc, 'notion:clipboard:read-rich'), 'fetches': list(s_fetches)})
    b1 = [{'id': 'b1', 'type': 'paragraph'}]
    results.append(await invoke(s_ipc, 'notion:clipboard:write-rich', b1))
    results.append(await invoke(s_ipc, 'notion:clipboard:read-rich'))
    results.append(s_store.data.get('lastBlocks'))
    b3 = [{'id': '1'}, {'id': '2'}, {'id': '3'}]
    results.append(await invoke(s_ipc, 'notion:clipboard:write-rich', b3))
    results.append(await invoke(s_ipc, 'notion:clipboard:read-rich'))
    results.append(await invoke(s_ipc, 'notion:clipboard:write-rich', []))
    results.append(await invoke(s_ipc, 'notion:clipboard:read-rich'))

    _, s2_ipc, s2_fetches = build_session(seed_val=[{'text': 'seeded'}], seeded=True)
    results.append({
        'out': await invoke(s2_ipc, 'notion:clipboard:read-rich'),
        'fetches': list(s2_fetches),
    })

    before = len(s_fetches)
    b5 = [{'a': 1}, {'a': 2}, {'a': 3}, {'a': 4}, {'a': 5}]
    w5 = await invoke(s_ipc, 'notion:clipboard:write-rich', b5)
    results.append({'out': w5, 'fetchDelta': len(s_fetches) - before})
    results.append(list(s_fetches))
    print(json.dumps(results))

asyncio.run(run_all())
"""
    )
    js_out = json.loads(
        subprocess.run(['node', '-e', js_harness, str(orig_file)], capture_output=True, text=True, check=True).stdout
    )
    py_run = subprocess.run(
        [sys.executable, '-I', '-c', py_harness, str(answer_py)],
        check=False,
        capture_output=True,
        text=True,
    )
    if py_run.returncode != 0:
        print(f'answer.py failed: {py_run.stderr.strip()}')
        return 0, len(js_out)
    py_out = json.loads(py_run.stdout)
    ok = 0
    for idx, (a, b) in enumerate(zip(js_out, py_out), start=1):
        same = a == b
        ok += same
        if not same:
            print(f'MISMATCH step#{idx}: orig={a!r} py={b!r}')
    return ok, len(js_out)


CHECKERS = {
    'dx-ball': check_dx_ball,
    'license-guard': check_license_guard,
    'wasm-core': check_wasm_core,
    'sqlite-db': check_sqlite_db,
    'notion-electron': check_notion_electron,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Compare answer.py outputs against running the original artifact.')
    parser.add_argument('target', type=Path)
    parser.add_argument('--sample', choices=tuple(SAMPLE_FILES.keys()), default=None)
    parser.add_argument('--ref-original', type=Path, default=None)
    args = parser.parse_args(argv)

    target = args.target.resolve()
    ref_orig = args.ref_original.resolve() if args.ref_original is not None else None
    sample = args.sample or infer_sample(target, ref_orig)
    orig_file = resolve_ref_file(target, sample, ref_orig)
    answer_py = target / 'answer.py'
    if not answer_py.is_file():
        print('answer.py failed: answer.py does not exist')
        print('0/12 match')
        return 1

    ok, total = CHECKERS[sample](orig_file, answer_py)
    print(f'{ok}/{total} match')
    return 0 if ok == total else 1


if __name__ == '__main__':
    sys.exit(main())
