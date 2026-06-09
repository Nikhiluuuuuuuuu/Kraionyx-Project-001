$dir = "d:\Downloads\creative\Kraionyx-Project-001"
$files = Get-ChildItem -Path $dir -File -Recurse | Where-Object { $_.DirectoryName -notmatch "\\\.git" -and $_.DirectoryName -notmatch "\\certs" }
foreach ($f in $files) {
    if ($f.Name -match "Dockerfile" -or $f.Name -match "Makefile" -or $f.Name -match "\.gitignore" -or $f.Extension -match "\.(md|yml|yaml|sh|go|py|env|example|proto|tpl|json|txt|conf|mod|sum)$") {
        $path = $f.FullName
        try {
            $content = [System.IO.File]::ReadAllText($path)
            if ($content -cmatch "kraionyx" -or $content -cmatch "Kraionyx" -or $content -cmatch "KRAIONYX") {
                $content = $content -creplace "kraionyx", "svaani" -creplace "Kraionyx", "Svaani" -creplace "KRAIONYX", "SVAANI"
                [System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding($false)))
            }
        } catch {}
    }
}

$helmDir = Join-Path $dir "deploy\helm"
if (Test-Path (Join-Path $helmDir "kraionyx")) {
    Rename-Item -Path (Join-Path $helmDir "kraionyx") -NewName "svaani"
}
$helmSvaani = Join-Path $helmDir "svaani"
if (Test-Path $helmSvaani) {
    Get-ChildItem -Path $helmSvaani -File -Recurse | Where-Object { $_.Name -match "kraionyx" } | ForEach-Object {
        $newName = $_.Name -creplace "kraionyx", "svaani" -creplace "Kraionyx", "Svaani" -creplace "KRAIONYX", "SVAANI"
        Rename-Item -Path $_.FullName -NewName $newName
    }
}

$protoDir = Join-Path $dir "proto"
if (Test-Path (Join-Path $protoDir "kraionyx")) {
    Rename-Item -Path (Join-Path $protoDir "kraionyx") -NewName "svaani"
}
$protoSvaani = Join-Path $protoDir "svaani"
if (Test-Path $protoSvaani) {
    Get-ChildItem -Path $protoSvaani -File -Recurse | Where-Object { $_.Name -match "kraionyx" } | ForEach-Object {
        $newName = $_.Name -creplace "kraionyx", "svaani" -creplace "Kraionyx", "Svaani" -creplace "KRAIONYX", "SVAANI"
        Rename-Item -Path $_.FullName -NewName $newName
    }
}

Get-ChildItem -Path (Join-Path $dir "services") -Filter "Dockerfile.gpu" -Recurse | Remove-Item -Force
