[CmdletBinding()]
param(
    [ValidateSet('Check', 'Apply')]
    [string]$Mode = 'Check',
    [ValidatePattern('^[0-9a-fA-F]{64}$')]
    [string]$ExpectedSourceSha256,
    [string]$SourcePath,
    [string]$CodexSkillsRoot = (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex\skills'),
    [string]$ClaudeSkillsRoot = (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.claude\skills'),
    [Parameter(DontShow = $true)]
    [switch]$TestFailAfterFirstSwap
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$CanonicalArchive = 'https://codeload.github.com/medking82/skills/zip/refs/heads/main'
$SkillName = 'apple-design'

function Get-SafeChildPath {
    param([string]$Root, [string]$Child)

    $rootFull = [IO.Path]::GetFullPath($Root)
    $targetFull = [IO.Path]::GetFullPath((Join-Path $rootFull $Child))
    $separators = [char[]]@([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    $prefix = $rootFull.TrimEnd($separators) + [IO.Path]::DirectorySeparatorChar
    if (-not $targetFull.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe target path outside skills root: $targetFull"
    }
    return $targetFull
}

function Assert-DirectoryNotReparsePoint {
    param([string]$Path, [string]$Label)

    if (-not (Test-Path -LiteralPath $Path)) { return }
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer) { throw "$Label is not a directory: $Path" }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "$Label must not be a reparse point: $Path"
    }
}

function Assert-SafeTree {
    param([string]$Root, [switch]$RequireSkill)

    Assert-DirectoryNotReparsePoint -Path $Root -Label 'Tree root'
    $rootFull = [IO.Path]::GetFullPath($Root)
    $items = @(Get-ChildItem -LiteralPath $rootFull -Force -Recurse)
    foreach ($item in $items) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Reparse points are not allowed: $($item.FullName)"
        }
        $relative = [IO.Path]::GetRelativePath($rootFull, $item.FullName)
        if ([IO.Path]::IsPathRooted($relative) -or $relative -eq '..' -or $relative.StartsWith("..$([IO.Path]::DirectorySeparatorChar)")) {
            throw "Unsafe relative path in tree: $relative"
        }
    }

    $files = @($items | Where-Object { -not $_.PSIsContainer })
    if ($files.Count -eq 0) { throw "Skill source is empty: $Root" }
    if ($RequireSkill) {
        $skillFile = Join-Path $rootFull 'SKILL.md'
        if (-not (Test-Path -LiteralPath $skillFile -PathType Leaf)) {
            throw "Skill source has no regular SKILL.md: $Root"
        }
        $content = Get-Content -LiteralPath $skillFile -Raw
        $frontmatter = [regex]::Match(
            $content,
            '\A---\r?\n(?<body>.*?)\r?\n---(?:\r?\n|\z)',
            [Text.RegularExpressions.RegexOptions]::Singleline
        )
        if (-not $frontmatter.Success -or $frontmatter.Groups['body'].Value -notmatch '(?m)^name:\s*apple-design\s*$') {
            throw 'SKILL.md frontmatter must declare name: apple-design'
        }
    }
}

function Get-TreeManifest {
    param([string]$Root)

    $rootFull = [IO.Path]::GetFullPath($Root)
    $entries = @(
        Get-ChildItem -LiteralPath $rootFull -Force -Recurse -File |
            ForEach-Object {
                [pscustomobject]@{
                    path = ([IO.Path]::GetRelativePath($rootFull, $_.FullName) -replace '\\', '/')
                    length = $_.Length
                    sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
                }
            } |
            Sort-Object path
    )
    if ($entries.Count -eq 0) { throw "Cannot manifest an empty tree: $Root" }
    return ($entries | ConvertTo-Json -Compress)
}

function Get-StringSha256 {
    param([string]$Value)

    $hasher = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
        return ([BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    }
    finally {
        $hasher.Dispose()
    }
}

function Copy-CompleteTree {
    param([string]$Source, [string]$Destination)

    New-Item -ItemType Directory -Path $Destination | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $Source -Force) {
        Copy-Item -LiteralPath $item.FullName -Destination $Destination -Recurse -Force
    }
}

function Resolve-CanonicalSource {
    param([string]$TemporaryRoot)

    if ($SourcePath) {
        return (Resolve-Path -LiteralPath $SourcePath).Path
    }

    $zipPath = Join-Path $TemporaryRoot 'skills.zip'
    $extractPath = Join-Path $TemporaryRoot 'archive'
    Invoke-WebRequest -Uri $CanonicalArchive -OutFile $zipPath
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractPath
    $candidates = @(
        Get-ChildItem -LiteralPath $extractPath -Directory |
            ForEach-Object { Join-Path $_.FullName 'skills\apple-design' } |
            Where-Object { Test-Path -LiteralPath $_ -PathType Container }
    )
    if ($candidates.Count -ne 1) {
        throw "Expected exactly one skills/apple-design directory in canonical archive; found $($candidates.Count)"
    }
    return $candidates[0]
}

function Get-ScopeState {
    param([string]$Name, [string]$SkillsRoot, [string]$CanonicalManifest)

    $rootFull = [IO.Path]::GetFullPath($SkillsRoot)
    $target = Get-SafeChildPath -Root $rootFull -Child $SkillName
    Assert-DirectoryNotReparsePoint -Path $rootFull -Label "$Name skills root"
    if (-not (Test-Path -LiteralPath $target)) {
        return [pscustomobject]@{ Name = $Name; Root = $rootFull; Target = $target; Status = 'missing' }
    }
    Assert-SafeTree -Root $target -RequireSkill
    $status = if ((Get-TreeManifest -Root $target) -ceq $CanonicalManifest) { 'current' } else { 'drifted' }
    return [pscustomobject]@{ Name = $Name; Root = $rootFull; Target = $target; Status = $status }
}

function Invoke-TransactionalApply {
    param([object[]]$States, [string]$CanonicalSource, [string]$CanonicalManifest)

    $transactionId = [guid]::NewGuid().ToString('N')
    $changes = @()
    try {
        foreach ($state in $States | Where-Object { $_.Status -ne 'current' }) {
            $rootCreated = -not (Test-Path -LiteralPath $state.Root)
            if ($rootCreated) { New-Item -ItemType Directory -Path $state.Root -Force | Out-Null }
            Assert-DirectoryNotReparsePoint -Path $state.Root -Label "$($state.Name) skills root"
            if (Test-Path -LiteralPath $state.Target) { Assert-SafeTree -Root $state.Target -RequireSkill }

            $stage = Get-SafeChildPath -Root $state.Root -Child ".$SkillName.stage.$transactionId"
            $backup = Get-SafeChildPath -Root $state.Root -Child ".$SkillName.backup.$transactionId"
            if ((Test-Path -LiteralPath $stage) -or (Test-Path -LiteralPath $backup)) {
                throw "Transaction path collision in $($state.Root)"
            }
            $change = [pscustomobject]@{
                Name = $state.Name
                Root = $state.Root
                Target = $state.Target
                Stage = $stage
                Backup = $backup
                RootCreated = $rootCreated
                HadTarget = (Test-Path -LiteralPath $state.Target)
                Swapped = $false
            }
            $changes += $change
            Copy-CompleteTree -Source $CanonicalSource -Destination $stage
            Assert-SafeTree -Root $stage -RequireSkill
            if ((Get-TreeManifest -Root $stage) -cne $CanonicalManifest) {
                throw "Staged $($state.Name) copy does not match canonical manifest"
            }
        }

        $swapCount = 0
        foreach ($change in $changes) {
            if ($TestFailAfterFirstSwap -and $swapCount -eq 1) {
                throw 'Injected failure before second scope swap'
            }
            if ($change.HadTarget) { Move-Item -LiteralPath $change.Target -Destination $change.Backup }
            Move-Item -LiteralPath $change.Stage -Destination $change.Target
            $change.Swapped = $true
            $swapCount++
        }

        foreach ($change in $changes) {
            Assert-SafeTree -Root $change.Target -RequireSkill
            if ((Get-TreeManifest -Root $change.Target) -cne $CanonicalManifest) {
                throw "Post-write verification failed for $($change.Name)"
            }
        }
        foreach ($change in $changes) {
            if (Test-Path -LiteralPath $change.Backup) { Remove-Item -LiteralPath $change.Backup -Recurse -Force }
            Write-Output "APPLE_DESIGN_SYNC scope=$($change.Name) status=applied"
        }
    }
    catch {
        foreach ($change in @($changes | Sort-Object Name -Descending)) {
            if ((Test-Path -LiteralPath $change.Target) -and ($change.Swapped -or (Test-Path -LiteralPath $change.Backup))) {
                Remove-Item -LiteralPath $change.Target -Recurse -Force
            }
            if (Test-Path -LiteralPath $change.Backup) {
                Move-Item -LiteralPath $change.Backup -Destination $change.Target
            }
            if (Test-Path -LiteralPath $change.Stage) { Remove-Item -LiteralPath $change.Stage -Recurse -Force }
            if ($change.RootCreated -and (Test-Path -LiteralPath $change.Root) -and
                @(Get-ChildItem -LiteralPath $change.Root -Force).Count -eq 0) {
                Remove-Item -LiteralPath $change.Root -Force
            }
        }
        throw
    }
}

$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ("apple-design-sync-" + [guid]::NewGuid().ToString('N'))
$exitCode = 1
try {
    New-Item -ItemType Directory -Path $temporaryRoot | Out-Null
    $canonicalSource = Resolve-CanonicalSource -TemporaryRoot $temporaryRoot
    Assert-SafeTree -Root $canonicalSource -RequireSkill
    $canonicalManifest = Get-TreeManifest -Root $canonicalSource
    $canonicalSha256 = Get-StringSha256 -Value $canonicalManifest
    Write-Output "APPLE_DESIGN_SYNC source_sha256=$canonicalSha256"
    if ($Mode -eq 'Apply') {
        if (-not $ExpectedSourceSha256) {
            throw 'Apply requires -ExpectedSourceSha256 from a prior Check'
        }
        if ($ExpectedSourceSha256.ToLowerInvariant() -cne $canonicalSha256) {
            throw "Expected source SHA-256 does not match canonical manifest: expected=$($ExpectedSourceSha256.ToLowerInvariant()) actual=$canonicalSha256"
        }
    }
    $states = @(
        Get-ScopeState -Name 'Codex' -SkillsRoot $CodexSkillsRoot -CanonicalManifest $canonicalManifest
        Get-ScopeState -Name 'Claude' -SkillsRoot $ClaudeSkillsRoot -CanonicalManifest $canonicalManifest
    )

    foreach ($state in $states) {
        Write-Output "APPLE_DESIGN_SYNC scope=$($state.Name) status=$($state.Status)"
    }
    if ($Mode -eq 'Check') {
        $exitCode = if (@($states | Where-Object { $_.Status -ne 'current' }).Count -gt 0) { 3 } else { 0 }
    }
    else {
        Invoke-TransactionalApply -States $states -CanonicalSource $canonicalSource -CanonicalManifest $canonicalManifest
        foreach ($state in $states) {
            Assert-SafeTree -Root $state.Target -RequireSkill
            if ((Get-TreeManifest -Root $state.Target) -cne $canonicalManifest) {
                throw "Final verification failed for $($state.Name)"
            }
        }
        $exitCode = 0
    }
}
catch {
    [Console]::Error.WriteLine("APPLE_DESIGN_SYNC status=error message=$($_.Exception.Message)")
    $exitCode = 1
}
finally {
    if (Test-Path -LiteralPath $temporaryRoot) { Remove-Item -LiteralPath $temporaryRoot -Recurse -Force }
}
exit $exitCode
