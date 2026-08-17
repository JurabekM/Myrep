using System;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using AetherQMessenger.Crypto;
using AetherQMessenger.Data;

namespace AetherQMessenger;

public partial class MainWindow : Window
{
    private readonly AppContainer _container;
    private ContactRecord? _selectedContact;

    public MainWindow()
    {
        InitializeComponent();
        _container = ((App)Application.Current).Container;
        _container.Repository.DataChanged += () => Dispatcher.Invoke(RefreshAll);

        RefreshContacts();
        _ = _container.Repository.ConnectMqttAsync();
    }

    private void RefreshAll()
    {
        RefreshContacts();
        if (_selectedContact != null)
        {
            RefreshMessages(_selectedContact.UserId);
        }
    }

    private void RefreshContacts()
    {
        var selectedUserId = _selectedContact?.UserId;
        var contacts = _container.Repository.GetContacts();
        ContactsListBox.ItemsSource = contacts;
        if (selectedUserId != null)
        {
            ContactsListBox.SelectedItem = contacts.FirstOrDefault(c => c.UserId == selectedUserId);
        }
    }

    private void RefreshMessages(string contactUserId)
    {
        var messages = _container.Repository.GetMessages(contactUserId);
        var outgoingBrush = (Brush)FindResource("Brush.BubbleOutgoing");
        var incomingBrush = (Brush)FindResource("Brush.BubbleIncoming");
        MessagesListBox.ItemsSource = messages.Select(m => new MessageViewItem
        {
            Text = m.Plaintext,
            Background = m.IsOutgoing ? outgoingBrush : incomingBrush,
            Alignment = m.IsOutgoing ? HorizontalAlignment.Right : HorizontalAlignment.Left,
        }).ToList();
    }

    private void ContactsListBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        _selectedContact = ContactsListBox.SelectedItem as ContactRecord;
        if (_selectedContact != null)
        {
            RefreshMessages(_selectedContact.UserId);
        }
    }

    private async void SendButton_Click(object sender, RoutedEventArgs e)
    {
        await SendCurrentMessageAsync();
    }

    private async void MessageInputTextBox_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter)
        {
            await SendCurrentMessageAsync();
        }
    }

    private async Task SendCurrentMessageAsync()
    {
        var text = MessageInputTextBox.Text.Trim();
        if (string.IsNullOrEmpty(text) || _selectedContact == null)
        {
            return;
        }

        MessageInputTextBox.Text = "";
        try
        {
            await _container.Repository.SendMessageAsync(_selectedContact, text);
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, $"Xabar yuborilmadi: {ex.Message}", "Xato", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void AddContactButton_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new AddContactWindow { Owner = this };
        if (dialog.ShowDialog() == true && dialog.Result != null)
        {
            _container.Repository.AddContact(dialog.Result, dialog.DisplayName);
        }
    }

    private void MyCardButton_Click(object sender, RoutedEventArgs e)
    {
        new MyCardWindow(_container.Identity) { Owner = this }.ShowDialog();
    }

    private void SelfTestButton_Click(object sender, RoutedEventArgs e)
    {
        var result = SelfTest.Run();
        MessageBox.Show(
            this,
            result.Details,
            result.Success ? "Self-test: MUVAFFAQIYATLI" : "Self-test: XATO",
            MessageBoxButton.OK,
            result.Success ? MessageBoxImage.Information : MessageBoxImage.Error);
    }
}

public sealed class MessageViewItem
{
    public string Text { get; init; } = "";
    public Brush Background { get; init; } = Brushes.LightGray;
    public HorizontalAlignment Alignment { get; init; }
}
