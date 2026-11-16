param([string]$ToolsDirectory = "")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m PyInstaller --noconfirm --clean VideoDownloader.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
Copy-Item README.md, LICENSE, THIRD_PARTY.md dist/VideoDownloader/
if ($ToolsDirectory) {
    New-Item -ItemType Directory -Force dist/VideoDownloader/tools | Out-Null
    foreach ($name in @("ffmpeg.exe", "ffprobe.exe", "node.exe")) {
        $source = Join-Path $ToolsDirectory $name
        if (!(Test-Path $source)) { throw "Missing $source" }
        Copy-Item $source dist/VideoDownloader/tools/
    }
    Write-Warning "Include the licenses and corresponding-source obligations for your exact tool builds."
}
Write-Output "Executable: dist/VideoDownloader/VideoDownloader.exe. Keep the entire directory."
