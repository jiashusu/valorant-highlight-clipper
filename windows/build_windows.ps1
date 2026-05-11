$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $ProjectRoot

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

$VendorDir = Join-Path $ProjectRoot "vendor\ffmpeg"
New-Item -ItemType Directory -Force -Path $VendorDir | Out-Null

if (!(Test-Path (Join-Path $VendorDir "ffmpeg.exe")) -or !(Test-Path (Join-Path $VendorDir "ffprobe.exe"))) {
  $ZipPath = Join-Path $env:TEMP "ffmpeg-release-essentials.zip"
  $ExtractDir = Join-Path $env:TEMP "ffmpeg-release-essentials"
  Remove-Item -Recurse -Force $ExtractDir -ErrorAction SilentlyContinue
  Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $ZipPath
  Expand-Archive -Path $ZipPath -DestinationPath $ExtractDir -Force
  $FfmpegRoot = Get-ChildItem $ExtractDir -Directory | Select-Object -First 1
  Copy-Item (Join-Path $FfmpegRoot.FullName "bin\ffmpeg.exe") $VendorDir -Force
  Copy-Item (Join-Path $FfmpegRoot.FullName "bin\ffprobe.exe") $VendorDir -Force
}

pyinstaller --noconfirm --clean windows\ValorantHighlightClipper.spec

Write-Host "Built: $ProjectRoot\dist\ValorantHighlightClipper.exe"
