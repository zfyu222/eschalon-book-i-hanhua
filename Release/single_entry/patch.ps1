param([ValidateSet('install','uninstall')][string]$Action,[switch]$NoLaunch)
$ErrorActionPreference='Stop'
$temporary=@()
try {
    $root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
    function Within([string]$base,[string]$relative) {
        if ([IO.Path]::IsPathRooted($relative) -or $relative -match '(^|[/\\])\.\.([/\\]|$)|:') { throw '无效文件路径。' }
        $p=[IO.Path]::GetFullPath((Join-Path $base $relative))
        if (!$p.StartsWith($base.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) { throw '无效文件路径。' }
        return $p
    }
    function Digest($p) {
        if(Test-Path -LiteralPath $p -PathType Leaf) {
            $stream=[IO.File]::OpenRead($p);$algorithm=[Security.Cryptography.SHA256]::Create()
            try { return ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
            finally { $stream.Dispose();$algorithm.Dispose() }
        };return $null
    }
    function SaveState($value) { $value|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $statePath -Encoding UTF8 }
    function CopyChecked($source,$target,$hash) {
        $null=New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target)
        Copy-Item -LiteralPath $source -Destination $target -Force
        if ((Digest $target) -ne $hash) { throw '文件写入失败。' }
    }
    function BuildGfx($deltaPath,$file,$basePath,$baseIndex,$output) {
        $data=[IO.File]::ReadAllBytes($basePath)
        $delta=[IO.BinaryReader]::new([IO.File]::OpenRead($deltaPath))
        try {
            if ([Text.Encoding]::ASCII.GetString($delta.ReadBytes(4)) -cne 'EZG1') { throw '贴图补丁格式不正确。' }
            $count=$delta.ReadUInt32()
            if (!$count -or $count -gt 1024) { throw '贴图补丁目录不正确。' }
            $writer=[IO.File]::Open($output,[IO.FileMode]::Truncate)
            try {
                for ($index=0; $index -lt $count; $index++) {
                    $offsets=@($delta.ReadInt32(),$delta.ReadInt32())
                    $length=$delta.ReadInt32()
                    if ($length -le 0 -or $writer.Position+$length -gt $file.size) { throw '贴图补丁长度不正确。' }
                    $offset=$offsets[$baseIndex]
                    if ($offset -eq -1 -and $offsets[1-$baseIndex] -eq -1) {
                        $bytes=$delta.ReadBytes($length)
                        if ($bytes.Length -ne $length) { throw '贴图补丁内容不完整。' }
                        $writer.Write($bytes,0,$length)
                    } elseif ($offset -ge 0 -and [long]$offset+$length -le $data.Length) {
                        $writer.Write($data,$offset,$length)
                    } else { throw '贴图补丁资源位置不正确。' }
                }
                if ($writer.Position -ne $file.size -or $delta.BaseStream.Position -ne $delta.BaseStream.Length) { throw '贴图补丁文件不完整。' }
            } finally { $writer.Dispose() }
        } finally { $delta.Dispose() }
        if ((Digest $output) -ne $file.sha256) { throw '中文贴图生成校验失败。' }
    }
    $config=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'config.json') -Raw -Encoding UTF8|ConvertFrom-Json
    if ((Digest (Within $root $config.exe)) -ne $config.exe_sha256) { throw '请将补丁解压到受支持版本的游戏目录。' }
    if (@(Get-Process -Name ([IO.Path]::GetFileNameWithoutExtension($config.exe)) -ErrorAction SilentlyContinue).Count) { throw '请先退出游戏，再运行脚本。' }
    $stateDir=Within $root '.zfy-localization';$statePath=Within $stateDir 'state.json'
    $state=$null;if(Test-Path -LiteralPath $statePath) { $state=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8|ConvertFrom-Json }
    $manifest=Get-Content -LiteralPath (Join-Path $root 'PATCH_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json
    $legacyHashes=@{};foreach($known in $config.legacy) { $legacyHashes[($known.path+'|'+$known.sha256)]=$true }
    $originalPaths=@{};foreach($known in $config.originals) { $originalPaths[$known.path]=$true }
    if ($Action -eq 'install') {
        if($state -and $state.status -notin @('installed','uninstalled')) { throw '上次安装未完成，请先运行卸载汉化。' }
        # Complete source and current-state preflight before changing the game.
        $sources=@{}
        foreach($file in $manifest.files) {
            $source=Within $root $file.archive_path
            if ($file.format -eq 'eschalon-gfx-delta-v1') { $archiveHash=$file.archive_sha256 }
            else { $archiveHash=$file.sha256 }
            if((Digest $source) -ne $archiveHash) { throw '补丁文件不完整，请重新解压。' }
            $sources[$file.path]=$source
        }
        if($state -and $state.status -eq 'installed') {
            foreach($r in $state.records) { if((Digest (Within $root $r.path)) -and (Digest (Within $root $r.path)) -ne $r.installed) { throw '安装文件已改变，请先运行卸载汉化。' } }
            foreach($file in $manifest.files) {
                if($file.path -notin @($state.records.path)) {
                    $prior=Digest (Within $root $file.path)
                    if($prior){throw '新安装路径已存在其他文件。'}
                    $state.records+= [pscustomobject]@{path=$file.path;original=$null;installed=$null;previous=$null;restore_steam=$false}
                }
            }
        }
        foreach($file in $manifest.files) {
            if ($file.format -ne 'eschalon-gfx-delta-v1') { continue }
            if ($file.path -ne 'gfx.pak' -or @($file.base_sha256).Count -ne 2) { throw '无效的贴图补丁目标。' }
            $target=Within $root $file.path
            if ((Digest $target) -eq $file.sha256) { $sources[$file.path]=$target; continue }
            $basePath=$null
            $baseIndex=-1
            $cachedBase=Within $stateDir 'base/gfx.pak'
            foreach ($candidate in @((Within $stateDir 'original/gfx.pak'),$target,$cachedBase)) {
                $baseIndex=[Array]::IndexOf([object[]]@($file.base_sha256),(Digest $candidate))
                if ($baseIndex -ge 0) { $basePath=$candidate; break }
            }
            if (!$basePath) { throw '贴图资源版本不受支持，请在 Steam 中验证游戏文件完整性。' }
            $generated=[IO.Path]::GetTempFileName()
            $temporary+=$generated
            BuildGfx $sources[$file.path] $file $basePath $baseIndex $generated
            $sources[$file.path]=$generated
            if ($baseIndex -eq 1 -and $basePath -ne $cachedBase) {
                CopyChecked $basePath $cachedBase $file.base_sha256[$baseIndex]
            }
        }
        if (!$state -or $state.status -ne 'installed') {
            $null=New-Item -ItemType Directory -Force -Path $stateDir
            $records=@()
            foreach($file in $manifest.files) {
                $target=Within $root $file.path;$prior=Digest $target;$legacy=$legacyHashes.ContainsKey($file.path+'|'+$prior)
                $original=$prior
                if($legacy) { $original=$null } elseif($prior) { CopyChecked $target (Within $stateDir ('original/'+$file.path)) $prior }
                $restoreSteam=$legacy -and $originalPaths.ContainsKey($file.path)
                $records+=[pscustomobject]@{path=$file.path;original=$original;installed=$prior;previous=$prior;restore_steam=$restoreSteam}
            }
            $oldLauncher='EschalonBook_Chinese_Launcher.exe'
            $oldLauncherHash=Digest (Within $root $oldLauncher)
            if ($oldLauncher -notin @($manifest.files.path) -and $legacyHashes.ContainsKey($oldLauncher+'|'+$oldLauncherHash)) {
                $records+=[pscustomobject]@{path=$oldLauncher;original=$null;installed=$oldLauncherHash;previous=$oldLauncherHash;restore_steam=$false}
            }
            $state=@{status='installing';records=$records};SaveState $state
        }
        # Persist ALL write intentions before the first write. Uninstall accepts
        # either the previous/original or intended bytes for every path, so a
        # partial install remains recoverable without rewriting the full journal
        # once per payload file (quadratic work on large game patches).
        $recordByPath=@{};foreach($r in $state.records) { $recordByPath[$r.path]=$r }
        foreach($file in $manifest.files) {
            $r=$recordByPath[$file.path];$r.previous=$r.installed;$r.installed=$file.sha256
        }
        $state.status='installing';SaveState $state
        foreach($file in $manifest.files) {
            $target=Within $root $file.path
            if ((Digest $target) -ne $file.sha256) { CopyChecked $sources[$file.path] $target $file.sha256 }
        }
        foreach($r in $state.records) {
            if($r.path -eq 'EschalonBook_Chinese_Launcher.exe' -and $r.path -notin @($manifest.files.path)) {
                $oldTarget=Within $root $r.path
                if(Test-Path -LiteralPath $oldTarget){Remove-Item -LiteralPath $oldTarget -Force}
                $r.previous=$r.installed;$r.installed=$null
            }
        }
        $state.status='installed'
        if ($state -is [System.Collections.IDictionary]) { $state['package_version']=$manifest.version }
        else { $state|Add-Member -NotePropertyName package_version -NotePropertyValue $manifest.version -Force }
        SaveState $state
        Write-Host '汉化安装完成，可以启动游戏。'
    } else {
        if(!$state -or $state.status -eq 'uninstalled') {
            # Legacy root-extraction packages have no installer state.
            $records=@();foreach($file in $manifest.files) {
                $prior=Digest (Within $root $file.path);if(!$prior) { continue }
                $knownMatch=$legacyHashes.ContainsKey($file.path+'|'+$prior)
                if(!$knownMatch) { continue }
                $records+=@{path=$file.path;original=$null;installed=$prior;restore_steam=$originalPaths.ContainsKey($file.path)}
            }
            $state=@{status='installed';records=$records}
        }
        foreach($r in $state.records) {
            $current=Digest (Within $root $r.path)
            if($current -and $current -ne $r.installed -and $current -ne $r.original -and $current -ne $r.previous) { throw '文件已被其他程序修改，暂未卸载。' }
            if($r.original -and (Digest (Within $stateDir ('original/'+$r.path))) -ne $r.original) { throw '还原文件不完整。' }
        }
        $steam=$false
        foreach($r in $state.records) {
            $target=Within $root $r.path
            if($r.original) { CopyChecked (Within $stateDir ('original/'+$r.path)) $target $r.original }
            elseif($r.restore_steam) { $steam=$true }
            elseif(Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Force }
        }
        $null=New-Item -ItemType Directory -Force -Path $stateDir
        $state.status='uninstalled';SaveState $state
        if($steam) {
            if(!$config.steam_app_id -or "$($config.steam_app_id)" -notmatch '^\d+$') { throw '缺少游戏恢复信息。' }
            if(!$NoLaunch) { Start-Process ('steam://validate/'+$config.steam_app_id) -WindowStyle Hidden }
            Write-Host '汉化已停用，Steam 正在恢复游戏文件。'
        } else { Write-Host '汉化卸载完成。' }
        if($NoLaunch) { Write-Output ('STEAM_RESTORE='+$steam) }
    }
} catch { Write-Host $_.Exception.Message;exit 1 }
finally { foreach($path in $temporary) { Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue } }
