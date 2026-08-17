using System.IO;
using System.Linq;
using System.Windows;

namespace AetherQMessenger;

public partial class App : Application
{
    public AppContainer Container { get; private set; } = null!;

    protected override void OnStartup(StartupEventArgs e)
    {
        // Headless tekshiruv rejimi: GUI oynasini ochmasdan to'liq kripto round-trip'ini
        // ishga tushiradi va natijani faylga yozadi (CI/avtomatlashtirilgan build tekshiruvi uchun).
        if (e.Args.Contains("--selftest"))
        {
            var result = Crypto.SelfTest.Run();
            File.WriteAllText("selftest_result.txt", $"{result.Success}\n{result.Details}");
            Shutdown(result.Success ? 0 : 1);
            return;
        }

        base.OnStartup(e);
        Container = new AppContainer();
        new MainWindow().Show();
    }
}
