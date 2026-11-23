# ALR TECH — Monitor de IPs v1.1

Monitoramento local de **disponibilidade (online/offline) e latência ICMP** com histórico em SQLite e dashboard no navegador.

## Windows
1. Instale Python 3.11 ou superior, com `py` disponível no terminal.
2. Extraia o ZIP para uma pasta e execute `iniciar_windows.bat`.
3. Abra http://localhost:8501 (o arquivo .bat também tenta abrir o navegador).
4. Os três IPs de exemplo já estão cadastrados no primeiro início. Você pode cadastrar outros IPs na barra lateral. Mantenha a janela **Coletor** aberta.
5. Selecione 1, 2, 5 ou 30 minutos e o período (hoje, ontem, 7 dias ou datas personalizadas).

A primeira execução instala as bibliotecas e pode exigir acesso à internet. Para desligar, feche a janela do coletor e do dashboard.

## Personalização
- Coleta a cada **5 segundos** por padrão. Modifique a variável de ambiente `MONITOR_INTERVAL_SECONDS` antes de iniciar o coletor para alterar.
- Histórico preservado por **90 dias** por padrão (`MONITOR_RETENTION_DAYS`).
- Dados armazenados em `monitor.db` na mesma pasta. Faça backup deste arquivo com o coletor parado.
- O dashboard é restrito a `127.0.0.1` (somente o computador local).

## Observações
- Pings ICMP podem ser bloqueados pelo firewall, gerando status Offline mesmo com o equipamento ativo.
- O horário e fuso dependem da configuração do Windows e da máquina coletora.
- A disponibilidade exibida reflete o percentual de **amostras**, não tempo exato de inatividade.
- Esta versão **não** captura volume de tráfego, conexões, portas ou uso por dispositivo. Para isso, é necessária integração com SNMP, NetFlow/sFlow, API do Meraki/FortiGate ou dados de um switch.
- O computador deve permanecer ligado, e o coletor deve estar em execução para haver histórico contínuo.


## IPs iniciais para testes
| Descrição | IP |
|---|---|
| IP Exemplo 01 | `187.45.181.182` |
| IP Exemplo 02 | `189.73.48.167` |
| IP Exemplo 03 | `187.49.84.183` |

Os três endereços são cadastrados automaticamente **quando o banco não contém nenhum IP**. A inclusão não comprova que estejam online nem que respondam a ICMP. Testes de ping em endereços públicos dependem das regras de rede e de firewall. Use apenas ativos próprios ou que você esteja autorizado a monitorar continuamente.

## Publicar o código no GitHub

**Opção pelo navegador (sem Git instalado):**
1. Crie um repositório novo no GitHub (por exemplo `alr-tech-monitor-ips`), sem inicializá-lo com README.
2. Extraia o ZIP e abra a pasta `ip-monitor`.
3. No repositório, escolha **Add file → Upload files**; envie os arquivos da pasta, inclusive `.gitignore`, mas **não** envie `.venv`, `monitor.db`, arquivos `-wal` e `-shm` ou relatórios CSV.
4. Clique em **Commit changes**.

**Opção pelo Git (PowerShell na pasta `ip-monitor`):**
```powershell
git init
git add .
git commit -m "Versão 1.1 - IPs de exemplo e dashboard"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/alr-tech-monitor-ips.git
git push -u origin main
```
Substitua `SEU-USUARIO` pelo nome da sua conta. Caso use o GitHub Pages, lembre que **ele não executa Python, Streamlit, ping ou SQLite**. A publicação do repositório hospeda o código, mas o dashboard e o coletor precisam executar em um computador/servidor (ou em um serviço compatível com Python).

## Segurança
- O dashboard inicia somente em `127.0.0.1`; não o exponha diretamente à internet sem autenticação, HTTPS e controles de acesso.
- O banco e histórico local ficam fora do Git graças ao `.gitignore`.
- Os dados exibidos são medições reais somente depois que o coletor for iniciado.
