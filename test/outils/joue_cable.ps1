# Joue un WAV PCM 16 bits vers le peripherique waveOut dont le nom commence par $dev
# (par defaut "CABLE Input", VB-Cable), sans toucher la sortie par defaut de Windows.
#   powershell -File joue_cable.ps1 -wav boucle-P16.wav [-dev "CABLE Input"]
param([string]$wav, [string]$dev = "CABLE Input")
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Threading;
public static class WO {
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Auto)]
  public struct CAPS { public ushort wMid, wPid; public uint ver; [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string name; public uint fmt; public ushort ch, res; public uint sup; }
  [StructLayout(LayoutKind.Sequential)]
  public struct WFX { public ushort tag, ch; public uint sr, bps; public ushort align, bits, cb; }
  [StructLayout(LayoutKind.Sequential)]
  public struct HDR { public IntPtr data; public uint len, rec; public IntPtr user; public uint flags, loops; public IntPtr next, res; }
  [DllImport("winmm.dll")] public static extern int waveOutGetNumDevs();
  [DllImport("winmm.dll", CharSet=CharSet.Auto)] public static extern int waveOutGetDevCaps(IntPtr id, ref CAPS c, int sz);
  [DllImport("winmm.dll")] public static extern int waveOutOpen(out IntPtr h, IntPtr id, ref WFX f, IntPtr cb, IntPtr inst, int fl);
  [DllImport("winmm.dll")] public static extern int waveOutPrepareHeader(IntPtr h, IntPtr hdr, int sz);
  [DllImport("winmm.dll")] public static extern int waveOutWrite(IntPtr h, IntPtr hdr, int sz);
  [DllImport("winmm.dll")] public static extern int waveOutUnprepareHeader(IntPtr h, IntPtr hdr, int sz);
  [DllImport("winmm.dll")] public static extern int waveOutClose(IntPtr h);
  public static int Find(string pre) { int n = waveOutGetNumDevs(); for (int i = 0; i < n; i++) { var c = new CAPS(); waveOutGetDevCaps((IntPtr)i, ref c, Marshal.SizeOf(c)); if (c.name.StartsWith(pre)) return i; } return -1; }
  public static string Play(byte[] pcm, int sr, int ch, int id) {
    var f = new WFX { tag = 1, ch = (ushort)ch, sr = (uint)sr, bits = 16, align = (ushort)(2 * ch), bps = (uint)(sr * 2 * ch), cb = 0 };
    IntPtr h; int r = waveOutOpen(out h, (IntPtr)id, ref f, IntPtr.Zero, IntPtr.Zero, 0); if (r != 0) return "open " + r;
    IntPtr buf = Marshal.AllocHGlobal(pcm.Length); Marshal.Copy(pcm, 0, buf, pcm.Length);
    var hd = new HDR { data = buf, len = (uint)pcm.Length };
    IntPtr ph = Marshal.AllocHGlobal(Marshal.SizeOf(hd)); Marshal.StructureToPtr(hd, ph, false);
    waveOutPrepareHeader(h, ph, Marshal.SizeOf(hd)); waveOutWrite(h, ph, Marshal.SizeOf(hd));
    while (true) { hd = (HDR)Marshal.PtrToStructure(ph, typeof(HDR)); if ((hd.flags & 1) != 0) break; Thread.Sleep(50); }
    waveOutUnprepareHeader(h, ph, Marshal.SizeOf(hd)); waveOutClose(h); Marshal.FreeHGlobal(buf); Marshal.FreeHGlobal(ph); return "ok";
  }
}
"@
$b = [IO.File]::ReadAllBytes($wav)
$ch = [BitConverter]::ToUInt16($b, 22); $sr = [BitConverter]::ToInt32($b, 24)
$i = 12; while ([Text.Encoding]::ASCII.GetString($b, $i, 4) -ne 'data') { $i += 8 + [BitConverter]::ToInt32($b, $i + 4) }
$n = [BitConverter]::ToInt32($b, $i + 4); $pcm = New-Object byte[] $n; [Array]::Copy($b, $i + 8, $pcm, 0, $n)
$id = [WO]::Find($dev); if ($id -lt 0) { "peripherique $dev introuvable"; exit 1 }
"device $id sr $sr ch $ch octets $n"
[WO]::Play($pcm, $sr, $ch, $id)
