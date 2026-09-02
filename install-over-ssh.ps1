[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [ValidateNotNullOrEmpty()]
  [string]$DeviceHost = "batocera.local",

  [ValidateNotNullOrEmpty()]
  [string]$SshUser = "root"
)

$ErrorActionPreference = "Stop"
$releaseVersion = "1.8.1"
$installerUrl = "https://raw.githubusercontent.com/HDR-Performance/lan-batocera/v$releaseVersion/standalone-install.sh"
$remoteInstallerPath = "/tmp/lan-batocera-install.sh"

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
  throw "OpenSSH is required. Install the Windows OpenSSH Client optional feature first."
}

$remoteTarget = "$SshUser@$DeviceHost"
$remoteCommand = "curl -fL '$installerUrl' -o '$remoteInstallerPath' && chmod 0700 '$remoteInstallerPath' && '$remoteInstallerPath'"

Write-Host "Installing LAN Batocera v$releaseVersion on $remoteTarget..."
& ssh $remoteTarget $remoteCommand
if ($LASTEXITCODE -ne 0) {
  throw "The remote installer failed with exit code $LASTEXITCODE."
}

Write-Host "LAN Batocera v$releaseVersion installed successfully."
