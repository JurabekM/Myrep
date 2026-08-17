using System;
using System.Collections.Generic;
using System.IO;
using Microsoft.Data.Sqlite;

namespace AetherQMessenger.Data;

/// <summary>
/// Mahalliy SQLite baza — kontaktlar va xabar tarixi. PoC doirasida shifrlanmagan
/// (identity maxfiy kalitlari alohida, Windows DPAPI bilan himoyalanadi — <see cref="Crypto.IdentityStore"/>).
/// </summary>
public sealed class AppDatabase : IDisposable
{
    // MQTT callback (background thread) va UI thread bir vaqtda bazaga murojaat qilishi
    // mumkin — Microsoft.Data.Sqlite bitta connection'ni parallel chaqiruvlar uchun
    // kafolatlamaydi, shuning uchun barcha kirish shu lock orqali ketma-ketlashtiriladi.
    private readonly object _lock = new();
    private readonly SqliteConnection _connection;

    private AppDatabase(SqliteConnection connection)
    {
        _connection = connection;
    }

    public static AppDatabase Open()
    {
        var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AetherQMessenger");
        Directory.CreateDirectory(dir);
        var dbPath = Path.Combine(dir, "aether_messenger.db");

        var connection = new SqliteConnection($"Data Source={dbPath}");
        connection.Open();

        using (var cmd = connection.CreateCommand())
        {
            cmd.CommandText = """
                CREATE TABLE IF NOT EXISTS contacts (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    ed_pk_hex TEXT NOT NULL,
                    x_pk_hex TEXT NOT NULL,
                    mlkem_pk_hex TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_user_id TEXT NOT NULL,
                    is_outgoing INTEGER NOT NULL,
                    plaintext TEXT NOT NULL,
                    timestamp INTEGER NOT NULL
                );
                """;
            cmd.ExecuteNonQuery();
        }

        return new AppDatabase(connection);
    }

    public void UpsertContact(ContactRecord contact)
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = """
                INSERT INTO contacts (user_id, display_name, ed_pk_hex, x_pk_hex, mlkem_pk_hex, created_at)
                VALUES ($userId, $displayName, $edPk, $xPk, $mlkemPk, $createdAt)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    ed_pk_hex = excluded.ed_pk_hex,
                    x_pk_hex = excluded.x_pk_hex,
                    mlkem_pk_hex = excluded.mlkem_pk_hex;
                """;
            cmd.Parameters.AddWithValue("$userId", contact.UserId);
            cmd.Parameters.AddWithValue("$displayName", contact.DisplayName);
            cmd.Parameters.AddWithValue("$edPk", contact.EdPkHex);
            cmd.Parameters.AddWithValue("$xPk", contact.XPkHex);
            cmd.Parameters.AddWithValue("$mlkemPk", contact.MlkemPkHex);
            cmd.Parameters.AddWithValue("$createdAt", contact.CreatedAt);
            cmd.ExecuteNonQuery();
        }
    }

    public List<ContactRecord> GetAllContacts()
    {
        lock (_lock)
        {
            var result = new List<ContactRecord>();
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = "SELECT user_id, display_name, ed_pk_hex, x_pk_hex, mlkem_pk_hex, created_at FROM contacts ORDER BY created_at DESC;";
            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                result.Add(new ContactRecord
                {
                    UserId = reader.GetString(0),
                    DisplayName = reader.GetString(1),
                    EdPkHex = reader.GetString(2),
                    XPkHex = reader.GetString(3),
                    MlkemPkHex = reader.GetString(4),
                    CreatedAt = reader.GetInt64(5),
                });
            }
            return result;
        }
    }

    public ContactRecord? FindContact(string userId)
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = "SELECT user_id, display_name, ed_pk_hex, x_pk_hex, mlkem_pk_hex, created_at FROM contacts WHERE user_id = $userId;";
            cmd.Parameters.AddWithValue("$userId", userId);
            using var reader = cmd.ExecuteReader();
            if (!reader.Read())
            {
                return null;
            }
            return new ContactRecord
            {
                UserId = reader.GetString(0),
                DisplayName = reader.GetString(1),
                EdPkHex = reader.GetString(2),
                XPkHex = reader.GetString(3),
                MlkemPkHex = reader.GetString(4),
                CreatedAt = reader.GetInt64(5),
            };
        }
    }

    public long InsertMessage(MessageRecord message)
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = """
                INSERT INTO messages (contact_user_id, is_outgoing, plaintext, timestamp)
                VALUES ($contactUserId, $isOutgoing, $plaintext, $timestamp);
                SELECT last_insert_rowid();
                """;
            cmd.Parameters.AddWithValue("$contactUserId", message.ContactUserId);
            cmd.Parameters.AddWithValue("$isOutgoing", message.IsOutgoing ? 1 : 0);
            cmd.Parameters.AddWithValue("$plaintext", message.Plaintext);
            cmd.Parameters.AddWithValue("$timestamp", message.Timestamp);
            return (long)cmd.ExecuteScalar()!;
        }
    }

    public List<MessageRecord> GetMessagesForContact(string contactUserId)
    {
        lock (_lock)
        {
            var result = new List<MessageRecord>();
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = "SELECT id, contact_user_id, is_outgoing, plaintext, timestamp FROM messages WHERE contact_user_id = $contactUserId ORDER BY timestamp ASC;";
            cmd.Parameters.AddWithValue("$contactUserId", contactUserId);
            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                result.Add(new MessageRecord
                {
                    Id = reader.GetInt64(0),
                    ContactUserId = reader.GetString(1),
                    IsOutgoing = reader.GetInt64(2) != 0,
                    Plaintext = reader.GetString(3),
                    Timestamp = reader.GetInt64(4),
                });
            }
            return result;
        }
    }

    public void Dispose() => _connection.Dispose();
}
