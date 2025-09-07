param(
  [string]$Action = "reset" # or "delete"
)
$Project = if ($env:PROJECT) { $env:PROJECT } else { (gcloud config get-value core/project --quiet).Trim() }
$Region  = if ($env:RUN_REGION) { $env:RUN_REGION } else { "us-central1" }
$Service = if ($env:TG_WEBHOOK) { $env:TG_WEBHOOK } else { "tg-webhook" }

$Token = $env:TELEGRAM_BOT_TOKEN
if (-not $Token) { $Token = Read-Host -AsSecureString -Prompt "Enter TELEGRAM_BOT_TOKEN (hidden)"; 
  $ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($Token)
  $Token=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

$svc = gcloud run services describe $Service --region $Region --project $Project --format=json | ConvertFrom-Json
if (-not $svc) { Write-Error "Service not found."; exit 1 }
$BASE = $svc.status.url.TrimEnd("/")
# Extract TELEGRAM_SECRET_TOKEN from env
$Secret = ""
try{
  $envs = $svc.spec.template.spec.containers[0].env
  foreach($e in $envs){ if($e.name -eq "TELEGRAM_SECRET_TOKEN"){ $Secret=$e.value; break } }
}catch{}
if (-not $Secret) { Write-Error "Secret not found in service env."; exit 1 }

if ($Action -eq "delete") {
  Invoke-WebRequest "https://api.telegram.org/bot$Token/deleteWebhook" -UseBasicParsing | Out-Null
  Write-Host "Webhook deleted."
} else {
  $body = @{ url = "$BASE/tg/webhook"; secret_token = $Secret } | ConvertTo-Json
  Invoke-WebRequest "https://api.telegram.org/bot$Token/setWebhook" -Method Post -ContentType "application/json" -Body $body -UseBasicParsing | Out-Null
  Write-Host "Webhook reset."
}
