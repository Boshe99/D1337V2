# Anonymize Lobe Chat Repository
# Rewrite semua authors menjadi anonymous

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Anonymize Lobe Chat - Rewrite All Authors" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check if in correct directory
if (-not (Test-Path ".git")) {
    Write-Host "❌ Not a git repository!" -ForegroundColor Red
    Write-Host "Run this script from inside the lobe-chat directory" -ForegroundColor Yellow
    exit
}

Write-Host "Current directory: $(Get-Location)" -ForegroundColor Green
Write-Host ""

# Legal warning
Write-Host "⚠️  LEGAL WARNING:" -ForegroundColor Yellow
Write-Host "• This will rewrite ALL commit history" -ForegroundColor Yellow
Write-Host "• All authors will be changed to Anonymous" -ForegroundColor Yellow
Write-Host "• This cannot be easily undone" -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Continue? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Aborted." -ForegroundColor Red
    exit
}

# Get author info
Write-Host ""
Write-Host "Enter new author info (or press Enter for Anonymous):" -ForegroundColor Green
$newName = Read-Host "Author name (default: Anonymous)"
if ([string]::IsNullOrWhiteSpace($newName)) {
    $newName = "Anonymous"
}

$newEmail = Read-Host "Author email (default: anonymous@example.com)"
if ([string]::IsNullOrWhiteSpace($newEmail)) {
    $newEmail = "anonymous@example.com"
}

Write-Host ""
Write-Host "New author: $newName <$newEmail>" -ForegroundColor Cyan
Write-Host ""

# Step 1: Remove origin
Write-Host "[1/5] Removing origin remote..." -ForegroundColor Green
git remote remove origin 2>$null
Write-Host "✅ Origin removed" -ForegroundColor Green

# Step 2: Change config
Write-Host "[2/5] Changing git configuration..." -ForegroundColor Green
git config user.name $newName
git config user.email $newEmail
Write-Host "✅ Config updated" -ForegroundColor Green

# Step 3: Rewrite history
Write-Host "[3/5] Rewriting commit history..." -ForegroundColor Green
Write-Host "This may take a while for large repositories..." -ForegroundColor Yellow
Write-Host ""

$env:GIT_AUTHOR_NAME = $newName
$env:GIT_AUTHOR_EMAIL = $newEmail
$env:GIT_COMMITTER_NAME = $newName
$env:GIT_COMMITTER_EMAIL = $newEmail

git filter-branch --env-filter "export GIT_AUTHOR_NAME='$newName'; export GIT_AUTHOR_EMAIL='$newEmail'; export GIT_COMMITTER_NAME='$newName'; export GIT_COMMITTER_EMAIL='$newEmail'" --tag-name-filter cat -- --all

Write-Host ""
Write-Host "✅ History rewritten" -ForegroundColor Green

# Step 4: Cleanup
Write-Host "[4/5] Cleaning up traces..." -ForegroundColor Green
git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin 2>$null
git reflog expire --expire=now --all 2>$null
git gc --prune=now --aggressive --quiet 2>$null
Write-Host "✅ Cleanup complete" -ForegroundColor Green

# Step 5: Verification
Write-Host "[5/5] Verifying..." -ForegroundColor Green
$authors = git log --format='%an <%ae>' | Select-Object -Unique
$authorCount = ($authors | Measure-Object).Count

Write-Host ""
Write-Host "Authors found: $authorCount" -ForegroundColor Cyan
if ($authorCount -eq 1) {
    Write-Host "✅ All authors anonymized: $authors" -ForegroundColor Green
} else {
    Write-Host "⚠️  Multiple authors found:" -ForegroundColor Yellow
    $authors | ForEach-Object { Write-Host "  $_" }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ Anonymization Complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Add your remote: git remote add origin https://github.com/Boshe99/D1337V2.git"
Write-Host "2. Push: git push -u origin main"
Write-Host ""
