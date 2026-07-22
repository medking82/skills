[CmdletBinding()]
param(
    [switch]$Execute,
    [string]$TaskName = 'Apple Design Skill Update',
    [ValidatePattern('^([01]\d|2[0-3]):[0-5]\d$')]
    [string]$At = '06:30'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$wrapper = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'invoke-apple-design-update.ps1')).Path
$powerShellCommand = Get-Command pwsh -ErrorAction SilentlyContinue
if (-not $powerShellCommand) { $powerShellCommand = Get-Command powershell -ErrorAction Stop }
$arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$wrapper`" -Mode Check"
$runAt = [DateTime]::Today.Add([TimeSpan]::ParseExact($At, 'hh\:mm', [Globalization.CultureInfo]::InvariantCulture))

Write-Output "APPLE_DESIGN_TASK name=$TaskName schedule=daily@$At mode=Check"
Write-Output "APPLE_DESIGN_TASK executable=$($powerShellCommand.Source)"
Write-Output "APPLE_DESIGN_TASK arguments=$arguments"
if (-not $Execute) {
    Write-Output 'APPLE_DESIGN_TASK status=preview-only'
    exit 0
}

Import-Module ScheduledTasks -ErrorAction Stop
$action = New-ScheduledTaskAction -Execute $powerShellCommand.Source -Argument $arguments -WorkingDirectory (Split-Path $PSScriptRoot -Parent)
$trigger = New-ScheduledTaskTrigger -Daily -At $runAt
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Checks medking82/skills for apple-design drift; never applies updates.'
Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null

$installed = Get-ScheduledTask -TaskName $TaskName
$installedArguments = @($installed.Actions | ForEach-Object Arguments) -join ' '
if ($installedArguments -notmatch '(?i)-Mode\s+Check' -or $installedArguments -match '(?i)-Mode\s+Apply') {
    throw 'Registered task is not check-only'
}
Write-Output 'APPLE_DESIGN_TASK status=registered-check-only'
