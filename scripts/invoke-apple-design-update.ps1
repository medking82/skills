[CmdletBinding()]
param(
    [ValidateSet('Check', 'Apply')]
    [string]$Mode = 'Check',
    [ValidatePattern('^[0-9a-fA-F]{64}$')]
    [string]$ExpectedSourceSha256,
    [string]$LogDirectory = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'AppleDesignSkillUpdate'),
    [Parameter(DontShow = $true)]
    [string]$SourcePath,
    [Parameter(DontShow = $true)]
    [string]$CodexSkillsRoot,
    [Parameter(DontShow = $true)]
    [string]$ClaudeSkillsRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

$engine = Join-Path $PSScriptRoot 'sync-apple-design.ps1'
if (-not (Test-Path -LiteralPath $engine -PathType Leaf)) { throw "Updater engine not found: $engine" }
New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
$logPath = Join-Path $LogDirectory ("apple-design-update-{0}.log" -f (Get-Date -Format 'yyyyMMdd'))
$powerShellPath = (Get-Process -Id $PID).Path
$arguments = @('-NoProfile', '-NonInteractive', '-File', $engine, '-Mode', $Mode)
if ($Mode -eq 'Apply') {
    if (-not $ExpectedSourceSha256) { throw 'Apply requires -ExpectedSourceSha256 from a prior Check' }
    $arguments += @('-ExpectedSourceSha256', $ExpectedSourceSha256)
}
if ($SourcePath) { $arguments += @('-SourcePath', $SourcePath) }
if ($CodexSkillsRoot) { $arguments += @('-CodexSkillsRoot', $CodexSkillsRoot) }
if ($ClaudeSkillsRoot) { $arguments += @('-ClaudeSkillsRoot', $ClaudeSkillsRoot) }

"[{0}] mode={1}" -f (Get-Date -Format o), $Mode | Add-Content -LiteralPath $logPath
$output = & $powerShellPath @arguments 2>&1
$exitCode = $LASTEXITCODE
$output | Tee-Object -FilePath $logPath -Append | Write-Output
exit $exitCode
