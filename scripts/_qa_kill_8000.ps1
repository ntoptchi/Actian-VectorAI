$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
  $procId = $conn[0].OwningProcess
  Stop-Process -Id $procId -Force
  Start-Sleep -Seconds 2
}
(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count
