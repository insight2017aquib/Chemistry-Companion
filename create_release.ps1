$token = "REMOVED"
$headers = @{
    Authorization = "Bearer $token"
    Accept = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

$body = @{
    tag_name = "v1.1.0"
    name = "Chemistry Companion v1.1.0"
    body = "Fixed Proton NMR frontend integration
Fixed Carbon NMR frontend integration
Resolved frontend-backend schema mismatch
Improved GUI integration reliability
Added regression test coverage
Added API contract testing
Improved Open Babel isolation boundaries
Improved batch processing robustness
Frontend wiring stabilization
NMR rendering fixes"
    draft = $false
    prerelease = $false
} | ConvertTo-Json

Invoke-RestMethod -Uri "https://api.github.com/repos/insight2017aquib/Chemistry-Companion/releases" -Method Post -Headers $headers -Body $body -ContentType "application/json"
