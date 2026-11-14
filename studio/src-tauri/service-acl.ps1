# TAMGA himoyalangan rejimi: %ProgramData%\TAMGA ni xavfsiz tayyorlash (o'rnatuvchi administrator
# sifatida chaqiradi, `tamgad` xizmati yaratilgandan keyin).
#
# Muammo: %ProgramData% da oddiy foydalanuvchi ham papka yarata oladi. O'rnatuvchi administrator
# huquqida ishlaydi — agar u foydalanuvchi oldindan tayyorlagan papkaga (ichida junction/symlink yoki
# begona fayllar bilan) ishonib, rekursiv ACL qo'ysa, tizim fayllarining ACL'ini buzishi yoki
# foydalanuvchiga tegishli faylni "himoyalangan" deb qabul qilishi mumkin edi. Shuning uchun:
#   1. mavjud papka faqat ISHONCHLI bo'lsa saqlanadi (egasi administratorlar/SYSTEM, hech qayerda
#      reparse point yo'q, administratorlar/SYSTEM/xizmatdan boshqa hech kimda yozish huquqi yo'q —
#      ya'ni oldingi o'rnatish qo'ygan holat buzilmagan); aks holda u chetga olinadi;
#   2. yangi papka darhol himoyalangan DACL bilan yaratiladi (yaratish va ACL orasida oyna yo'q);
#   3. hech qanday amal reparse point ortidan yurmaydi; oxirida butun daraxt qayta tekshiriladi.
#
# Chiqish kodlari: 0 — tayyor; 10 — ishonchsiz papkani chetga olib bo'lmadi; 11 — yaratilgan papka
# ishonchsiz (poyga); 12 — yakuniy tekshiruv; 13 — boshqa xato.
#
# `-Root` va `-ServiceSid` — faqat sinov uchun (o'rnatuvchi ularni bermaydi).
param(
    [Parameter(Mandatory)][string]$InstallDir,
    [string]$Root,
    [string]$ServiceSid
)
$ErrorActionPreference = 'Stop'

$ReparsePoint = [IO.FileAttributes]::ReparsePoint
$SY = New-Object Security.Principal.SecurityIdentifier 'S-1-5-18'
$BA = New-Object Security.Principal.SecurityIdentifier 'S-1-5-32-544'
$BU = New-Object Security.Principal.SecurityIdentifier 'S-1-5-32-545'
# Yozish, qo'shish, o'chirish, atribut/ACL/egani o'zgartirish va umumiy yozish/to'liq huquqlar.
$WriteMask = 0x2 -bor 0x4 -bor 0x10 -bor 0x40 -bor 0x100 -bor 0x10000 -bor 0x40000 -bor 0x80000 -bor 0x40000000 -bor 0x10000000
$Closed = 'secrets', 'vault', 'spool'
$Subdirs = 'logs', 'policies', 'vault', 'secrets', 'spool'

function Get-Root {
    if ($Root) { return $Root }
    # Muhit o'zgaruvchisi emas (`tamga_win::service::program_data` bilan bir xil manba).
    Join-Path ([Environment]::GetFolderPath('CommonApplicationData')) 'TAMGA'
}

# Nom band-mi (osilib qolgan symlink ham hisob: Test-Path uni "yo'q" deydi).
function Test-Entry([string]$path) {
    [bool](Get-ChildItem -LiteralPath (Split-Path -Parent $path) -Force -Filter (Split-Path -Leaf $path) -ErrorAction SilentlyContinue)
}

function New-Dacl([bool]$usersRead, $svc) {
    $sd = New-Object Security.AccessControl.DirectorySecurity
    $sd.SetOwner($BA)
    $sd.SetAccessRuleProtection($true, $false)
    $inh = [Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
    $none = [Security.AccessControl.PropagationFlags]::None
    $allow = [Security.AccessControl.AccessControlType]::Allow
    $full = [Security.AccessControl.FileSystemRights]::FullControl
    $sd.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule $SY, $full, $inh, $none, $allow))
    $sd.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule $BA, $full, $inh, $none, $allow))
    $sd.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule $svc, ([Security.AccessControl.FileSystemRights]::Modify), $inh, $none, $allow))
    if ($usersRead) {
        $sd.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule $BU, ([Security.AccessControl.FileSystemRights]::ReadAndExecute), $inh, $none, $allow))
    }
    $sd
}

# Daraxt ishonchlimi. Reparse point ortidan yurmaydi (ularning o'zi ishonchsizlik belgisi).
function Test-Trusted([string]$root, $svc) {
    $queue = New-Object Collections.Queue
    $queue.Enqueue((Get-Item -LiteralPath $root -Force))
    while ($queue.Count) {
        $item = $queue.Dequeue()
        if ($item.Attributes -band $ReparsePoint) { return "reparse: $($item.FullName)" }
        if (-not $item.PSIsContainer) { continue }
        $acl = Get-Acl -LiteralPath $item.FullName
        $owner = $acl.GetOwner([Security.Principal.SecurityIdentifier])
        if ($owner -ne $BA -and $owner -ne $SY) { return "egasi $owner : $($item.FullName)" }
        $rel = $item.FullName.Substring($root.Length).TrimStart('\')
        $closed = $Closed -contains ($rel -split '\\')[0]
        foreach ($rule in $acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])) {
            $sid = $rule.IdentityReference
            if ($rule.AccessControlType -ne 'Allow' -or $sid -eq $SY -or $sid -eq $BA -or $sid -eq $svc) { continue }
            if ($closed -or ([int64]$rule.FileSystemRights -band $WriteMask)) {
                return "ruxsat $sid ($($rule.FileSystemRights)) : $($item.FullName)"
            }
        }
        Get-ChildItem -LiteralPath $item.FullName -Force | ForEach-Object { $queue.Enqueue($_) }
    }
    $null
}

try {
    $svc = if ($ServiceSid) {
        New-Object Security.Principal.SecurityIdentifier $ServiceSid
    } else {
        (New-Object Security.Principal.NTAccount 'NT SERVICE\tamgad').Translate([Security.Principal.SecurityIdentifier])
    }
    $root = Get-Root

    if (Test-Entry $root) {
        $why = Test-Trusted $root $svc
        if ($why) {
            Write-Output "ishonchsiz mavjud papka chetga olinadi: $why"
            try {
                Rename-Item -LiteralPath $root ('TAMGA.untrusted-' + (Get-Date -Format yyyyMMddHHmmss))
            } catch {
                Write-Output "chetga olib bo'lmadi: $_"
                exit 10
            }
        }
    }
    if (-not (Test-Entry $root)) {
        # Yaratish bilan bir vaqtda himoyalangan DACL: oraliqda foydalanuvchi ichiga hech narsa qo'ya olmaydi.
        [void][IO.Directory]::CreateDirectory($root, (New-Dacl $true $svc))
    }
    # Poyga: chetga olish va yaratish orasida foydalanuvchi o'z papkasini qo'ygan bo'lishi mumkin.
    $why = Test-Trusted $root $svc
    if ($why) {
        Write-Output "papka ishonchsiz: $why"
        exit 11
    }

    # Ildiz ishonchli — endi uning ichiga faqat administratorlar yoza oladi.
    (Get-Item -LiteralPath $root).SetAccessControl((New-Dacl $true $svc))
    foreach ($d in $Subdirs) {
        $p = Join-Path $root $d
        $dacl = New-Dacl (-not ($Closed -contains $d)) $svc
        if (Test-Path -LiteralPath $p) {
            (Get-Item -LiteralPath $p -Force).SetAccessControl($dacl)
        } else {
            [void][IO.Directory]::CreateDirectory($p, $dacl)
        }
    }

    $why = Test-Trusted $root $svc
    if ($why) {
        Write-Output "yakuniy tekshiruv: $why"
        exit 12
    }

    # Belgi: mijozlar (hook, CLI, Studio) himoyalangan rejimni shundan biladi. Ildiz ACL'ini meros oladi.
    $marker = @{ mode = 'service'; pipe = 'tamga-service'; install_dir = $InstallDir } | ConvertTo-Json
    [IO.File]::WriteAllText((Join-Path $root 'service.json'), $marker, (New-Object Text.UTF8Encoding $false))
    Write-Output "tayyor: $root"
    exit 0
} catch {
    Write-Output "xato: $_"
    exit 13
}
