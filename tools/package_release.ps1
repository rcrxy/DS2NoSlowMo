[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$loaderRoot = Join-Path $projectRoot 'third_party/ultimate-asi-loader'
$loader = Get-Content -LiteralPath (Join-Path $loaderRoot 'manifest.json') -Raw | ConvertFrom-Json
$loaderPath = Join-Path $loaderRoot 'version.dll'
if ((Get-FileHash -LiteralPath $loaderPath -Algorithm SHA256).Hash -cne $loader.sha256) {
    throw 'Bundled ASI Loader SHA256 differs from third_party/ultimate-asi-loader/manifest.json.'
}

& (Join-Path $projectRoot 'do_build.bat') Release
if ($LASTEXITCODE -ne 0) { throw 'Release build failed.' }

$source = Get-Content -LiteralPath (Join-Path $projectRoot 'src/ds2_no_slowmo.cpp') -Raw
$versionMatch = [regex]::Match($source, 'constexpr char PluginVersion\[\] = "([0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?)";')
if (-not $versionMatch.Success) { throw 'Cannot read PluginVersion from src/ds2_no_slowmo.cpp.' }
$version = $versionMatch.Groups[1].Value
$readmePath = Join-Path $projectRoot 'docs/release-readme.md'
if (-not (Get-Content -LiteralPath $readmePath -Raw).Contains("**Version:** $version ")) {
    throw 'Release README version differs from PluginVersion.'
}

$inputs = @(
    @{ name = 'DS2NoSlowMo.asi'; source = Join-Path $projectRoot 'build/Release/DS2NoSlowMo.asi' }
    @{ name = 'DS2NoSlowMo.ini'; source = Join-Path $projectRoot 'DS2NoSlowMo.ini' }
    @{ name = 'version.dll'; source = $loaderPath }
    @{ name = 'README.md'; source = $readmePath }
    @{ name = 'LICENSE'; source = Join-Path $projectRoot 'LICENSE' }
    @{ name = 'LICENSE-Ultimate-ASI-Loader.txt'; source = Join-Path $loaderRoot 'LICENSE' }
)
$files = @($inputs | ForEach-Object {
    $file = Get-Item -LiteralPath $_.source
    [ordered]@{
        name = $_.name
        sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        size = $file.Length
    }
})

Add-Type -AssemblyName System.IO.Compression.FileSystem
$releaseRoot = Join-Path $projectRoot 'build/releases'
New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null
$zipPath = Join-Path $releaseRoot "DS2NoSlowMo-$version.zip"
$temporaryZip = Join-Path $releaseRoot ([IO.Path]::GetRandomFileName() + '.zip')
try {
    $archive = [IO.Compression.ZipFile]::Open($temporaryZip, [IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($inputFile in $inputs) {
            [IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive, $inputFile.source, $inputFile.name, [IO.Compression.CompressionLevel]::Optimal) | Out-Null
        }
    }
    finally { $archive.Dispose() }

    $archive = [IO.Compression.ZipFile]::OpenRead($temporaryZip)
    try {
        if ($archive.Entries.Count -ne $files.Count) { throw 'ZIP file count differs from the release file list.' }
        foreach ($file in $files) {
            $entry = $archive.GetEntry($file.name)
            if ($null -eq $entry -or $entry.Length -ne $file.size) { throw "ZIP entry missing or wrong size: $($file.name)" }
            $stream = $entry.Open()
            $algorithm = [Security.Cryptography.SHA256]::Create()
            try { $hash = [BitConverter]::ToString($algorithm.ComputeHash($stream)).Replace('-', '') }
            finally { $stream.Dispose(); $algorithm.Dispose() }
            if ($hash -cne $file.sha256) { throw "ZIP content hash differs: $($file.name)" }
        }
    }
    finally { $archive.Dispose() }

    Move-Item -LiteralPath $temporaryZip -Destination $zipPath -Force
}
finally {
    if (Test-Path -LiteralPath $temporaryZip) { Remove-Item -LiteralPath $temporaryZip }
}

$manifest = [ordered]@{
    version = $version
    zip = $zipPath
    zip_sha256 = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash
    files = $files
}
$manifestPath = Join-Path $releaseRoot "DS2NoSlowMo-$version-manifest.json"
[IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 4) + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
Write-Output "Packaged and verified: $zipPath"
Write-Output "SHA256 manifest: $manifestPath"
