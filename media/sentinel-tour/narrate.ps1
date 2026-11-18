$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$tourScenes = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'scenes.json') -Raw | ConvertFrom-Json
$tourSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$tourSynth.SelectVoice('Microsoft Zira Desktop')
$tourSynth.Rate = 2
try {
  foreach ($tourScene in $tourScenes) {
    $tourAudio = Join-Path $PSScriptRoot "assets/voice-$($tourScene.id).wav"
    $tourSynth.SetOutputToWaveFile($tourAudio)
    $tourSynth.Speak($tourScene.narration)
    $tourSynth.SetOutputToNull()
  }
} finally { $tourSynth.Dispose() }
Write-Output "Generated $($tourScenes.Count) scene narration files."
