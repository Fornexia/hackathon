<?php
// Migração aditiva e repetível; não altera senhas, perfis, planos ou dados existentes.
declare(strict_types=1);

function migrar_autenticacao(PDO $pdo): void {
    if ((int)$pdo->query("SELECT GET_LOCK('fornex_auth_migration', 30)")->fetchColumn() !== 1) {
        throw new RuntimeException('Migração ocupada.');
    }
    try {
        $colunas = [
            'email_verificado_em' => 'DATETIME NULL',
            // Contas anteriores continuam funcionando, sem afirmar que foram verificadas.
            'email_verificacao_exigida' => 'TINYINT NOT NULL DEFAULT 0',
            'auth_versao' => 'INT UNSIGNED NOT NULL DEFAULT 0',
        ];
        foreach ($colunas as $coluna => $tipo) {
            $st = $pdo->prepare('SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = "usuarios" AND COLUMN_NAME = ?');
            $st->execute([$coluna]);
            if (!(int)$st->fetchColumn()) $pdo->exec("ALTER TABLE usuarios ADD COLUMN $coluna $tipo");
        }
        $pdo->exec('CREATE TABLE IF NOT EXISTS auth_tokens (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            usuario_id INT NOT NULL,
            finalidade ENUM("verificar", "redefinir") NOT NULL,
            token_hash CHAR(64) NOT NULL UNIQUE,
            expira_em DATETIME NOT NULL,
            usado_em DATETIME NULL,
            criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX (usuario_id, finalidade),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4');
        $pdo->exec('CREATE TABLE IF NOT EXISTS auth_limites (
            chave CHAR(64) PRIMARY KEY,
            inicio DATETIME NOT NULL,
            total INT UNSIGNED NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4');
        $pdo->exec('CREATE TABLE IF NOT EXISTS auth_emails (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            token_id BIGINT UNSIGNED NOT NULL,
            conteudo MEDIUMTEXT NULL,
            tentativas INT NOT NULL DEFAULT 0,
            disponivel_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reserva CHAR(32) NULL,
            reserva_ate DATETIME NULL,
            enviado_em DATETIME NULL,
            INDEX (disponivel_em, enviado_em),
            FOREIGN KEY (token_id) REFERENCES auth_tokens(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4');
    } finally {
        $pdo->query("SELECT RELEASE_LOCK('fornex_auth_migration')");
    }
}

if (PHP_SAPI === 'cli' && realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) {
    require __DIR__ . '/config.php';
    $dsn = 'mysql:host=' . DB_HOST . (defined('DB_PORT') ? ';port=' . DB_PORT : '') . ';dbname=' . DB_NAME . ';charset=utf8mb4';
    migrar_autenticacao(new PDO($dsn, DB_USER, DB_PASS, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]));
    echo "Migração de autenticação concluída.\n";
}
