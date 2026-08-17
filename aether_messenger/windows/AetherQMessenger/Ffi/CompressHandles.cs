using System;

namespace AetherQMessenger.Ffi;

/// <summary>Compress-KEM (0x04) — bitta yo'nalishdagi yuboruvchi ratchet holati.</summary>
public sealed class CompressSenderHandle : IDisposable
{
    private IntPtr _handle;

    public CompressSenderHandle(byte[] sessionId, byte[] baseSeed)
    {
        _handle = AetherNative.aether_compress_sender_new(sessionId, (UIntPtr)sessionId.Length, baseSeed, (UIntPtr)baseSeed.Length);
        if (_handle == IntPtr.Zero)
        {
            throw new AetherOperationException("AETHER_DECRYPT_FAILURE");
        }
    }

    /// <summary>Yangi ratchet qadami: yangi ephemeral X25519 juftlik + 77-baytli frame.</summary>
    public CompressStepResult NextFrame(byte[] recipientPkX25519)
    {
        var rc = AetherNative.aether_compress_sender_next_frame(_handle, recipientPkX25519, (UIntPtr)recipientPkX25519.Length, out var result);
        if (rc != 0)
        {
            AetherNative.aether_free_buffer(result.Frame);
            AetherNative.aether_free_buffer(result.SharedSecret);
            throw new AetherOperationException("AETHER_DECRYPT_FAILURE");
        }

        return new CompressStepResult
        {
            Frame = AetherNative.ToManagedAndFree(result.Frame),
            SharedSecret = AetherNative.ToManagedAndFree(result.SharedSecret),
        };
    }

    public void Dispose()
    {
        if (_handle != IntPtr.Zero)
        {
            AetherNative.aether_compress_sender_free(_handle);
            _handle = IntPtr.Zero;
        }
        GC.SuppressFinalize(this);
    }

    ~CompressSenderHandle() => Dispose();
}

/// <summary>
/// Compress-KEM (0x04) — bitta yo'nalishdagi qabul qiluvchi ratchet holati
/// (delta_tag tekshiruvi + replay-himoya bitmap Rust tomonida).
/// </summary>
public sealed class CompressRecipientHandle : IDisposable
{
    private IntPtr _handle;

    public CompressRecipientHandle(byte[] sessionId, byte[] baseSeed)
    {
        _handle = AetherNative.aether_compress_recipient_new(sessionId, (UIntPtr)sessionId.Length, baseSeed, (UIntPtr)baseSeed.Length);
        if (_handle == IntPtr.Zero)
        {
            throw new AetherOperationException("AETHER_DECRYPT_FAILURE");
        }
    }

    public byte[] AcceptFrame(byte[] frame, byte[] skX25519)
    {
        var rc = AetherNative.aether_compress_recipient_accept_frame(_handle, frame, (UIntPtr)frame.Length, skX25519, (UIntPtr)skX25519.Length, out var buf);
        if (rc != 0)
        {
            AetherNative.aether_free_buffer(buf);
            throw new AetherOperationException("AETHER_DECRYPT_FAILURE");
        }
        return AetherNative.ToManagedAndFree(buf);
    }

    public void Dispose()
    {
        if (_handle != IntPtr.Zero)
        {
            AetherNative.aether_compress_recipient_free(_handle);
            _handle = IntPtr.Zero;
        }
        GC.SuppressFinalize(this);
    }

    ~CompressRecipientHandle() => Dispose();
}
