<?php
// Tokens MCP: a pessoa gera na página da conta e usa no Claude ou no Codex para consultar o FornexIA pelo MCP.
// O banco guarda só o SHA-256 do token; o token aparece uma vez, na hora em que é gerado.
// Migração aditiva e repetível: só cria a tabela se ela não existir.
declare(strict_types=1);

function migrar_tokens(PDO $pdo): void {
    $pdo->exec('CREATE TABLE IF NOT EXISTS tokens_mcp (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT NOT NULL,
        hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
        prefixo VARCHAR(16) NOT NULL,
        criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        revogado_em DATETIME NULL,
        INDEX (usuario_id, revogado_em),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4');
}

if (PHP_SAPI === 'cli' && realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) {
    require __DIR__ . '/config.php';
    $dsn = 'mysql:host=' . DB_HOST . (defined('DB_PORT') ? ';port=' . DB_PORT : '') . ';dbname=' . DB_NAME . ';charset=utf8mb4';
    migrar_tokens(new PDO($dsn, DB_USER, DB_PASS, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]));
    echo "Migração de tokens MCP concluída.\n";
}
