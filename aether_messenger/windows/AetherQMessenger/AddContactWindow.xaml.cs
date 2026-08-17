using System;
using System.Windows;
using AetherQMessenger.Crypto;

namespace AetherQMessenger;

public partial class AddContactWindow : Window
{
    public ContactCard? Result { get; private set; }

    public string DisplayName => DisplayNameTextBox.Text;

    public AddContactWindow()
    {
        InitializeComponent();
    }

    private void AddButton_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var card = ContactCardCodec.Decode(CardTextBox.Text);
            Result = card;
            if (string.IsNullOrWhiteSpace(DisplayNameTextBox.Text))
            {
                DisplayNameTextBox.Text = $"Kontakt-{card.UserId[..Math.Min(6, card.UserId.Length)]}";
            }
            DialogResult = true;
        }
        catch (Exception ex)
        {
            ErrorText.Text = $"Karta matnini o'qib bo'lmadi: {ex.Message}";
        }
    }
}
