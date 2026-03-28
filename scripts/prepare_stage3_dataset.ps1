param(
    [string]$ProjectRoot = "C:\Users\User\Desktop\MyProject1",
    [int]$Seed = 42
)

$ErrorActionPreference = "Stop"

$imageRoot = Join-Path $ProjectRoot "DB\images\images"
$xmlRoot = Join-Path $ProjectRoot "DB\label\label"
$outputRoot = Join-Path $ProjectRoot "stage3_outputs"

New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null

$classConfig = @(
    [PSCustomObject]@{ class_id = 1;  xml_label = "1_chongkong"; class_name = "punching_hole" }
    [PSCustomObject]@{ class_id = 2;  xml_label = "2_hanfeng";   class_name = "welding_line" }
    [PSCustomObject]@{ class_id = 3;  xml_label = "3_yueyawan";  class_name = "crescent_gap" }
    [PSCustomObject]@{ class_id = 4;  xml_label = "4_shuiban";   class_name = "water_spot" }
    [PSCustomObject]@{ class_id = 5;  xml_label = "5_youban";    class_name = "oil_spot" }
    [PSCustomObject]@{ class_id = 6;  xml_label = "6_siban";     class_name = "silk_spot" }
    [PSCustomObject]@{ class_id = 7;  xml_label = "7_yiwu";      class_name = "inclusion" }
    [PSCustomObject]@{ class_id = 8;  xml_label = "8_yahen";     class_name = "rolled_pit" }
    [PSCustomObject]@{ class_id = 9;  xml_label = "9_zhehen";    class_name = "crease" }
    [PSCustomObject]@{ class_id = 10; xml_label = "10_yaozhed";  class_name = "waist_folding" }
)

$labelToClass = @{}
foreach ($item in $classConfig) {
    $labelToClass[$item.xml_label] = $item
}

$cleanRows = New-Object System.Collections.Generic.List[object]
$excludedRows = New-Object System.Collections.Generic.List[object]

$imageFiles = Get-ChildItem -Recurse -File $imageRoot | Where-Object { $_.Extension -match '^\.(jpg|jpeg|png|bmp)$' }

foreach ($img in $imageFiles) {
    $xmlPath = Join-Path $xmlRoot ($img.BaseName + ".xml")

    if (-not (Test-Path -LiteralPath $xmlPath)) {
        $excludedRows.Add([PSCustomObject]@{
            image_path = $img.FullName
            source_folder = $img.Directory.Name
            reason = "missing_xml"
            xml_labels = ""
        })
        continue
    }

    $xmlText = Get-Content -Raw -LiteralPath $xmlPath
    $xmlLabels = @(
        [regex]::Matches($xmlText, '<name>([^<]+)</name>') |
        ForEach-Object { $_.Groups[1].Value.Trim() } |
        Sort-Object -Unique
    )

    if ($xmlLabels.Count -ne 1) {
        $excludedRows.Add([PSCustomObject]@{
            image_path = $img.FullName
            source_folder = $img.Directory.Name
            reason = "multi_class"
            xml_labels = ($xmlLabels -join "|")
        })
        continue
    }

    $xmlLabel = $xmlLabels[0]
    if (-not $labelToClass.ContainsKey($xmlLabel)) {
        $excludedRows.Add([PSCustomObject]@{
            image_path = $img.FullName
            source_folder = $img.Directory.Name
            reason = "unknown_label"
            xml_labels = $xmlLabel
        })
        continue
    }

    $classInfo = $labelToClass[$xmlLabel]
    $cleanRows.Add([PSCustomObject]@{
        image_path = $img.FullName
        class_name = $classInfo.class_name
        class_id = $classInfo.class_id
        xml_label = $xmlLabel
        source_folder = $img.Directory.Name
        folder_matches_xml = ($img.Directory.Name -replace ' ', '_') -eq $classInfo.class_name
    })
}

$cleanManifestPath = Join-Path $outputRoot "clean_manifest.csv"
$excludedManifestPath = Join-Path $outputRoot "excluded_manifest.csv"
$classSummaryPath = Join-Path $outputRoot "class_summary.csv"
$splitManifestPath = Join-Path $outputRoot "split_manifest.csv"
$splitSummaryPath = Join-Path $outputRoot "split_summary.csv"
$trainManifestPath = Join-Path $outputRoot "train_manifest.csv"
$valManifestPath = Join-Path $outputRoot "val_manifest.csv"
$testManifestPath = Join-Path $outputRoot "test_manifest.csv"

($cleanRows |
Sort-Object class_id, image_path) |
Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath $cleanManifestPath

($excludedRows |
Sort-Object reason, image_path) |
Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath $excludedManifestPath

$classSummary = $cleanRows |
Group-Object class_id, class_name |
ForEach-Object {
    $row = $_.Group[0]
    [PSCustomObject]@{
        class_id = $row.class_id
        class_name = $row.class_name
        image_count = $_.Count
        folder_match_count = ($_.Group | Where-Object folder_matches_xml).Count
        folder_mismatch_count = ($_.Group | Where-Object { -not $_.folder_matches_xml }).Count
    }
}

($classSummary |
Sort-Object class_id) |
Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath $classSummaryPath

$rng = [System.Random]::new($Seed)
$splitRows = New-Object System.Collections.Generic.List[object]

foreach ($group in ($cleanRows | Group-Object class_id)) {
    $shuffled = $group.Group |
    Sort-Object { $rng.NextDouble() }

    $count = $shuffled.Count
    $trainCount = [int][math]::Floor($count * 0.70)
    $valCount = [int][math]::Floor($count * 0.15)
    $testCount = $count - $trainCount - $valCount

    for ($i = 0; $i -lt $count; $i++) {
        $split = if ($i -lt $trainCount) {
            "train"
        } elseif ($i -lt ($trainCount + $valCount)) {
            "val"
        } else {
            "test"
        }

        $row = $shuffled[$i]
        $splitRows.Add([PSCustomObject]@{
            image_path = $row.image_path
            class_name = $row.class_name
            class_id = $row.class_id
            xml_label = $row.xml_label
            source_folder = $row.source_folder
            folder_matches_xml = $row.folder_matches_xml
            split = $split
        })
    }
}

($splitRows |
Sort-Object split, class_id, image_path) |
Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath $splitManifestPath

$splitRows | Where-Object split -eq "train" | Sort-Object class_id, image_path | Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath $trainManifestPath
$splitRows | Where-Object split -eq "val"   | Sort-Object class_id, image_path | Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath $valManifestPath
$splitRows | Where-Object split -eq "test"  | Sort-Object class_id, image_path | Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath $testManifestPath

$splitSummary = $splitRows |
Group-Object split, class_id, class_name |
ForEach-Object {
    $row = $_.Group[0]
    [PSCustomObject]@{
        split = $row.split
        class_id = $row.class_id
        class_name = $row.class_name
        image_count = $_.Count
    }
}

($splitSummary |
Sort-Object split, class_id) |
Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath $splitSummaryPath

Write-Output "CLEAN_ROWS=$($cleanRows.Count)"
Write-Output "EXCLUDED_ROWS=$($excludedRows.Count)"
Write-Output "OUTPUT_DIR=$outputRoot"
