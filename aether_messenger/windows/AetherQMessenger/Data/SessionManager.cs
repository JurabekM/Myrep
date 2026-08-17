using System;
using System.Collections.Concurrent;
using AetherQMessenger.Ffi;

namespace AetherQMessenger.Data;

/// <summary>
/// Bitta kontakt bilan bo'lgan ratchet-seansi — AUTH-AKEM handshake'dan olingan
/// <c>shared_secret</c>dan hosil qilingan <c>session_id</c>/<c>base_seed</c> asosida.
///
/// PoC chegarasi: bu holat faqat jarayon-ichida (in-memory) saqlanadi — ilova qayta
/// ishga tushganda har bir kontakt uchun handshake avtomatik qayta bajariladi.
/// </summary>
public sealed class ContactSession
{
    public required byte[] SessionId { get; init; }
    public required CompressSenderHandle Sender { get; init; }
    public required CompressRecipientHandle Recipient { get; init; }
}

public sealed class SessionManager
{
    private readonly ConcurrentDictionary<string, ContactSession> _sessions = new();
    private readonly ConcurrentDictionary<string, string> _sessionIdIndex = new();

    public ContactSession? SessionFor(string contactUserId) =>
        _sessions.TryGetValue(contactUserId, out var session) ? session : null;

    public bool HasSession(string contactUserId) => _sessions.ContainsKey(contactUserId);

    public string? ContactForSessionId(byte[] sessionId) =>
        _sessionIdIndex.TryGetValue(Convert.ToHexString(sessionId).ToLowerInvariant(), out var contactId) ? contactId : null;

    /// <summary>AUTH-AKEM handshake natijasidan ratchet-seansini o'rnatadi.</summary>
    public ContactSession EstablishSession(string contactUserId, byte[] sharedSecret)
    {
        var baseSeed = AetherCrypto.DeriveRatchetSeed(sharedSecret);
        var sessionId = AetherCrypto.DeriveSessionId(sharedSecret);
        var session = new ContactSession
        {
            SessionId = sessionId,
            Sender = new CompressSenderHandle(sessionId, baseSeed),
            Recipient = new CompressRecipientHandle(sessionId, baseSeed),
        };
        _sessions[contactUserId] = session;
        _sessionIdIndex[Convert.ToHexString(sessionId).ToLowerInvariant()] = contactUserId;
        return session;
    }
}
