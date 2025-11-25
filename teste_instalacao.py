#!/usr/bin/env python3
"""
Teste de Instalação - Monitor CAN Windows/Kvaser
Verifica se todos os componentes estão funcionando corretamente
"""

import sys
import os

def test_python_version():
    """Testa versão do Python"""
    print("🐍 Testando versão do Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Requer Python 3.8+")
        return False

def test_dependencies():
    """Testa se todas as dependências estão instaladas"""
    print("\n📦 Testando dependências Python...")
    
    dependencies = [
        ('can', 'python-can'),
        ('matplotlib', 'matplotlib'),
        ('numpy', 'numpy'),
        ('pandas', 'pandas')
    ]
    
    all_ok = True
    
    for module, package in dependencies:
        try:
            __import__(module)
            print(f"✅ {package} - OK")
        except ImportError:
            print(f"❌ {package} - NÃO INSTALADO")
            print(f"   Execute: pip install {package}")
            all_ok = False
    
    return all_ok

def test_kvaser_driver():
    """Testa se driver Kvaser está disponível"""
    print("\n🔧 Testando driver Kvaser...")
    
    try:
        import can.interface.kvaser
        print("✅ Driver Kvaser - Disponível")
        return True
    except ImportError:
        print("❌ Driver Kvaser - NÃO DISPONÍVEL")
        print("   1. Instale driver Kvaser: https://www.kvaser.com/downloads/")
        print("   2. Reinicie o computador")
        return False

def test_can_interfaces():
    """Lista interfaces CAN disponíveis"""
    print("\n🔌 Testando interfaces CAN...")
    
    try:
        import can
        interfaces = can.interface.Bus.available_interfaces()
        print("📋 Interfaces disponíveis:")
        for interface in interfaces:
            print(f"   • {interface}")
        
        if 'kvaser' in interfaces:
            print("✅ Interface Kvaser - OK")
            return True
        else:
            print("❌ Interface Kvaser - NÃO ENCONTRADA")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar interfaces: {e}")
        return False

def test_kvaser_channels():
    """Testa canais Kvaser disponíveis"""
    print("\n📡 Testando canais Kvaser...")
    
    try:
        import can
        
        available_channels = []
        for channel in range(4):  # Testa canais 0-3
            try:
                bus = can.interface.Bus(channel=str(channel), interface='kvaser')
                available_channels.append(channel)
                print(f"✅ Canal {channel} - Disponível")
                bus.shutdown()
            except:
                print(f"❌ Canal {channel} - Não disponível")
        
        if available_channels:
            print(f"\n📡 Canais disponíveis: {available_channels}")
            return True
        else:
            print("\n⚠️  Nenhum canal Kvaser encontrado")
            print("   Verifique se o hardware está conectado")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao testar canais: {e}")
        return False

def test_files():
    """Testa se arquivos necessários existem"""
    print("\n📁 Testando arquivos do projeto...")
    
    required_files = [
        'README.md',
        'monitor_windows_kvaser.py',
        'replay_windows_kvaser.py',
        'exemplo_log_can.log',
        'QUICK_START_WINDOWS.md'
    ]
    
    all_files_ok = True
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} - OK")
        else:
            print(f"❌ {file} - NÃO ENCONTRADO")
            all_files_ok = False
    
    return all_files_ok

def test_matplotlib():
    """Testa se matplotlib funciona corretamente"""
    print("\n📊 Testando matplotlib...")
    
    try:
        import matplotlib
        matplotlib.use('Agg')  # Backend não-interativo para teste
        import matplotlib.pyplot as plt
        
        # Teste simples
        plt.figure()
        plt.plot([1, 2, 3], [1, 4, 2])
        plt.title('Teste')
        plt.savefig('teste_plot.png')
        plt.close()
        
        # Verificar se arquivo foi criado
        if os.path.exists('teste_plot.png'):
            print("✅ Matplotlib - OK")
            os.remove('teste_plot.png')  # Limpar arquivo de teste
            return True
        else:
            print("❌ Matplotlib - Erro ao gerar gráfico")
            return False
            
    except Exception as e:
        print(f"❌ Matplotlib - Erro: {e}")
        return False

def run_simulation_test():
    """Testa o modo simulação do monitor"""
    print("\n🎮 Testando modo simulação...")
    
    try:
        # Importar classes do monitor
        sys.path.insert(0, os.path.dirname(__file__))
        from monitor_windows_kvaser import WindowsKvasorMonitor, InverterData
        
        # Criar instância de teste
        monitor = WindowsKvaserMonitor(channel=0, buffer_size=10)
        
        # Testar dados simulados
        monitor.simulate_can_data()
        
        # Verificar se dados foram gerados
        if len(monitor.inverter_a.timestamps) > 0:
            print("✅ Modo simulação - OK")
            print(f"   Dados gerados: {len(monitor.inverter_a.timestamps)} amostras")
            return True
        else:
            print("❌ Modo simulação - Nenhum dado gerado")
            return False
            
    except Exception as e:
        print(f"❌ Modo simulação - Erro: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("=" * 60)
    print("🧪 TESTE DE INSTALAÇÃO - Monitor CAN Windows/Kvaser")
    print("=" * 60)
    
    tests = [
        ("Python", test_python_version),
        ("Dependências", test_dependencies),
        ("Driver Kvaser", test_kvaser_driver),
        ("Interfaces CAN", test_can_interfaces),
        ("Canais Kvaser", test_kvaser_channels),
        ("Arquivos", test_files),
        ("Matplotlib", test_matplotlib),
        ("Simulação", run_simulation_test),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} - Erro inesperado: {e}")
            results.append((test_name, False))
    
    # Resumo final
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name:20} | {status}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\n🏆 Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("   ✅ Sua instalação está pronta para uso")
        print("\n🚀 Comandos para testar:")
        print("   python monitor_windows_kvaser.py --simulate")
        print("   python replay_windows_kvaser.py exemplo_log_can.log")
    elif passed >= total - 2:  # Se passou em todos exceto 2 ou menos
        print("\n⚠️  INSTALAÇÃO PARCIAL")
        print("   ⚡ Você pode testar em modo simulação")
        print("   🔧 Para usar hardware, resolva os problemas acima")
        print("\n🎮 Teste disponível:")
        print("   python monitor_windows_kvaser.py --simulate")
    else:
        print("\n❌ INSTALAÇÃO INCOMPLETA")
        print("   🔧 Resolva os problemas listados acima")
        print("   📚 Consulte o README.md para instruções detalhadas")
    
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n💡 Comandos úteis:")
        print("   python -m pip install --upgrade python-can matplotlib numpy pandas")
        print("   python replay_windows_kvaser.py --check-drivers")
        print("   python monitor_windows_kvaser.py --simulate")
    
    print("\n👋 Para mais ajuda, consulte:")
    print("   📖 README.md")
    print("   🚀 QUICK_START_WINDOWS.md")
    
    input("\nPressione Enter para sair...")
    sys.exit(0 if success else 1)