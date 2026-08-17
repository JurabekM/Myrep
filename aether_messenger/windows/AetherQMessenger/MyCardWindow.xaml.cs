using System.IO;
using System.Windows;
using System.Windows.Media.Imaging;
using AetherQMessenger.Crypto;
using QRCoder;

namespace AetherQMessenger;

public partial class MyCardWindow : Window
{
    public MyCardWindow(Identity identity)
    {
        InitializeComponent();

        var card = ContactCardCodec.FromIdentity(identity);
        var json = ContactCardCodec.Encode(card);
        CardTextBox.Text = json;

        var qrGenerator = new QRCodeGenerator();
        var qrData = qrGenerator.CreateQrCode(json, QRCodeGenerator.ECCLevel.L);
        var pngQr = new PngByteQRCode(qrData);
        var pngBytes = pngQr.GetGraphic(6);

        var bitmap = new BitmapImage();
        using (var stream = new MemoryStream(pngBytes))
        {
            bitmap.BeginInit();
            bitmap.CacheOption = BitmapCacheOption.OnLoad;
            bitmap.StreamSource = stream;
            bitmap.EndInit();
        }
        bitmap.Freeze();
        QrImage.Source = bitmap;
    }

    private void CopyButton_Click(object sender, RoutedEventArgs e)
    {
        Clipboard.SetText(CardTextBox.Text);
    }
}
