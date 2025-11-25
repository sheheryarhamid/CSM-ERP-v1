Param(
  [string]$base = 'main',
  [string]$head = 'prep/secure-blob-stream-pr',
  [string]$title = 'feat: secure blob streaming (chunked AES-GCM)'
)

if (-not $env:GITHUB_TOKEN) {
  Write-Host 'GITHUB_TOKEN not found in environment. This script will only prepare the PR payload.' -ForegroundColor Yellow
  Write-Host 'To create the PR automatically, set $env:GITHUB_TOKEN and re-run this script.' -ForegroundColor Yellow
  exit 0
}

$repo = 'sheheryarhamid/CSM-ERP-v1'
$body = Get-Content -Raw "..\pr_body_secure_blob.md"

$payload = @{
  title = $title
  head  = $head
  base  = $base
  body  = $body
} | ConvertTo-Json -Depth 6

$headers = @{
  Authorization = "token $env:GITHUB_TOKEN"
  Accept = 'application/vnd.github.v3+json'
}

$uri = "https://api.github.com/repos/$repo/pulls"
try {
  $resp = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $payload -ContentType 'application/json'
  Write-Host "PR created: $($resp.html_url)" -ForegroundColor Green
} catch {
  Write-Host 'PR creation failed:' -ForegroundColor Red
  Write-Host $_.Exception.Message
  if ($_.Exception.Response) {
    $r = $_.Exception.Response.GetResponseStream()
    $sr = New-Object System.IO.StreamReader($r)
    Write-Host ($sr.ReadToEnd())
  }
  exit 1
}
