# TOM v3.0 - Git Status Check auf allen Standorten
# Prüft Git-Status auf E:, G: und gibt Zusammenfassung

Write-Host "===== GIT STATUS CHECK =====" -ForegroundColor Cyan
Write-Host ""

$locations = @(
    @{
        Name = "Privat (E:)"
        Path = "E:\_____1111____Projekte-Programmierung\___TelefonAssistent_3.0"
    },
    @{
        Name = "Cloud (G:)"
        Path = "G:\Meine Ablage\_____1111____Projekte-Programmierung\___TelefonAssistent_3.0"
    }
)

foreach ($loc in $locations) {
    Write-Host "--- $($loc.Name) ---" -ForegroundColor Yellow
    Write-Host "Pfad: $($loc.Path)"
    
    if (Test-Path $loc.Path) {
        Push-Location $loc.Path -ErrorAction SilentlyContinue
        
        if ($?) {
            # Git Status
            $gitStatus = git status --short 2>&1
            $branch = git branch --show-current 2>&1
            $commitsAhead = git rev-list --count origin/master..HEAD 2>&1
            
            Write-Host "Branch: $branch" -ForegroundColor Green
            
            if ($commitsAhead -and $commitsAhead -match '^\d+$' -and [int]$commitsAhead -gt 0) {
                Write-Host "Commits ahead of origin/master: $commitsAhead" -ForegroundColor Yellow
            } else {
                Write-Host "Up to date mit origin/master" -ForegroundColor Green
            }
            
            if ($gitStatus) {
                Write-Host "Geaenderte Dateien:" -ForegroundColor White
                $gitStatus
            } else {
                Write-Host "Keine Aenderungen (clean)" -ForegroundColor Green
            }
            
            Pop-Location
        } else {
            Write-Host "Nicht erreichbar oder kein Git Repo" -ForegroundColor Red
        }
    } else {
        Write-Host "Pfad existiert nicht" -ForegroundColor Red
    }
    
    Write-Host ""
}

Write-Host "===== ZUSAMMENFASSUNG =====" -ForegroundColor Cyan
Write-Host ""
Write-Host "Empfehlungen:" -ForegroundColor Yellow
Write-Host "1. Auf lokalem Standort: git add . && git commit -m 'Beschreibung'"
Write-Host "2. Dann: git push origin master"
Write-Host "3. Auf anderen Standorten: git pull origin master"
Write-Host ""

