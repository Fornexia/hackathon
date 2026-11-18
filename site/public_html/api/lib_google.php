<?php
declare(strict_types=1);
if (!defined('API')) { http_response_code(404); exit; }

function google_client_id(): string {
    return trim((string)auth_config('GOOGLE_CLIENT_ID'));
}

function google_tokeninfo_url(): string {
    $endpoint = 'https://oauth2.googleapis.com/tokeninfo';
    // Simulador só no executor descartável; produção não aceita substituir a origem do validador.
    if (defined('AMBIENTE') && AMBIENTE === 'test' && str_starts_with(DB_NAME, 'fornex_auth_test_')) {
        $teste = (string)auth_config('AUTH_TEST_GOOGLE_TOKENINFO');
        if (preg_match('#^http://127\.0\.0\.1:[0-9]+/tokeninfo$#D', $teste)) $endpoint = $teste;
    }
    return $endpoint;
}

/** O token nunca é aceito apenas por decodificar o JWT: tokeninfo valida a assinatura no Google. */
function google_validar_token(string $credential): ?array {
    if (!preg_match('/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/D', $credential)) return null;
    $contexto = stream_context_create([
        'http' => ['timeout' => 5, 'follow_location' => 0, 'ignore_errors' => true,
            'header' => "Accept: application/json\r\n"],
        'ssl' => ['verify_peer' => true, 'verify_peer_name' => true, 'allow_self_signed' => false],
    ]);
    // Suprimir avisos evita registrar a URL que contém a credencial. Falha fechada, sem detalhes externos.
    $resposta = @file_get_contents(google_tokeninfo_url() . '?id_token=' . rawurlencode($credential), false, $contexto, 0, 32769);
    if ($resposta === false || strlen($resposta) > 32768
        || !preg_match('#^HTTP/\S+ 200(?:\s|$)#', $http_response_header[0] ?? '')) return null;
    try { $claims = json_decode($resposta, true, 16, JSON_THROW_ON_ERROR); }
    catch (Throwable) { return null; }
    if (!is_array($claims) || ($claims['aud'] ?? null) !== google_client_id()
        || !in_array($claims['iss'] ?? null, ['accounts.google.com', 'https://accounts.google.com'], true)
        || !(is_int($claims['exp'] ?? null) || is_string($claims['exp'] ?? null))
        || !ctype_digit((string)$claims['exp']) || (int)$claims['exp'] <= time()
        || !in_array($claims['email_verified'] ?? null, [true, 'true'], true)
        || !is_string($claims['sub'] ?? null) || !preg_match('/^[A-Za-z0-9_-]{1,64}$/D', $claims['sub'])) return null;
    $email = auth_email($claims['email'] ?? '');
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) return null;
    return ['sub' => $claims['sub'], 'email' => $email,
        'nome' => texto_limpo($claims['name'] ?? '', 120) ?: 'Usuário'];
}

/** Sem exit: libera travas em toda recusa e serializa criação/vinculação concorrentes. */
function google_vincular(array $claims): ?array {
    $pdo = db();
    $chaves = array_map(fn($v) => 'google:' . substr(hash('sha256', DB_NAME . ':' . $v), 0, 57),
        ['sub:' . $claims['sub'], 'email:' . $claims['email']]);
    sort($chaves, SORT_STRING);
    $travadas = [];
    try {
        foreach ($chaves as $chave) {
            $st = $pdo->prepare('SELECT GET_LOCK(?, 5)');
            $st->execute([$chave]);
            if ((int)$st->fetchColumn() !== 1) return null;
            $travadas[] = $chave;
        }
        $pdo->beginTransaction();
        $st = $pdo->prepare('SELECT * FROM usuarios WHERE google_sub = ? OR email = ? ORDER BY id FOR UPDATE');
        $st->execute([$claims['sub'], $claims['email']]);
        $contas = $st->fetchAll();
        // Nunca juntar contas distintas nem sobrescrever um vínculo já existente.
        if (count($contas) > 1) { $pdo->rollBack(); return null; }
        $u = $contas[0] ?? null;
        if ($u && ($u['papel'] === 'admin' || ($u['google_sub'] !== null && $u['google_sub'] !== $claims['sub']))) {
            $pdo->rollBack(); return null;
        }
        if (!$u) {
            $pdo->prepare('INSERT INTO usuarios (nome, email, senha_hash, papel, email_verificado_em, email_verificacao_exigida, google_sub)
                VALUES (?, ?, NULL, "usuario", NOW(), 0, ?)')->execute([$claims['nome'], $claims['email'], $claims['sub']]);
            $id = (int)$pdo->lastInsertId();
        } else {
            $id = (int)$u['id'];
            if ($u['email_verificado_em'] === null) {
                $pdo->prepare('UPDATE usuarios SET senha_hash = NULL, auth_versao = auth_versao + 1 WHERE id = ?')->execute([$id]);
                $pdo->prepare('UPDATE auth_tokens SET usado_em = NOW() WHERE usuario_id = ? AND usado_em IS NULL')->execute([$id]);
                $pdo->prepare('UPDATE auth_emails e JOIN auth_tokens t ON t.id = e.token_id SET e.conteudo = NULL WHERE t.usuario_id = ?')->execute([$id]);
            }
            // sub é a identidade estável. Não reescrever e-mail/nomes existentes em logins posteriores.
            $pdo->prepare('UPDATE usuarios SET google_sub = ?, email_verificado_em = COALESCE(email_verificado_em, NOW()) WHERE id = ?')
                ->execute([$claims['sub'], $id]);
        }
        $st = $pdo->prepare('SELECT id, auth_versao FROM usuarios WHERE id = ?');
        $st->execute([$id]);
        $resultado = $st->fetch();
        $pdo->commit();
        return $resultado ?: null;
    } catch (PDOException $e) {
        if ($pdo->inTransaction()) $pdo->rollBack();
        if ((int)($e->errorInfo[1] ?? 0) === 1062) return null;
        throw $e;
    } catch (Throwable $e) {
        if ($pdo->inTransaction()) $pdo->rollBack();
        throw $e;
    } finally {
        foreach (array_reverse($travadas) as $chave) $pdo->prepare('SELECT RELEASE_LOCK(?)')->execute([$chave]);
    }
}

function rota_login_google(): never {
    if (google_client_id() === '') erro(404, 'Rota não encontrada.');
    exigir_csrf();
    $c = corpo(16384);
    $credential = is_string($c['credential'] ?? null) ? $c['credential'] : '';
    auth_limitar('google', hash('sha256', $credential));
    if ($credential === '' || strlen($credential) > 12000) erro(401, 'Não foi possível entrar com Google.');
    $claims = google_validar_token($credential);
    if (!$claims) erro(401, 'Não foi possível entrar com Google.');
    auth_limitar('google-conta', $claims['email']);
    $u = google_vincular($claims);
    if (!$u) erro(401, 'Não foi possível entrar com Google.');
    entrar((int)$u['id'], (int)$u['auth_versao']);
    $logado = usuario_atual();
    if (!$logado) erro(401, 'Não foi possível entrar com Google.');
    responder(200, ['usuario' => usuario_para_json($logado), 'plano' => plano_ativo((int)$logado['id']), 'csrf' => csrf_token()]);
}
