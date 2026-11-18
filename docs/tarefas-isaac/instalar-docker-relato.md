# Item 0d (diário do Rodrigo de 14/11): `ligar-tudo-e-instalar-docker.bat` no Windows do Isaac

**Data:** 15/11/2026. **Máquina:** Windows 11 Home, com Docker Desktop já instalado (em `%LOCALAPPDATA%\Programs\DockerDesktop`), Python, PHP, bun e git.
**Versão:** `scripts/instalar-e-ligar.ps1` igual ao da `feat/portabilidade-windows-linux` em `584efc2` (só muda o fim de linha).

## O que rodei

```
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\instalar-e-ligar.ps1 -Teste
```

Código de saída 0. As 4 etapas apareceram na ordem certa:

| Etapa | Resultado |
|---|---|
| 1/4 Docker Desktop | No modo de teste ele finge que falta Docker: mostrou o comando `winget install -e --id Docker.DockerDesktop`, os avisos (administrador, WSL 2, reinício, termos de uso, licença) e disse que nada foi instalado |
| 2/4 Configuração | `.env e site\hackathon-config.php já existem (não mexi neles)` |
| 3/4 Outros programas | git, python, php e bun encontrados; "tudo o que o ligar-tudo precisa está no lugar" |
| 4/4 Ligar tudo | Disse que chamaria o `ligar-tudo.ps1` e não ligou nada |

## O que não rodei, e por quê

- **A instalação de verdade do Docker** (o objetivo do item): esta máquina já tem Docker Desktop. Precisa de alguém **sem** Docker.
- **A execução sem `-Teste`:** nesta máquina ela só pularia a instalação e chamaria o `ligar-tudo.ps1`, que o Rodrigo já verificou numa máquina com Docker. Além disso, o `ligar-tudo` abre o gateway do WhatsApp, e aqui ele não está pareado: pediria para ligar um número por QR code.

## Para quem for testar sem Docker

Anotar: se o Windows pediu administrador, se o Docker pediu WSL 2 ou reinício, quanto tempo levou, se precisou rodar o comando de novo depois de reiniciar, e o que apareceu na janela dos termos de uso.
