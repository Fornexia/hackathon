<?php
declare(strict_types=1);
if (!defined('API')) { http_response_code(404); exit; }

function auth_config(string $nome, mixed $padrao = ''): mixed {
    $valor = getenv($nome);
    return $valor !== false ? $valor : (defined($nome) ? constant($nome) : $padrao);
}

function auth_email(mixed $valor): string {
    return strtolower(texto_limpo($valor, 190));
}

function auth_validar_senha(array $c): string {
    $senha = is_string($c['senha'] ?? null) ? $c['senha'] : '';
    if (!mb_check_encoding($senha, 'UTF-8') || mb_strlen($senha) < 15 || mb_strlen($senha) > 128 || str_contains($senha, "\0")) {
        erro(400, 'Use uma senha exclusiva do FORNEX com 15 a 128 caracteres.');
    }
    if (!is_string($c['confirmacao'] ?? null) || !hash_equals($senha, $c['confirmacao'])) {
        erro(400, 'As senhas precisam ser iguais.');
    }
    return $senha;
}

function auth_hash(string $senha): string {
    if (!defined('PASSWORD_ARGON2ID')) throw new RuntimeException('Argon2id indisponível.');
    return password_hash($senha, PASSWORD_ARGON2ID);
}

/** Contadores atômicos por IP e por endereço; a chave não contém o endereço em claro. */
function auth_limitar(string $acao, string $email): void {
    $pdo = db();
    foreach (['ip:' . ip_do_cliente() => 20, 'email:' . $email => 5] as $alvo => $maximo) {
        $chave = hash('sha256', $acao . ':' . $alvo);
        $pdo->beginTransaction();
        try {
            $pdo->prepare('INSERT INTO auth_limites (chave, inicio, total) VALUES (?, NOW(), 1)
                ON DUPLICATE KEY UPDATE total = IF(inicio < NOW() - INTERVAL 15 MINUTE, 1, total + 1),
                inicio = IF(inicio < NOW() - INTERVAL 15 MINUTE, NOW(), inicio)')->execute([$chave]);
            $st = $pdo->prepare('SELECT total FROM auth_limites WHERE chave = ? FOR UPDATE');
            $st->execute([$chave]);
            $total = (int)$st->fetchColumn();
            $pdo->commit();
        } catch (Throwable $e) {
            if ($pdo->inTransaction()) $pdo->rollBack();
            throw $e;
        }
        if ($total > $maximo) {
            header('Retry-After: 900');
            erro(429, 'Muitas solicitações. Aguarde alguns minutos.');
        }
    }
    if (random_int(1, 100) === 1) $pdo->exec('DELETE FROM auth_limites WHERE inicio < NOW() - INTERVAL 1 DAY');
}

function auth_chave_email(): string {
    $chave = base64_decode((string)auth_config('AUTH_MAIL_KEY'), true);
    if ($chave === false || strlen($chave) !== 32) throw new RuntimeException('Chave da fila ausente.');
    return $chave;
}

function auth_transporte_teste(): bool {
    return defined('AMBIENTE') && AMBIENTE === 'test' && str_starts_with(DB_NAME, 'fornex_auth_test_')
        && auth_config('MAIL_TRANSPORT') === 'capture';
}

function auth_email_pronto(): bool {
    try {
        auth_chave_email();
        $url = (string)auth_config('APP_URL');
        $partes = parse_url($url);
        if (!$partes || empty($partes['host']) || isset($partes['query']) || isset($partes['fragment'])
            || isset($partes['user']) || isset($partes['pass']) || !in_array($partes['path'] ?? '', ['', '/'], true)) return false;
        if (($partes['scheme'] ?? '') !== 'https' && !(auth_transporte_teste() && ($partes['host'] === '127.0.0.1'))) return false;
        if (auth_transporte_teste()) return auth_config('AUTH_MAIL_CAPTURE') !== '';
        return auth_config('SMTP_HOST') !== '' && auth_config('SMTP_USER') !== ''
            && auth_config('SMTP_PASS') !== '' && filter_var(auth_config('MAIL_FROM'), FILTER_VALIDATE_EMAIL)
            && in_array(auth_config('SMTP_SECURITY', 'tls'), ['tls', 'ssl'], true)
            && is_file(dirname(__DIR__, 2) . '/vendor/autoload.php');
    } catch (Throwable) { return false; }
}

function auth_exigir_email(): void {
    if (!auth_email_pronto()) erro(503, 'O envio de e-mails ainda não está disponível. Tente mais tarde.');
}

/** Dentro da transação, com o usuário bloqueado antes de chamar. Nunca retorna o token pela API. */
function auth_emitir_token(array $u, string $finalidade): void {
    $pdo = db();
    $pdo->prepare('UPDATE auth_tokens SET usado_em = NOW() WHERE usuario_id = ? AND finalidade = ? AND usado_em IS NULL')
        ->execute([$u['id'], $finalidade]);
    $token = bin2hex(random_bytes(32));
    $minutos = $finalidade === 'verificar' ? 1440 : 30;
    $pdo->prepare("INSERT INTO auth_tokens (usuario_id, finalidade, token_hash, expira_em) VALUES (?, ?, ?, DATE_ADD(NOW(), INTERVAL $minutos MINUTE))")
        ->execute([$u['id'], $finalidade, hash('sha256', $token)]);
    $id = (int)$pdo->lastInsertId();
    $link = rtrim((string)auth_config('APP_URL'), '/') . '/acesso.html#' . $finalidade . '=' . $token;
    $titulo = $finalidade === 'verificar' ? 'Verifique seu endereço no FORNEX' : 'Redefina sua senha do FORNEX';
    $mensagem = $titulo . ".\n\nAbra o endereço e confirme a ação:\n" . $link
        . "\n\nO link vale por $minutos minutos e pode ser usado uma vez. Se não solicitou, ignore esta mensagem.";
    $iv = random_bytes(12);
    $tag = '';
    $conteudo = json_encode(['email' => $u['email'], 'assunto' => $titulo, 'texto' => $mensagem], JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE);
    $cifrado = openssl_encrypt($conteudo, 'aes-256-gcm', auth_chave_email(), OPENSSL_RAW_DATA, $iv, $tag);
    if ($cifrado === false) throw new RuntimeException('Falha ao preparar e-mail.');
    $pdo->prepare('INSERT INTO auth_emails (token_id, conteudo) VALUES (?, ?)')->execute([$id, base64_encode($iv . $tag . $cifrado)]);
}

function auth_resposta_envio(): never {
    responder(202, ['mensagem' => 'Se o endereço puder receber esta solicitação, enviaremos as instruções. Confira sua caixa de entrada e o spam.']);
}

function rota_auth_solicitar(string $finalidade): never {
    exigir_csrf();
    $c = corpo(2048);
    $email = auth_email($c['email'] ?? '');
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) erro(400, 'Informe um e-mail válido.');
    auth_limitar($finalidade, $email);
    auth_exigir_email();
    $pdo = db();
    $pdo->beginTransaction();
    try {
        $st = $pdo->prepare('SELECT * FROM usuarios WHERE email = ? FOR UPDATE');
        $st->execute([$email]);
        $u = $st->fetch();
        $pendente = $u && (int)$u['email_verificacao_exigida'] === 1 && $u['email_verificado_em'] === null;
        if ($u && (($finalidade === 'verificar' && $pendente) || ($finalidade === 'redefinir' && !$pendente))) {
            auth_emitir_token($u, $finalidade);
        }
        $pdo->commit();
    } catch (Throwable $e) {
        if ($pdo->inTransaction()) $pdo->rollBack();
        throw $e;
    }
    auth_resposta_envio();
}

function rota_verificar_conta(): never {
    $u = exigir_login();
    exigir_csrf();
    auth_limitar('verificar', $u['email']);
    if ($u['email_verificado_em'] === null) auth_exigir_email();
    $pdo = db();
    $pdo->beginTransaction();
    try {
        $st = $pdo->prepare('SELECT id, email, email_verificado_em FROM usuarios WHERE id = ? FOR UPDATE');
        $st->execute([$u['id']]);
        $atual = $st->fetch();
        if ($atual && $atual['email_verificado_em'] === null) {
            auth_emitir_token($atual, 'verificar');
        }
        $pdo->commit();
    } catch (Throwable $e) {
        if ($pdo->inTransaction()) $pdo->rollBack();
        throw $e;
    }
    auth_resposta_envio();
}

function rota_auth_confirmar(string $finalidade): never {
    exigir_csrf();
    $c = corpo(8192);
    $token = is_string($c['token'] ?? null) ? $c['token'] : '';
    auth_limitar('confirmar-' . $finalidade, hash('sha256', $token));
    if (!preg_match('/^[a-f0-9]{64}$/D', $token)) erro(400, 'Link inválido ou expirado. Solicite outro.');
    $senhaHash = $finalidade === 'redefinir' ? auth_hash(auth_validar_senha($c)) : null;
    $pdo = db();
    $hash = hash('sha256', $token);
    $st = $pdo->prepare('SELECT usuario_id FROM auth_tokens WHERE token_hash = ? AND finalidade = ?');
    $st->execute([$hash, $finalidade]);
    $uid = $st->fetchColumn();
    if (!$uid) erro(400, 'Link inválido ou expirado. Solicite outro.');
    $pdo->beginTransaction();
    try {
        // Mesma ordem em emissão e consumo: usuário, depois token. Evita corrida de reenvio/consumo.
        $st = $pdo->prepare('SELECT id FROM usuarios WHERE id = ? FOR UPDATE');
        $st->execute([$uid]);
        $st = $pdo->prepare('SELECT id FROM auth_tokens WHERE token_hash = ? AND finalidade = ? AND usado_em IS NULL AND expira_em > NOW() FOR UPDATE');
        $st->execute([$hash, $finalidade]);
        $id = $st->fetchColumn();
        if (!$id) { $pdo->rollBack(); erro(400, 'Link inválido ou expirado. Solicite outro.'); }
        $pdo->prepare('UPDATE auth_tokens SET usado_em = NOW() WHERE id = ?')->execute([$id]);
        if ($finalidade === 'verificar') {
            $pdo->prepare('UPDATE usuarios SET email_verificado_em = NOW() WHERE id = ?')->execute([$uid]);
        } else {
            $pdo->prepare('UPDATE usuarios SET senha_hash = ?, auth_versao = auth_versao + 1 WHERE id = ?')->execute([$senhaHash, $uid]);
            $pdo->prepare('UPDATE auth_tokens SET usado_em = NOW() WHERE usuario_id = ? AND usado_em IS NULL')->execute([$uid]);
        }
        $pdo->commit();
    } catch (Throwable $e) {
        if ($pdo->inTransaction()) $pdo->rollBack();
        throw $e;
    }
    responder(200, ['mensagem' => $finalidade === 'verificar' ? 'E-mail verificado. Agora entre com sua senha do FORNEX.' : 'Senha atualizada. Entre novamente com a nova senha.']);
}
