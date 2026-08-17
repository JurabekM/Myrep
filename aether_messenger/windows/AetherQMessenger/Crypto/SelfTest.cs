using System;
using System.Text;
using AetherQMessenger.Ffi;

namespace AetherQMessenger.Crypto;

/// <summary>
/// Bitta jarayon ichida Alice/Bob identity'larini simulyatsiya qilib to'liq
/// AUTH-AKEM + Compress-KEM ratchet + record layer round-trip'ini tekshiradi —
/// P/Invoke chegarasini tasdiqlash uchun.
/// </summary>
public static class SelfTest
{
    public sealed record Result(bool Success, string Details);

    public static Result Run()
    {
        try
        {
            var aliceEd = AetherCrypto.GenerateEd25519Identity();
            var bobEd = AetherCrypto.GenerateEd25519Identity();
            var bobX = AetherCrypto.GenerateX25519Identity();
            var bobMlkem = AetherCrypto.GenerateMlKem768Identity();
            var bobZ = AetherCrypto.RandomBytes(32);

            var encaps = AetherCrypto.AkemEncapsulate(
                bobMlkem.PublicKey, bobX.PublicKey,
                aliceEd.SecretKey, aliceEd.PublicKey, bobEd.PublicKey);

            var bobSharedSecret = AetherCrypto.AkemDecapsulate(
                bobMlkem.SecretKey, bobX.SecretKey, bobX.PublicKey, bobZ,
                aliceEd.PublicKey, bobEd.PublicKey,
                encaps.CtMlkem, encaps.CtX25519, encaps.Signature);

            if (!encaps.SharedSecret.AsSpan().SequenceEqual(bobSharedSecret))
            {
                return new Result(false, "AKEM shared_secret mos kelmadi");
            }

            var baseSeed = AetherCrypto.DeriveRatchetSeed(encaps.SharedSecret);
            var sessionId = AetherCrypto.DeriveSessionId(encaps.SharedSecret);

            using var sender = new CompressSenderHandle(sessionId, baseSeed);
            using var recipient = new CompressRecipientHandle(sessionId, baseSeed);

            var step = sender.NextFrame(bobX.PublicKey);
            if (step.Frame.Length != 77)
            {
                return new Result(false, $"Compress frame 77 bayt emas: {step.Frame.Length}");
            }

            var bobStepSecret = recipient.AcceptFrame(step.Frame, bobX.SecretKey);
            if (!step.SharedSecret.AsSpan().SequenceEqual(bobStepSecret))
            {
                return new Result(false, "Ratchet step shared_secret mos kelmadi");
            }

            var plaintext = Encoding.UTF8.GetBytes("AETHER-Q self-test xabari");
            var recordFrame = AetherCrypto.SealRecord(step.SharedSecret, sessionId, plaintext);
            var decrypted = AetherCrypto.OpenRecord(bobStepSecret, sessionId, recordFrame);

            if (!decrypted.AsSpan().SequenceEqual(plaintext))
            {
                return new Result(false, "Record layer roundtrip mos kelmadi");
            }

            return new Result(
                true,
                "AUTH-AKEM + Compress-KEM ratchet + Record layer — barchasi P/Invoke orqali muvaffaqiyatli o'tdi.");
        }
        catch (Exception e)
        {
            return new Result(false, $"Xato: {e.Message}");
        }
    }
}
