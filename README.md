# Monitor CAN - Dois Inversores e Replay de Logs

Este repositório contém ferramentas para trabalhar com comunicação CAN em Windows, com foco no driver Kvaser.

## 📋 Descrição

- **Replayer CAN**: Reproduz mensagens CAN de arquivos de log do candump
- **Monitor Dual**: Monitora dois inversores CAN em tempo real com visualização gráfica
- **Compatibilidade Windows**: Totalmente funcional com driver Kvaser no Windows

## 🚀 Instalação no Windows

### 1. Instalar Python 3.8+

```bash
# Baixe e instale Python 3.8+ de https://python.org
# Marque "Add Python to PATH" durante a instalação
```

### 2. Instalar Driver Kvaser

1. Baixe o **Kvaser Driver** em: https://www.kvaser.com/downloads/
2. Instale o **Windows Driver** (Kvaser Windows Driver Package)
3. Reinicie o computador após a instalação

### 3. Instalar dependências

```bash
# Clone ou baixe este repositório
# Abra o Prompt de Comando ou PowerShell na pasta do projeto

# Instale as dependências
pip install python-can matplotlib numpy pandas
```

### 4. Testar instalação do Kvaser

```bash
# Verificar dispositivos Kvaser disponíveis
python -c "import can; print(can.interface.Bus(interface='kvaser'))"
```

## 🎯 Scripts Disponíveis

### 1. Monitor de Dois Inversores (`monitor_dual_inverter.py`)

Monitora dois inversores CAN simultaneamente com visualização em tempo real.

#### Uso Básico - Modo Simulação (Para testar no Windows):

```bash
python monitor_dual_inverter.py --simulate
```

#### Uso com Hardware Kvaser:

```bash
# Para primeira interface Kvaser
python monitor_dual_inverter.py --interface kvaser --channel 0

# Para segunda interface Kvaser
python monitor_dual_inverter.py --interface kvaser --channel 1

# Com logging CSV
python monitor_dual_inverter.py --interface kvaser --channel 0 --csv dados_inversores.csv
```

#### Parâmetros Disponíveis:

- `--interface`: Interface CAN (kvaser, socketcan, ixxat, pcan)
- `--channel`: Canal (0, 1, etc. para Kvaser)
- `--simulate`: Modo simulação (dados sintéticos)
- `--buffer`: Tamanho do buffer (padrão: 8000)
- `--csv`: Arquivo CSV para salvar dados

### 2. Replayer CAN (`replay_can_log.py`)

Reproduz mensagens CAN de arquivos de log do candump.

#### Uso Básico:

```bash
# Com interface padrão (para testar no Windows, use simulação do monitor)
python replay_can_log.py arquivo.log --interface vcan0
```

#### Para usar com Kvaser:

```bash
# Para interface Kvaser 0
python replay_can_log.py arquivo.log --interface can0

# Repetir replay indefinidamente
python replay_can_log.py arquivo.log --interface can0 --loop

# Velocidade 2x mais rápida
python replay_can_log.py arquivo.log --interface can0 --speed 2.0
```

#### Parâmetros:

- `arquivo.log`: Arquivo de log do candump
- `--interface`: Interface CAN (can0, can1 para Kvaser)
- `--speed`: Fator de velocidade (1.0 = tempo real)
- `--loop`: Repetir indefinidamente

## 🔧 Configuração para Kvaser

### Identificar Interfaces Kvaser

```bash
# Listar interfaces disponíveis
python -c "import can; print(can.interface.Bus.available_interfaces())"
```

### Canais Kvaser Comuns:

- **Canal 0**: Primeira interface Kvaser (USB, PCIe, etc.)
- **Canal 1**: Segunda interface Kvaser (se houver)

### Exemplo de Configuração Real:

```bash
# Monitorar inversor A e B em interfaces diferentes
python monitor_dual_inverter.py --interface kvaser --channel 0 --csv inversor_a_b.csv
```

## 📊 Formato de Dados

### IDs CAN Monitorados:

1. **Setpoint Velocidade Compartilhado**: `0x18FFF3FE`
   - Bytes 0-1: Velocidade (int16, offset -32000)

2. **Inversor A - Setpoint Torque**: `0x18FFE103`
   - Bytes 3-4: Torque (float × 526.3157, offset -60)

3. **Inversor A - Status**: `0x18FFA120`
   - Bytes 1-2: Velocidade atual
   - Bytes 5-6: Torque atual

4. **Inversor B - Setpoint Torque**: `0x18FFE203`
   - Bytes 3-4: Torque (float × 526.3157, offset -60)

5. **Inversor B - Status**: `0x18FFB120`
   - Bytes 1-2: Velocidade atual
   - Bytes 5-6: Torque atual

## 💡 Exemplos Práticos

### Exemplo 1: Teste Rápido (Simulação)

```bash
# Monitor com dados sintéticos
python monitor_dual_inverter.py --simulate --csv teste_simulacao.csv
```

### Exemplo 2: Monitoramento Real

```bash
# Com hardware Kvaser conectado
python monitor_dual_inverter.py --interface kvaser --channel 0 --csv dados_reais.csv
```

### Exemplo 3: Replay de Log

```bash
# Verificar formato do arquivo de log primeiro
head -5 arquivo.log

# Exemplo de formato candump:
# (1234567890.123456) vcan0 18FFF3FE#0BB80000FF000000
# (1234567890.234567) vcan0 18FFE103#0000133F00000000

# Fazer replay em velocidade normal
python replay_can_log.py arquivo.log --interface can0
```

### Exemplo 4: Análise de Dados

```bash
# Gerar CSV com dados do monitor
python monitor_dual_inverter.py --interface kvaser --channel 0 --csv analise_completa.csv

# Analisar CSV em Excel/pandas
import pandas as pd
df = pd.read_csv('analise_completa.csv')
print(df.describe())
```

## 🔍 Solução de Problemas

### Erro: "Interface kvaser not available"

```bash
# Verificar se driver Kvaser está instalado
python -c "import can.interface.kvaser; print('Driver OK')"

# Listar interfaces
python -c "import can; print(can.interface.Bus.available_interfaces())"
```

### Erro: "No kvaser device found"

1. Verificar conexão USB/PCI do hardware
2. Reinstalar driver Kvaser
3. Verificar Device Manager do Windows

### Erro: "Permission denied"

```bash
# Executar como administrador (no Windows, clique direito > "Executar como administrador")
# Ou modificar permissões da interface
```

### Modo SocketCAN no Windows

SocketCAN não está disponível nativamente no Windows. Use sempre Kvaser ou outros drivers Windows:

```bash
# Interface Kvaser (recomendado)
--interface kvaser --channel 0

# Outras opções Windows
--interface ixxat  # Para hardware IXXAT
--interface pcan   # Para PCAN
```

## 📈 Visualização dos Dados

O monitor gera gráficos em tempo real mostrando:

- **Velocidade Atual vs Setpoint** (para cada inversor)
- **Torque Atual vs Setpoint** (para cada inversor)  
- **Erro de Velocidade** (diferença setpoint - atual)
- **Erro de Torque** (diferença setpoint - atual)
- **Estatísticas em tempo real** (taxa de mensagens, valores atuais)

### Controles dos Gráficos:

- **Fechar janela**: Para o monitoramento
- **Ctrl+C**: Para o programa no terminal
- **Zoom**: Rodinha do mouse nos gráficos

## 🎮 Arquivos CSV Gerados

Os arquivos CSV contêm as colunas:

```csv
timestamp,datetime,inv_a_act_speed_rpm,inv_a_speed_setpoint_rpm,inv_a_act_torque_nm,inv_a_torque_setpoint_nm,inv_b_act_speed_rpm,inv_b_speed_setpoint_rpm,inv_b_act_torque_nm,inv_b_torque_setpoint_nm
```

## 🛠️ Desenvolvimento

### Adicionar Nova Interface CAN:

```python
# No monitor_dual_inverter.py, linha ~200:
bus = can.interface.Bus(channel=self.channel, interface=self.interface)
```

### Modificar IDs CAN:

```python
# No monitor_dual_inverter.py, classe CANDecoder:
MSG_MOTOR_SETPOINTS_A = 0x18FFE103  # Novo ID
```

### Customizar Gráficos:

```python
# No método setup_plots(), linha ~460:
# Modificar cores, títulos, layout dos gráficos
```

## 📞 Suporte

Para problemas específicos:

1. **Driver Kvaser**: https://www.kvaser.com/support/
2. **python-can**: https://python-can.readthedocs.io/
3. **Logs detalhados**: Execute com `--simulate` para testar sem hardware

## 📝 Logs de Exemplo

Formato candump:
```
(1234567890.123456) vcan0 18FFF3FE#0BB80000FF000000
(1234567891.123456) vcan0 18FFE103#0000133F00000000
(1234567892.123456) vcan0 18FFA120#0BB8000013370000
```

Formato CSV gerado:
```csv
timestamp,datetime,inv_a_act_speed_rpm,inv_a_speed_setpoint_rpm,inv_a_act_torque_nm,inv_a_torque_setpoint_nm
0.123,2024-01-15 10:30:15.123,3000,3000,35.2,35.0
0.223,2024-01-15 10:30:15.223,2998,3000,35.1,35.0
```

---

**Desenvolvido para Windows com driver Kvaser** 🚀