param(
  [double]$olat = 28.5383,   # Orlando
  [double]$olon = -81.3792,
  [double]$dlat = 27.9506,   # Tampa
  [double]$dlon = -82.4572
)
$body = @{
  origin = @{ lat = $olat; lon = $olon }
  destination = @{ lat = $dlat; lon = $dlon }
  timestamp = $null
} | ConvertTo-Json -Depth 4
$resp = Invoke-WebRequest -Uri 'http://localhost:8000/trip/brief' -Method POST -Body $body -ContentType 'application/json' -UseBasicParsing -TimeoutSec 120
$resp.Content | Out-File -Encoding utf8 -NoNewline 'scripts\trip-brief-sample.json'
"len=$($resp.Content.Length)"
