using System;
using System.Threading;
using System.Threading.Tasks;
using MQTTnet;
using MQTTnet.Client;

namespace AetherQMessenger.Mqtt;

/// <summary>
/// <c>broker.hivemq.com</c> public MQTT broker'i ustidan yupqa transport qatlami —
/// Android versiyasidagi <c>MqttClient.kt</c> bilan bir xil topic sxemasi
/// (<c>aetherq/msgr/&lt;userId&gt;</c>), shu bilan ikkala klient bir-biriga xabar
/// yubora oladi. Xavfsizlik butunlay E2E shifrlashga tayanadi — broker ishonchsiz.
/// </summary>
public sealed class MqttClientWrapper : IAsyncDisposable
{
    private const string BrokerHost = "broker.hivemq.com";
    private const int BrokerPort = 8883;
    private const string TopicPrefix = "aetherq/msgr/";

    private readonly string _ownUserId;
    private readonly IMqttClient _client;

    public MqttClientWrapper(string ownUserId)
    {
        _ownUserId = ownUserId;
        _client = new MqttFactory().CreateMqttClient();
    }

    public async Task ConnectAndSubscribeAsync(Action<byte[]> onMessage, CancellationToken ct = default)
    {
        _client.ApplicationMessageReceivedAsync += e =>
        {
            onMessage(e.ApplicationMessage.PayloadSegment.ToArray());
            return Task.CompletedTask;
        };

        var options = new MqttClientOptionsBuilder()
            .WithClientId($"aetherq-{_ownUserId}-{Guid.NewGuid():N}")
            .WithTcpServer(BrokerHost, BrokerPort)
            .WithTlsOptions(o => o.UseTls())
            .Build();

        await _client.ConnectAsync(options, ct);
        await _client.SubscribeAsync(
            new MqttClientSubscribeOptionsBuilder()
                .WithTopicFilter(TopicPrefix + _ownUserId, MQTTnet.Protocol.MqttQualityOfServiceLevel.AtLeastOnce)
                .Build(),
            ct);
    }

    public async Task PublishToAsync(string recipientUserId, byte[] payload, CancellationToken ct = default)
    {
        var message = new MqttApplicationMessageBuilder()
            .WithTopic(TopicPrefix + recipientUserId)
            .WithPayload(payload)
            .WithQualityOfServiceLevel(MQTTnet.Protocol.MqttQualityOfServiceLevel.AtLeastOnce)
            .Build();

        await _client.PublishAsync(message, ct);
    }

    public async ValueTask DisposeAsync()
    {
        if (_client.IsConnected)
        {
            await _client.DisconnectAsync();
        }
        _client.Dispose();
    }
}
