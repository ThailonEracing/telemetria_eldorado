#!/usr/bin/env python3
"""
Monitor de Dois Inversores CAN - Versão Windows/Kvaser
Adaptado especificamente para Windows com driver Kvaser

Uso no Windows:
    python monitor_windows_kvaser.py --channel 0
    python monitor_windows_kvaser.py --channel 0 --simulate
"""

import can
import struct
import threading
import time
import csv
from collections import deque
from datetime import datetime
import warnings
import os
import argparse

# Configuração do matplotlib para Windows
warnings.filterwarnings('ignore')
import matplotlib
matplotlib.use('TkAgg')  # Backend compatível com Windows

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.gridspec as gridspec

# Configurar tema dark científico
plt.style.use('dark_background')

# Configurações de estilo refinado
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = '#0e1117'
plt.rcParams['axes.facecolor'] = '#1a1d23'
plt.rcParams['axes.edgecolor'] = '#3a3f4b'
plt.rcParams['axes.labelcolor'] = '#c9d1d9'
plt.rcParams['text.color'] = '#c9d1d9'
plt.rcParams['xtick.color'] = '#8b949e'
plt.rcParams['ytick.color'] = '#8b949e'
plt.rcParams['grid.color'] = '#3a3f4b'
plt.rcParams['grid.alpha'] = 0.3
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['lines.linewidth'] = 1.2
plt.rcParams['lines.antialiased'] = True
plt.rcParams['font.size'] = 9
plt.rcParams['axes.titlesize'] = 10
plt.rcParams['axes.labelsize'] = 9
plt.rcParams['xtick.labelsize'] = 8
plt.rcParams['ytick.labelsize'] = 8
plt.rcParams['legend.fontsize'] = 8
plt.rcParams['legend.framealpha'] = 0.6
plt.rcParams['legend.facecolor'] = '#1a1d23'
plt.rcParams['legend.edgecolor'] = '#3a3f4b'
plt.rcParams['xtick.major.pad'] = 4
plt.rcParams['ytick.major.pad'] = 4


class CANDecoder:
    """Decodifica mensagens CAN baseado no arquivo de descrição"""

    # Setpoint de velocidade compartilhado para A e B
    MSG_MOTOR_SETPOINTS_AB_VEL = 0x18FFF3FE
    
    # IDs das mensagens CAN - Inversor A (apenas torque agora)
    MSG_MOTOR_SETPOINTS_A = 0x18FFE103
    MSG_MOTOR_STATUS_A = 0x18FFA120
    
    # IDs das mensagens CAN - Inversor B (apenas torque agora)
    MSG_MOTOR_SETPOINTS_B = 0x18FFE203
    MSG_MOTOR_STATUS_B = 0x18FFB120
    
    # Mensagens de log
    MSG_INVERTER1_RX = 0x18FFE103
    MSG_INVERTER2_RX = 0x18FFE203
    
    @staticmethod
    def decode_speed(data, byte_start):
        """Decodifica velocidade (int16, offset -32000)"""
        raw_value = struct.unpack_from('<H', data, byte_start)[0]
        return raw_value - 32000
    
    @staticmethod
    def decode_speed_set(data, byte_start):
        """Decodifica velocidade (int16, offset -32000)"""
        raw_value = struct.unpack_from('<H', data, 0)[0]
        return raw_value - 32000
    
    @staticmethod
    def decode_torque(data, byte_start):
        """Decodifica torque (float com multiplicador 526.3157, offset -60)"""
        raw_value = struct.unpack_from('<H', data, byte_start)[0]
        return ((raw_value / 526.3157) - 60)
    
    @staticmethod
    def decode_motor_setpoints_torque(data):
        """Decodifica Motor Setpoints - APENAS TORQUE (bytes 3-4)"""
        if len(data) < 5:
            return None
        
        return {
            'torque_setpoint': CANDecoder.decode_torque(data, 3),  # byte 3-4
        }
    
    @staticmethod
    def decode_motor_setpoints_velocity(data):
        """Decodifica Motor Setpoints - VELOCIDADE COMPARTILHADA (bytes 0-1)"""
        if len(data) < 2:
            return None
        
        return {
            'speed_setpoint': CANDecoder.decode_speed_set(data, 0),  # byte 0-1
        }
    
    @staticmethod
    def decode_motor_status(data):
        """Decodifica Motor Status"""
        if len(data) < 6:
            return None
        
        return {
            'act_speed': CANDecoder.decode_speed(data, 1),      # byte 1-2 (índice 0-1)
            'act_torque': CANDecoder.decode_torque(data, 5),    # byte 5-6 (índice 4-5)
        }


class InverterData:
    """Armazena dados de um inversor"""
    
    def __init__(self, name, buffer_size=500):
        self.name = name
        self.buffer_size = buffer_size
        
        # Buffers de dados
        self.timestamps = deque(maxlen=buffer_size)
        self.act_speed = deque(maxlen=buffer_size)
        self.speed_setpoint = deque(maxlen=buffer_size)
        self.act_torque = deque(maxlen=buffer_size)
        self.torque_setpoint = deque(maxlen=buffer_size)
        
        self.msg_count = 0
        
        # Armazenar último setpoint de velocidade recebido
        self.last_speed_setpoint = None
    
    def update_speed_setpoint(self, speed_sp):
        """Atualiza o último setpoint de velocidade (compartilhado)"""
        self.last_speed_setpoint = speed_sp
    
    def add_torque_setpoint_data(self, timestamp, torque_sp):
        """Adiciona dados de setpoint de torque"""
        self.timestamps.append(timestamp)
        self.torque_setpoint.append(torque_sp)
        # Usar último setpoint de velocidade conhecido
        if self.last_speed_setpoint is not None:
            self.speed_setpoint.append(self.last_speed_setpoint)
    
    def add_status_data(self, timestamp, speed_act, torque_act):
        """Adiciona dados de status"""
        if not self.timestamps or self.timestamps[-1] != timestamp:
            self.timestamps.append(timestamp)
        self.act_speed.append(speed_act)
        self.act_torque.append(torque_act)
    
    def get_latest_values(self):
        """Retorna os últimos valores disponíveis"""
        return {
            'speed_act': self.act_speed[-1] if self.act_speed else None,
            'speed_sp': self.speed_setpoint[-1] if self.speed_setpoint else None,
            'torque_act': self.act_torque[-1] if self.act_torque else None,
            'torque_sp': self.torque_setpoint[-1] if self.torque_setpoint else None,
        }


class WindowsKvaserMonitor:
    """Monitor de dois inversores CAN para Windows com driver Kvaser"""
    
    def __init__(self, channel=0, buffer_size=500, csv_output=None):
        self.channel = channel
        self.buffer_size = buffer_size
        self.running = False
        self.csv_output = csv_output
        
        # Lock para sincronização thread-safe
        self.data_lock = threading.Lock()
        
        # Dados dos dois inversores
        self.inverter_a = InverterData("Inversor A", buffer_size)
        self.inverter_b = InverterData("Inversor B", buffer_size)
        
        # CSV logging
        self.csv_file = None
        self.csv_writer = None
        if self.csv_output:
            self._init_csv_file()
        
        # Estatísticas
        self.total_msg_count = 0
        self.start_time = None
    
    def _init_csv_file(self):
        """Inicializa arquivo CSV para logging de dados"""
        try:
            self.csv_file = open(self.csv_output, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            
            # Escrever cabeçalho
            header = [
                'timestamp', 
                'datetime',
                'inv_a_act_speed_rpm', 
                'inv_a_speed_setpoint_rpm',
                'inv_a_act_torque_nm', 
                'inv_a_torque_setpoint_nm',
                'inv_b_act_speed_rpm', 
                'inv_b_speed_setpoint_rpm',
                'inv_b_act_torque_nm', 
                'inv_b_torque_setpoint_nm'
            ]
            self.csv_writer.writerow(header)
            self.csv_file.flush()
            print(f"✓ Arquivo CSV criado: {self.csv_output}")
        except Exception as e:
            print(f"✗ Erro ao criar arquivo CSV: {e}")
            self.csv_file = None
            self.csv_writer = None
    
    def _write_to_csv(self, timestamp):
        """Escreve uma linha no arquivo CSV com dados de ambos inversores"""
        if not self.csv_writer:
            return
        
        try:
            dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            
            # Pegar dados dos inversores
            data_a = self.inverter_a.get_latest_values()
            data_b = self.inverter_b.get_latest_values()
            
            # Escrever linha
            row = [
                f"{timestamp:.3f}",
                dt,
                f"{data_a['speed_act']:.2f}" if data_a['speed_act'] is not None else "",
                f"{data_a['speed_sp']:.2f}" if data_a['speed_sp'] is not None else "",
                f"{data_a['torque_act']:.2f}" if data_a['torque_act'] is not None else "",
                f"{data_a['torque_sp']:.2f}" if data_a['torque_sp'] is not None else "",
                f"{data_b['speed_act']:.2f}" if data_b['speed_act'] is not None else "",
                f"{b['speed_sp']:.2f}" if (data_b['speed_sp'] is not None) else "",
                f"{data_b['torque_act']:.2f}" if data_b['torque_act'] is not None else "",
                f"{data_b['torque_sp']:.2f}" if data_b['torque_sp'] is not None else "",
            ]
            
            self.csv_writer.writerow(row)
            
            # Flush periodicamente
            if self.total_msg_count % 10 == 0:
                self.csv_file.flush()
                
        except Exception as e:
            print(f"Erro ao escrever no CSV: {e}")
    
    def start_can_listener(self):
        """Inicia listener do barramento CAN Kvaser"""
        try:
            self.bus = can.interface.Bus(channel=str(self.channel), interface='kvaser')
            print(f"✓ Conectado ao Kvaser Canal {self.channel}")
            return True
        except Exception as e:
            print(f"✗ Erro ao conectar ao Kvaser Canal {self.channel}: {e}")
            print(f"  Verifique se o driver Kvaser está instalado e o canal está disponível")
            return False
    
    def read_can_messages(self):
        """Thread para ler mensagens CAN"""
        print("Iniciando leitura de mensagens CAN...")
        self.start_time = time.time()
        
        while self.running:
            try:
                msg = self.bus.recv(timeout=0.1)
                if msg:
                    self.process_message(msg)
            except Exception as e:
                print(f"Erro ao ler mensagem: {e}")
                time.sleep(0.01)
    
    def process_message(self, msg):
        """Processa mensagem CAN recebida"""
        self.total_msg_count += 1
        timestamp = time.time() - self.start_time
        
        with self.data_lock:
            # Processar setpoint de velocidade compartilhado
            if msg.arbitration_id == CANDecoder.MSG_MOTOR_SETPOINTS_AB_VEL:
                decoded = CANDecoder.decode_motor_setpoints_velocity(msg.data)
                if decoded:
                    # Atualizar setpoint de velocidade para AMBOS inversores
                    self.inverter_a.update_speed_setpoint(decoded['speed_setpoint'])
                    self.inverter_b.update_speed_setpoint(decoded['speed_setpoint'])
                    print(f"Setpoint velocidade: {decoded['speed_setpoint']:.0f} rpm")
            
            # Processar mensagens do Inversor A
            elif msg.arbitration_id == CANDecoder.MSG_MOTOR_SETPOINTS_A:
                decoded = CANDecoder.decode_motor_setpoints_torque(msg.data)
                if decoded:
                    self.inverter_a.add_torque_setpoint_data(
                        timestamp,
                        decoded['torque_setpoint']
                    )
                    self.inverter_a.msg_count += 1
                    
            elif msg.arbitration_id == CANDecoder.MSG_MOTOR_STATUS_A:
                decoded = CANDecoder.decode_motor_status(msg.data)
                if decoded:
                    self.inverter_a.add_status_data(
                        timestamp,
                        decoded['act_speed'],
                        decoded['act_torque']
                    )
                    self.inverter_a.msg_count += 1
            
            # Processar mensagens do Inversor B
            elif msg.arbitration_id == CANDecoder.MSG_MOTOR_SETPOINTS_B:
                decoded = CANDecoder.decode_motor_setpoints_torque(msg.data)
                if decoded:
                    self.inverter_b.add_torque_setpoint_data(
                        timestamp,
                        decoded['torque_setpoint']
                    )
                    self.inverter_b.msg_count += 1
                    
            elif msg.arbitration_id == CANDecoder.MSG_MOTOR_STATUS_B:
                decoded = CANDecoder.decode_motor_status(msg.data)
                if decoded:
                    self.inverter_b.add_status_data(
                        timestamp,
                        decoded['act_speed'],
                        decoded['act_torque']
                    )
                    self.inverter_b.msg_count += 1
        
        # Salvar em CSV se habilitado
        if self.csv_output:
            self._write_to_csv(timestamp)
    
    def simulate_can_data(self):
        """Simula dados CAN para teste"""
        try:
            import numpy as np
        except ImportError:
            print("✗ numpy não está instalado. Instale com: pip install numpy")
            return
            
        print("Modo simulação ativado - gerando dados de teste")
        self.start_time = time.time()
        
        while self.running:
            timestamp = time.time() - self.start_time
            
            # Simular setpoint de velocidade COMPARTILHADO
            speed_sp_shared = 3000 + 500 * np.sin(timestamp * 0.5)
            
            # Atualizar setpoint de velocidade para ambos
            with self.data_lock:
                self.inverter_a.update_speed_setpoint(speed_sp_shared)
                self.inverter_b.update_speed_setpoint(speed_sp_shared)
            
            # Simular dados do Inversor A
            speed_act_a = speed_sp_shared + 50 * np.sin(timestamp * 2)
            torque_sp_a = 30 + 10 * np.sin(timestamp * 0.3)
            torque_act_a = torque_sp_a + 2 * np.sin(timestamp * 1.5)
            
            # Simular dados do Inversor B (com pequena diferença)
            speed_act_b = speed_sp_shared + 60 * np.sin(timestamp * 1.8)
            torque_sp_b = 35 + 12 * np.sin(timestamp * 0.35 + 0.3)
            torque_act_b = torque_sp_b + 3 * np.sin(timestamp * 1.3)
            
            with self.data_lock:
                # Adicionar dados do Inversor A
                self.inverter_a.add_torque_setpoint_data(timestamp, torque_sp_a)
                self.inverter_a.add_status_data(timestamp, speed_act_a, torque_act_a)
                self.inverter_a.msg_count += 2
                
                # Adicionar dados do Inversor B
                self.inverter_b.add_torque_setpoint_data(timestamp, torque_sp_b)
                self.inverter_b.add_status_data(timestamp, speed_act_b, torque_act_b)
                self.inverter_b.msg_count += 2
            
            # Salvar em CSV se habilitado
            if self.csv_output:
                self._write_to_csv(timestamp)
            
            self.total_msg_count += 4
            time.sleep(0.05)  # 20 Hz
    
    def setup_plots(self):
        """Configura os gráficos para dois inversores"""
        self.fig = plt.figure(figsize=(16, 10))
        
        # Grid: 2 linhas x 2 colunas
        gs = gridspec.GridSpec(2, 2, figure=self.fig, hspace=0.3, wspace=0.3)
        
        # ===== INVERSOR A (coluna esquerda) =====
        # Velocidade A
        self.ax_speed_a = self.fig.add_subplot(gs[0, 0])
        self.line_speed_act_a, = self.ax_speed_a.plot([], [], '#00d4aa', linewidth=1.2, label='Atual')
        self.line_speed_sp_a, = self.ax_speed_a.plot([], [], '#ff6b6b', linewidth=1.2, linestyle='--', label='Setpoint', alpha=0.8)
        self.ax_speed_a.set_xlabel('Tempo (s)', alpha=0.7)
        self.ax_speed_a.set_ylabel('Velocidade (rpm)', alpha=0.7)
        self.ax_speed_a.set_title('INVERSOR A - Velocidade', fontweight='bold', color='#58a6ff')
        self.ax_speed_a.legend(loc='upper right')
        self.ax_speed_a.grid(True)
        
        # Torque A
        self.ax_torque_a = self.fig.add_subplot(gs[1, 0])
        self.line_torque_act_a, = self.ax_torque_a.plot([], [], '#3de8b4', linewidth=1.2, label='Atual')
        self.line_torque_sp_a, = self.ax_torque_a.plot([], [], '#c678dd', linewidth=1.2, linestyle='--', label='Setpoint', alpha=0.8)
        self.ax_torque_a.set_xlabel('Tempo (s)', alpha=0.7)
        self.ax_torque_a.set_ylabel('Torque (N/m)', alpha=0.7)
        self.ax_torque_a.set_title('INVERSOR A - Torque', fontweight='bold', color='#58a6ff')
        self.ax_torque_a.legend(loc='upper right')
        self.ax_torque_a.grid(True)
        
        # ===== INVERSOR B (coluna direita) =====
        # Velocidade B
        self.ax_speed_b = self.fig.add_subplot(gs[0, 1])
        self.line_speed_act_b, = self.ax_speed_b.plot([], [], '#00d4aa', linewidth=1.2, label='Atual')
        self.line_speed_sp_b, = self.ax_speed_b.plot([], [], '#ff6b6b', linewidth=1.2, linestyle='--', label='Setpoint', alpha=0.8)
        self.ax_speed_b.set_xlabel('Tempo (s)', alpha=0.7)
        self.ax_speed_b.set_ylabel('Velocidade (rpm)', alpha=0.7)
        self.ax_speed_b.set_title('INVERSOR B - Velocidade', fontweight='bold', color='#f97583')
        self.ax_speed_b.legend(loc='upper right')
        self.ax_speed_b.grid(True)
        
        # Torque B
        self.ax_torque_b = self.fig.add_subplot(gs[1, 1])
        self.line_torque_act_b, = self.ax_torque_b.plot([], [], '#3de8b4', linewidth=1.2, label='Atual')
        self.line_torque_sp_b, = self.ax_torque_b.plot([], [], '#c678dd', linewidth=1.2, linestyle='--', label='Setpoint', alpha=0.8)
        self.ax_torque_b.set_xlabel('Tempo (s)', alpha=0.7)
        self.ax_torque_b.set_ylabel('Torque (N/m)', alpha=0.7)
        self.ax_torque_b.set_title('INVERSOR B - Torque', fontweight='bold', color='#f97583')
        self.ax_torque_b.legend(loc='upper right')
        self.ax_torque_b.grid(True)
        
        # Texto de estatísticas
        self.stats_text = self.fig.text(0.02, 0.99, '', transform=self.fig.transFigure, 
                                       verticalalignment='top', fontsize=9,
                                       color='#c9d1d9',
                                       bbox=dict(boxstyle='round', facecolor='#1a1d23', 
                                                edgecolor='#3a3f4b', alpha=0.85))
        
        plt.suptitle('Monitor Windows - Dois Inversores CAN (Kvaser)', 
                    fontsize=14, fontweight='bold', y=0.998, color='#c9d1d9')
    
    def update_plot(self, frame):
        """Atualiza os gráficos (chamado pela animação)"""
        with self.data_lock:
            # Copiar dados thread-safe
            inv_a = self.inverter_a
            inv_b = self.inverter_b
            
            if len(inv_a.timestamps) < 2 and len(inv_b.timestamps) < 2:
                return
            
            # Dados do Inversor A
            t_a = list(inv_a.timestamps)
            speed_act_a = list(inv_a.act_speed)
            speed_sp_a = list(inv_a.speed_setpoint)
            torque_act_a = list(inv_a.act_torque)
            torque_sp_a = list(inv_a.torque_setpoint)
            
            # Dados do Inversor B
            t_b = list(inv_b.timestamps)
            speed_act_b = list(inv_b.act_speed)
            speed_sp_b = list(inv_b.speed_setpoint)
            torque_act_b = list(inv_b.act_torque)
            torque_sp_b = list(inv_b.torque_setpoint)
        
        # ===== Atualizar gráficos do Inversor A =====
        if len(speed_act_a) > 0:
            self.line_speed_act_a.set_data(t_a[-len(speed_act_a):], speed_act_a)
        if len(speed_sp_a) > 0:
            self.line_speed_sp_a.set_data(t_a[-len(speed_sp_a):], speed_sp_a)
        
        if len(torque_act_a) > 0:
            self.line_torque_act_a.set_data(t_a[-len(torque_act_a):], torque_act_a)
        if len(torque_sp_a) > 0:
            self.line_torque_sp_a.set_data(t_a[-len(torque_sp_a):], torque_sp_a)
        
        # ===== Atualizar gráficos do Inversor B =====
        if len(speed_act_b) > 0:
            self.line_speed_act_b.set_data(t_b[-len(speed_act_b):], speed_act_b)
        if len(speed_sp_b) > 0:
            self.line_speed_sp_b.set_data(t_b[-len(speed_sp_b):], speed_sp_b)
        
        if len(torque_act_b) > 0:
            self.line_torque_act_b.set_data(t_b[-len(torque_act_b):], torque_act_b)
        if len(torque_sp_b) > 0:
            self.line_torque_sp_b.set_data(t_b[-len(torque_sp_b):], torque_sp_b)
        
        # Ajustar limites dos eixos X (janela de 10 segundos)
        max_time = max(t_a[-1] if t_a else 0, t_b[-1] if t_b else 0)
        window = 10
        
        for ax in [self.ax_speed_a, self.ax_torque_a, self.ax_speed_b, self.ax_torque_b]:
            ax.set_xlim(max(0, max_time - window), max_time + 1)
        
        # Ajustar limites dos eixos Y
        for ax in [self.ax_speed_a, self.ax_torque_a, self.ax_speed_b, self.ax_torque_b]:
            ax.relim()
            ax.autoscale_view()
        
        # Atualizar estatísticas
        elapsed_time = max_time
        msg_rate = self.total_msg_count / elapsed_time if elapsed_time > 0 else 0
        
        stats_str = f"Tempo: {elapsed_time:.1f}s | Msgs: {self.total_msg_count} | Taxa: {msg_rate:.1f} msg/s\n"
        stats_str += f"Inversor A: {inv_a.msg_count} msgs"
        if len(speed_act_a) > 0:
            stats_str += f" | Vel: {speed_act_a[-1]:.0f} rpm"
        if len(torque_act_a) > 0:
            stats_str += f" | Torque: {torque_act_a[-1]:.1f} N/m"
        
        stats_str += f"\nInversor B: {inv_b.msg_count} msgs"
        if len(speed_act_b) > 0:
            stats_str += f" | Vel: {speed_act_b[-1]:.0f} rpm"
        if len(torque_act_b) > 0:
            stats_str += f" | Torque: {torque_act_b[-1]:.1f} N/m"
        
        # Mostrar setpoint de velocidade compartilhado
        if inv_a.last_speed_setpoint is not None:
            stats_str += f"\nVel Setpoint Compartilhado: {inv_a.last_speed_setpoint:.0f} rpm"
        
        self.stats_text.set_text(stats_str)
    
    def run(self, simulation_mode=False):
        """Executa o monitor"""
        self.running = True
        
        # Tentar conectar ao barramento CAN
        if not simulation_mode:
            can_connected = self.start_can_listener()
            if can_connected:
                # Iniciar thread de leitura CAN
                self.can_thread = threading.Thread(target=self.read_can_messages, daemon=True)
                self.can_thread.start()
            else:
                simulation_mode = True
        
        # Se modo simulação, usar dados sintéticos
        if simulation_mode:
            self.sim_thread = threading.Thread(target=self.simulate_can_data, daemon=True)
            self.sim_thread.start()
        
        # Configurar gráficos
        self.setup_plots()
        
        # Iniciar animação
        print("\n🎯 Iniciando monitor Windows - Dois Inversores CAN")
        print("📊 Visualização em tempo real")
        print("🛑 Feche a janela ou pressione Ctrl+C para parar\n")
        
        # Armazenar animação para evitar garbage collection
        self.anim = FuncAnimation(self.fig, self.update_plot, interval=50, blit=False)
        
        # Mostrar plot interativo
        try:
            plt.show()
        except KeyboardInterrupt:
            print("\n\nParando monitor...")
            self.running = False
    
    def stop(self):
        """Para o monitor"""
        self.running = False
        if hasattr(self, 'bus'):
            self.bus.shutdown()
        
        # Fechar arquivo CSV
        if self.csv_file:
            try:
                self.csv_file.flush()
                self.csv_file.close()
                print(f"✓ Arquivo CSV fechado: {self.csv_output}")
            except Exception as e:
                print(f"Erro ao fechar CSV: {e}")


def check_kvaser_drivers():
    """Verifica se o driver Kvaser está instalado"""
    try:
        import can.interface.kvaser
        print("✓ Driver Kvaser encontrado")
        return True
    except ImportError:
        print("✗ Driver Kvaser não encontrado")
        print("  Instale o driver Kvaser de: https://www.kvaser.com/downloads/")
        return False


def list_kvaser_channels():
    """Lista canais Kvaser disponíveis"""
    try:
        # Tenta criar um bus para verificar canais
        print("🔍 Verificando canais Kvaser disponíveis...")
        for i in range(4):  # Verificar até 4 canais
            try:
                bus = can.interface.Bus(channel=str(i), interface='kvaser')
                print(f"✓ Canal {i}: Disponível")
                bus.shutdown()
            except:
                print(f"✗ Canal {i}: Não disponível")
    except Exception as e:
        print(f"Erro ao verificar canais: {e}")


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='Monitor Windows - Dois Inversores CAN (Driver Kvaser)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python monitor_windows_kvaser.py                    # Canal 0 com Kvaser
  python monitor_windows_kvaser.py --channel 1       # Canal 1 com Kvaser  
  python monitor_windows_kvaser.py --simulate        # Modo simulação
  python monitor_windows_kvaser.py --csv dados.csv   # Com logging CSV
        """
    )
    parser.add_argument('--channel', type=int, default=0, 
                       help='Canal Kvaser (0, 1, 2, etc.) - padrão: 0')
    parser.add_argument('--simulate', action='store_true', 
                       help='Modo simulação (sem hardware Kvaser)')
    parser.add_argument('--buffer', type=int, default=500, 
                       help='Tamanho do buffer de dados')
    parser.add_argument('--csv', type=str, default=None,
                       help='Arquivo CSV para salvar dados')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🖥️  Monitor Windows - Dois Inversores CAN (Driver Kvaser)")
    print("=" * 70)
    
    # Verificar driver Kvaser
    if not args.simulate:
        if not check_kvaser_drivers():
            print("\n💡 Dica: Use --simulate para testar sem hardware")
            return
        list_kvaser_channels()
    
    print(f"Canal Kvaser: {args.channel}")
    print(f"Modo: {'Simulação' if args.simulate else 'Hardware Kvaser'}")
    print(f"Buffer: {args.buffer} amostras")
    if args.csv:
        print(f"Salvando em CSV: {args.csv}")
    print("=" * 70)
    print("\nIDs CAN monitorados:")
    print("  • Setpoint Velocidade Compartilhado: 0x18FFF3FE")
    print("  • Inversor A: Torque (0x18FFE103) | Status (0x18FFA120)")
    print("  • Inversor B: Torque (0x18FFE203) | Status (0x18FFB120)")
    print("=" * 70)
    
    monitor = WindowsKvaserMonitor(
        channel=args.channel,
        buffer_size=args.buffer,
        csv_output=args.csv
    )
    
    try:
        monitor.run(simulation_mode=args.simulate)
    except KeyboardInterrupt:
        print("\n\nEncerrando...")
        monitor.stop()
    
    print("\n✓ Monitor finalizado")


if __name__ == "__main__":
    main()