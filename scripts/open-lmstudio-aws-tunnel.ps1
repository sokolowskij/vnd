<#
Exposes LM Studio running on this Windows machine to the AWS server.

Keep this PowerShell window open while running the AWS pipeline script.
LM Studio must be running locally with its server enabled on port 1234.
#>

[CmdletBinding()]
param(
    [string]$Key = "$env:USERPROFILE\.ssh\vnd_aws",
    [string]$Server = "ubuntu@51.102.104.11",
    [int]$LocalPort = 1234,
    [int]$RemotePort = 1234
)

$ErrorActionPreference = "Stop"

Write-Host "Opening reverse tunnel:"
Write-Host "  AWS 127.0.0.1:$RemotePort -> local 127.0.0.1:$LocalPort"
Write-Host "Keep this window open while AWS processes products."

ssh -i $Key `
    -N `
    -o ExitOnForwardFailure=yes `
    -R "127.0.0.1:${RemotePort}:127.0.0.1:${LocalPort}" `
    $Server
