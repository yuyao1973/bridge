param(
    [Parameter(Mandatory = $true)]
    [string]$CloudEnvId
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$TemplateDir = Join-Path $ProjectRoot "cloudtemplates\bridge-api"
$TargetDir = Join-Path $ProjectRoot "cloudfunctions\$CloudEnvId\containers\bridge-api"

if (-not (Test-Path $TemplateDir)) {
    Write-Error "Cloud template not found: $TemplateDir"
}

if (Test-Path $TargetDir) {
    Write-Error "Target directory already exists: $TargetDir"
}

New-Item -ItemType Directory -Force -Path (Split-Path $TargetDir -Parent) | Out-Null
Copy-Item -Recurse -Force $TemplateDir $TargetDir

Write-Host "Cloud container template deployed to:"
Write-Host $TargetDir
