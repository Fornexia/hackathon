<?php
// Acompanhamento de fornecedores: a pessoa escolhe CNPJs na página da conta e recebe um e-mail quando algo muda neles.
// Quem lê esta tabela e manda os e-mails é o monitor de alertas (alertas/ponte_site.py), pela rota protegida do worker.
// Migração aditiva e repetível: só cria a tabela se ela não existir.
declare(strict_types=1);

function migrar_acompanhamentos(PDO $pdo): void {
    $pdo->exec('CREATE TABLE IF NOT EXISTS acompanhamentos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        usuario_id INT NOT NULL,
        cnpj CHAR(14) CHARACTER SET ascii NOT NULL,
        criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        cancelado_em DATETIME NULL,
        INDEX (usuario_id, cancelado_em),
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4');
}

if (PHP_SAPI === 'cli' && realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) {
    require __DIR__ . '/config.php';
    $dsn = 'mysql:host=' . DB_HOST . (defined('DB_PORT') ? ';port=' . DB_PORT : '') . ';dbname=' . DB_NAME . ';charset=utf8mb4';
    migrar_acompanhamentos(new PDO($dsn, DB_USER, DB_PASS, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]));
    echo "Migração de acompanhamentos concluída.\n";
}
