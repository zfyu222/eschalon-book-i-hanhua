Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W5 {
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int w, int h2, uint f);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr e);
  public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
[W5]::SetProcessDPIAware() | Out-Null

function Get-GameWindow {
    $p = Get-Process eschalon_book_1 -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $p) { return $null }
    return $p.MainWindowHandle
}

function Click-Rel($rx, $ry) {
    $h = Get-GameWindow
    if ($h -eq [IntPtr]::Zero) { Write-Output "no window"; return }
    $r = New-Object W5+RECT
    [W5]::GetWindowRect($h, [ref]$r) | Out-Null
    $w = $r.Right - $r.Left; $hh = $r.Bottom - $r.Top
    $x = $r.Left + [int]($w * $rx); $y = $r.Top + [int]($hh * $ry)
    [W5]::SetForegroundWindow($h) | Out-Null
    Start-Sleep -Milliseconds 200
    [W5]::SetCursorPos($x, $y) | Out-Null
    Start-Sleep -Milliseconds 150
    [W5]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 80
    [W5]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)
    Write-Output "clicked at $x,$y (win ${w}x${hh})"
}

function Pin-Window {
    $h = Get-GameWindow
    if ($h -eq [IntPtr]::Zero) { return }
    [W5]::ShowWindow($h, 9) | Out-Null
    [W5]::SetWindowPos($h, [IntPtr](-1), 5, 5, 0, 0, 0x0001 -bor 0x0040) | Out-Null
    [W5]::SetForegroundWindow($h) | Out-Null
    Start-Sleep -Milliseconds 600
}

function Shot($name) {
    Pin-Window
    $h = Get-GameWindow
    if ($h -eq [IntPtr]::Zero) { Write-Output "no window"; return }
    $r = New-Object W5+RECT
    [W5]::GetWindowRect($h, [ref]$r) | Out-Null
    $w = $r.Right - $r.Left; $hh = $r.Bottom - $r.Top
    $bmp = New-Object System.Drawing.Bitmap $w, $hh
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($r.Left, $r.Top, 0, 0, $bmp.Size)
    $out = "D:\StaticHanHua\Projects\EschalonBook\TranslateFiles\reports\$name"
    $bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    Write-Output "shot $name"
}
