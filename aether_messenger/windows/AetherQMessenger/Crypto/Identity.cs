using System;
using System.IO;
using System.Security.Cryptography;
using System.Text.Json;
using AetherQMessenger.Ffi;

namespace AetherQMessenger.Crypto;

/// <summary>
/// Qurilmaning o'z uzoq-muddatli identity kalitlar to'plami: Ed25519 (imzo), X25519
/// (statik DH), ML-KEM-768 (post-kvant KEM) — AUTH-AKEM handshake'ida ishlatiladi.
/// <c>ZRecip</c> — Implicit Rejection uchun <c>XSk</c> bilan birga saqlanadigan alohida
/// maxfiy qiymat (spec 4.1-bo'lim, band 4).
/// </summary>
public sealed class Identity
{
    public required string UserId { get; init; }
    public required byte[] EdPk { get; init; }
    public required byte[] EdSk { get; init; }
    public required byte[] XPk { get; init; }
    public required byte[] XSk { get; init; }
    public required byte[] MlkemPk { get; init; }
    public required byte[] MlkemSk { get; init; }
    public required byte[] ZRecip { get; init; }
}

internal sealed class IdentityFile
{
    public string UserId { get; set; } = "";
    public string EdPk { get; set; } = "";
    public string EdSkProtected { get; set; } = "";
    public string XPk { get; set; } = "";
    public string XSkProtected { get; set; } = "";
    public string MlkemPk { get; set; } = "";
    public string MlkemSkProtected { get; set; } = "";
    public string ZRecipProtected { get; set; } = "";
}

/// <summary>
/// Identity — Windows DPAPI (<see cref="ProtectedData"/>, CurrentUser scope) bilan
/// himoyalangan mahalliy faylda saqlanadi. Ochiq kalitlar aniq matnda, maxfiy kalitlar
/// esa har biri alohida DPAPI-shifrlangan holda yoziladi.
/// </summary>
public static class IdentityStore
{
    private static string FilePath =>
        Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "AetherQMessenger",
            "identity.json");

    public static Identity GetOrCreate()
    {
        if (File.Exists(FilePath))
        {
            var json = File.ReadAllText(FilePath);
            var file = JsonSerializer.Deserialize<IdentityFile>(json)
                       ?? throw new InvalidOperationException("identity.json buzilgan yoki bo'sh");

            return new Identity
            {
                UserId = file.UserId,
                EdPk = Convert.FromBase64String(file.EdPk),
                EdSk = Unprotect(file.EdSkProtected),
                XPk = Convert.FromBase64String(file.XPk),
                XSk = Unprotect(file.XSkProtected),
                MlkemPk = Convert.FromBase64String(file.MlkemPk),
                MlkemSk = Unprotect(file.MlkemSkProtected),
                ZRecip = Unprotect(file.ZRecipProtected),
            };
        }

        var edKp = AetherCrypto.GenerateEd25519Identity();
        var xKp = AetherCrypto.GenerateX25519Identity();
        var mlkemKp = AetherCrypto.GenerateMlKem768Identity();
        var zRecip = AetherCrypto.RandomBytes(32);

        var userIdBytes = SHA256.HashData(edKp.PublicKey)[..8];
        var userId = Convert.ToHexString(userIdBytes).ToLowerInvariant();

        var identity = new Identity
        {
            UserId = userId,
            EdPk = edKp.PublicKey,
            EdSk = edKp.SecretKey,
            XPk = xKp.PublicKey,
            XSk = xKp.SecretKey,
            MlkemPk = mlkemKp.PublicKey,
            MlkemSk = mlkemKp.SecretKey,
            ZRecip = zRecip,
        };

        Save(identity);
        return identity;
    }

    private static void Save(Identity identity)
    {
        var dir = Path.GetDirectoryName(FilePath)!;
        Directory.CreateDirectory(dir);

        var file = new IdentityFile
        {
            UserId = identity.UserId,
            EdPk = Convert.ToBase64String(identity.EdPk),
            EdSkProtected = Protect(identity.EdSk),
            XPk = Convert.ToBase64String(identity.XPk),
            XSkProtected = Protect(identity.XSk),
            MlkemPk = Convert.ToBase64String(identity.MlkemPk),
            MlkemSkProtected = Protect(identity.MlkemSk),
            ZRecipProtected = Protect(identity.ZRecip),
        };

        File.WriteAllText(FilePath, JsonSerializer.Serialize(file));
    }

    private static string Protect(byte[] data) =>
        Convert.ToBase64String(ProtectedData.Protect(data, null, DataProtectionScope.CurrentUser));

    private static byte[] Unprotect(string base64) =>
        ProtectedData.Unprotect(Convert.FromBase64String(base64), null, DataProtectionScope.CurrentUser);
}
