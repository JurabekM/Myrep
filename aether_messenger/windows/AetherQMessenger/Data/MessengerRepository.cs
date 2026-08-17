using System;
using System.Collections.Generic;
using System.Text;
using System.Threading.Tasks;
using AetherQMessenger.Crypto;
using AetherQMessenger.Ffi;
using AetherQMessenger.Mqtt;

namespace AetherQMessenger.Data;

/// <summary>
/// MQTT transport, AUTH-AKEM handshake, Compress-KEM ratchet va mahalliy bazani
/// bir joyga bog'laydigan yuqori darajadagi fasad (Android'dagi
/// <c>MessengerRepository.kt</c>ning C# ekvivalenti).
/// </summary>
public sealed class MessengerRepository
{
    private readonly Identity _identity;
    private readonly AppDatabase _db;
    private readonly SessionManager _sessionManager;
    private readonly MqttClientWrapper _mqttClient;

    /// <summary>Kontakt yoki xabar ro'yxati o'zgarganda ishga tushadi (istalgan thread'dan).</summary>
    public event Action? DataChanged;

    public MessengerRepository(Identity identity, AppDatabase db, SessionManager sessionManager, MqttClientWrapper mqttClient)
    {
        _identity = identity;
        _db = db;
        _sessionManager = sessionManager;
        _mqttClient = mqttClient;
    }

    public List<ContactRecord> GetContacts() => _db.GetAllContacts();

    public List<MessageRecord> GetMessages(string contactUserId) => _db.GetMessagesForContact(contactUserId);

    public void AddContact(ContactCard card, string displayName)
    {
        _db.UpsertContact(new ContactRecord
        {
            UserId = card.UserId,
            DisplayName = displayName,
            EdPkHex = card.EdPk,
            XPkHex = card.XPk,
            MlkemPkHex = card.MlkemPk,
            CreatedAt = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
        });
        DataChanged?.Invoke();
    }

    public Task ConnectMqttAsync() => _mqttClient.ConnectAndSubscribeAsync(HandleIncoming);

    public async Task SendMessageAsync(ContactRecord contact, string text)
    {
        await EnsureSessionAsync(contact);
        var session = _sessionManager.SessionFor(contact.UserId) ?? throw new InvalidOperationException("Seans o'rnatilmadi");

        var step = session.Sender.NextFrame(Convert.FromHexString(contact.XPkHex));
        var recordFrame = AetherCrypto.SealRecord(step.SharedSecret, session.SessionId, Encoding.UTF8.GetBytes(text));
        var envelope = MessageEnvelope.EncodeMessage(step.Frame, recordFrame);
        await _mqttClient.PublishToAsync(contact.UserId, envelope);

        _db.InsertMessage(new MessageRecord
        {
            ContactUserId = contact.UserId,
            IsOutgoing = true,
            Plaintext = text,
            Timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
        });
        DataChanged?.Invoke();
    }

    /// <summary>Kontakt bilan seans yo'q bo'lsa AUTH-AKEM handshake bajarib MQTT orqali yuboradi.</summary>
    private async Task EnsureSessionAsync(ContactRecord contact)
    {
        if (_sessionManager.HasSession(contact.UserId))
        {
            return;
        }

        var encaps = AetherCrypto.AkemEncapsulate(
            Convert.FromHexString(contact.MlkemPkHex),
            Convert.FromHexString(contact.XPkHex),
            _identity.EdSk,
            _identity.EdPk,
            Convert.FromHexString(contact.EdPkHex));

        _sessionManager.EstablishSession(contact.UserId, encaps.SharedSecret);

        var envelope = MessageEnvelope.EncodeHandshake(Convert.FromHexString(_identity.UserId), encaps);
        await _mqttClient.PublishToAsync(contact.UserId, envelope);
    }

    private void HandleIncoming(byte[] payload)
    {
        switch (MessageEnvelope.Decode(payload))
        {
            case InboundEnvelope.Handshake handshake:
                HandleHandshake(handshake);
                break;
            case InboundEnvelope.RatchetMessage message:
                HandleRatchetMessage(message);
                break;
        }
    }

    private void HandleHandshake(InboundEnvelope.Handshake envelope)
    {
        var senderUserId = Convert.ToHexString(envelope.SenderUserId).ToLowerInvariant();
        // Noma'lum yuboruvchi (oldindan QR/matn orqali qo'shilmagan) e'tiborsiz qoldiriladi.
        var contact = _db.FindContact(senderUserId);
        if (contact == null)
        {
            return;
        }

        var sharedSecret = AetherCrypto.AkemDecapsulate(
            _identity.MlkemSk,
            _identity.XSk,
            _identity.XPk,
            _identity.ZRecip,
            Convert.FromHexString(contact.EdPkHex),
            _identity.EdPk,
            envelope.CtMlkem,
            envelope.CtX25519,
            envelope.Signature);

        _sessionManager.EstablishSession(contact.UserId, sharedSecret);
    }

    private void HandleRatchetMessage(InboundEnvelope.RatchetMessage envelope)
    {
        var sessionIdBytes = envelope.CompressFrame[1..9];
        var contactUserId = _sessionManager.ContactForSessionId(sessionIdBytes);
        if (contactUserId == null)
        {
            return;
        }

        var session = _sessionManager.SessionFor(contactUserId);
        if (session == null)
        {
            return;
        }

        var stepSecret = session.Recipient.AcceptFrame(envelope.CompressFrame, _identity.XSk);
        var plaintext = AetherCrypto.OpenRecord(stepSecret, session.SessionId, envelope.RecordFrame);

        _db.InsertMessage(new MessageRecord
        {
            ContactUserId = contactUserId,
            IsOutgoing = false,
            Plaintext = Encoding.UTF8.GetString(plaintext),
            Timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
        });
        DataChanged?.Invoke();
    }
}
