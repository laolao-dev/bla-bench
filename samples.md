# BLA 官方样本清单与 W3 选样说明

BLA 3.6.0，固定提交 `8dcf9858f5c931e26c4d3526b29c8e10a97ec17f`。
来源：`bla/src/engine/benchmark.ts`。官方 CLI 把原件写到临时目录后删除；下表是用各案例 `protectTarget` 前的原始构造代码重新生成的持久副本，不含加固产物。

## 前 14 项官方样本

| # | ID | 名称 | 格式 | 路径（相对 bla-bench） | 原始大小（字节） | W3 是否入选 |
|---:|---|---|---|---|---:|:---:|
| 1 | `dx-ball` | DX-Ball Sound-Pan Calculation | `.js` | `fixtures/dx-ball/dx-ball-sound-pan.js` | 403 | **入选** |
| 2 | `notion-electron` | Notion Electron Clipboard Bridge (.asar) | `.asar` | `fixtures/notion-electron/notion-clipboard.asar` | 1,769 | **入选** |
| 3 | `license-guard` | Enterprise License & Crypto Validator | `.js` | `fixtures/license-guard/license-validator.js` | 782 | **入选** |
| 4 | `wasm-core` | WebAssembly Crypto Kernel (.wasm) | `.wasm` | `fixtures/wasm-core/crypto-core.wasm` | 54 | **入选** |
| 5 | `native-elf` | Native ELF64 Rust/Go/Electron/Dart Binary | `.elf` | `fixtures/native-elf/enclave-daemon.elf` | 51,339 | 排除 |
| 6 | `sqlite-db` | Local SQLite Entitlement Database (.sqlite) | `.sqlite` | `fixtures/sqlite-db/entitlements.sqlite` | 12,288 | **入选** |
| 7 | `safetensors-model` | Proprietary Edge AI Model (.safetensors) | `.safetensors` | `fixtures/safetensors-model/proprietary-weights.safetensors` | 184 | 排除 |
| 8 | `android-dex` | Android Dalvik Bytecode (classes.dex) | `.dex` | `fixtures/android-dex/classes.dex` | 174 | 排除 |
| 9 | `apple-plist` | Apple Bundle PropertyList (Info.plist) | `.plist` | `fixtures/apple-plist/Info.plist` | 267 | 排除 |
| 10 | `dotnet-managed` | .NET Managed CLR Assembly (.dll) | `.dll` | `fixtures/dotnet-managed/EnterpriseVault.dll` | 213 | 排除 |
| 11 | `erlang-beam` | Erlang/OTP BEAM Module (.beam) | `.beam` | `fixtures/erlang-beam/enclave_guard.beam` | 104 | 排除 |
| 12 | `evm-bytecode` | EVM Contract Bytecode (Solidity metadata) | `.evm` | `fixtures/evm-bytecode/Vault.evm` | 39 | 排除 |
| 13 | `pcap-capture` | libpcap Network Capture (.pcap) | `.pcap` | `fixtures/pcap-capture/enclave-traffic.pcap` | 86 | 排除 |
| 14 | `gpu-ptx` | NVIDIA PTX Text Module (.ptx) | `.ptx` | `fixtures/gpu-ptx/enclave_kernel.ptx` | 290 | 排除 |

## 当前版本额外的第 15、16 项（不在前 14 项选样范围内）

| # | ID | 名称 | 格式 | 路径（相对 bla-bench） | 原始大小（字节） |
|---:|---|---|---|---|---:|
| 15 | `javascript-strings` | JavaScript Entitlement String Table (.js) | `.js` | `fixtures/javascript-strings/entitlement-labels.js` | 3,196 |
| 16 | `gguf-model` | GGUF Model Metadata (.gguf) | `.gguf` | `fixtures/gguf-model/tensorless.gguf` | 24 |

## W3 实测入选的 5 个样本与选择理由

筛选准则：从前 14 个官方样本中选 5 个（含必选 `dx-ball`），要求**格式与体积尽量分散**，且**原件可在离线容器中真实运行或由官方引擎直接执行查询，产出确定性结果与 `answer.py` 做 12 组输入逐项比对**；原件本身不含有效指令、实跑存在字节码跳转缺陷或容器缺少硬件驱动的样本逐一排除并顺延。

### 入选的 5 个样本（覆盖 `.wasm` / `.js` / `.asar` / `.sqlite` 四种格式，原始体积跨越 54 B – 12,288 B）

1. **`wasm-core`（#4，`.wasm`，原始 54 B → 加固后 6,880,378 B）**
   - **理由**：入选样本中原始体积最小（54 字节），代表紧凑二进制 WebAssembly 字节码格式；`bankrupt` 加固后膨胀至约 6.56 MiB 并重命名导出符号、注入诱饵导出表。
   - **自动正确性检查**：用 Node 原生 `WebAssembly.Instance` 直接实例化并实跑原始 `crypto-core.wasm` 的导出函数，对 12 组有符号/边界 32 位整数输入（含零、负数、`INT32_MAX` 溢出回绕）逐项比对 `answer.py` 输出。
2. **`dx-ball`（#1，`.js`，原始 403 B → 加固后 170,886 B）**
   - **理由**：任务指定必选样本，代表小型数值与位运算 JavaScript 模块（加固注入 AST 混淆、数论不透明谓词与诱饵 SourceMap）。
   - **自动正确性检查**：用 Node 直接 `require` 实跑原始 `dx-ball-sound-pan.js`，在 12 组输入（居中、两端、上下界钳位、零宽、`int32` 回绕、浮点数截断）上比对 `answer.py` 输出。
3. **`license-guard`（#3，`.js`，原始 782 B → 加固后 183,188 B）**
   - **理由**：代表中等体积字符串哈希与企业授权校验逻辑（32 位 FNV-1a `Math.imul` 无符号回绕、前缀判定与结构化字典返回），检验 AST 混淆与诱饵分支对多函数调用链和常量还原的影响。
   - **自动正确性检查**：用 Node 直接实跑原始 `license-validator.js`，在 12 组序列号/产品码/校验和组合（合法授权、1-bit 篡改、非 `ENT-` 前缀、空串、负数无符号转换 `>>> 0`、BMP Unicode 字符等）上逐字段比对返回字典。
4. **`notion-electron`（#2，`.asar`，原始 1,769 B → 加固后 24,671,339 B）**
   - **理由**：代表包含 `package.json`、`main.js`、`preload.js` 多文件的 Electron 归档容器格式；加固后膨胀至 23.53 MiB（触发 REA 默认 16 MiB ASAR 头部上限并注入诱饵硬件飞地模块）。
   - **自动正确性检查**：用 Node 直接解包原始 `notion-clipboard.asar` 并在 Electron IPC 沙箱中实跑 `main.js`，比对注册的精确 IPC 通道名集合及读写交互序列（空仓读取、多块写入计数、覆盖更新、`fetch` 触发路径等共 12 项检查）与 `answer.py` 的运行结果。
5. **`sqlite-db`（#6，`.sqlite`，原始 12,288 B → 加固后 49,152 B；注：加固评分 68/100，加固评分未达 BLA 默认门槛 70/100，使用 `--fail-under 0` 导出）**
   - **理由**：入选样本中原始体积最大（12 KiB），代表本地关系型数据库二进制格式；默认 stock 模式下（不启用会破坏标准客户端 `PRAGMA integrity_check` 的 `--sqlite-eval-trap`）BLA 诚实评分上限为 `68/100`（低于 `bla defend` 默认门槛 `70`），因此在统计、图表与结论中单独标注「加固评分未达 BLA 默认门槛」，并拆分为「达标样本组（4 样本）」与「全部样本组（5 样本）」两组报告。
   - **自动正确性检查**：用容器内 SQLite 引擎直接打开原始 `entitlements.sqlite` 执行 12 组真实 SQL 查询（全表有序查询、精确命中主键、大小写/空白边界、SQL 通配符与蜜罐主键查询），与 `answer.py` 返回结果逐项比对。

### 其余 9 项官方样本的排除原因

- **`#12 evm-bytecode`（`.evm`，39 B）**：编写按以太坊黄皮书逐条执行的标准 EVM 解释器实跑原始 `Vault.evm` 时发现，官方手写字节码存在跳转偏移错误——`PUSH1 0x1b; JUMPI` 跳往偏移 `27`（`0x00 STOP`，而合法 `0x5b JUMPDEST` 位于偏移 `26`），`PUSH1 0x20; JUMPI` 跳往偏移 `32`（落在 `PUSH1 0x00` 立即数内部，而合法 `JUMPDEST` 位于偏移 `28`）。按真实 EVM 规范执行时，空 `calldata` 与命中选择器 `0x67e408a7` 均触发 `BadJumpDestination` 异常中止，与注释宣称的返回 `uint256(42)` 矛盾（`benchmark.ts` 仅检查前缀字节相等而未进 EVM 实跑），故按规则排除并换用 `sqlite-db`。
- **`#5 native-elf`（`.elf`，51,339 B）**：由 `buildMappedGoFlutterElfFixture()` 构造的合成桩文件，仅含 `.shstrtab`、`.go.buildinfo`、`.isolate`、`.dynsym`、`.dynstr` 数据节，**无 `.text` 代码节和任何机器指令**，无法作为程序实跑。
- **`#7 safetensors-model`（`.safetensors`，184 B）**：仅存储两个静态 `F32` 权重张量，不含前向计算图或可执行代码。
- **`#8 android-dex`（`.dex`，174 B）**：仅含 112 字节头部和类名字符串常量的合成桩文件，无 `class_defs` 与 Dalvik 字节码指令，无法在虚拟机实跑。
- **`#9 apple-plist`（`.plist`，267 B）**：静态 XML 属性列表配置，无可执行逻辑。
- **`#10 dotnet-managed`（`.dll`，213 B）**：仅含 `MZ`/`PE`/`BSJB` 魔数与符号字符串的合成桩文件，无 CIL 字节码指令，无法在 CLR 实跑。
- **`#11 erlang-beam`（`.beam`，104 B）**：`FOR1`/`BEAM` 合成块头（`Code` 块仅 20 字节头部、0 条指令），无法被 Erlang BEAM 加载执行。
- **`#13 pcap-capture`（`.pcap`，86 B）**：静态单帧 UDP 抓包文件，无可运行程序逻辑。
- **`#14 gpu-ptx`（`.ptx`，290 B）**：NVIDIA PTX GPU 核函数汇编（`sm_70`），隔离评测容器为无 GPU/CUDA 驱动的纯 CPU 环境，无法在容器内实跑原核函数。
