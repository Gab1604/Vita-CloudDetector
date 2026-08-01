param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory,

    [string]$ReferencePath = ""
)

$arguments = @(
    "balkan1",
    "--input", $InputPath,
    "--output-dir", $OutputDirectory,
    "--resolution", "10",
    "--threshold", "0.40",
    "--model-version", "4.0",
    "--dtype", "fp32"
)

if ($ReferencePath) {
    $arguments += @("--reference", $ReferencePath)
}

vita-cloud-detector @arguments
