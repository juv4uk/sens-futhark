$ErrorActionPreference = 'Stop'
$SourceRoot = $PSScriptRoot
$InstallRoot = Join-Path $env:USERPROFILE 'sens-gpu-runner'
$Task = 'SENS GPU Runner'

New-Item -ItemType Directory -Force $InstallRoot | Out-Null
Copy-Item (Join-Path $SourceRoot 'worker.py') (Join-Path $InstallRoot 'worker.py') -Force
Copy-Item (Join-Path $SourceRoot 'client.py') (Join-Path $InstallRoot 'client.py') -Force

$Pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $Pythonw) {
    $Python = (Get-Command python.exe -ErrorAction Stop).Source
    $Pythonw = Join-Path (Split-Path $Python) 'pythonw.exe'
}
if (-not (Test-Path $Pythonw)) { throw "pythonw.exe not found: $Pythonw" }

$Worker = Join-Path $InstallRoot 'worker.py'
$Action = New-ScheduledTaskAction -Execute $Pythonw -Argument ('"' + $Worker + '"') -WorkingDirectory $InstallRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $Task -Action $Action -Trigger $Trigger -Settings $Settings -Description 'Local SENS CUDA worker. IPC is localhost-only; admitted numerical work executes on CUDA.' -Force | Out-Null
Start-ScheduledTask -TaskName $Task
Write-Output "TASK_INSTALLED=$Task"
Write-Output "INSTALL_ROOT=$InstallRoot"
