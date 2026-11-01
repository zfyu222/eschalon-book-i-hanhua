$ErrorActionPreference='Stop'
try {
 $root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
 function Hash($p) { if(Test-Path -LiteralPath $p -PathType Leaf){$stream=[IO.File]::OpenRead($p);$alg=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($alg.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$stream.Dispose();$alg.Dispose()}};return $null }
 $config=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'config.json') -Raw -Encoding UTF8|ConvertFrom-Json
 if((Hash (Join-Path $root $config.exe)) -ne $config.exe_sha256){throw '请将补丁解压到受支持版本的游戏目录。'}
 if(Get-Process -Name ([IO.Path]::GetFileNameWithoutExtension($config.exe)) -ErrorAction SilentlyContinue){throw '游戏已经运行，请先退出。'}
 $manifestPath=Join-Path $root 'PATCH_MANIFEST.json'
 $manifest=Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8|ConvertFrom-Json
 $statePath=Join-Path $root '.zfy-localization/state.json'
 $state=$null;if(Test-Path -LiteralPath $statePath){$state=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8|ConvertFrom-Json}
 $complete=$state -and $state.status -eq 'installed' -and $state.package_version -eq $manifest.version
 foreach($file in $manifest.files){if((Hash (Join-Path $root $file.path)) -ne $file.sha256){$complete=$false}}
 if(!$complete){
  & (Join-Path $env:WINDIR 'System32/WindowsPowerShell/v1.0/powershell.exe') -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'patch.ps1') -Action install -NoLaunch
  if($LASTEXITCODE -ne 0){throw '汉化安装失败，游戏尚未启动。'}
  foreach($file in $manifest.files){if((Hash (Join-Path $root $file.path)) -ne $file.sha256){throw '汉化安装校验失败。'}}
  $state=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8|ConvertFrom-Json
  $state|Add-Member -NotePropertyName package_version -NotePropertyValue $manifest.version -Force
  $state|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $statePath -Encoding UTF8
 }
 $env:ESCHALON_RUNTIME=$root
 Start-Process -FilePath (Join-Path $PSScriptRoot 'runtime/EschalonBook_Chinese_Launcher.exe') -WorkingDirectory $root -WindowStyle Hidden
 exit 0
}catch{Write-Error $_.Exception.Message;exit 1}
