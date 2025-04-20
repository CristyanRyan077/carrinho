from time import sleep
from estoque import exibir_estoque
import mysql.connector
import keyring


METODOS_PAGAMENTO = ["Dinheiro", "Cartão", "Pix"]


def get_db_config():
    return {
        "user": "root",
        "password": keyring.get_password("estoque_db", "root"),
        "host": "localhost",
        "database": "estoque_python",
        "raise_on_warnings": True,
    }


def testar_conexao():
    config = get_db_config()
    try:
        conn = mysql.connector.connect(**config)
        print("✅ Conexão bem-sucedida!")
        conn.close()
    except Exception as e:
        print(f"❌ Falha na conexão: {e}")


def criar_tabela():
    config = get_db_config()
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS vendas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    metodo_pagamento VARCHAR(50),
                    total DECIMAL(10,2),
                    data_venda TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        )

        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS itens_venda (
                    venda_id INT,
                    produto_id INT,
                    quantidade INT,
                    preco_unitario DECIMAL(10,2),
                    FOREIGN KEY (venda_id) REFERENCES vendas(id),
                    FOREIGN KEY (produto_id) REFERENCES produtos(id)
                )
            """
        )

        conn.commit()
    except mysql.connector.Error as err:
        if err.errno != 1050:
            print(f"Erro ao criar tabela vendas: {err}")
    finally:
        if "conn" in locals() and conn.is_connected():
            cursor.close()
            conn.close()


def menu(conn):
    while True:
        exibir_estoque()
        try:
            produto_id = int(input("Digite o ID do produto (0 para sair): "))
            if produto_id == 0:
                break

            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, quantidade, preco FROM produtos WHERE id = %s",
                    (produto_id,),
                )
                result = cursor.fetchone()

                if not result:
                    print("ID inválido!")
                    continue

                estoque_atual = result[1]
                preco_unitario = result[2]

                quantidade = int(input("Quantidade: "))
                if quantidade > estoque_atual:
                    print("Quantidade indisponível!")
                    continue

                print("\nMétodos de pagamento disponíveis:")
                for i, metodo in enumerate(METODOS_PAGAMENTO, 1):
                    print(f"{i} - {metodo}")
                try:
                    opcao_metodo = int(input("Escolha o método: "))
                    if opcao_metodo < 1 or opcao_metodo >len(METODOS_PAGAMENTO):
                        raise ValueError  
                    metodo_pagamento = METODOS_PAGAMENTO[opcao_metodo - 1]
                except ValueError:
                    print(f"Opcão invalida! Digite um numero entre 1 e {len(METODOS_PAGAMENTO)}")
                    continue
                total = preco_unitario * quantidade

                confirm = input("Confirmar compra? (S/N): ").strip().upper()
                while confirm not in ("S", "N"):
                    print("Opção inválida!")
                    confirm = input("Confirmar compra? (S/N): ").strip().upper()

                if confirm == "N":
                    continue

            with conn.cursor() as cursor:
                try:
                    conn.autocommit = False

                    cursor.execute(
                        "INSERT INTO vendas (metodo_pagamento, total) VALUES (%s, %s)",
                        (metodo_pagamento, total),
                    )
                    venda_id = cursor.lastrowid

                    cursor.execute(
                        """INSERT INTO itens_venda 
                        (venda_id, produto_id, quantidade, preco_unitario)
                        VALUES (%s, %s, %s, %s)""",
                        (venda_id, produto_id, quantidade, preco_unitario),
                    )

                    cursor.execute(
                        "UPDATE produtos SET quantidade = quantidade - %s WHERE id = %s",
                        (quantidade, produto_id),
                    )

                    conn.commit()
                    print("✅ Venda registrada com sucesso!")

                except Exception as e:
                    conn.rollback()
                    print(f"❌ Erro na transação: {e}")
                finally:
                    conn.autocommit = True

        except ValueError:
            print("Erro: Digite números válidos")


def main():
    criar_tabela()
    config = get_db_config()

    try:
        conn = mysql.connector.connect(**config)
        conn.autocommit = False
        menu(conn)
    except Exception as e:
        print(f"Erro geral: {e}")
    finally:
        if "conn" in locals() and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    print("=-" * 30)
    print("Bem vindo a Loja Python!")
    print("=-" * 30)
    main()
