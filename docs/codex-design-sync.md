# Codex design auto-update

The dedicated **Codex Design Skill Update** Windows task tracks `medking82/skills`
for the local `%USERPROFILE%\.codex\skills\design` package. It runs every 30 minutes
and at current-user logon, only while that user is logged in, with Limited privileges,
StartWhenAvailable, IgnoreNew, and a five-minute execution limit. It does not change
the disabled **Agent SOP Kit Update** shared updater.

From PowerShell 7, after the sync script is present in the canonical checkout:

For a reinstall, first restore Codex and the workstation SOP's
`C:\Users\Marck\.codex\bin\invoke-hidden.ps1`, and clone this repository to
`C:\github\SOP\skills`. If the design package is absent, restore the known source
version below with Codex's bundled installer before enabling the updater:

```powershell
$repo = 'C:\github\SOP\skills'
$python = (Get-Command python.exe -CommandType Application).Source
$runner = Join-Path $env:USERPROFILE '.codex\bin\invoke-hidden.ps1'
$installer = Join-Path $env:USERPROFILE '.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py'
& $runner -FilePath $python -ArgumentList @(
    '-B', $installer, '--repo', 'medking82/skills', '--path', 'skills/design',
    '--ref', '44eaa4f53c294975475417c3473835f2f74f9e12', '--method', 'download'
) -WorkingDirectory $repo
if ($LASTEXITCODE -ne 0) { throw 'Restore failed; do not enable the updater.' }
```

The installer refuses to overwrite an existing package. For an existing install,
use its own source commit for enrollment rather than replacing its files. Download
mode preserves the source bytes, avoiding checkout line-ending conversions.
Then enable the task; its first preflight immediately checks the latest `main`:

```powershell
& C:\github\SOP\skills\scripts\install-codex-design-sync.ps1 -InitialCommit 44eaa4f53c294975475417c3473835f2f74f9e12
# Optional: -PythonPath 'C:\path\to\python.exe'
```

`InitialCommit` must be the full 40-character commit identifying the currently installed design bytes.
Enrollment verifies those bytes against that source archive, and runs only when
`%USERPROFILE%\.codex\design-sync\state.json` is absent. An existing enrollment is
retained. The installer runs an apply preflight before enabling the task. An
unknown existing task with the same name but a different action is left untouched.

The installer copies the trusted local `scripts/sync-codex-design.py` to the fixed
runtime as `sync.py`. The scheduled action uses `wscript.exe` and a tiny VBS bridge
to hide PowerShell; its runtime wrapper launches the actual `python.exe` through
`C:\Users\Marck\.codex\bin\invoke-hidden.ps1`, with the canonical checkout as its
working directory. No interactive window is opened. Keep that checkout and Python
path available. Upgrading the sync implementation requires rerunning the installer.

Updates download source package files; remote scripts are never executed. Only
the design package is updated atomically; new modes are included automatically.
Other skills and `config.toml` are outside this updater's scope. Codex normally
detects skill file changes automatically; the initial configuration restart remains
a one-time step.

On Windows, replacement preserves the existing design directory's DACL and checks
the owner and permission entries of retained paths. If permissions cannot be safely
preserved, the update rolls back and reports `attention` instead of replacing the
installed package. Newly added paths inherit the restored directory permissions.

Inspect `%USERPROFILE%\.codex\design-sync\last-run.json` for `enrolled`, `updated`,
`unchanged`, or `attention`. Success returns 0; errors return 2. Local drift fails
closed instead of overwriting edits. Resolve the reported issue before retrying;
do not delete enrollment state to bypass drift checks. Wrapper startup exceptions
are also recorded in `launcher-error.log`; Task Scheduler exposes the action exit
code. Failed installation restores previous runtime helpers and task registration;
an already successful enrollment or package preflight is not rolled back.

Disable and stop the dedicated task:

```powershell
Disable-ScheduledTask -TaskName 'Codex Design Skill Update'
Stop-ScheduledTask -TaskName 'Codex Design Skill Update'
```

Each installer invocation saves overwritten runtime helpers and any matching task
XML under `design-sync\backups\<UTC timestamp>`. To restore a prior installation,
disable/stop the task above, select its backup, and run:

```powershell
$runtime = Join-Path $env:USERPROFILE '.codex\design-sync'
$backup = Join-Path $runtime 'backups\<UTC timestamp>'
$names = @(Get-Content -LiteralPath (Join-Path $backup 'helper-files.json') -Raw | ConvertFrom-Json)
foreach ($name in @('sync.py', 'invoke-sync.ps1', 'invoke-hidden.vbs')) {
    if ($name -in $names) {
        Copy-Item -LiteralPath (Join-Path $backup $name) -Destination (Join-Path $runtime $name) -Force
    } else {
        Remove-Item -LiteralPath (Join-Path $runtime $name) -ErrorAction SilentlyContinue
    }
}
if (Test-Path -LiteralPath (Join-Path $backup 'task.xml')) {
    Register-ScheduledTask -TaskName 'Codex Design Skill Update' -TaskPath '\' -Xml (Get-Content -LiteralPath (Join-Path $backup 'task.xml') -Raw) -Force
} else {
    Unregister-ScheduledTask -TaskName 'Codex Design Skill Update' -Confirm:$false
}
```

Restoring task XML restores its prior enabled/disabled setting. These commands
restore launcher files and registration only; retain `state.json` and diagnostics.
