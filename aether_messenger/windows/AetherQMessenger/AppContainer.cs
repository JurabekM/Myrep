using AetherQMessenger.Crypto;
using AetherQMessenger.Data;
using AetherQMessenger.Mqtt;

namespace AetherQMessenger;

/// <summary>Qo'lda ulanadigan (manual DI) qaramliklar konteyneri — Android'dagi AppContainer'ga mos.</summary>
public sealed class AppContainer
{
    public Identity Identity { get; }
    public AppDatabase Database { get; }
    public SessionManager SessionManager { get; }
    public MqttClientWrapper MqttClient { get; }
    public MessengerRepository Repository { get; }

    public AppContainer()
    {
        Identity = IdentityStore.GetOrCreate();
        Database = AppDatabase.Open();
        SessionManager = new SessionManager();
        MqttClient = new MqttClientWrapper(Identity.UserId);
        Repository = new MessengerRepository(Identity, Database, SessionManager, MqttClient);
    }
}
