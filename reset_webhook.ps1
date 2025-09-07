param(
  [string]$Action = "reset" # or "delete"
)
$Token = $env:TELEGRAM_BOT_TOKEN
$Secret = $env:TELEGRAM_SECRET_TOKEN
$Service = $env:TG_WEBHOOK
if (-not $Token -or -not $Secret -or -not $Service) { Write-Error "Missing env vars."; exit 1 }
$svc = gcloud run services describe $Service --region $env:RUN_REGION --project $env:PROJECT --format=json | ConvertFrom-Json
$Url = ($svc.status.url).TrimEnd("/") + "/tg/webhook"
if ($Action -eq "delete") {
  Invoke-WebRequest "https://api.telegram.org/bot$Token/deleteWebhook" -UseBasicParsing
  Write-Host "Webhook deleted."
} elseif ($Action -eq "reset") {
  $body = @{ url = $Url; secret_token = $Secret } | ConvertTo-Json
  Invoke-WebRequest "https://api.telegram.org/bot$Token/setWebhook" -Method Post -ContentType "application/json" -Body $body -UseBasicParsing
  Write-Host "Webhook reset → response above."
}
