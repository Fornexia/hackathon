<?php
// Execute por cron a cada minuto, fora do document root. Não imprime destinatários, links ou credenciais.
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
define('API', true);
require __DIR__ . '/config.php';
require __DIR__ . '/public_html/api/lib_base.php';
require __DIR__ . '/public_html/api/lib_auth.php';

if (!auth_email_pronto()) { fwrite(STDERR, "Configuração de e-mail incompleta.\n"); exit(1); }
if (!auth_transporte_teste()) require __DIR__ . '/vendor/autoload.php';
$pdo = db();
$falhas = 0;
$enviados = 0;
// Retira os segredos de links usados/expirados, inclusive os que nunca chegaram a ser enviados.
$pdo->exec('UPDATE auth_emails e JOIN auth_tokens t ON t.id = e.token_id SET e.conteudo = NULL
    WHERE t.usado_em IS NOT NULL OR t.expira_em <= NOW()');
for ($n = 0; $n < 20; $n++) {
    $reserva = bin2hex(random_bytes(16));
    $pdo->prepare('UPDATE auth_emails SET reserva = ?, reserva_ate = DATE_ADD(NOW(), INTERVAL 5 MINUTE)
        WHERE enviado_em IS NULL AND conteudo IS NOT NULL AND tentativas < 5 AND disponivel_em <= NOW()
        AND (reserva_ate IS NULL OR reserva_ate < NOW()) ORDER BY id LIMIT 1')->execute([$reserva]);
    $st = $pdo->prepare('SELECT e.*, t.usado_em, t.expira_em > NOW() AS valido FROM auth_emails e JOIN auth_tokens t ON t.id = e.token_id WHERE e.reserva = ?');
    $st->execute([$reserva]);
    $linha = $st->fetch();
    if (!$linha) break;
    try {
        if ($linha['usado_em'] !== null || !$linha['valido']) {
            $pdo->prepare('UPDATE auth_emails SET conteudo = NULL, reserva = NULL, reserva_ate = NULL WHERE id = ? AND reserva = ?')->execute([$linha['id'], $reserva]);
            continue;
        }
        $bruto = base64_decode($linha['conteudo'], true);
        if ($bruto === false || strlen($bruto) < 29) throw new RuntimeException('Conteúdo inválido.');
        $json = openssl_decrypt(substr($bruto, 28), 'aes-256-gcm', auth_chave_email(), OPENSSL_RAW_DATA, substr($bruto, 0, 12), substr($bruto, 12, 16));
        if ($json === false) throw new RuntimeException('Conteúdo inválido.');
        $mensagem = json_decode($json, true, 8, JSON_THROW_ON_ERROR);
        if (auth_transporte_teste()) {
            $arquivo = (string)auth_config('AUTH_MAIL_CAPTURE');
            $anterior = umask(0077);
            try {
                if (file_put_contents($arquivo, json_encode($mensagem, JSON_THROW_ON_ERROR) . "\n", FILE_APPEND | LOCK_EX) === false) throw new RuntimeException('Captura indisponível.');
            } finally { umask($anterior); }
        } else {
            $mail = new PHPMailer\PHPMailer\PHPMailer(true);
            $mail->isSMTP();
            $mail->Host = (string)auth_config('SMTP_HOST');
            $mail->Port = (int)auth_config('SMTP_PORT', 587);
            $mail->SMTPAuth = true;
            $mail->Username = (string)auth_config('SMTP_USER');
            $mail->Password = (string)auth_config('SMTP_PASS');
            $mail->SMTPSecure = (string)auth_config('SMTP_SECURITY', 'tls');
            $mail->Timeout = 10;
            $mail->CharSet = 'UTF-8';
            $mail->setFrom((string)auth_config('MAIL_FROM'), (string)auth_config('MAIL_FROM_NAME', 'FORNEX'));
            $mail->addAddress($mensagem['email']);
            $mail->Subject = $mensagem['assunto'];
            $mail->Body = $mensagem['texto'];
            $mail->send();
        }
        $pdo->prepare('UPDATE auth_emails SET enviado_em = NOW(), conteudo = NULL, reserva = NULL, reserva_ate = NULL WHERE id = ? AND reserva = ?')->execute([$linha['id'], $reserva]);
        $enviados++;
    } catch (Throwable) {
        // Sem mensagens da biblioteca SMTP: podem conter o destinatário e dados do servidor.
        $pdo->prepare('UPDATE auth_emails SET tentativas = tentativas + 1,
            disponivel_em = DATE_ADD(NOW(), INTERVAL 5 MINUTE), reserva = NULL, reserva_ate = NULL WHERE id = ? AND reserva = ?')->execute([$linha['id'], $reserva]);
        $falhas++;
    }
}
// Retenção limitada dos registros; a conta e seus relacionamentos permanecem intactos.
$pdo->exec('DELETE FROM auth_tokens WHERE expira_em < NOW() - INTERVAL 7 DAY');
echo "E-mails processados: $enviados; falhas: $falhas.\n";
exit($falhas ? 1 : 0);
