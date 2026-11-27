<#
.SYNOPSIS
  构建纯净运行镜像 bla-bench:local 与验证镜像 bla-bench:verifier -> 离线检查 -> 隔离自检 -> 实测与一致性检查。

.EXAMPLE
  .\run-docker.ps1                        # 全流程（构建 + 离线检查 + 隔离自检 + 空载基线 + dx-ball original）
  .\run-docker.ps1 -Stage check           # 只构建 + 离线检查，不调用模型
  .\run-docker.ps1 -Stage isolation-check # 启动纯净运行容器核验 bench 可读文件，写入 evidence/isolation_check.txt
  .\run-docker.ps1 -Stage harden          # 在验证容器内用 BLA 官方 CLI 生成 5 个入选样本的 hardened 版本与清单
  .\run-docker.ps1 -Stage baseline        # 在纯净运行容器内跑空载基线（宿主收集日志）
  .\run-docker.ps1 -Stage dx-ball         # 在纯净运行容器内跑 dx-ball original + 一致性检查
  .\run-docker.ps1 -Stage relay-start     # 校验 Internal=true 并启动隔离中继容器 bla-relay
  .\run-docker.ps1 -Stage relay-stop      # 停止隔离中继容器 bla-relay

.NOTES
  - 运行容器（bla-bench:local）只挂载单样本工作目录与只读凭据，不挂载 runs/、results.csv、fixtures/、scripts/、tests/。
  - 日志由宿主机在容器外捕获 stdout/stderr 写入 runs/。
#>
[CmdletBinding()]
param(
  [ValidateSet('all', 'build', 'check', 'isolation-check', 'harden', 'baseline', 'dx-ball', 'relay-start', 'relay-stop')]
  [string]$Stage = 'all',
  [string]$Image = 'bla-bench:local',
  [string]$VerifierImage = 'bla-bench:verifier',
  [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex')
)
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Evidence = Join-Path $Root 'evidence'
$Work = Join-Path $Root 'docker-work'
New-Item -ItemType Directory -Force -Path $Evidence, (Join-Path $Root 'runs') | Out-Null

function Invoke-Docker {
  param([string[]]$DockerArgs, [string]$Log)
  $line = 'docker ' + (($DockerArgs | ForEach-Object { if ($_ -match '[\s"]') { '"' + $_ + '"' } else { $_ } }) -join ' ')
  & cmd.exe /d /c "$line 2>&1" | ForEach-Object { Write-Host $_; $_ } | Out-File -FilePath $Log -Append -Encoding utf8
  if ($LASTEXITCODE -ne 0) { throw "docker failed (exit $LASTEXITCODE), log: $Log" }
}

function Get-Mount([string]$Source, [string]$Target, [switch]$ReadOnly) {
  $spec = "type=bind,source=$Source,target=$Target"
  if ($ReadOnly) { $spec += ',readonly' }
  return @('--mount', $spec)
}

$Common = @('run', '--rm', '--security-opt', 'no-new-privileges', '--cap-drop', 'ALL')

function Get-AuthMounts {
  $auth = Join-Path $CodexHome 'auth.json'
  $catalog = Join-Path $CodexHome 'cpa-gui-model-catalog.json'
  foreach ($f in @($auth, $catalog)) { if (-not (Test-Path $f)) { throw "缺少 $f" } }
  return (Get-Mount $auth '/home/bench/.codex/auth.json' -ReadOnly) +
         (Get-Mount $catalog '/home/bench/.codex/cpa-gui-model-catalog.json' -ReadOnly)
}

$Network = 'bla-internal'
$Relay = 'bla-relay'

function Start-Relay([string]$Log) {
  Stop-Relay
  & docker network inspect $Network *> $null
  if ($LASTEXITCODE -ne 0) { Invoke-Docker -DockerArgs @('network', 'create', '--internal', $Network) -Log $Log }
  $internal = (& docker network inspect -f '{{.Internal}}' $Network | Out-String).Trim()
  if ($internal -ne 'true') { throw "网络 $Network 不是 --internal（Internal=$internal），拒绝运行；请先 docker network rm $Network" }
  Invoke-Docker -DockerArgs @('run', '-d', '--rm', '--name', $Relay, '--security-opt', 'no-new-privileges',
    '--cap-drop', 'ALL', $VerifierImage, 'relay') -Log $Log
  Invoke-Docker -DockerArgs @('network', 'connect', $Network, $Relay) -Log $Log
}

function Stop-Relay {
  & docker rm -f $Relay *> $null
}

function New-Target([string]$Name, [string]$From) {
  $dir = Join-Path $Work "targets\$Name"
  if (Test-Path $dir) { Remove-Item -Recurse -Force $dir }
  New-Item -ItemType Directory -Force -Path (Join-Path $dir 'original') | Out-Null
  Copy-Item -Path (Join-Path $From '*') -Destination (Join-Path $dir 'original')
  return $dir
}

if ($Stage -in 'all', 'build', 'check') {
  Write-Host '== build verifier & clean runtime images ==' -ForegroundColor Cyan
  $buildLog = Join-Path $Evidence 'docker-build.log'
  Remove-Item -Force -ErrorAction SilentlyContinue $buildLog
  Invoke-Docker -DockerArgs @('build', '--progress=plain', '--target', 'verifier', '-t', $VerifierImage, $Root) -Log $buildLog
  Invoke-Docker -DockerArgs @('build', '--progress=plain', '--target', 'runtime', '-t', $Image, $Root) -Log $buildLog
}

if ($Stage -in 'all', 'check') {
  Write-Host '== offline check (verifier container) ==' -ForegroundColor Cyan
  $log = Join-Path $Evidence 'docker-check.log'
  Remove-Item -Force -ErrorAction SilentlyContinue $log
  $hostAnswer = Join-Path $Root 'targets\dx-ball\answer.py'
  Invoke-Docker -DockerArgs ($Common +
    (Get-Mount $hostAnswer '/bench/host-answer/answer.py' -ReadOnly) +
    (Get-Mount (Join-Path $Root 'fixtures') '/bench/fixtures' -ReadOnly) +
    @($VerifierImage, 'check')) -Log $log
}

if ($Stage -in 'all', 'isolation-check') {
  Write-Host '== runtime container isolation self-check ==' -ForegroundColor Cyan
  & python (Join-Path $Root 'scripts\check_isolation.py') --image $Image --codex-home $CodexHome
  if ($LASTEXITCODE -ne 0) { throw "isolation-check failed (exit $LASTEXITCODE)" }
}

if ($Stage -eq 'harden') {
  Write-Host '== harden 5 official samples in verifier container ==' -ForegroundColor Cyan
  $log = Join-Path $Evidence 'docker-harden.log'
  Remove-Item -Force -ErrorAction SilentlyContinue $log
  Invoke-Docker -DockerArgs ($Common + @('--network', 'none') +
    (Get-Mount (Join-Path $Root 'fixtures') '/bench/all-fixtures' -ReadOnly) +
    (Get-Mount (Join-Path $Root 'targets') '/bench/out-targets') +
    (Get-Mount $Evidence '/bench/out-evidence') +
    @($VerifierImage, 'harden')) -Log $log
}

if ($Stage -eq 'relay-start') {
  Start-Relay -Log (Join-Path $Evidence 'docker-relay.log')
}

if ($Stage -eq 'relay-stop') {
  Stop-Relay
}

if ($Stage -in 'all', 'baseline', 'dx-ball') {
  Start-Relay -Log (Join-Path $Evidence 'docker-relay.log')
  try {
    if ($Stage -in 'all', 'baseline') {
      Write-Host '== live: empty-load baseline (clean runtime container, host log collection) ==' -ForegroundColor Cyan
      & python (Join-Path $Root 'scripts\run_w3_r2.py') --single-sample baseline --single-label baseline --prompt-file prompt-baseline.txt --timeout 300 --codex-home $CodexHome --no-manage-relay
      if ($LASTEXITCODE -ne 0) { throw "baseline run failed (exit $LASTEXITCODE)" }
    }
    if ($Stage -in 'all', 'dx-ball') {
      Write-Host '== live: dx-ball original (clean runtime container, host log collection) ==' -ForegroundColor Cyan
      & python (Join-Path $Root 'scripts\run_w3_r2.py') --single-sample dx-ball --single-label original --prompt-file prompt.txt --timeout 900 --codex-home $CodexHome --no-manage-relay
      if ($LASTEXITCODE -ne 0) { throw "dx-ball run failed (exit $LASTEXITCODE)" }
    }
  } finally {
    Stop-Relay
  }
}
