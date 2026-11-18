<?php
// Cria as tabelas, os planos de demonstração e, se pedido, o administrador. Roda no servidor, por SSH:
//   php ~/domains/fornexia.figueiredo.dev/setup.php admin@email "Nome" senha
// (fica ao lado do hackathon-config.php, fora do public_html)
// Pode rodar de novo: tabelas usam IF NOT EXISTS, os planos são atualizados e o admin é atualizado.

declare(strict_types=1);

if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }   // nunca pela web

require __DIR__ . '/config.php';

$dsn = 'mysql:host=' . DB_HOST . (defined('DB_PORT') ? ';port=' . DB_PORT : '') . ';dbname=' . DB_NAME . ';charset=utf8mb4';
$pdo = new PDO($dsn, DB_USER, DB_PASS, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);

$tabelas = [
    'usuarios' => 'CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(120) NOT NULL,
        email VARCHAR(190) NOT NULL UNIQUE,
        senha_hash VARCHAR(255) NOT NULL,
        papel ENUM("admin","usuario") NOT NULL DEFAULT "usuario",
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',

    // Planos de demonstração: os valores são hipótese, não preço validado.
    'planos' => 'CREATE TABLE IF NOT EXISTS planos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(60) NOT NULL UNIQUE,
        preco_mensal DECIMAL(10,2) NOT NULL,
        franquia INT NOT NULL,
        preco_excedente DECIMAL(10,2) NOT NULL,
        tenants JSON NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',

    'assinaturas' => 'CREATE TABLE IF NOT EXISTS assinaturas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT NOT NULL,
        plano_id INT NOT NULL,
        status ENUM("ativa","cancelada") NOT NULL DEFAULT "ativa",
        criada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX (usuario_id, status),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
        FOREIGN KEY (plano_id) REFERENCES planos(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',

    'telefones' => 'CREATE TABLE IF NOT EXISTS telefones (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT NOT NULL,
        numero VARCHAR(20) NOT NULL UNIQUE,
        status ENUM("pendente","aprovado","revogado") NOT NULL DEFAULT "aprovado",
        aprovado_por INT NULL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX (usuario_id),
        INDEX (status),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
        FOREIGN KEY (aprovado_por) REFERENCES usuarios(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',

    // A fila: o notebook busca a pergunta mais antiga e devolve os eventos. Os entes são copiados do plano
    // no momento da pergunta, então mudar de plano depois não altera uma consulta em andamento.
    'perguntas' => 'CREATE TABLE IF NOT EXISTS perguntas (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT NOT NULL,
        plano_id INT NOT NULL,
        texto VARCHAR(500) NOT NULL,
        tenants JSON NOT NULL,
        status ENUM("fila","processando","concluida","erro") NOT NULL DEFAULT "fila",
        criada_em DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
        iniciada_em DATETIME(3) NULL,
        concluida_em DATETIME(3) NULL,
        duracao_ms INT NULL,
        INDEX (status, id),
        INDEX (usuario_id, status),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
        FOREIGN KEY (plano_id) REFERENCES planos(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',

    'eventos' => 'CREATE TABLE IF NOT EXISTS eventos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        pergunta_id INT NOT NULL,
        seq INT NOT NULL,
        tipo ENUM("consulta","texto","fonte","fim","erro") NOT NULL,
        dados JSON NULL,
        criado_em DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
        UNIQUE KEY pergunta_seq (pergunta_id, seq),
        FOREIGN KEY (pergunta_id) REFERENCES perguntas(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',

    // Só falhas: serve para limitar tentativas de login.
    'tentativas_login' => 'CREATE TABLE IF NOT EXISTS tentativas_login (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(190) NOT NULL,
        ip VARCHAR(45) NOT NULL,
        criada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX (email, ip, criada_em),
        INDEX (ip, criada_em)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4',
];
foreach ($tabelas as $nome => $sql) {
    $pdo->exec($sql);
}
require __DIR__ . '/migrar-autenticacao.php';
migrar_autenticacao($pdo);
require __DIR__ . '/migrar-tokens.php';
migrar_tokens($pdo);
require __DIR__ . '/migrar-acompanhamentos.php';
migrar_acompanhamentos($pdo);

// Elimina a etapa de aprovação também nos cadastros anteriores e no padrão do banco.
$pdo->exec('ALTER TABLE telefones ALTER COLUMN status SET DEFAULT "aprovado"');
$pdo->exec('UPDATE telefones SET status = "aprovado", aprovado_por = NULL WHERE status = "pendente"');

// Plano único de demonstração (R$ 149 por mês, conforme o pitch de 06/11/2026, sem franquia nem excedente).
// O valor é hipótese, não preço validado. Franquia e excedente ficam em 0: o banco ainda tem as colunas.
// Desde 14/11/2026 o plano inclui a União (sanções CEIS/CNEP e cadastro da Receita).
$planos = [
    ['Único', 149.00, 0, 0.00, ['pe-estado', 'pe-garanhuns', 'br-uniao']],
];
$pdo->beginTransaction();
try {
    $st = $pdo->prepare('INSERT INTO planos (nome, preco_mensal, franquia, preco_excedente, tenants) VALUES (?, ?, ?, ?, ?)
                         ON DUPLICATE KEY UPDATE preco_mensal = VALUES(preco_mensal), franquia = VALUES(franquia),
                         preco_excedente = VALUES(preco_excedente), tenants = VALUES(tenants)');
    foreach ($planos as [$nome, $preco, $franquia, $excedente, $tenants]) {
        $st->execute([$nome, $preco, $franquia, $excedente, json_encode($tenants)]);
    }
    // Preserva planos antigos referenciados no histórico de perguntas e assinaturas canceladas.
    // Só a oferta Único fica disponível na API; assinaturas ativas antigas passam para ela.
    $pdo->exec('UPDATE assinaturas a JOIN planos antigo ON antigo.id = a.plano_id
        JOIN planos novo ON novo.nome = "Único"
        SET a.plano_id = novo.id
        WHERE a.status = "ativa" AND antigo.nome IN ("Município", "Estado")');
    $pdo->commit();
} catch (Throwable $e) {
    if ($pdo->inTransaction()) $pdo->rollBack();
    throw $e;
}

[$_, $email, $nome, $senha] = $argv + [null, null, null, null];
if ($email && $senha) {
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        fwrite(STDERR, "E-mail do admin inválido: $email\n");
        exit(1);
    }
    // No site publicado o admin tem poder sobre as contas de todos: nada de senha curta ou conhecida.
    // Em desenvolvimento (AMBIENTE = 'dev') vale qualquer senha, para facilitar os testes.
    if (!defined('AMBIENTE') || AMBIENTE !== 'dev') {
        $conhecidas = ['admin', 'senha', 'password', '123456', '12345678', 'senha123', 'admin123', 'senha-local-123', 'trocar-esta-senha'];
        if (strlen($senha) < 12 || in_array(strtolower($senha), $conhecidas, true)) {
            fwrite(STDERR, "Senha do admin recusada: em produção ela precisa ter pelo menos 12 caracteres e não pode ser uma senha comum.\n");
            exit(1);
        }
    }
    $st = $pdo->prepare('INSERT INTO usuarios (nome, email, senha_hash, papel) VALUES (?, ?, ?, "admin")
                         ON DUPLICATE KEY UPDATE nome = VALUES(nome), senha_hash = VALUES(senha_hash), papel = "admin"');
    $st->execute([$nome ?: 'Admin', strtolower($email), password_hash($senha, PASSWORD_DEFAULT)]);
    echo "admin pronto: $email\n";
}
echo 'tabelas ok (' . count($tabelas) . '), planos: ' . count($planos) . "\n";
