param(
    [string]$ProjectRoot = "C:\Users\Misha\Documents\GitHub\MyProject1",
    [int]$Seed = 42
)

$ErrorActionPreference = "Stop"
$target = Join-Path $PSScriptRoot '..\stages\stage3\scripts\prepare_stage3_dataset.ps1'
$resolved = (Resolve-Path -LiteralPath $target).Path
& $resolved -ProjectRoot $ProjectRoot -Seed $Seed
