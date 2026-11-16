<?php
// Base da API: banco, respostas JSON, corpo da requisição, sessão e CSRF.
// Este arquivo só define funções: se alguém abrir o endereço dele direto, não acontece nada.

declare(strict_types=1);
if (!defined('API')) { http_response_code(404); exit; }

function db(): PDO {
    static $pdo;
    if ($pdo === null) {
        $dsn = 'mysql:host=' . DB_HOST . (defined('DB_PORT') ? ';port=' . DB_PORT : '') . ';dbname=' . DB_NAME . ';charset=utf8mb4';
        $pdo = new PDO($dsn, DB_USER, DB_PASS, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]);
    }
    return $pdo;
}

/** Responde em JSON e encerra. 204 não leva corpo. */
function responder(int $status, $dados = null): never {
    http_response_code($status);
    if ($status !== 204) {
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode($dados, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    }
    exit;
}

function erro(int $status, string $mensagem): never {
    responder($status, ['erro' => $mensagem]);
}

/** Corpo JSON da requisição. Recusa corpo grande demais ou inválido. */
function corpo(int $limite = 262144): array {
    $bruto = file_get_contents('php://input', false, null, 0, $limite + 1);
    if ($bruto === false || $bruto === '') return [];
    if (strlen($bruto) > $limite) erro(413, 'Requisição grande demais.');
    $j = json_decode($bruto, true);
    if (!is_array($j)) erro(400, 'O corpo da requisição precisa ser um JSON válido.');
    return $j;
}

function ip_do_cliente(): string {
    return substr((string)($_SERVER['REMOTE_ADDR'] ?? '0.0.0.0'), 0, 45);
}

// ---------- sessão e CSRF ----------

function iniciar_sessao(): void {
    $inativa = max(1, (int)auth_config('AUTH_IDLE_SECONDS', 1800));
    $maxima = max(1, (int)auth_config('AUTH_MAX_SECONDS', 43200));
    // Diretório exclusivo: o coletor de outro site não deve apagar nossas sessões antes do prazo.
    $pasta = (string)auth_config('AUTH_SESSION_PATH', dirname(__DIR__, 2) . '/sessoes');
    if (!is_dir($pasta) && !mkdir($pasta, 0700, true) && !is_dir($pasta)) {
        throw new RuntimeException('Diretório de sessões indisponível.');
    }
    $real = realpath($pasta);
    $publico = realpath(dirname(__DIR__));
    $normalizar = fn($p) => strtolower(str_replace('\\', '/', (string)$p));
    if ($real === false || !is_writable($real) || $normalizar($real) === $normalizar($publico)
        || str_starts_with($normalizar($real) . '/', $normalizar($publico) . '/')) {
        throw new RuntimeException('Diretório de sessões deve ser privado e gravável.');
    }
    ini_set('session.save_handler', 'files');
    session_save_path($real);
    ini_set('session.gc_maxlifetime', (string)max($inativa, $maxima));
    $seguro = !(defined('AMBIENTE') && in_array(AMBIENTE, ['dev', 'test'], true));
    ini_set('session.use_strict_mode', '1');
    ini_set('session.use_only_cookies', '1');
    session_name('hsid');
    session_set_cookie_params(['lifetime' => 0, 'path' => '/', 'httponly' => true, 'secure' => $seguro, 'samesite' => 'Lax']);
    session_start();
    if (isset($_SESSION['uid'])) {
        $agora = time();
        if ($agora - (int)($_SESSION['ativa_em'] ?? $agora) >= max(1, $inativa)
            || $agora - (int)($_SESSION['criada_em'] ?? $agora) >= max(1, $maxima)) {
            $_SESSION = [];
            session_regenerate_id(true);
        } else {
            $_SESSION['ativa_em'] ??= $agora;
            $_SESSION['criada_em'] ??= $agora;
        }
    }
}

function csrf_token(): string {
    if (empty($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(32));
    return $_SESSION['csrf'];
}

/** Toda rota de escrita do navegador exige o token, que vem de GET /api/me. */
function exigir_csrf(): void {
    $enviado = $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '';
    if (!is_string($enviado) || $enviado === '' || !hash_equals(csrf_token(), $enviado)) {
        responder(403, ['erro' => 'Sua sessão expirou. Recarregue a página e tente de novo.', 'codigo' => 'csrf']);
    }
}

// ---------- validação ----------

function texto_limpo(mixed $valor, int $maximo): string {
    if (!is_string($valor)) return '';
    $valor = trim(preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $valor) ?? '');   // sem caracteres de controle
    return mb_strlen($valor) > $maximo ? '' : $valor;
}
