using System;
using System.IO;
using AetherQMessenger.Ffi;

namespace AetherQMessenger.Mqtt;

public abstract record InboundEnvelope
{
    public sealed record Handshake(byte[] SenderUserId, byte[] CtMlkem, byte[] CtX25519, byte[] Signature) : InboundEnvelope;

    public sealed record RatchetMessage(byte[] CompressFrame, byte[] RecordFrame) : InboundEnvelope;
}

/// <summary>
/// MQTT payload'ga qadab yuboriladigan binary frame format — Android (Kotlin)
/// versiyasidagi <c>MessageEnvelope.kt</c> bilan bayt-baytiga bir xil, shu tufayli
/// ikkala klient (mobil/desktop) o'rtasida haqiqiy interop mumkin.
///
/// Har bir maydon spec-primitivlaridan kelib chiqqan qat'iy o'lchamga ega (ML-KEM-768 ct,
/// Ed25519 sig, Compress-KEM frame) — uzunlik-prefikslar kerak emas.
/// </summary>
public static class MessageEnvelope
{
    private const byte TypeHandshake = 0x01;
    private const byte TypeMessage = 0x02;

    private const int UserIdLen = 8;
    private const int CtMlkemLen = 1088;
    private const int CtX25519Len = 32;
    private const int SignatureLen = 64;
    private const int CompressFrameLen = 77;

    public static byte[] EncodeHandshake(byte[] senderUserId, AkemEncapsulation encaps)
    {
        if (senderUserId.Length != UserIdLen)
        {
            throw new ArgumentException($"senderUserId {UserIdLen} bayt bo'lishi SHART", nameof(senderUserId));
        }
        if (encaps.CtMlkem.Length != CtMlkemLen)
        {
            throw new ArgumentException($"ct_mlkem kutilmagan uzunlik: {encaps.CtMlkem.Length}");
        }
        if (encaps.CtX25519.Length != CtX25519Len)
        {
            throw new ArgumentException($"ct_x25519 kutilmagan uzunlik: {encaps.CtX25519.Length}");
        }
        if (encaps.Signature.Length != SignatureLen)
        {
            throw new ArgumentException($"signature kutilmagan uzunlik: {encaps.Signature.Length}");
        }

        using var stream = new MemoryStream(1 + UserIdLen + CtMlkemLen + CtX25519Len + SignatureLen);
        stream.WriteByte(TypeHandshake);
        stream.Write(senderUserId);
        stream.Write(encaps.CtMlkem);
        stream.Write(encaps.CtX25519);
        stream.Write(encaps.Signature);
        return stream.ToArray();
    }

    public static byte[] EncodeMessage(byte[] compressFrame, byte[] recordFrame)
    {
        if (compressFrame.Length != CompressFrameLen)
        {
            throw new ArgumentException("compress_frame 77 bayt bo'lishi SHART", nameof(compressFrame));
        }

        using var stream = new MemoryStream(1 + CompressFrameLen + recordFrame.Length);
        stream.WriteByte(TypeMessage);
        stream.Write(compressFrame);
        stream.Write(recordFrame);
        return stream.ToArray();
    }

    public static InboundEnvelope? Decode(byte[] payload)
    {
        if (payload.Length == 0)
        {
            return null;
        }

        return payload[0] switch
        {
            TypeHandshake => DecodeHandshake(payload),
            TypeMessage => DecodeMessage(payload),
            _ => null,
        };
    }

    private static InboundEnvelope.Handshake? DecodeHandshake(byte[] payload)
    {
        const int expected = 1 + UserIdLen + CtMlkemLen + CtX25519Len + SignatureLen;
        if (payload.Length != expected)
        {
            return null;
        }

        var offset = 1;
        var userId = payload[offset..(offset + UserIdLen)]; offset += UserIdLen;
        var ctMlkem = payload[offset..(offset + CtMlkemLen)]; offset += CtMlkemLen;
        var ctX25519 = payload[offset..(offset + CtX25519Len)]; offset += CtX25519Len;
        var signature = payload[offset..(offset + SignatureLen)];
        return new InboundEnvelope.Handshake(userId, ctMlkem, ctX25519, signature);
    }

    private static InboundEnvelope.RatchetMessage? DecodeMessage(byte[] payload)
    {
        const int minLen = 1 + CompressFrameLen;
        if (payload.Length < minLen)
        {
            return null;
        }

        var compressFrame = payload[1..(1 + CompressFrameLen)];
        var recordFrame = payload[(1 + CompressFrameLen)..];
        return new InboundEnvelope.RatchetMessage(compressFrame, recordFrame);
    }
}
