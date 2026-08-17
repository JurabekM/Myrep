namespace AetherQMessenger.Data;

/// <summary>QR orqali olingan kontaktning uzoq-muddatli ochiq kalitlari.</summary>
public sealed class ContactRecord
{
    public required string UserId { get; init; }
    public required string DisplayName { get; init; }
    public required string EdPkHex { get; init; }
    public required string XPkHex { get; init; }
    public required string MlkemPkHex { get; init; }
    public required long CreatedAt { get; init; }
}

/// <summary>Bitta matnli xabar (deshifrlangan holda saqlanadi).</summary>
public sealed class MessageRecord
{
    public long Id { get; init; }
    public required string ContactUserId { get; init; }
    public required bool IsOutgoing { get; init; }
    public required string Plaintext { get; init; }
    public required long Timestamp { get; init; }
}
