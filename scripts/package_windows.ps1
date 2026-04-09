$ErrorActionPreference = "Stop"

Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location -Path (Resolve-Path "..")

New-Item -ItemType Directory -Force -Path "dist_release" | Out-Null

$src = Join-Path (Resolve-Path "dist") "TalkieType"
$zip = Join-Path (Resolve-Path "dist_release") "TalkieType-windows.zip"

if (Test-Path $zip) { Remove-Item -Force $zip }
$maxAttempts = 8
for ($i = 1; $i -le $maxAttempts; $i++) {
  try {
    Compress-Archive -Path "$src\*" -DestinationPath $zip -Force
    break
  } catch {
    if ($i -eq $maxAttempts) { throw }
    Start-Sleep -Milliseconds 500
  }
}
