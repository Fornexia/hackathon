<?php
// Conta: cadastro, login com limite de tentativas, logout, planos e assinatura.

declare(strict_types=1);
if (!defined('API')) { http_response_code(404); exit; }

const LOGIN_MAX_POR_EMAIL_E_IP = 5;    // falhas em 15 minutos
const LOGIN_MAX_POR_IP = 20;
const LOGIN_MAX_POR_EMAIL = 30;        // limite global do e-mail: segura ataque vindo de muitos IPs

function usuario_atual(): ?array {
    $id = (int)($_SESSION['uid'] ?? 0);
    if ($id <= 0) return null;
    $st = db()->prepare('SELECT id, nome, email, papel, auth_versao, email_verificacao_exigida, email_verificado_em FROM usuarios WHERE id = ?');
    $st->execute([$id]);
    $u = $st->fetch() ?: null;
    if ($u === null || (int)$u['auth_versao'] !== (int)($_SESSION['auth_versao'] ?? 0)
        || ((int)$u['email_verificacao_exigida'] === 1 && $u['email_verificado_em'] === null)) {
        $_SESSION = [];
        session_regenerate_id(true);
        return null;
    }
    return $u;
}

function exigir_login(): array {
    $u = usuario_atual();
    if ($u === null) erro(401, 'Faça login para continuar.');
    return $u;
}

/** Área técnica: o conteúdo fica fora do public_html e só sai com login. */
function rota_painel(): never {
    exigir_login();
    $arquivo = dirname(__DIR__, 2) . '/painel.json';
    if (!is_file($arquivo)) erro(503, 'A área técnica ainda não foi publicada.');
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: private, no-store');
    readfile($arquivo);
    exit;
}

function exigir_admin(): array {
    $u = exigir_login();
    if ($u['papel'] !== 'admin') erro(403, 'Acesso restrito ao administrador.');
    return $u;
}

function plano_para_json(array $p): array {
    return [
        'id' => (int)$p['id'],
        'nome' => $p['nome'],
        'preco_mensal' => (float)$p['preco_mensal'],
        'franquia' => (int)$p['franquia'],
        'preco_excedente' => (float)$p['preco_excedente'],
        'tenants' => json_decode((string)$p['tenants'], true) ?: [],
    ];
}

/** Plano da assinatura ativa do usuário, ou null. */
function plano_ativo(int $usuarioId): ?array {
    $st = db()->prepare('SELECT p.* FROM assinaturas a JOIN planos p ON p.id = a.plano_id
                         WHERE a.usuario_id = ? AND a.status = "ativa" ORDER BY a.id DESC LIMIT 1');
    $st->execute([$usuarioId]);
    $p = $st->fetch();
    return $p ? plano_para_json($p) : null;
}

function entrar(int $usuarioId, int $versao = 0): void {
    session_regenerate_id(true);   // evita fixação de sessão
    $_SESSION = [];
    $_SESSION['uid'] = $usuarioId;
    $_SESSION['auth_versao'] = $versao;
    $_SESSION['criada_em'] = $_SESSION['ativa_em'] = time();
    $_SESSION['csrf'] = bin2hex(random_bytes(32));
}

// ---------- limite de tentativas ----------

function contar_falhas(string $campo, string $valor, ?string $email = null): int {
    $sql = "SELECT COUNT(*) FROM tentativas_login WHERE $campo = ? AND criada_em > NOW() - INTERVAL 15 MINUTE";
    $args = [$valor];
    if ($email !== null) { $sql .= ' AND email = ?'; $args[] = $email; }
    $st = db()->prepare($sql);
    $st->execute($args);
    return (int)$st->fetchColumn();
}

function login_bloqueado(string $email, string $ip): bool {
    return contar_falhas('ip', $ip, $email) >= LOGIN_MAX_POR_EMAIL_E_IP
        || contar_falhas('ip', $ip) >= LOGIN_MAX_POR_IP
        || contar_falhas('email', $email) >= LOGIN_MAX_POR_EMAIL;
}

function registrar_falha(string $email, string $ip): void {
    db()->prepare('INSERT INTO tentativas_login (email, ip) VALUES (?, ?)')->execute([$email, $ip]);
    if (random_int(1, 50) === 1) {   // limpeza ocasional, sem precisar de tarefa agendada
        db()->exec('DELETE FROM tentativas_login WHERE criada_em < NOW() - INTERVAL 1 DAY');
    }
}

// ---------- rotas ----------

function rota_me(): never {
    $u = usuario_atual();
    responder(200, [
        'usuario' => $u ? usuario_para_json($u) : null,
        'plano' => $u ? plano_ativo((int)$u['id']) : null,
        'csrf' => csrf_token(),
    ]);
}

function usuario_para_json(array $u): array {
    return ['id' => (int)$u['id'], 'nome' => $u['nome'], 'email' => $u['email'],
        'papel' => $u['papel'], 'email_verificado' => $u['email_verificado_em'] !== null];
}

function rota_planos(): never {
    $linhas = db()->query('SELECT * FROM planos WHERE nome = "Único" ORDER BY id')->fetchAll();
    responder(200, array_map('plano_para_json', $linhas));
}

function rota_cadastro(): never {
    exigir_csrf();
    $c = corpo(8192);
    $nome = texto_limpo($c['nome'] ?? '', 120);
    $email = auth_email($c['email'] ?? '');
    $senha = auth_validar_senha($c);

    if ($nome === '') erro(400, 'Informe seu nome.');
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) erro(400, 'Informe um e-mail válido.');
    auth_limitar('cadastro', $email);
    auth_exigir_email();
    $hash = auth_hash($senha);
    $pdo = db();
    $pdo->beginTransaction();

    try {
        $st = $pdo->prepare('INSERT INTO usuarios (nome, email, senha_hash, papel, email_verificacao_exigida) VALUES (?, ?, ?, "usuario", 1)');
        $st->execute([$nome, $email, $hash]);
        auth_emitir_token(['id' => (int)$pdo->lastInsertId(), 'email' => $email], 'verificar');
        $pdo->commit();
    } catch (PDOException $e) {
        if ($pdo->inTransaction()) $pdo->rollBack();
        if ((int)($e->errorInfo[1] ?? 0) === 1062) auth_resposta_envio();
        throw $e;
    } catch (Throwable $e) {
        if ($pdo->inTransaction()) $pdo->rollBack();
        throw $e;
    }
    auth_resposta_envio();
}

/** Sem respostas/exit aqui: finally precisa liberar as duas travas, inclusive nas recusas. */
function validar_login(string $email, string $senha, string $ip): array {
    $chaves = array_map(fn($v) => 'login:' . substr(hash('sha256', DB_NAME . ':' . $v), 0, 58), ['ip:' . $ip, 'email:' . $email]);
    sort($chaves, SORT_STRING);
    $travadas = [];
    try {
        foreach ($chaves as $chave) {
            $st = db()->prepare('SELECT GET_LOCK(?, 5)');
            $st->execute([$chave]);
            if ((int)$st->fetchColumn() !== 1) return [429, null];
            $travadas[] = $chave;
        }
        return validar_login_travado($email, $senha, $ip);
    } finally {
        foreach (array_reverse($travadas) as $chave) {
            db()->prepare('SELECT RELEASE_LOCK(?)')->execute([$chave]);
        }
    }
}

function validar_login_travado(string $email, string $senha, string $ip): array {
    if (login_bloqueado($email, $ip)) return [429, null];
    $st = db()->prepare('SELECT id, senha_hash, auth_versao, email_verificacao_exigida, email_verificado_em FROM usuarios WHERE email = ?');
    $st->execute([$email]);
    $u = $st->fetch();
    // Mesmo sem conta, executa a verificação de hash. Hashes legados podem ter custo diferente.
    $hash = $u['senha_hash'] ?? '$argon2id$v=19$m=65536,t=4,p=1$cGp5cm15eUdXWndCT2l1UQ$y45kMLx7UCtFPNkCnRDuI9V9aPwRkAhG14VI9JwEsNM';
    $ok = password_verify($senha, $hash) && $u !== false;
    if (!$ok) {
        registrar_falha($email, $ip);
        return [401, null];
    }
    if ((int)$u['email_verificacao_exigida'] === 1 && $u['email_verificado_em'] === null) {
        registrar_falha($email, $ip);
        return [403, null];
    }
    db()->prepare('DELETE FROM tentativas_login WHERE email = ? AND ip = ?')->execute([$email, $ip]);
    return [200, $u];
}

function rota_login(): never {
    exigir_csrf();
    $c = corpo(8192);
    $email = strtolower(texto_limpo($c['email'] ?? '', 190));
    $senha = is_string($c['senha'] ?? null) ? $c['senha'] : '';
    if (strlen($senha) > 1024) erro(401, 'E-mail ou senha inválidos.');
    [$status, $u] = validar_login($email, $senha, ip_do_cliente());
    if ($status === 429) {
        header('Retry-After: 900');
        erro(429, 'Muitas tentativas. Aguarde alguns minutos e tente de novo.');
    }
    if ($status === 401) erro(401, 'E-mail ou senha inválidos.');
    if ($status === 403) responder(403, ['erro' => 'Verifique seu e-mail antes de entrar. Você pode solicitar um novo link.', 'codigo' => 'email_nao_verificado']);
    entrar((int)$u['id'], (int)$u['auth_versao']);
    $logado = usuario_atual();
    if (!$logado) erro(401, 'Sua senha foi alterada. Entre novamente.');
    responder(200, [
        'usuario' => usuario_para_json($logado),
        'plano' => plano_ativo((int)$logado['id']),
        'csrf' => csrf_token(),
    ]);
}

function rota_logout(): never {
    exigir_csrf();
    $_SESSION = [];
    $p = session_get_cookie_params();
    setcookie(session_name(), '', ['expires' => time() - 3600, 'path' => $p['path'], 'secure' => $p['secure'], 'httponly' => true, 'samesite' => 'Lax']);
    session_destroy();
    responder(200, ['ok' => true]);
}

/** Ativa um plano de demonstração. Sem pagamento, sem cartão (RF-07). */
function rota_assinatura(): never {
    $u = exigir_login();
    exigir_csrf();
    $c = corpo(1024);
    $planoId = $c['plano_id'] ?? null;
    if (!is_int($planoId) || $planoId <= 0) erro(400, 'Escolha um plano.');

    $st = db()->prepare('SELECT id FROM planos WHERE id = ? AND nome = "Único"');
    $st->execute([$planoId]);
    if (!$st->fetch()) erro(404, 'Plano não encontrado.');

    $pdo = db();
    $pdo->beginTransaction();
    try {
        $pdo->prepare('UPDATE assinaturas SET status = "cancelada" WHERE usuario_id = ? AND status = "ativa"')->execute([$u['id']]);
        $pdo->prepare('INSERT INTO assinaturas (usuario_id, plano_id) VALUES (?, ?)')->execute([$u['id'], $planoId]);
        $pdo->commit();
    } catch (Throwable $e) {
        $pdo->rollBack();
        throw $e;
    }
    responder(201, ['plano' => plano_ativo((int)$u['id'])]);
}
