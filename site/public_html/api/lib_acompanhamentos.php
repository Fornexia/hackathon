<?php
// Acompanhar fornecedores (alertas por e-mail). A pessoa escolhe CNPJs; o monitor do notebook compara a base com a foto anterior
// e manda um e-mail quando aparece sanção, contrato ou mudança cadastral. Só recebe aviso quem confirmou o e-mail.
// O que o aviso enxerga vem do plano da conta, lido pelo monitor em GET /api/worker/acompanhamentos.

declare(strict_types=1);
if (!defined('API')) { http_response_code(404); exit; }

const ACOMPANHAMENTOS_POR_CONTA = 10;

/** 14 dígitos com os dois dígitos verificadores certos. Aceita pontuação na entrada; devolve só os dígitos, ou null. */
function normalizar_cnpj(mixed $bruto): ?string {
    if (!is_string($bruto) || strlen($bruto) > 30 || !preg_match('#^[\d\s./\-]+$#D', $bruto)) return null;
    $d = preg_replace('/\D+/', '', $bruto);
    if ($d === null || strlen($d) !== 14 || preg_match('/^(\d)\1{13}$/', $d)) return null;
    foreach ([12, 13] as $n) {
        $pesos = $n === 12 ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
        $soma = 0;
        foreach ($pesos as $i => $p) $soma += (int)$d[$i] * $p;
        $resto = $soma % 11;
        if ((int)$d[$n] !== ($resto < 2 ? 0 : 11 - $resto)) return null;
    }
    return $d;
}

function email_verificado(int $usuarioId): bool {
    $st = db()->prepare('SELECT email_verificado_em IS NOT NULL FROM usuarios WHERE id = ?');
    $st->execute([$usuarioId]);
    return (bool)$st->fetchColumn();
}

function acompanhamentos_da_conta(int $usuarioId): array {
    $st = db()->prepare('SELECT id, cnpj, criado_em FROM acompanhamentos WHERE usuario_id = ? AND cancelado_em IS NULL ORDER BY id');
    $st->execute([$usuarioId]);
    return array_map(fn($a) => ['id' => (int)$a['id'], 'cnpj' => $a['cnpj'], 'criado_em' => $a['criado_em']], $st->fetchAll());
}

function rota_acompanhamentos_listar(): never {
    $u = exigir_login();
    responder(200, ['itens' => acompanhamentos_da_conta((int)$u['id']), 'limite' => ACOMPANHAMENTOS_POR_CONTA,
                    'email_verificado' => email_verificado((int)$u['id'])]);
}

function rota_acompanhamentos_criar(): never {
    $u = exigir_login();
    exigir_csrf();
    $c = corpo(1024);
    $cnpj = normalizar_cnpj($c['cnpj'] ?? null);
    if ($cnpj === null) erro(400, 'Informe um CNPJ válido, com os 14 números, como 12.345.678/0001-95.');
    if (plano_ativo((int)$u['id']) === null) erro(403, 'Ative um plano para acompanhar fornecedores.');
    if (!email_verificado((int)$u['id'])) {
        responder(403, ['erro' => 'Confirme o seu e-mail para receber os alertas: use o botão "Verificar agora" em Seus dados.', 'codigo' => 'email_nao_verificado']);
    }
    $pdo = db();
    $pdo->beginTransaction();
    try {
        // Trava a conta: pedidos simultâneos não furam o limite nem duplicam o CNPJ.
        $pdo->prepare('SELECT id FROM usuarios WHERE id = ? FOR UPDATE')->execute([$u['id']]);
        $st = $pdo->prepare('SELECT cnpj FROM acompanhamentos WHERE usuario_id = ? AND cancelado_em IS NULL');
        $st->execute([$u['id']]);
        $ativos = $st->fetchAll(PDO::FETCH_COLUMN);
        if (in_array($cnpj, $ativos, true)) { $pdo->rollBack(); erro(409, 'Você já acompanha este CNPJ.'); }
        if (count($ativos) >= ACOMPANHAMENTOS_POR_CONTA) {
            $pdo->rollBack();
            erro(400, 'Cada conta pode acompanhar até ' . ACOMPANHAMENTOS_POR_CONTA . ' CNPJs. Remova um para incluir outro.');
        }
        $pdo->prepare('INSERT INTO acompanhamentos (usuario_id, cnpj) VALUES (?, ?)')->execute([$u['id'], $cnpj]);
        $id = (int)$pdo->lastInsertId();
        $pdo->commit();
    } catch (Throwable $e) {
        if ($pdo->inTransaction()) $pdo->rollBack();
        throw $e;
    }
    responder(201, ['id' => $id, 'cnpj' => $cnpj]);
}

function rota_acompanhamentos_remover(int $id): never {
    $u = exigir_login();
    exigir_csrf();
    $st = db()->prepare('UPDATE acompanhamentos SET cancelado_em = NOW() WHERE id = ? AND usuario_id = ? AND cancelado_em IS NULL');
    $st->execute([$id, $u['id']]);
    if ($st->rowCount() === 0) erro(404, 'Acompanhamento não encontrado.');   // inexistente ou de outra conta: mesma resposta
    responder(204);
}

/** Para o monitor de alertas: por conta com e-mail confirmado e plano ativo, o e-mail, os entes do plano e os CNPJs acompanhados. */
function rota_worker_acompanhamentos(): never {
    exigir_worker();
    $linhas = db()->query('SELECT u.id AS usuario_id, u.email, p.tenants, a.id AS acompanhamento_id, a.cnpj FROM acompanhamentos a
        JOIN usuarios u ON u.id = a.usuario_id AND u.email_verificado_em IS NOT NULL
        JOIN assinaturas s ON s.usuario_id = u.id AND s.status = "ativa"
        JOIN planos p ON p.id = s.plano_id
        WHERE a.cancelado_em IS NULL ORDER BY u.id, a.id')->fetchAll();
    $contas = [];
    foreach ($linhas as $l) {
        $id = (int)$l['usuario_id'];
        $contas[$id] ??= ['usuario_id' => $id, 'email' => $l['email'], 'tenants' => json_decode((string)$l['tenants'], true) ?: [], 'cnpjs' => [], 'acompanhamentos' => []];
        if (!in_array($l['cnpj'], $contas[$id]['cnpjs'], true)) {
            $contas[$id]['cnpjs'][] = $l['cnpj'];
            $contas[$id]['acompanhamentos'][] = ['id' => (int)$l['acompanhamento_id'], 'cnpj' => $l['cnpj']];
        }
    }
    responder(200, array_values($contas));
}
