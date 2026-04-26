# send_email.ps1 — Sends Spec Proximity refresh summary via open Outlook session

$summaryPath = "$PSScriptRoot\last_run.json"

if (-not (Test-Path $summaryPath)) {
    Write-Host "No summary file found at $summaryPath"
    exit 1
}

$data     = Get-Content $summaryPath -Raw | ConvertFrom-Json
$ts       = $data.timestamp
$specs    = $data.specs
$files    = $data.files
$errors   = $data.errors
$hasError = $errors.Count -gt 0

# ── Build spec table rows ────────────────────────────────────────────────────
$specRows = ""
foreach ($s in $specs) {
    $chgColor = "#888"
    $chgText  = "—"
    if ($null -ne $s.wow_chg_k) {
        if ($s.wow_chg_k -gt 0) { $chgColor = "#4ade80"; $chgText = "+$($s.wow_chg_k)k" }
        elseif ($s.wow_chg_k -lt 0) { $chgColor = "#f87171"; $chgText = "$($s.wow_chg_k)k" }
        else { $chgText = "0.0k" }
    }
    $netColor = if ($s.net_spec_k -gt 0) { "#4ade80" } else { "#f87171" }
    $specRows += @"
    <tr>
      <td style='padding:8px 12px;border-bottom:1px solid #1e3040;color:#bcd4de;font-weight:500'>$($s.ticker)</td>
      <td style='padding:8px 12px;border-bottom:1px solid #1e3040;color:#8aa6b3'>$($s.label)</td>
      <td style='padding:8px 12px;border-bottom:1px solid #1e3040;color:$netColor;font-weight:600;font-family:monospace'>$($s.net_spec_k)k</td>
      <td style='padding:8px 12px;border-bottom:1px solid #1e3040;color:$chgColor;font-family:monospace'>$chgText</td>
      <td style='padding:8px 12px;border-bottom:1px solid #1e3040;color:#5e7b89;font-size:12px'>$($s.latest_cot_date)</td>
    </tr>
"@
}

# ── Build file list ──────────────────────────────────────────────────────────
$fileList = ($files | ForEach-Object { "$($_.name) ($($_.size_kb) KB)" }) -join " &nbsp;·&nbsp; "

# ── Error block ──────────────────────────────────────────────────────────────
$errorBlock = ""
if ($hasError) {
    $errText = ($errors -join "<br>")
    $errorBlock = "<div style='margin-top:16px;padding:12px 16px;background:#3d1a1a;border-left:3px solid #f87171;border-radius:6px;color:#f87171;font-size:13px'><strong>Errors</strong><br>$errText</div>"
}

# ── Status badge ─────────────────────────────────────────────────────────────
$badgeColor = if ($hasError) { "#f87171" } else { "#4ade80" }
$badgeText  = if ($hasError) { "ERRORS" } else { "OK" }
$subject    = if ($hasError) { "Spec Proximity Refresh — ERRORS ($ts)" } else { "Spec Proximity Refresh — OK ($ts)" }

# ── HTML body ────────────────────────────────────────────────────────────────
$body = @"
<div style='font-family:-apple-system,Segoe UI,sans-serif;background:#0d1620;color:#e8eef2;padding:28px;max-width:620px;border-radius:12px'>

  <div style='display:flex;align-items:center;gap:12px;margin-bottom:20px'>
    <span style='font-size:20px;font-weight:300;letter-spacing:-.02em'>Spec <em style='color:#6ab3c9'>Proximity</em></span>
    <span style='margin-left:auto;padding:3px 10px;border-radius:999px;background:$badgeColor;color:#0d1620;font-size:11px;font-weight:700;letter-spacing:.06em'>$badgeText</span>
  </div>

  <p style='font-size:12px;color:#5e7b89;margin-bottom:20px'>Refreshed: $ts</p>

  <table style='width:100%;border-collapse:collapse;background:#15222e;border-radius:8px;overflow:hidden;margin-bottom:16px'>
    <thead>
      <tr style='background:#1e3040'>
        <th style='padding:8px 12px;text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#5e7b89;font-weight:600'>Ticker</th>
        <th style='padding:8px 12px;text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#5e7b89;font-weight:600'>Commodity</th>
        <th style='padding:8px 12px;text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#5e7b89;font-weight:600'>Net Spec</th>
        <th style='padding:8px 12px;text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#5e7b89;font-weight:600'>WoW</th>
        <th style='padding:8px 12px;text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#5e7b89;font-weight:600'>COT Date</th>
      </tr>
    </thead>
    <tbody>
      $specRows
    </tbody>
  </table>

  <p style='font-size:11px;color:#3a5568;margin-bottom:8px'>$fileList</p>

  $errorBlock

  <div style='margin-top:20px;padding-top:16px;border-top:1px solid #1e3040;display:flex;justify-content:space-between;align-items:center'>
    <span style='font-size:11px;color:#3a5568'>ICEBREAKER · HardMiner</span>
    <a href='https://icebreaker-spec-proximity-s5z6seowgfjp677qtwmj3l.streamlit.app/' style='font-size:11px;color:#6ab3c9;text-decoration:none'>Open Dashboard ↗</a>
  </div>
</div>
"@

# ── Send via open Outlook session ────────────────────────────────────────────
try {
    try {
        $outlook = [Runtime.InteropServices.Marshal]::GetActiveObject("Outlook.Application")
    } catch {
        $outlook = New-Object -ComObject Outlook.Application
    }

    $mail             = $outlook.CreateItem(0)
    $mail.To          = "virat.arya@etgworld.com"
    $mail.Subject     = $subject
    $mail.HTMLBody    = $body
    $mail.Send()

    Write-Host "Email sent: $subject"
} catch {
    Write-Host "Email failed: $_"
    exit 1
}
