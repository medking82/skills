[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$EngineArguments
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'PowerShell 7 or newer is required.' }
if (-not $EngineArguments -or $EngineArguments.Count -eq 0) { throw 'Specify an Impeccable engine command.' }

$skillRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\upstream'))
$version = (Get-Content -Raw -LiteralPath (Join-Path $skillRoot 'scripts\VERSION')).Trim()
if ($version -notmatch '^\d+\.\d+\.\d+$') { throw 'Invalid pinned Impeccable engine version.' }
$manifest = Get-Content -LiteralPath (Join-Path $skillRoot 'scripts\engine-checksums.txt')
$architecture = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'x64' }
$asset = "impeccable-windows-$architecture.exe"
$line = @($manifest | Where-Object { $_ -match "^$([regex]::Escape($version))\s+$([regex]::Escape($asset))\s+[0-9a-fA-F]{64}\s*$" })
if ($line.Count -eq 0 -and $architecture -eq 'arm64') {
    $asset = 'impeccable-windows-x64.exe'
    $line = @($manifest | Where-Object { $_ -match "^$([regex]::Escape($version))\s+$([regex]::Escape($asset))\s+[0-9a-fA-F]{64}\s*$" })
}
if ($line.Count -ne 1) { throw 'The pinned engine checksum is missing or ambiguous.' }
$expected = ($line[0] -split '\s+')[2].ToLowerInvariant()
$cache = Join-Path $env:USERPROFILE ".impeccable\bin\$version"
$engine = Join-Path $cache 'impeccable.exe'

if (-not (Test-Path -LiteralPath $engine -PathType Leaf)) {
    New-Item -ItemType Directory -Path $cache -Force | Out-Null
    $part = Join-Path $cache ('.download-' + [Guid]::NewGuid().ToString('N') + '.tmp')
    try {
        $url = "https://github.com/pbakaus/impeccable/releases/download/engine-v$version/$asset"
        Invoke-WebRequest -Uri $url -OutFile $part -TimeoutSec 60
        if ((Get-FileHash -LiteralPath $part -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
            throw 'Downloaded Impeccable engine checksum does not match the pinned manifest.'
        }
        if (-not (Test-Path -LiteralPath $engine -PathType Leaf)) {
            Move-Item -LiteralPath $part -Destination $engine
        }
    } finally {
        if (Test-Path -LiteralPath $part -PathType Leaf) { Remove-Item -LiteralPath $part -Force }
    }
}
if ((Get-FileHash -LiteralPath $engine -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    throw 'Cached Impeccable engine checksum does not match the pinned manifest.'
}
$env:IMPECCABLE_SKILL_DIR = $skillRoot
$env:IMPECCABLE_SELF = Join-Path $skillRoot 'scripts\impeccable.cmd'
$runner = Join-Path $env:USERPROFILE '.codex\bin\invoke-hidden.ps1'
& $runner -FilePath $engine -ArgumentList $EngineArguments -WorkingDirectory (Get-Location).Path
exit $LASTEXITCODE
