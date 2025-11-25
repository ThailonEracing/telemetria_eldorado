#!/usr/bin/env python3
"""
Replayer CAN para Windows - Driver Kvaser
Reproduz mensagens CAN de arquivos de log do candump

Uso no Windows:
    python replay_windows_kvaser.py arquivo.log
    python replay_windows_kvaser.py arquivo.log --channel 0
"""

import can
import time
import sys
import argparse
from pathlib import Path
import struct


def parse_candump_line(line):
    """
    Parse uma linha do formato candump log
    Formato: (timestamp) interface canid#data
    Exemplo: (1234567890.123456) vcan0 123#0102030405060708
    """
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    try:
        # Extrai timestamp
        timestamp_end = line.index(')')
        timestamp_str = line[1:timestamp_end]
        timestamp = float(timestamp_str)
        
        # Extrai o resto da linha após o timestamp
        rest = line[timestamp_end + 1:].strip()
        
        # Separa interface e mensagem
        parts = rest.split()
        if len(parts) < 2:
            return None
        
        # Parse da mensagem CAN (formato: ID#DATA)
        can_msg = parts[1]
        if '#' not in can_msg:
            return None
        
        can_id_str, data_str = can_msg.split('#', 1)
        
        # Converte ID (pode ser hexadecimal)
        can_id = int(can_id_str, 16)
        
        # Converte dados de hex para bytes
        data = bytes.fromhex(data_str) if data_str else b''
        
        return {
            'timestamp': timestamp,
            'arbitration_id': can_id,
            'data': data
        }
    except (ValueError, IndexError) as e:
        print(f"Erro ao parsear linha: {line} - {e}", file=sys.stderr)
        return None


def replay_can_log_kvaser(log_file, channel=0, speed_factor=1.0, loop=False, can_interface='can'):
    """
    Reproduz mensagens CAN de um arquivo de log usando driver Kvaser
    
    Args:
        log_file: Caminho para o arquivo .log do candump
        channel: Canal Kvaser (0, 1, 2, etc.)
        speed_factor: Fator de velocidade (1.0 = tempo real, 2.0 = 2x mais rápido)
        loop: Se True, repete o replay continuamente
        can_interface: Nome da interface CAN (can0, can1 para Kvaser)
    """
    
    # Carrega todas as mensagens do arquivo
    messages = []
    print(f"📁 Carregando arquivo: {log_file}")
    
    try:
        with open(log_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                msg_data = parse_candump_line(line)
                if msg_data:
                    messages.append(msg_data)
                elif line.strip() and not line.startswith('#'):
                    print(f"⚠️  Linha {line_num} ignorada: formato inválido")
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {log_file}")
        return
    except Exception as e:
        print(f"❌ Erro ao ler arquivo: {e}")
        return
    
    if not messages:
        print(f"❌ Nenhuma mensagem válida encontrada em {log_file}")
        return
    
    print(f"✅ Carregadas {len(messages)} mensagens do log")
    print(f"🔧 Interface Kvaser Canal {channel} ({can_interface})")
    print(f"⚡ Fator de velocidade: {speed_factor}x")
    
    # Calcula duração total do log
    if len(messages) >= 2:
        duration = messages[-1]['timestamp'] - messages[0]['timestamp']
        print(f"⏱️  Duração do log: {duration:.1f} segundos")
    
    # Cria conexão com o barramento CAN Kvaser
    interface_name = f"{can_interface}{channel}"
    
    try:
        bus = can.interface.Bus(channel=str(channel), interface='kvaser')
        print(f"✅ Conectado ao Kvaser Canal {channel}")
    except Exception as e:
        print(f"❌ Erro ao conectar com Kvaser Canal {channel}: {e}")
        print("💡 Verifique se:")
        print("   - Driver Kvaser está instalado")
        print("   - Hardware Kvaser está conectado")
        print("   - Canal especificado existe")
        return
    
    try:
        iteration = 0
        while True:
            iteration += 1
            if loop:
                print(f"\n🔄 === Iteração {iteration} ===")
            
            # Timestamp de referência (primeira mensagem)
            start_timestamp = messages[0]['timestamp']
            start_time = time.time()
            
            print(f"🚀 Iniciando replay...")
            
            for i, msg_data in enumerate(messages):
                # Calcula o delay relativo ao início
                relative_delay = (msg_data['timestamp'] - start_timestamp) / speed_factor
                target_time = start_time + relative_delay
                
                # Aguarda até o momento correto
                current_time = time.time()
                sleep_time = target_time - current_time
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                # Envia mensagem
                try:
                    msg = can.Message(
                        arbitration_id=msg_data['arbitration_id'],
                        data=msg_data['data'],
                        is_extended_id=True
                    )
                    bus.send(msg)
                    
                    # Mostra progresso
                    if (i + 1) % 100 == 0 or i == len(messages) - 1:
                        progress = (i + 1) / len(messages) * 100
                        print(f"📊 Progresso: {i + 1}/{len(messages)} ({progress:.1f}%)", end='\r')
                        
                except Exception as e:
                    print(f"\n❌ Erro ao enviar mensagem {i}: {e}")
                    continue
            
            print(f"\n✅ Replay completo! {len(messages)} mensagens enviadas")
            
            if not loop:
                break
            
            print("⏸️  Pausa de 1 segundo antes da próxima iteração...")
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\n\n⛔ Replay interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro durante o replay: {e}")
    finally:
        bus.shutdown()
        print("🔌 Conexão CAN fechada")


def check_kvaser_drivers():
    """Verifica se o driver Kvaser está instalado"""
    try:
        import can.interface.kvaser
        print("✅ Driver Kvaser encontrado")
        return True
    except ImportError:
        print("❌ Driver Kvaser não encontrado")
        print("📥 Instale o driver Kvaser de: https://www.kvaser.com/downloads/")
        return False


def show_example_log_format():
    """Mostra exemplo do formato de arquivo de log"""
    example_log = """(1609459200.123456) can0 18FFF3FE#0BB80000FF000000
(1609459200.234567) can0 18FFE103#0000133F00000000
(1609459200.345678) can0 18FFA120#0BB8000013370000
(1609459200.456789) can0 18FFE203#0000154F00000000
(1609459200.567890) can0 18FFB120#0BB8000015390000

Formato: (timestamp) interface ID#dados_hex"""
    print("\n📋 Exemplo de arquivo de log (candump format):")
    print(example_log)


def main():
    parser = argparse.ArgumentParser(
        description='Replayer CAN para Windows - Driver Kvaser',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python replay_windows_kvaser.py arquivo.log                # Canal 0
  python replay_windows_kvaser.py arquivo.log --channel 1    # Canal 1
  python replay_windows_kvaser.py arquivo.log --speed 2.0    # 2x velocidade
  python replay_windows_kvaser.py arquivo.log --loop         # Repetir indefinidamente

IDs comuns nos exemplos:
  0x18FFF3FE - Setpoint de velocidade compartilhado
  0x18FFE103 - Inversor A setpoint torque
  0x18FFA120 - Inversor A status
  0x18FFE203 - Inversor B setpoint torque  
  0x18FFB120 - Inversor B status
        """
    )
    
    parser.add_argument('log_file', help='Arquivo .log do candump')
    parser.add_argument('-c', '--channel', type=int, default=0,
                       help='Canal Kvaser (0, 1, 2, etc.) - padrão: 0')
    parser.add_argument('-s', '--speed', type=float, default=1.0,
                       help='Fator de velocidade (padrão: 1.0 = tempo real)')
    parser.add_argument('-l', '--loop', action='store_true',
                       help='Repetir replay continuamente')
    parser.add_argument('-i', '--interface', default='can',
                       help='Nome da interface CAN (can, can0, etc.) - padrão: can')
    parser.add_argument('--check-drivers', action='store_true',
                       help='Verificar instalação do driver Kvaser')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔄 Replayer CAN Windows - Driver Kvaser")
    print("=" * 70)
    
    # Verificar drivers se solicitado
    if args.check_drivers:
        check_kvaser_drivers()
        return
    
    # Mostrar formato de exemplo se arquivo não existe
    if not Path(args.log_file).exists():
        print(f"❌ Arquivo não encontrado: {args.log_file}")
        print("\n💡 Use o arquivo de exemplo incluído:")
        print("   python replay_windows_kvaser.py exemplo_log_can.log")
        show_example_log_format()
        return
    
    # Verificar driver Kvaser
    if not check_kvaser_drivers():
        print("\n💡 Instale o driver Kvaser e tente novamente")
        return
    
    print(f"📁 Arquivo de log: {args.log_file}")
    print(f"🔧 Canal Kvaser: {args.channel}")
    print(f"⚡ Fator de velocidade: {args.speed}x")
    print(f"🔁 Loop: {'Sim' if args.loop else 'Não'}")
    print("=" * 70)
    
    # Executar replay
    replay_can_log_kvaser(
        log_file=args.log_file,
        channel=args.channel,
        speed_factor=args.speed,
        loop=args.loop,
        can_interface=args.interface
    )


if __name__ == '__main__':
    main()