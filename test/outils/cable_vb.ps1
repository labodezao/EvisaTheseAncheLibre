# Active (1) ou desactive (0) un point audio de Windows, comme le panneau Son, sans droits
# administrateur (IPolicyConfig::SetEndpointVisibility, interface non documentee de Windows).
#   powershell -File cable_vb.ps1 -id "{0.0.0.00000000}.{guid}" -visible 1
# Les identifiants : HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render|Capture\{guid}
# (rendu : {0.0.0.00000000}, capture : {0.0.1.00000000}). DeviceState 1 = actif, 0x10000001 = desactive.
# Noter l'etat d'origine avant, le remettre apres. Ne change pas les peripheriques par defaut.
param([string]$id, [int]$visible)
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
[Guid("f8679f50-850a-41cf-9c72-430f290290c8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IPolicyConfig {
  [PreserveSig] int GetMixFormat([MarshalAs(UnmanagedType.LPWStr)] string id, IntPtr p);
  [PreserveSig] int GetDeviceFormat([MarshalAs(UnmanagedType.LPWStr)] string id, int b, IntPtr p);
  [PreserveSig] int ResetDeviceFormat([MarshalAs(UnmanagedType.LPWStr)] string id);
  [PreserveSig] int SetDeviceFormat([MarshalAs(UnmanagedType.LPWStr)] string id, IntPtr a, IntPtr b);
  [PreserveSig] int GetProcessingPeriod([MarshalAs(UnmanagedType.LPWStr)] string id, int b, IntPtr a, IntPtr c);
  [PreserveSig] int SetProcessingPeriod([MarshalAs(UnmanagedType.LPWStr)] string id, IntPtr a);
  [PreserveSig] int GetShareMode([MarshalAs(UnmanagedType.LPWStr)] string id, IntPtr a);
  [PreserveSig] int SetShareMode([MarshalAs(UnmanagedType.LPWStr)] string id, IntPtr a);
  [PreserveSig] int GetPropertyValue([MarshalAs(UnmanagedType.LPWStr)] string id, IntPtr k, IntPtr v);
  [PreserveSig] int SetPropertyValue([MarshalAs(UnmanagedType.LPWStr)] string id, IntPtr k, IntPtr v);
  [PreserveSig] int SetDefaultEndpoint([MarshalAs(UnmanagedType.LPWStr)] string id, int role);
  [PreserveSig] int SetEndpointVisibility([MarshalAs(UnmanagedType.LPWStr)] string id, int visible);
}
[ComImport, Guid("870af99c-171d-4f9e-af0d-e63df40c2bc9")] class CPolicyConfigClient {}
public static class Pol {
  public static int Vis(string id, int v) { var p = (IPolicyConfig)new CPolicyConfigClient(); return p.SetEndpointVisibility(id, v); }
}
"@
"{0:X8}" -f [Pol]::Vis($id, $visible)
