# Primeira vez em um Windows: instala o Docker Desktop SE ainda não houver, prepara o .env e liga tudo (chama o ligar-tudo.ps1).
#
#   Dois cliques em ligar-tudo-e-instalar-docker.bat   (ou:  powershell -ExecutionPolicy Bypass -File scripts\instalar-e-ligar.ps1)
#   Só ver o que ele faria, sem instalar nada:          ... -Teste
#   Responder "sim" sozinho (sem perguntar):             ... -Sim
#
# O que faz, nesta ordem:
#   1) Docker Desktop: se já existe, segue. Se não existe, EXPLICA e PERGUNTA antes de instalar (winget install Docker.DockerDesktop).
#   2) .env e site\hackathon-config.php: se faltarem, cria com chaves NOVAS (conferir_ambiente.py --preparar). Nunca sobrescreve nada que já exista.
#   3) Confere os outros programas (Python, PHP, bun, git) e, se faltar algum, diz o comando do guia. Eles NÃO são instalados aqui.
#   4) Chama o ligar-tudo.ps1, que abre o Docker Desktop, sobe o MariaDB e o Neo4j (o Docker baixa as imagens na primeira vez) e o resto.
#
# O que pode acontecer na instalação do Docker (por isso o script pergunta): o Windows pede permissão de administrador; o Docker Desktop pode pedir para
# ativar o WSL 2 e REINICIAR o computador (reinicie e rode este mesmo comando de novo); na primeira abertura ele mostra uma janela de termos de uso (aceite).
# Isto NÃO apaga dado nenhum, não mexe em .env que já exista e não imprime número de telefone nem chave.
param([switch]$Teste, [switch]$Sim)

$raiz = Split-Path $PSScriptRoot -Parent
function Ok($m)    { Write-Host "  [OK]    $m" -ForegroundColor Green }
function Info($m)  { Write-Host "  [..]    $m" -ForegroundColor Gray }
function Aviso($m) { Write-Host "  [AVISO] $m" -ForegroundColor Yellow }
function Erro($m)  { Write-Host "  [ERRO]  $m" -ForegroundColor Red }
function Titulo($m){ Write-Host "`n$m" -ForegroundColor Cyan }

$caminhosDoDocker = @("$env:ProgramFiles\Docker\Docker\Docker Desktop.exe", "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe",
                      "$env:LOCALAPPDATA\Programs\Docker\Docker\Docker Desktop.exe")

function Docker-Instalado {
    if ($Teste) { return $false }       # no modo de teste finge que não há Docker, para mostrar o caminho da instalação
    [bool](Get-Command docker -ErrorAction SilentlyContinue) -or [bool]($caminhosDoDocker | Where-Object { Test-Path $_ })
}

# O PATH desta janela não vê programa instalado agora há pouco: relê o PATH do sistema e do usuário.
function Atualizar-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}

Write-Host 'PREPARAR E LIGAR O AMBIENTE (primeira vez em um Windows)' -ForegroundColor Cyan
if ($Teste) { Write-Host '  MODO TESTE: nada será instalado nem ligado; só mostra o que faria.' -ForegroundColor Yellow }

# 1) Docker -----------------------------------------------------------------------------------------------------------------
Titulo '1/4  Docker Desktop'
if (Docker-Instalado) {
    Ok 'Docker Desktop já está instalado'
} else {
    Aviso 'O Docker Desktop NÃO está instalado neste computador.'
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget -and -not $Teste) {
        Erro 'Não achei o winget (instalador do Windows). Atualize o "Instalador de Aplicativo" na Microsoft Store, ou instale o Docker Desktop pelo site docker.com, e rode este comando de novo.'
        exit 1
    }
    Write-Host ''
    Write-Host '  Vou instalar com:  winget install -e --id Docker.DockerDesktop' -ForegroundColor White
    Write-Host '   - precisa de internet (algumas centenas de MB) e o Windows vai pedir PERMISSÃO DE ADMINISTRADOR;'
    Write-Host '   - o Docker Desktop pode pedir para ativar o WSL 2 e REINICIAR o computador: se pedir, reinicie e rode este mesmo comando de novo;'
    Write-Host '   - na primeira abertura ele mostra uma janela de termos de uso: aceite (pode pular o login);'
    Write-Host '   - a licença do Docker Desktop depende do tamanho da empresa; confira os termos: https://www.docker.com/legal/docker-subscription-service-agreement'
    Write-Host ''
    if ($Teste) {
        Info 'TESTE: aqui o script perguntaria "Instalar o Docker Desktop agora? [S/N]" e rodaria o winget acima. Nada foi instalado.'
    } else {
        $resposta = if ($Sim) { 'S' } else { Read-Host '  Instalar o Docker Desktop agora? [S/N]' }
        if ($resposta -notmatch '^\s*[sSyY]') { Info 'Tudo bem, não instalei. Instale o Docker Desktop e rode este comando de novo.'; exit 1 }
        Info 'Instalando o Docker Desktop (pode levar alguns minutos; aceite o pedido de administrador)...'
        winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
        $codigo = $LASTEXITCODE
        Atualizar-Path
        if (-not (Docker-Instalado)) {
            Erro "A instalação não terminou (código $codigo). Se o Windows pediu para reiniciar, reinicie e rode este mesmo comando de novo. Senão, instale pelo site docker.com."
            exit 1
        }
        Ok 'Docker Desktop instalado'
        Aviso 'Se o Windows ou o Docker pedirem para ativar o WSL 2 ou reiniciar, faça isso e rode este comando de novo.'
    }
}

# 2) .env ----------------------------------------------------------------------------------------------------------------------
Titulo '2/4  Configuração (.env)'
$py = Join-Path $raiz '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $cmd = Get-Command python -ErrorAction SilentlyContinue; $py = if ($cmd) { $cmd.Source } else { $null } }
$temEnv = Test-Path (Join-Path $raiz '.env')
$temConfig = Test-Path (Join-Path $raiz 'site\hackathon-config.php')
if ($temEnv -and $temConfig) {
    Ok '.env e site\hackathon-config.php já existem (não mexi neles)'
} elseif ($Teste) {
    Info 'TESTE: rodaria "python conferir_ambiente.py --preparar" para criar o que falta, com chaves novas.'
} elseif (-not $py) {
    Aviso 'Falta criar o .env, mas não achei o Python. Instale com:  winget install --id Python.Python.3.12 -e   (e rode este comando de novo)'
} else {
    Push-Location $raiz
    & $py conferir_ambiente.py --preparar
    Pop-Location
}

# 3) Outros programas -----------------------------------------------------------------------------------------------------------
Titulo '3/4  Outros programas (só confere; não instala)'
$faltou = $false
foreach ($p in @(@('git', 'Git.Git'), @('python', 'Python.Python.3.12'), @('php', 'PHP.PHP.NTS.8.2'), @('bun', $null))) {
    if (Get-Command $p[0] -ErrorAction SilentlyContinue) { Ok "$($p[0]) encontrado" }
    else {
        $faltou = $true
        $como = if ($p[1]) { "winget install --id $($p[1]) -e   (guia: docs\rodar-no-windows-e-no-linux.md)" } else { 'powershell -c "irm bun.sh/install.ps1 | iex"   (só o WhatsApp precisa dele)' }
        Aviso "$($p[0]) não encontrado. Para instalar:  $como"
    }
}
if (-not (Test-Path (Join-Path $raiz '.venv\Scripts\python.exe'))) {
    $faltou = $true
    Aviso 'Falta a .venv do projeto (o worker usa). Crie com:  python -m venv .venv   e   .venv\Scripts\python -m pip install -r requirements.txt'
}
if (-not $faltou) { Ok 'tudo o que o ligar-tudo precisa está no lugar' }

# 4) Ligar tudo ---------------------------------------------------------------------------------------------------------------
Titulo '4/4  Ligar tudo'
if ($Teste) {
    Info 'TESTE: chamaria scripts\ligar-tudo.ps1 (abre o Docker Desktop, sobe os bancos e o resto). Nada foi ligado.'
    exit 0
}
& (Join-Path $PSScriptRoot 'ligar-tudo.ps1')
exit $LASTEXITCODE
