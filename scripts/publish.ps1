# Run from a normal authenticated terminal if this workspace cannot reach GitHub.
# Creates a fresh checkout and a normal commit; never force-pushes or rewrites history.
$ErrorActionPreference = 'Stop'
$sourceRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$manifestPath = Join-Path $sourceRoot 'delivery-manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw 'Falta delivery-manifest.json. Ejecuta python scripts/package.py antes de publicar.'
}
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
if ($manifest.repository -ne 'https://github.com/Baneado85/GeoPredIA.git' -or $manifest.branch -ne 'main') {
    throw 'El destino no coincide con el repositorio autorizado.'
}
function Invoke-CheckedGit {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArguments)
    & git @GitArguments
    if ($LASTEXITCODE -ne 0) { throw 'Git no pudo completar la operación. No se continuará ni se forzará el push.' }
}
$name = & git config --get user.name
$email = & git config --get user.email
if (-not $name -or -not $email) {
    throw 'Configura tu identidad de Git (user.name y user.email) antes de publicar. No se añadirá una identidad de IA.'
}
foreach ($entry in $manifest.files) {
    $relative = [string]$entry.path
    if ($relative -match '(^|/)(\.git|\.env|secrets\.h|\.local|node_modules|__pycache__)(/|$)' -or [IO.Path]::IsPathRooted($relative)) {
        throw "Ruta excluida de publicación: $relative"
    }
    $source = [IO.Path]::GetFullPath((Join-Path $sourceRoot $relative))
    if (-not $source.StartsWith($sourceRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'El manifiesto contiene una ruta fuera del proyecto.'
    }
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) {
        throw "Cambió el archivo $relative. Vuelve a generar el paquete antes de publicar."
    }
}
$checkoutName = 'GeoPredIA-publicacion-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss')
$checkout = Join-Path (Split-Path -Parent $sourceRoot) $checkoutName
if (Test-Path -LiteralPath $checkout) { throw 'La carpeta de publicación ya existe. No se sobrescribirá.' }
Invoke-CheckedGit clone --branch main --single-branch $manifest.repository $checkout
$baseCommit = (& git -C $checkout rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $baseCommit -ne $manifest.base_commit) {
    throw 'GitHub tiene cambios posteriores a la versión revisada. Conservamos el checkout; hay que integrar esos cambios antes de publicar.'
}
foreach ($entry in $manifest.files) {
    $destination = [IO.Path]::GetFullPath((Join-Path $checkout $entry.path))
    if (-not $destination.StartsWith($checkout + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Destino fuera del checkout.'
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $sourceRoot $entry.path) -Destination $destination
    if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) {
        throw "El archivo $($entry.path) cambió durante la preparación. No se publicará este checkout."
    }
}
Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $checkout 'delivery-manifest.json')
Invoke-CheckedGit -C $checkout add --all
Invoke-CheckedGit -C $checkout diff --cached --stat
Invoke-CheckedGit -C $checkout commit -m 'feat: implementar GeoPredIA con agentes, frontend, IoT e integraciones SAP'
Invoke-CheckedGit -C $checkout push origin main
Write-Host 'Publicado en https://github.com/Baneado85/GeoPredIA con tu identidad de Git.'
