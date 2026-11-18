<?php
// API do site: PHP puro + MySQL, sem framework. O contrato está em docs/specs/001-site-e-chat/plan.md.
//
// Navegador (sessão em cookie HttpOnly; escrita exige o cabeçalho X-CSRF-Token, que vem de GET /api/me):
//   GET  /api/saude
//   GET  /api/me                          usuário, plano e token CSRF
//   GET  /api/planos
//   POST /api/cadastro  /api/login  /api/logout
//   POST /api/assinatura                  {plano_id}: ativa um plano de demonstração
//   POST /api/perguntas                   {texto}
//   GET  /api/perguntas/aberta
//   GET  /api/perguntas/{id}/eventos?desde=N
//   GET  /api/perguntas/{id}/prova        pacote de prova (ZIP) de uma consulta; ?formato=json devolve só o JSON
//   GET  /api/provas?ids=1,2,3            dossiê com várias consultas (sem ids: as concluídas da conta)
//   GET  /api/telefones                   os telefones do usuário
//   POST /api/telefones                   {numero}: liberado automaticamente
//   DELETE /api/telefones/{id}
//   GET  /api/mcp                         endereço do MCP e os tokens ativos da conta (sem o token)
//   POST /api/mcp/tokens                  gera um token MCP (aparece uma vez)
//   DELETE /api/mcp/tokens/{id}           revoga
//   GET  /api/acompanhamentos             CNPJs que a conta acompanha (alertas por e-mail)
//   POST /api/acompanhamentos             {cnpj}: exige e-mail confirmado
//   DELETE /api/acompanhamentos/{id}
//
// Administrador (papel "admin"):
//   GET  /api/admin/telefones?status=pendente|aprovado|revogado|todos
//   POST /api/admin/telefones/{id}/aprovar  e  /revogar
//
// Worker (cabeçalho X-Worker-Key, sem sessão):
//   POST /api/worker/proxima
//   POST /api/worker/perguntas/{id}/eventos
//   GET  /api/worker/telefones
//   GET  /api/worker/tokens               hashes dos tokens MCP ativos e os entes do plano de cada dono
//   GET  /api/worker/acompanhamentos      por conta confirmada: e-mail, entes do plano e CNPJs acompanhados

declare(strict_types=1);
define('API', true);

require dirname(__DIR__, 2) . '/config.php';   // fora do public_html
foreach (['base', 'auth', 'conta', 'google', 'chat', 'telefones', 'worker', 'prova', 'mcp', 'acompanhamentos'] as $modulo) {
    require __DIR__ . "/lib_$modulo.php";
}

header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');

// [método, padrão, usa sessão, função]. Os ids capturados chegam como inteiros.
$rotas = [
    ['GET',  '#^saude$#',                          false, function () {
        db()->query('SELECT 1');
        responder(200, ['ok' => true, 'hora' => date('c')]);
    }],
    ['GET',  '#^me$#',                             true,  'rota_me'],
    ['GET',  '#^planos$#',                         true,  'rota_planos'],
    ['POST', '#^cadastro$#',                       true,  'rota_cadastro'],
    ['POST', '#^login$#',                          true,  'rota_login'],
    ['POST', '#^login/google$#',                   true,  'rota_login_google'],
    ['POST', '#^logout$#',                         true,  'rota_logout'],
    ['POST', '#^email/reenviar$#',                  true,  fn() => rota_auth_solicitar('verificar')],
    ['POST', '#^email/verificar$#',                 true,  fn() => rota_auth_confirmar('verificar')],
    ['POST', '#^email/verificar-conta$#',           true,  'rota_verificar_conta'],
    ['POST', '#^senha/recuperar$#',                  true,  fn() => rota_auth_solicitar('redefinir')],
    ['POST', '#^senha/redefinir$#',                 true,  fn() => rota_auth_confirmar('redefinir')],
    ['POST', '#^sessao/atividade$#',                true,  function () {
        exigir_login(); exigir_csrf(); $_SESSION['ativa_em'] = time(); responder(200, ['ok' => true]);
    }],
    ['POST', '#^assinatura$#',                     true,  'rota_assinatura'],
    ['POST', '#^perguntas$#',                      true,  'rota_perguntas_criar'],
    ['GET',  '#^perguntas/aberta$#',               true,  'rota_pergunta_aberta'],
    ['GET',    '#^telefones$#',                       true,  'rota_telefones_listar'],
    ['POST',   '#^telefones$#',                       true,  'rota_telefones_criar'],
    ['DELETE', '#^telefones/(\d+)$#',                 true,  'rota_telefones_remover'],
    ['GET',    '#^mcp$#',                             true,  'rota_mcp_info'],
    ['POST',   '#^mcp/tokens$#',                      true,  'rota_mcp_criar'],
    ['DELETE', '#^mcp/tokens/(\d+)$#',               true,  'rota_mcp_revogar'],
    ['GET',    '#^acompanhamentos$#',                 true,  'rota_acompanhamentos_listar'],
    ['POST',   '#^acompanhamentos$#',                 true,  'rota_acompanhamentos_criar'],
    ['DELETE', '#^acompanhamentos/(\d+)$#',          true,  'rota_acompanhamentos_remover'],
    ['GET',    '#^admin/telefones$#',                 true,  'rota_admin_telefones'],
    ['POST',   '#^admin/telefones/(\d+)/aprovar$#',   true,  'rota_admin_aprovar'],
    ['POST',   '#^admin/telefones/(\d+)/revogar$#',   true,  'rota_admin_revogar'],
    ['GET',  '#^perguntas/(\d+)/eventos$#',        true,  'rota_eventos'],
    ['GET',  '#^perguntas/(\d+)/prova$#',          true,  'rota_prova'],
    ['GET',  '#^provas$#',                         true,  'rota_provas'],
    ['GET',  '#^painel$#',                         true,  'rota_painel'],
    ['POST', '#^worker/proxima$#',                 false, 'rota_worker_proxima'],
    ['POST', '#^worker/perguntas/(\d+)/eventos$#', false, 'rota_worker_eventos'],
    ['GET',  '#^worker/telefones$#',               false, 'rota_worker_telefones'],
    ['GET',  '#^worker/tokens$#',                  false, 'rota_worker_tokens'],
    ['GET',  '#^worker/acompanhamentos$#',         false, 'rota_worker_acompanhamentos'],
];

$metodo = $_SERVER['REQUEST_METHOD'];
$rota = trim((string)preg_replace('#^/api#', '', (string)parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH)), '/');

try {
    $existe = false;
    foreach ($rotas as [$m, $padrao, $usaSessao, $funcao]) {
        if (!preg_match($padrao, $rota, $g)) continue;
        $existe = true;
        if ($m !== $metodo) continue;
        if ($usaSessao) iniciar_sessao();
        $funcao(...array_map('intval', array_slice($g, 1)));
    }
    erro($existe ? 405 : 404, $existe ? 'Método não permitido.' : 'Rota não encontrada.');
} catch (Throwable $e) {
    // Mensagens SQL/SMTP podem conter dados pessoais: só classe e localização no log.
    error_log('[api] ' . $e::class . ' em ' . basename($e->getFile()) . ':' . $e->getLine());
    erro(500, 'Erro interno. Tente novamente em instantes.');
}
