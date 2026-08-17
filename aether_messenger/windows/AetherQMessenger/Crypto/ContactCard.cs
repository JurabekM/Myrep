using System;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace AetherQMessenger.Crypto;

/// <summary>
/// Kontakt ochiq kalitlari — mobil (Android) versiyadagi <c>ContactCard</c> bilan bir xil
/// JSON shakli (<c>userId</c>/<c>edPk</c>/<c>xPk</c>/<c>mlkemPk</c>, kichik harfli hex) —
/// shu tufayli QR-kod matni ikkala klient o'rtasida almashtirilishi mumkin.
/// </summary>
public sealed class ContactCard
{
    [JsonPropertyName("userId")]
    public required string UserId { get; init; }

    [JsonPropertyName("edPk")]
    public required string EdPk { get; init; }

    [JsonPropertyName("xPk")]
    public required string XPk { get; init; }

    [JsonPropertyName("mlkemPk")]
    public required string MlkemPk { get; init; }
}

public static class ContactCardCodec
{
    public static string Encode(ContactCard card) => JsonSerializer.Serialize(card);

    public static ContactCard Decode(string raw) =>
        JsonSerializer.Deserialize<ContactCard>(raw.Trim())
        ?? throw new FormatException("Yaroqsiz kontakt-karta matni");

    public static ContactCard FromIdentity(Identity identity) =>
        new()
        {
            UserId = identity.UserId,
            EdPk = Convert.ToHexString(identity.EdPk).ToLowerInvariant(),
            XPk = Convert.ToHexString(identity.XPk).ToLowerInvariant(),
            MlkemPk = Convert.ToHexString(identity.MlkemPk).ToLowerInvariant(),
        };
}
