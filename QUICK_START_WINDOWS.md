# 🚀 Quick Start - Windows/Kvaser

## ⚡ Instalação Rápida

### 1. Clone e execute o setup

```bash
# Baixe os arquivos ou clone o repositório
# Execute o script de setup automático:
setup_windows.bat
```

### 2. Ou instale manualmente

```bash
# 1. Instalar dependências
pip install python-can matplotlib numpy pandas

# 2. Verificar driver Kvaser
python -c "import can; print('OK')"

# 3. Testar interfaces
python -c "import can; print(can.interface.Bus.available_interfaces())"
```

## 🎯 Comandos Essenciais

### ✅ Teste Inicial (Sem Hardware)

```bash
# Monitor em modo simulação
python monitor_windows_kvaser.py --simulate
```

### 🔧 Com Hardware Kvaser

```bash
# Primeiro canal Kvaser
python monitor_windows_kvaser.py --channel 0

# Segundo canal Kvaser (se disponível)
python monitor_windows_kvaser.py --channel 1

# Com logging CSV
python monitor_windows_kvaser.py --channel 0 --csv dados.csv
```

### 🔄 Replay de Logs

```bash
# Replay arquivo de exemplo
python replay_windows_kvaser.py exemplo_log_can.log

# Replay com canal específico
python replay_windows_kvaser.py exemplo_log_can.log --channel 0

# Replay em velocidade 2x
python replay_windows_kvaser.py exemplo_log_can.log --speed 2.0

# Replay contínuo
python replay_windows_kvaser.py exemplo_log_can.log --loop
```

## 📊 Verificação de Hardware

### Driver Kvaser

```bash
# Verificar se driver está instalado
python replay_windows_kvaser.py --check-drivers

# Listar interfaces
python -c "import can; print(can.interface.Bus.available_interfaces())"
```

### Canais Disponíveis

```bash
# Testar canais 0-3
for i in 0 1 2 3; do
    python -c "import can; can.interface.Bus(channel='$i', interface='kvaser').shutdown()" && echo "Canal $i: OK" || echo "Canal $i: OFF"
done
```

## 🔍 Solução Rápida de Problemas

### ❌ "Interface kvaser not available"

```bash
# 1. Instalar driver Kvaser
# Download: https://www.kvaser.com/downloads/

# 2. Reiniciar computador
# 3. Testar novamente
python replay_windows_kvaser.py --check-drivers
```

### ❌ "No kvaser device found"

```bash
# 1. Verificar conexão USB
# 2. Verificar Device Manager (Windows)
# 3. Reinstalar driver
```

### ❌ "Permission denied"

```bash
# Executar como administrador
# Clique direito no PowerShell/CMD > "Executar como administrador"
```

## 📋 Exemplos Práticos

### 1. Monitoramento Básico

```bash
# Abrir 2 terminais:

# Terminal 1: Monitor
python monitor_windows_kvaser.py --channel 0 --csv monitor.csv

# Terminal 2: Replay do arquivo de exemplo
python replay_windows_kvaser.py exemplo_log_can.log --channel 0
```

### 2. Análise de Dados

```bash
# Gerar dados CSV
python monitor_windows_kvaser.py --channel 0 --csv dados_reais.csv

# Analisar com Python/pandas
python -c "
import pandas as pd
df = pd.read_csv('dados_reais.csv')
print('Colunas:', df.columns.tolist())
print('Linhas:', len(df))
print('Estatísticas:')
print(df.describe())
"
```

### 3. Teste de Performance

```bash
# Monitor com buffer grande
python monitor_windows_kvaser.py --channel 0 --buffer 10000 --csv perf_test.csv

# Replay rápido
python replay_windows_kvaser.py exemplo_log_can.log --speed 5.0 --loop
```

## 📁 Arquivos Importantes

- `README.md` - Documentação completa
- `setup_windows.bat` - Script de instalação automática
- `exemplo_log_can.log` - Arquivo de exemplo para testes
- `monitor_windows_kvaser.py` - Monitor principal
- `replay_windows_kvaser.py` - Replayer de logs

## 🎮 IDs CAN Comuns

| ID (Hex) | Descrição | Bytes |
|----------|-----------|-------|
| `0x18FFF3FE` | Setpoint Velocidade Compartilhado | 0-1: Velocidade |
| `0x18FFE103` | Inversor A Setpoint Torque | 3-4: Torque |
| `0x18FFA120` | Inversor A Status | 1-2: Vel, 5-6: Torque |
| `0x18FFE203` | Inversor B Setpoint Torque | 3-4: Torque |
| `0x18FFB120` | Inversor B Status | 1-2: Vel, 5-6: Torque |

## 💡 Dicas de Produtividade

1. **Use CSV**: Sempre use `--csv` para salvar dados para análise posterior
2. **Buffer**: Ajuste `--buffer` conforme necessário (padrão: 500)
3. **Simulação**: Use `--simulate` para testar sem hardware
4. **Velocidade**: Use `--speed` no replay para acelerar testes

## 🚨 Emergência

### Reset Rápido

```bash
# Se algo não funcionar, execute:
python -c "
import can
bus = can.interface.Bus(channel='0', interface='kvaser')
bus.shutdown()
print('Bus resetado')
"
```

### Verificação Completa

```bash
# Um comando para verificar tudo:
python -c "
print('=== VERIFICAÇÃO COMPLETA ===')
try:
    import can
    print('✓ python-can OK')
    interfaces = can.interface.Bus.available_interfaces()
    print(f'✓ Interfaces: {interfaces}')
    if 'kvaser' in interfaces:
        print('✓ Driver Kvaser OK')
    else:
        print('✗ Driver Kvaser NÃO encontrado')
except Exception as e:
    print(f'✗ Erro: {e}')
print('=== FIM ===')
"
```

---

**🎯 Em caso de dúvidas, execute primeiro: `python monitor_windows_kvaser.py --simulate`**