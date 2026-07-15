param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Error "未找到虚拟环境。请先在项目根目录执行：python -m venv .venv"
}

Write-Host "安装桌面打包依赖..."
& $Python -m pip install -r requirements.txt -q
& $Python -m pip install -r requirements-desktop.txt -q

if ($Clean) {
    Write-Host "清理旧的构建产物..."
    if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
    if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
}

Write-Host "开始 PyInstaller 打包..."
& $Python -m PyInstaller --noconfirm bridge_trainer_desktop.spec

$OutputDir = Join-Path $ProjectRoot "dist\BridgeBiddingTrainer"
$ExePath = Join-Path $OutputDir "BridgeBiddingTrainer.exe"
if (-not (Test-Path $ExePath)) {
    Write-Error "打包失败：未找到 $ExePath"
}

Write-Host ""
Write-Host "打包完成。"
Write-Host "输出目录：$OutputDir"
Write-Host "启动程序：$ExePath"
Write-Host ""
Write-Host "可将整个 BridgeBiddingTrainer 文件夹压缩后分发给其他 Windows 用户。"
