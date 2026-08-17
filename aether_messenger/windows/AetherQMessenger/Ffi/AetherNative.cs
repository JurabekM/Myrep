using System;
using System.Runtime.InteropServices;

namespace AetherQMessenger.Ffi;

[StructLayout(LayoutKind.Sequential)]
internal struct NativeBuffer
{
    public IntPtr Ptr;
    public UIntPtr Len;
}

[StructLayout(LayoutKind.Sequential)]
internal struct NativeAkemEncapsulation
{
    public NativeBuffer CtMlkem;
    public NativeBuffer CtX25519;
    public NativeBuffer Signature;
    public NativeBuffer SharedSecret;
}

[StructLayout(LayoutKind.Sequential)]
internal struct NativeCompressFrameResult
{
    public NativeBuffer Frame;
    public NativeBuffer SharedSecret;
}

/// <summary>
/// Raw P/Invoke deklaratsiyalari — <c>aether_ffi_c</c> (Rust, `aether_q/crates/aether-ffi-c`)
/// kutubxonasi ustidan. Har bir chiqish <see cref="NativeBuffer"/> chaqiruvchi tomon
/// <see cref="aether_free_buffer"/> orqali tozalashi SHART bo'lgan Rust-egalik xotira.
/// </summary>
internal static class AetherNative
{
    private const string Lib = "aether_ffi_c";

    [DllImport(Lib)]
    internal static extern void aether_free_buffer(NativeBuffer buf);

    [DllImport(Lib)]
    internal static extern void aether_generate_x25519_keypair(out NativeBuffer outPk, out NativeBuffer outSk);

    [DllImport(Lib)]
    internal static extern void aether_generate_mlkem768_keypair(out NativeBuffer outPk, out NativeBuffer outSk);

    [DllImport(Lib)]
    internal static extern void aether_generate_ed25519_keypair(out NativeBuffer outPk, out NativeBuffer outSk);

    [DllImport(Lib)]
    internal static extern void aether_generate_random_bytes(UIntPtr len, out NativeBuffer out_);

    [DllImport(Lib)]
    internal static extern void aether_derive_bytes(
        byte[]? inputPtr, UIntPtr inputLen,
        byte[]? labelPtr, UIntPtr labelLen,
        UIntPtr outLen,
        out NativeBuffer out_);

    [DllImport(Lib)]
    internal static extern int aether_akem_encapsulate(
        byte[] pkRecipMlkem, UIntPtr pkRecipMlkemLen,
        byte[] pkRecipX25519, UIntPtr pkRecipX25519Len,
        byte[] skSenderSign, UIntPtr skSenderSignLen,
        byte[] pkSenderSign, UIntPtr pkSenderSignLen,
        byte[] pkRecipSign, UIntPtr pkRecipSignLen,
        out NativeAkemEncapsulation out_);

    [DllImport(Lib)]
    internal static extern void aether_akem_decapsulate(
        byte[] skRecipMlkem, UIntPtr skRecipMlkemLen,
        byte[] skRecipX25519, UIntPtr skRecipX25519Len,
        byte[] pkRecipX25519, UIntPtr pkRecipX25519Len,
        byte[] zRecip, UIntPtr zRecipLen,
        byte[] pkSenderSign, UIntPtr pkSenderSignLen,
        byte[] pkRecipSign, UIntPtr pkRecipSignLen,
        byte[] ctMlkem, UIntPtr ctMlkemLen,
        byte[] ctX25519, UIntPtr ctX25519Len,
        byte[] signature, UIntPtr signatureLen,
        out NativeBuffer out_);

    [DllImport(Lib)]
    internal static extern IntPtr aether_compress_sender_new(
        byte[] sessionId, UIntPtr sessionIdLen, byte[] baseSeed, UIntPtr baseSeedLen);

    [DllImport(Lib)]
    internal static extern void aether_compress_sender_free(IntPtr handle);

    [DllImport(Lib)]
    internal static extern int aether_compress_sender_next_frame(
        IntPtr handle, byte[] recipientPkX25519, UIntPtr recipientPkX25519Len, out NativeCompressFrameResult out_);

    [DllImport(Lib)]
    internal static extern IntPtr aether_compress_recipient_new(
        byte[] sessionId, UIntPtr sessionIdLen, byte[] baseSeed, UIntPtr baseSeedLen);

    [DllImport(Lib)]
    internal static extern void aether_compress_recipient_free(IntPtr handle);

    [DllImport(Lib)]
    internal static extern int aether_compress_recipient_accept_frame(
        IntPtr handle, byte[] frame, UIntPtr frameLen, byte[] skX25519, UIntPtr skX25519Len, out NativeBuffer out_);

    [DllImport(Lib)]
    internal static extern int aether_seal_record(
        byte profileId,
        byte[] sharedSecret, UIntPtr sharedSecretLen,
        byte[] sessionId, UIntPtr sessionIdLen,
        byte isClientToServer,
        uint counter,
        byte[] plaintext, UIntPtr plaintextLen,
        out NativeBuffer out_);

    [DllImport(Lib)]
    internal static extern int aether_open_record(
        byte profileId,
        byte[] sharedSecret, UIntPtr sharedSecretLen,
        byte[] sessionId, UIntPtr sessionIdLen,
        byte isClientToServer,
        byte[] frame, UIntPtr frameLen,
        out uint outCounter,
        out NativeBuffer out_);

    /// <summary>Native buferni managed bayt massiviga nusxalaydi va uni tozalaydi.</summary>
    internal static byte[] ToManagedAndFree(NativeBuffer buf)
    {
        if (buf.Ptr == IntPtr.Zero || buf.Len == UIntPtr.Zero)
        {
            aether_free_buffer(buf);
            return Array.Empty<byte>();
        }

        var length = checked((int)buf.Len);
        var result = new byte[length];
        Marshal.Copy(buf.Ptr, result, 0, length);
        aether_free_buffer(buf);
        return result;
    }
}
