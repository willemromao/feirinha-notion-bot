#!/usr/bin/env python3
"""
Script para validar credenciais antes do deploy
"""
import sys
import os
from pathlib import Path

# Adiciona o diretório src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from dotenv import load_dotenv
    import httpx
    from openai import OpenAI
    from notion_client import Client
except ImportError:
    print("❌ Dependências não instaladas. Execute: pip install -r requirements.txt")
    sys.exit(1)


def validate_env_vars():
    """Valida se todas as variáveis de ambiente estão definidas"""
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_SECRET_TOKEN",
        "AUTHORIZED_USER_ID",
        "OPENAI_API_KEY",
        "NOTION_TOKEN",
        "NOTION_DATABASE_ID"
    ]

    print("🔍 Verificando variáveis de ambiente...")
    missing = []
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing.append(var)
            print(f"  ❌ {var}: não definida")
        else:
            masked = value[:8] + "..." if len(value) > 8 else "***"
            print(f"  ✅ {var}: {masked}")

    if missing:
        print(f"\n❌ Variáveis faltando: {', '.join(missing)}")
        print("\nCrie um arquivo .env com base no .env.example")
        return False

    print("\n✅ Todas as variáveis de ambiente estão definidas\n")
    return True


def validate_telegram():
    """Valida credenciais do Telegram"""
    print("🤖 Validando Telegram Bot...")
    token = os.environ.get("TELEGRAM_BOT_TOKEN")

    try:
        with httpx.Client() as client:
            response = client.get(f"https://api.telegram.org/bot{token}/getMe")
            response.raise_for_status()
            data = response.json()

        if data.get("ok"):
            bot_info = data.get("result", {})
            print(f"  ✅ Bot conectado: @{bot_info.get('username')}")
            print(f"     Nome: {bot_info.get('first_name')}")
            return True
        else:
            print(f"  ❌ Erro: {data.get('description')}")
            return False

    except Exception as e:
        print(f"  ❌ Erro ao conectar: {e}")
        return False


def validate_openai():
    """Valida credenciais da OpenAI"""
    print("\n🧠 Validando OpenAI API...")
    api_key = os.environ.get("OPENAI_API_KEY")

    try:
        client = OpenAI(api_key=api_key)
        # Tenta listar modelos como forma de validar a chave
        models = client.models.list()
        print(f"  ✅ OpenAI conectada ({len(models.data)} modelos disponíveis)")
        return True

    except Exception as e:
        print(f"  ❌ Erro ao conectar: {e}")
        return False


def validate_notion():
    """Valida credenciais do Notion"""
    print("\n📝 Validando Notion Integration...")
    token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")

    try:
        client = Client(auth=token)

        # Tenta buscar informações do banco de dados
        database = client.databases.retrieve(database_id)
        print(f"  ✅ Base conectada: {database.get('title', [{}])[0].get('plain_text', 'Sem título')}")

        # Valida propriedades
        properties = database.get("properties", {})
        required_props = {
            "Produto": "title",
            "Data": "date",
            "Categoria": "select",
            "Tipo": "rich_text",
            "Qnt": "number",
            "Valor": "number",
            "Desconto": "number",
            "Forma de Pagamento": "select"
        }

        print("\n  Verificando propriedades da base:")
        all_valid = True
        for prop_name, expected_type in required_props.items():
            if prop_name not in properties:
                print(f"    ❌ {prop_name}: não encontrada")
                all_valid = False
            else:
                prop_type = properties[prop_name].get("type")
                if prop_type != expected_type:
                    print(f"    ⚠️  {prop_name}: tipo {prop_type} (esperado: {expected_type})")
                else:
                    print(f"    ✅ {prop_name}: {prop_type}")

        return all_valid

    except Exception as e:
        print(f"  ❌ Erro ao conectar: {e}")
        return False


def main():
    print("=" * 50)
    print("Validação de Credenciais - Feirinha Notion Bot")
    print("=" * 50)
    print()

    # Carrega .env se existir
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"📁 Arquivo .env carregado de: {env_file}\n")
    else:
        print("⚠️  Arquivo .env não encontrado. Usando variáveis de ambiente do sistema.\n")

    # Validações
    results = []
    results.append(("Variáveis de ambiente", validate_env_vars()))

    if results[0][1]:  # Só continua se as variáveis estiverem definidas
        results.append(("Telegram", validate_telegram()))
        results.append(("OpenAI", validate_openai()))
        results.append(("Notion", validate_notion()))

    # Resultado final
    print("\n" + "=" * 50)
    print("RESULTADO")
    print("=" * 50)

    for name, success in results:
        status = "✅ OK" if success else "❌ FALHOU"
        print(f"{status} - {name}")

    all_success = all(success for _, success in results)

    if all_success:
        print("\n🎉 Todas as validações passaram! Você está pronto para fazer deploy.")
        sys.exit(0)
    else:
        print("\n⚠️  Algumas validações falharam. Corrija os erros antes de fazer deploy.")
        sys.exit(1)


if __name__ == "__main__":
    main()
