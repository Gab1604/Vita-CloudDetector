param(
    [Parameter(Mandatory = $true)]
    [string]$SafePath,

    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory
)

vita-cloud-detector sentinel2 `
    --input $SafePath `
    --output-dir $OutputDirectory `
    --resolution 10 `
    --threshold 0.40 `
    --model-version 4.0 `
    --dtype fp32
