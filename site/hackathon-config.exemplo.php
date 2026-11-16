<?php
// Copie para site/hackathon-config.php (ignorado pelo git) e ajuste. Em produção, o deploy.sh gera este arquivo
// FORA do public_html, a partir do .env. Nada aqui pode ir para o repositório.

const AMBIENTE = 'dev';              // 'dev' desliga o cookie Secure (http://localhost). Em produção: 'prod'
const DB_HOST = '127.0.0.1';
const DB_PORT = 3307;                // contêiner de site/dev/docker-compose.yml
const DB_NAME = 'hackathon';
const DB_USER = 'hackathon';
const DB_PASS = 'dev-senha';
const WORKER_KEY = 'troque-por-uma-chave-longa-e-aleatoria';   // mínimo 24 caracteres
const API_KEY = '';                  // legado do modelo antigo; não é mais usado
const INFERENCIA_URL = '';           // legado do modelo antigo; não é mais usado

// Login público: configurar antes de liberar o cadastro. Também aceita variáveis de ambiente.
const APP_URL = 'https://seu-dominio.example'; // origem fixa dos links, nunca o Host da requisição
const SMTP_HOST = '';
const SMTP_PORT = 587;
const SMTP_SECURITY = 'tls';          // 'tls' (STARTTLS) ou 'ssl' (TLS implícito)
const SMTP_USER = '';
const SMTP_PASS = '';
const MAIL_FROM = '';                // remetente autorizado pelo provedor SMTP
const MAIL_FROM_NAME = 'FORNEX';
const AUTH_MAIL_KEY = '';            // base64 de 32 bytes aleatórios; guardar junto do backup privado
const AUTH_IDLE_SECONDS = 1800;       // 30 minutos sem interação
const AUTH_MAX_SECONDS = 43200;      // 12 horas desde o login
// AUTH_SESSION_PATH opcional (constante ou ambiente): diretório absoluto privado e gravável.
// Padrão: site/sessoes, fora de public_html; nunca compartilhar com outro aplicativo.
