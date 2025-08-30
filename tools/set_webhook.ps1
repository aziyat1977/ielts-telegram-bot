param([string]$Token=$env:TELEGRAM_TOKEN,[string]$Base=$env:PUBLIC_APP_URL,[string]$Secret=$env:TELEGRAM_WEBHOOK_SECRET)
if(-not $Token){ throw 'TELEGRAM_TOKEN missing' }
if(-not $Base){ throw 'PUBLIC_APP_URL missing (e.g. https://<app>.fly.dev)' }
if(-not $Secret){ throw 'TELEGRAM_WEBHOOK_SECRET missing' }
$url = ($Base.TrimEnd('/') + '/telegram')
$u = "https://api.telegram.org/bot$Token/setWebhook"
Invoke-RestMethod -Method Post -Uri $u -Body @{
  url = $url
  secret_token = $Secret
  drop_pending_updates = 'true'
  max_connections = 40
  allowed_updates = '["message","callback_query"]'
} -ContentType 'application/x-www-form-urlencoded' -TimeoutSec 30 | ConvertTo-Json -Depth 5