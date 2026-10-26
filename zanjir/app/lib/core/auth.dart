/// Serverga kirish (telefon + parol). Server 7-fazada ulanadi; hozircha shlyuz "server mavjud emas" qaytaradi
/// va foydalanuvchiga oflayn profil taklif qilinadi (ADR-0009).
abstract interface class AuthGateway {
  Future<AuthResult> login({required String phone, required String password});
}

enum AuthResult { ok, invalidCredentials, serverUnavailable }

class OfflineAuthGateway implements AuthGateway {
  const OfflineAuthGateway();

  @override
  Future<AuthResult> login({required String phone, required String password}) async => AuthResult.serverUnavailable;
}
