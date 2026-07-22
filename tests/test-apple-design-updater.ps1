[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false

$repoRoot = Split-Path $PSScriptRoot -Parent
$updater = Join-Path $repoRoot 'scripts\sync-apple-design.ps1'
$wrapper = Join-Path $repoRoot 'scripts\invoke-apple-design-update.ps1'
$taskInstaller = Join-Path $repoRoot 'scripts\install-apple-design-update-task.ps1'
$powerShellPath = (Get-Process -Id $PID).Path
$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ("apple-design-updater-test-" + [guid]::NewGuid().ToString('N'))
$source = Join-Path $temporaryRoot 'source'
$codexRoot = Join-Path $temporaryRoot 'codex-skills'
$claudeRoot = Join-Path $temporaryRoot 'claude-skills'
$script:Passed = 0

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
    $script:Passed++
    Write-Output "PASS: $Message"
}

function Write-TestSkill {
    param([string]$Version, [switch]$Invalid)
    New-Item -ItemType Directory -Path $source -Force | Out-Null
    $name = if ($Invalid) { 'wrong-name' } else { 'apple-design' }
    $content = "---`nname: $name`ndescription: test fixture`n---`n`n# Apple Design`n`nversion: $Version`n"
    Set-Content -LiteralPath (Join-Path $source 'SKILL.md') -Value $content -NoNewline
}

function Invoke-TestUpdater {
    param([string]$Mode, [string]$ExpectedSourceSha256, [switch]$InjectFailure)
    $arguments = @(
        '-NoProfile', '-NonInteractive', '-File', $updater,
        '-Mode', $Mode,
        '-SourcePath', $source,
        '-CodexSkillsRoot', $codexRoot,
        '-ClaudeSkillsRoot', $claudeRoot
    )
    if ($ExpectedSourceSha256) { $arguments += @('-ExpectedSourceSha256', $ExpectedSourceSha256) }
    if ($InjectFailure) { $arguments += '-TestFailAfterFirstSwap' }
    $output = & $powerShellPath @arguments 2>&1
    return [pscustomobject]@{ ExitCode = $LASTEXITCODE; Output = ($output -join "`n") }
}

function Get-ReportedSourceSha256 {
    param([object]$Result)
    $match = [regex]::Match($Result.Output, 'source_sha256=([0-9a-f]{64})')
    if (-not $match.Success) { throw 'Updater output did not contain a canonical source SHA-256' }
    return $match.Groups[1].Value
}

function Get-SkillSha256 {
    param([string]$Root)
    return (Get-FileHash -LiteralPath (Join-Path $Root 'apple-design\SKILL.md') -Algorithm SHA256).Hash
}

try {
    New-Item -ItemType Directory -Path $temporaryRoot | Out-Null
    Write-TestSkill -Version 'one'

    $result = Invoke-TestUpdater -Mode Check
    Assert-True ($result.ExitCode -eq 3) 'check reports drift when both installations are missing'
    $sourceSha256 = Get-ReportedSourceSha256 -Result $result
    Assert-True ($sourceSha256 -match '^[0-9a-f]{64}$') 'check reports a deterministic canonical manifest SHA-256'
    Assert-True (-not (Test-Path -LiteralPath $codexRoot) -and -not (Test-Path -LiteralPath $claudeRoot)) 'check-only creates no destination roots'

    $result = Invoke-TestUpdater -Mode Apply
    Assert-True ($result.ExitCode -eq 1 -and -not (Test-Path -LiteralPath $codexRoot) -and -not (Test-Path -LiteralPath $claudeRoot)) 'apply without an expected source SHA-256 performs zero destination writes'
    $result = Invoke-TestUpdater -Mode Apply -ExpectedSourceSha256 ('0' * 64)
    Assert-True ($result.ExitCode -eq 1 -and -not (Test-Path -LiteralPath $codexRoot) -and -not (Test-Path -LiteralPath $claudeRoot)) 'apply with a mismatched source SHA-256 performs zero destination writes'
    $result = Invoke-TestUpdater -Mode Apply -ExpectedSourceSha256 $sourceSha256
    Assert-True ($result.ExitCode -eq 0) 'apply installs both scopes'
    Assert-True ((Get-FileHash (Join-Path $codexRoot 'apple-design\SKILL.md')).Hash -eq (Get-FileHash (Join-Path $claudeRoot 'apple-design\SKILL.md')).Hash) 'both installed scopes are byte-identical'

    $beforeHash = Get-SkillSha256 -Root $codexRoot
    $result = Invoke-TestUpdater -Mode Apply -ExpectedSourceSha256 $sourceSha256
    Assert-True ($result.ExitCode -eq 0 -and $beforeHash -eq (Get-SkillSha256 -Root $codexRoot)) 'apply is byte-idempotent when current'
    $result = Invoke-TestUpdater -Mode Check
    Assert-True ($result.ExitCode -eq 0) 'check reports current after apply'

    Write-TestSkill -Version 'two'
    $result = Invoke-TestUpdater -Mode Check
    $sourceSha256 = Get-ReportedSourceSha256 -Result $result
    Assert-True ($result.ExitCode -eq 3 -and $beforeHash -eq (Get-SkillSha256 -Root $codexRoot)) 'check detects canonical updates without writing installations'
    $result = Invoke-TestUpdater -Mode Apply -ExpectedSourceSha256 $sourceSha256
    Assert-True ($result.ExitCode -eq 0 -and (Get-Content (Join-Path $claudeRoot 'apple-design\SKILL.md') -Raw) -match 'version: two') 'apply propagates a canonical update to both scopes'

    Add-Content -LiteralPath (Join-Path $codexRoot 'apple-design\SKILL.md') -Value "`nlocal edit"
    $result = Invoke-TestUpdater -Mode Check
    Assert-True ($result.ExitCode -eq 3 -and $result.Output -match 'scope=Codex status=drifted') 'check identifies local drift without overwriting it'
    $result = Invoke-TestUpdater -Mode Apply -ExpectedSourceSha256 $sourceSha256
    Assert-True ($result.ExitCode -eq 0) 'explicit apply repairs local drift'

    $stableCodexHash = Get-SkillSha256 -Root $codexRoot
    $stableClaudeHash = Get-SkillSha256 -Root $claudeRoot
    Write-TestSkill -Version 'invalid' -Invalid
    $result = Invoke-TestUpdater -Mode Apply -ExpectedSourceSha256 $sourceSha256
    Assert-True ($result.ExitCode -eq 1) 'invalid skill frontmatter fails closed'
    Assert-True ($stableCodexHash -eq (Get-SkillSha256 -Root $codexRoot) -and $stableClaudeHash -eq (Get-SkillSha256 -Root $claudeRoot)) 'invalid source leaves both scopes unchanged'

    Write-TestSkill -Version 'three'
    $result = Invoke-TestUpdater -Mode Check
    $sourceSha256 = Get-ReportedSourceSha256 -Result $result
    $result = Invoke-TestUpdater -Mode Apply -ExpectedSourceSha256 $sourceSha256 -InjectFailure
    Assert-True ($result.ExitCode -eq 1) 'injected second-scope failure returns non-zero'
    Assert-True ($stableCodexHash -eq (Get-SkillSha256 -Root $codexRoot) -and $stableClaudeHash -eq (Get-SkillSha256 -Root $claudeRoot)) 'transaction failure restores both prior installations'

    $wrapperLogRoot = Join-Path $temporaryRoot 'wrapper-logs'
    $wrapperOutput = & $powerShellPath -NoProfile -NonInteractive -File $wrapper -Mode Check -SourcePath $source -CodexSkillsRoot $codexRoot -ClaudeSkillsRoot $claudeRoot -LogDirectory $wrapperLogRoot 2>&1
    $wrapperExitCode = $LASTEXITCODE
    $wrapperLog = Get-Content -LiteralPath (Get-ChildItem -LiteralPath $wrapperLogRoot -File | Select-Object -First 1).FullName -Raw
    Assert-True ($wrapperExitCode -eq 3 -and ($wrapperOutput -join "`n") -match 'status=drifted') 'logging wrapper preserves the expected drift exit code'
    Assert-True ($wrapperLog -match 'source_sha256=[0-9a-f]{64}' -and $wrapperLog -match 'status=drifted') 'logging wrapper records drift evidence before exiting'

    $preview = & $powerShellPath -NoProfile -NonInteractive -File $taskInstaller -TaskName "Apple Design Test $([guid]::NewGuid().ToString('N'))" 2>&1
    Assert-True ($LASTEXITCODE -eq 0 -and ($preview -join "`n") -match 'mode=Check' -and ($preview -join "`n") -match 'preview-only') 'scheduled-task installer is preview-first and check-only'

    foreach ($scriptPath in @($updater, $wrapper, $taskInstaller, $PSCommandPath)) {
        $tokens = $null
        $errors = $null
        [Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tokens, [ref]$errors) | Out-Null
        Assert-True ($errors.Count -eq 0) "PowerShell parser accepts $([IO.Path]::GetFileName($scriptPath))"
    }
    Write-Output "RESULT: $script:Passed passed, 0 failed"
}
finally {
    if (Test-Path -LiteralPath $temporaryRoot) { Remove-Item -LiteralPath $temporaryRoot -Recurse -Force }
}
