[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^[0-9a-f]{40}$')]
    [string]$InitialCommit,
    [string]$PythonPath = (Get-Command python.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Run this installer with PowerShell 7.' }
$repository = 'C:\github\SOP\skills'
$runtime = Join-Path $env:USERPROFILE '.codex\design-sync'
$source = Join-Path $repository 'scripts\sync-codex-design.py'
$hiddenRunner = 'C:\Users\Marck\.codex\bin\invoke-hidden.ps1'
$taskName = 'Codex Design Skill Update'
$taskPath = '\'
$python = (Get-Command $PythonPath -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
if ([IO.Path]::GetFileName($python) -ine 'python.exe') { throw 'PythonPath must resolve to the actual python.exe interpreter.' }
$pwsh = (Get-Command pwsh.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
$wscript = Join-Path $env:WINDIR 'System32\wscript.exe'
foreach ($required in @($source, $hiddenRunner, $pwsh, $wscript)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Required file missing: $required" }
}

# All arguments are paths resolved above; reject command-line delimiters explicitly.
foreach ($value in @($runtime, $pwsh)) {
    if ($value -match '["\r\n]') { throw 'Runtime and PowerShell paths cannot contain quotes or newlines.' }
}
$bridge = Join-Path $runtime 'invoke-hidden.vbs'
$wrapper = Join-Path $runtime 'invoke-sync.ps1'
$actionArguments = '//B //Nologo "{0}" "{1}" -NoProfile -NonInteractive -WindowStyle Hidden -File "{2}"' -f $bridge, $pwsh, $wrapper
$existing = Get-ScheduledTask -TaskPath $taskPath -ErrorAction Stop | Where-Object TaskName -EQ $taskName
if ($existing) {
    $actions = @($existing.Actions)
    if ($actions.Count -ne 1 -or $actions[0].Execute -ine $wscript -or
        $actions[0].Arguments -cne $actionArguments -or $actions[0].WorkingDirectory -ine $repository) {
        throw "Existing '$taskName' has an unknown action; left untouched."
    }
}

for ($probe = $runtime; $probe; $probe = [IO.Path]::GetDirectoryName($probe)) {
    if (Test-Path -LiteralPath $probe) {
        if ((Get-Item -LiteralPath $probe -Force).LinkType) { throw "Runtime must not traverse a link: $probe" }
    }
}
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$backup = Join-Path $runtime ('backups\' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$helperNames = @('sync.py', 'invoke-sync.ps1', 'invoke-hidden.vbs')
$previousFiles = @()
foreach ($name in $helperNames) {
    $path = Join-Path $runtime $name
    if (Test-Path -LiteralPath $path) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Expected a file: $path" }
        Copy-Item -LiteralPath $path -Destination (Join-Path $backup $name)
        $previousFiles += $name
    }
}
ConvertTo-Json -InputObject @($previousFiles) | Set-Content -LiteralPath (Join-Path $backup 'helper-files.json') -Encoding utf8
if ($existing) {
    Export-ScheduledTask -TaskName $taskName -TaskPath $taskPath |
        Set-Content -LiteralPath (Join-Path $backup 'task.xml') -Encoding unicode
}

function Quote-PowerShellLiteral([string]$Value) { "'" + $Value.Replace("'", "''") + "'" }
$wrapperText = @'
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
try {
    & __RUNNER__ -FilePath __PYTHON__ -ArgumentList @('-B', __SYNC__, '--runtime', __RUNTIME__, '--apply') -WorkingDirectory __REPO__
    exit $LASTEXITCODE
} catch {
    ($_ | Out-String) | Add-Content -LiteralPath __LOG__ -Encoding utf8
    exit 2
}
'@
$tokens = @{
    '__RUNNER__' = $hiddenRunner
    '__PYTHON__' = $python
    '__SYNC__' = (Join-Path $runtime 'sync.py')
    '__RUNTIME__' = $runtime
    '__REPO__' = $repository
    '__LOG__' = (Join-Path $runtime 'launcher-error.log')
}
foreach ($token in $tokens.Keys) { $wrapperText = $wrapperText.Replace($token, (Quote-PowerShellLiteral $tokens[$token])) }
$bridgeText = @'
Option Explicit
Dim shell, args, command, i, result
Set shell = CreateObject("WScript.Shell")
Set args = WScript.Arguments
If args.Count = 0 Then WScript.Quit 2
command = ""
For i = 0 To args.Count - 1
    If InStr(args(i), Chr(34)) > 0 Then WScript.Quit 2
    If i > 0 Then command = command & " "
    command = command & Chr(34) & args(i) & Chr(34)
Next
result = shell.Run(command, 0, True)
WScript.Quit result
'@

$registrationAttempted = $false
try {
    # Stop a matching scheduled invocation before replacing its runtime helpers.
    if ($existing) {
        Disable-ScheduledTask -TaskName $taskName -TaskPath $taskPath | Out-Null
        Stop-ScheduledTask -TaskName $taskName -TaskPath $taskPath
    }
    Copy-Item -LiteralPath $source -Destination (Join-Path $runtime 'sync.py') -Force
    Set-Content -LiteralPath $wrapper -Value $wrapperText -Encoding utf8
    Set-Content -LiteralPath $bridge -Value $bridgeText -Encoding ascii
    if (-not (Test-Path -LiteralPath (Join-Path $runtime 'state.json'))) {
        & $hiddenRunner -FilePath $python -ArgumentList @('-B', (Join-Path $runtime 'sync.py'), '--runtime', $runtime, '--enroll', $InitialCommit) -WorkingDirectory $repository
        if ($LASTEXITCODE -ne 0) { throw "Enrollment failed (exit $LASTEXITCODE); inspect $runtime\last-run.json." }
    }
    & $hiddenRunner -FilePath $python -ArgumentList @('-B', (Join-Path $runtime 'sync.py'), '--runtime', $runtime, '--apply') -WorkingDirectory $repository
    if ($LASTEXITCODE -ne 0) { throw "Apply preflight failed (exit $LASTEXITCODE); inspect $runtime\last-run.json." }

    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $periodic = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(30) -RepetitionInterval (New-TimeSpan -Minutes 30)
    $logon = New-ScheduledTaskTrigger -AtLogOn -User $identity
    $principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
    $settings.Enabled = $false
    $action = New-ScheduledTaskAction -Execute $wscript -Argument $actionArguments -WorkingDirectory $repository
    $task = New-ScheduledTask -Action $action -Trigger @($periodic, $logon) -Principal $principal -Settings $settings
    $registrationAttempted = $true
    Register-ScheduledTask -TaskName $taskName -TaskPath $taskPath -InputObject $task -Force | Out-Null
    Enable-ScheduledTask -TaskName $taskName -TaskPath $taskPath | Out-Null
} catch {
    $failure = $_
    foreach ($name in $helperNames) {
        $path = Join-Path $runtime $name
        if ($name -in $previousFiles) {
            Copy-Item -LiteralPath (Join-Path $backup $name) -Destination $path -Force
        } elseif (Test-Path -LiteralPath $path -PathType Leaf) {
            Remove-Item -LiteralPath $path
        }
    }
    if ($existing) {
        Register-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Xml (Get-Content -LiteralPath (Join-Path $backup 'task.xml') -Raw) -Force | Out-Null
    } elseif ($registrationAttempted) {
        Unregister-ScheduledTask -TaskName $taskName -TaskPath $taskPath -Confirm:$false -ErrorAction SilentlyContinue
    }
    throw $failure
}
Write-Output "Enabled '$taskName'. Runtime: $runtime. Backup: $backup"
