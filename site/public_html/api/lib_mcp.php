<?php
// Tokens MCP: a pessoa conecta a IA dela (Claude, Codex) às consultas do FornexIA pelo MCP.
// O token aparece uma única vez, quando é gerado; o banco guarda só o SHA-256.
// O que o token enxerga vem do plano da conta, lido pelo servidor do MCP (GET /api/worker/tokens): nunca do token nem do pedido.

declare(strict_types=1);
if (!defined('API')) { http_response_code(404); exit; }

const MCP_TOKENS_POR_CONTA = 3;
const MCP_URL_PADRAO = 'https://luks108-samgung-x40.tailc7827f.ts.net/mcp';

function mcp_url(): string {
    return defined('MCP_URL') && is_string(MCP_URL) && MCP_URL !== '' ? MCP_URL : MCP_URL_PADRAO;
}

/** O mesmo formato das chaves da API (api/chaves.py): "fx_" + 24 bytes aleatórios em base64 de URL. */
function mcp_novo_token(): string {
    return 'fx_' . rtrim(strtr(base64_encode(random_bytes(24)), '+/', '-_'), '=');
}

function mcp_tokens_da_conta(int $usuarioId): array {
    $st = db()->prepare('SELECT id, prefixo, criado_em FROM tokens_mcp WHERE usuario_id = ? AND revogado_em IS NULL ORDER BY id');
    $st->execute([$usuarioId]);
    return array_map(fn($t) => ['id' => (int)$t['id'], 'prefixo' => $t['prefixo'], 'criado_em' => $t['criado_em']], $st->fetchAll());
}

function rota_mcp_info(): never {
    $u = exigir_login();
    responder(200, ['url' => mcp_url(), 'limite' => MCP_TOKENS_POR_CONTA, 'tokens' => mcp_tokens_da_conta((int)$u['id'])]);
}

function rota_mcp_criar(): never {
    $u = exigir_login();
    exigir_csrf();
    if (plano_ativo((int)$u['id']) === null) erro(403, 'Ative um plano para gerar um token.');

    $token = mcp_novo_token();
    $prefixo = substr($token, 0, 10);
    $pdo = db();
    $pdo->beginTransaction();
    try {
        // Trava a conta: pedidos simultâneos não furam o limite.
        $pdo->prepare('SELECT id FROM usuarios WHERE id = ? FOR UPDATE')->execute([$u['id']]);
        $st = $pdo->prepare('SELECT COUNT(*) FROM tokens_mcp WHERE usuario_id = ? AND revogado_em IS NULL');
        $st->execute([$u['id']]);
        if ((int)$st->fetchColumn() >= MCP_TOKENS_POR_CONTA) {
            $pdo->rollBack();
            erro(400, 'Cada conta pode ter até ' . MCP_TOKENS_POR_CONTA . ' tokens ativos. Revogue um para gerar outro.');
        }
        $pdo->prepare('INSERT INTO tokens_mcp (usuario_id, hash, prefixo) VALUES (?, ?, ?)')
            ->execute([$u['id'], hash('sha256', $token), $prefixo]);
        $id = (int)$pdo->lastInsertId();
        $pdo->commit();
    } catch (Throwable $e) {
        if ($pdo->inTransaction()) $pdo->rollBack();
        throw $e;
    }
    responder(201, ['id' => $id, 'token' => $token, 'prefixo' => $prefixo, 'url' => mcp_url()]);
}

function rota_mcp_revogar(int $id): never {
    $u = exigir_login();
    exigir_csrf();
    $st = db()->prepare('UPDATE tokens_mcp SET revogado_em = NOW() WHERE id = ? AND usuario_id = ? AND revogado_em IS NULL');
    $st->execute([$id, $u['id']]);
    if ($st->rowCount() === 0) erro(404, 'Token não encontrado.');   // inexistente, revogado ou de outra conta: mesma resposta
    responder(204);
}

/** Para o servidor do MCP: hashes dos tokens ativos e os entes do plano de cada dono. Quem perdeu o plano deixa de aparecer. */
function rota_worker_tokens(): never {
    exigir_worker();
    $linhas = db()->query('SELECT t.hash, t.usuario_id, p.tenants FROM tokens_mcp t
        JOIN assinaturas a ON a.usuario_id = t.usuario_id AND a.status = "ativa"
        JOIN planos p ON p.id = a.plano_id
        WHERE t.revogado_em IS NULL ORDER BY t.id')->fetchAll();
    responder(200, array_map(fn($l) => ['hash' => $l['hash'], 'usuario_id' => (int)$l['usuario_id'],
        'tenants' => json_decode((string)$l['tenants'], true) ?: []], $linhas));
}
