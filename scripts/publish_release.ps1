$ErrorActionPreference = "Stop"

Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location -Path (Resolve-Path "..")

git status --porcelain | ForEach-Object { throw "Working tree is not clean. Commit or stash before publishing." }

$version = & .\.venv\Scripts\python.exe -c "import voicetype; print(voicetype.__version__)"
$tag = "v$version"

Write-Host "Publishing release tag $tag"

$existing = git tag --list $tag
if ($existing) {
  Write-Host "Tag already exists locally: $tag"
} else {
  git tag $tag
}

git push origin main
git push origin $tag
