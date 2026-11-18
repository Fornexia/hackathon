<?php
// Configuração privada. A substituição é feita pelo processo/CLI, nunca por parâmetros HTTP.
declare(strict_types=1);
require getenv('FORNEX_CONFIG') ?: __DIR__ . '/hackathon-config.php';
