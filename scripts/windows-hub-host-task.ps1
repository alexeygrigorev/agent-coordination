<#
.SYNOPSIS
Installs or previews the Agent Hub Host Task Scheduler logon task for Windows.
#>
param(
    [switch]$Install,
    [switch]$Remove,
    [switch]$ConfirmAction,
    [string]$HubSourceDir = "$env:USERPROFILE\git\agent-hub",
    [string]$PythonExe = "python.exe"
)

$ErrorActionPreference = "Stop"

if (-not $env:APPDATA) {
    Write-Error "APPDATA environment variable is missing. This script requires a full user session."
    exit 1
}

$TaskName = "AgentHubHostDaemon"
$HostDir = Join-Path $HubSourceDir "host"
$ExeArgs = "-m agent_hub_host.agent"

if (-not (Test-Path $HostDir)) {
    Write-Error "Hub source directory '$HostDir' not found. Please provide valid -HubSourceDir."
    exit 1
}

if ($Remove) {
    if (-not $ConfirmAction) {
        Write-Warning "Running with -Remove. Add -ConfirmAction to actually delete the task."
        Write-Output "Would remove Task Scheduler task: $TaskName"
        exit 0
    }
    
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Output "Removed task $TaskName successfully. No other services were modified."
    } else {
        Write-Output "Task $TaskName does not exist."
    }
    exit 0
}

if (-not (Get-Command $PythonExe -ErrorAction SilentlyContinue) -and -not (Test-Path $PythonExe)) {
    Write-Error "PythonExe not found or invalid: $PythonExe"
    exit 1
}

if (-not $Install) {
    Write-Output "=== PREVIEW ONLY ==="
    Write-Output "To install, run with -Install"
    Write-Output "Task Name: $TaskName"
    Write-Output "Executable: $PythonExe"
    Write-Output "Arguments: $ExeArgs"
    Write-Output "Working Directory: $HostDir"
    Write-Output "Trigger: At log on (Current User)"
    Write-Output "Settings: Interactive, Single Instance (IgnoreNew), Bounded Restart"
    exit 0
}

Write-Output "Installing Task Scheduler task: $TaskName..."

# Evidence/Windows API behavior: New-ScheduledTaskAction -Execute takes the executable path as a separate property.
# We do not add literal quotes around `$PythonExe` here because the Task Scheduler API natively handles paths with spaces
# in the Execute property. Adding explicit quotes can cause the task registration to fail or execution to fail.
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument $ExeArgs -WorkingDirectory $HostDir
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -DontStopOnIdleSystem -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew

# Non-admin Interactive logon for current user
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal

Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force

Write-Output "Task $TaskName installed successfully."
