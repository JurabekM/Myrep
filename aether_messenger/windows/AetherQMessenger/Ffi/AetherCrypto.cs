using System;
using System.Text;

namespace AetherQMessenger.Ffi;

public sealed class KeyPair
{
    public byte[] PublicKey { get; }
    public byte[] SecretKey { get; }

    public KeyPair(byte[] publicKey, byte[] secretKey)
    {
        PublicKey = publicKey;
        SecretKey = secretKey;
    }
}

public sealed class AkemEncapsulation
{
    public required byte[] CtMlkem { get; init; }
    public required byte[] CtX25519 { get; init; }
    public required byte[] Signature { get; init; }
    public required byte[] SharedSecret { get; init; }
}

public sealed class CompressStepResult
{
    public required byte[] Frame { get; init; }
    public required byte[] SharedSecret { get; init; }
}

/// <summary>S2/7.4: barcha kripto-operatsiya xatolari uchun yagona umumiy xato turi.</summary>
public sealed class AetherOperationException : Exception
{
    public AetherOperationException(string message) : base(message)
    {
    }
}

/// <summary>
/// AETHER-Q v4 kripto-yadrosi (Rust/<c>aether-ffi-c</c>) ustidan C# fasadi — Android
/// (Kotlin) versiyasidagi <c>AetherCrypto.kt</c>ga bevosita mos keladi, shu bilan ikkala
/// klient bir xil protokol semantikasiga ega bo'ladi.
/// </summary>
public static class AetherCrypto
{
    public const byte ProfileAuthAkem = 0x05;
    public const byte ProfileCompress = 0x04;

    private static readonly byte[] LabelRatchetSeed = Encoding.ASCII.GetBytes("AETHER-Q-MSGR/ratchet-base-seed");
    private static readonly byte[] LabelSessionId = Encoding.ASCII.GetBytes("AETHER-Q-MSGR/session-id");

    public static KeyPair GenerateX25519Identity()
    {
        AetherNative.aether_generate_x25519_keypair(out var pk, out var sk);
        return new KeyPair(AetherNative.ToManagedAndFree(pk), AetherNative.ToManagedAndFree(sk));
    }

    public static KeyPair GenerateMlKem768Identity()
    {
        AetherNative.aether_generate_mlkem768_keypair(out var pk, out var sk);
        return new KeyPair(AetherNative.ToManagedAndFree(pk), AetherNative.ToManagedAndFree(sk));
    }

    public static KeyPair GenerateEd25519Identity()
    {
        AetherNative.aether_generate_ed25519_keypair(out var pk, out var sk);
        return new KeyPair(AetherNative.ToManagedAndFree(pk), AetherNative.ToManagedAndFree(sk));
    }

    public static byte[] RandomBytes(int len)
    {
        AetherNative.aether_generate_random_bytes((UIntPtr)len, out var buf);
        return AetherNative.ToManagedAndFree(buf);
    }

    /// <summary>
    /// Bitta AUTH-AKEM <c>shared_secret</c>dan ikkala tomon mustaqil ravishda bir xil
    /// Compress-KEM <c>base_seed</c>/<c>session_id</c>ni hosil qiladi.
    /// </summary>
    public static byte[] DeriveRatchetSeed(byte[] sharedSecret) => DeriveBytes(sharedSecret, LabelRatchetSeed, 32);

    public static byte[] DeriveSessionId(byte[] sharedSecret) => DeriveBytes(sharedSecret, LabelSessionId, 8);

    private static byte[] DeriveBytes(byte[] input, byte[] label, int outLen)
    {
        AetherNative.aether_derive_bytes(input, (UIntPtr)input.Length, label, (UIntPtr)label.Length, (UIntPtr)outLen, out var buf);
        return AetherNative.ToManagedAndFree(buf);
    }

    public static AkemEncapsulation AkemEncapsulate(
        byte[] pkRecipMlkem, byte[] pkRecipX25519,
        byte[] skSenderSign, byte[] pkSenderSign, byte[] pkRecipSign)
    {
        var rc = AetherNative.aether_akem_encapsulate(
            pkRecipMlkem, (UIntPtr)pkRecipMlkem.Length,
            pkRecipX25519, (UIntPtr)pkRecipX25519.Length,
            skSenderSign, (UIntPtr)skSenderSign.Length,
            pkSenderSign, (UIntPtr)pkSenderSign.Length,
            pkRecipSign, (UIntPtr)pkRecipSign.Length,
            out var result);

        if (rc != 0)
        {
            AetherNative.aether_free_buffer(result.CtMlkem);
            AetherNative.aether_free_buffer(result.CtX25519);
            AetherNative.aether_free_buffer(result.Signature);
            AetherNative.aether_free_buffer(result.SharedSecret);
            throw new AetherOperationException("AETHER_DECRYPT_FAILURE");
        }

        return new AkemEncapsulation
        {
            CtMlkem = AetherNative.ToManagedAndFree(result.CtMlkem),
            CtX25519 = AetherNative.ToManagedAndFree(result.CtX25519),
            Signature = AetherNative.ToManagedAndFree(result.Signature),
            SharedSecret = AetherNative.ToManagedAndFree(result.SharedSecret),
        };
    }

    /// <summary>Imzo yaroqsiz bo'lsa ham xato tashlanmaydi — Implicit Rejection natijasi qaytadi.</summary>
    public static byte[] AkemDecapsulate(
        byte[] skRecipMlkem, byte[] skRecipX25519, byte[] pkRecipX25519, byte[] zRecip,
        byte[] pkSenderSign, byte[] pkRecipSign,
        byte[] ctMlkem, byte[] ctX25519, byte[] signature)
    {
        AetherNative.aether_akem_decapsulate(
            skRecipMlkem, (UIntPtr)skRecipMlkem.Length,
            skRecipX25519, (UIntPtr)skRecipX25519.Length,
            pkRecipX25519, (UIntPtr)pkRecipX25519.Length,
            zRecip, (UIntPtr)zRecip.Length,
            pkSenderSign, (UIntPtr)pkSenderSign.Length,
            pkRecipSign, (UIntPtr)pkRecipSign.Length,
            ctMlkem, (UIntPtr)ctMlkem.Length,
            ctX25519, (UIntPtr)ctX25519.Length,
            signature, (UIntPtr)signature.Length,
            out var buf);
        return AetherNative.ToManagedAndFree(buf);
    }

    /// <summary>
    /// Har bir xabar yangi ratchet qadami bilan shifrlanadi, shuning uchun AEAD counter
    /// har doim <c>1</c> — kalit har safar yangi (mustaqil X25519 DH natijasi).
    /// </summary>
    public static byte[] SealRecord(byte[] sharedSecret, byte[] sessionId, byte[] plaintext)
    {
        var rc = AetherNative.aether_seal_record(
            ProfileCompress,
            sharedSecret, (UIntPtr)sharedSecret.Length,
            sessionId, (UIntPtr)sessionId.Length,
            1, 1,
            plaintext, (UIntPtr)plaintext.Length,
            out var buf);

        if (rc != 0)
        {
            AetherNative.aether_free_buffer(buf);
            throw new AetherOperationException("AETHER_DECRYPT_FAILURE");
        }

        return AetherNative.ToManagedAndFree(buf);
    }

    public static byte[] OpenRecord(byte[] sharedSecret, byte[] sessionId, byte[] frame)
    {
        var rc = AetherNative.aether_open_record(
            ProfileCompress,
            sharedSecret, (UIntPtr)sharedSecret.Length,
            sessionId, (UIntPtr)sessionId.Length,
            1,
            frame, (UIntPtr)frame.Length,
            out _,
            out var buf);

        if (rc != 0)
        {
            AetherNative.aether_free_buffer(buf);
            throw new AetherOperationException("AETHER_DECRYPT_FAILURE");
        }

        return AetherNative.ToManagedAndFree(buf);
    }
}
