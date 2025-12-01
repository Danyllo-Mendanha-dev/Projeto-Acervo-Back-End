from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
from datetime import date

# --- Helper Function ---
def dictfetchall(cursor):
    """Retorna todas as linhas de um cursor como um dict."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def _get_autores_para_livro(livro_id):
    """
    Função auxiliar para buscar autores SEM JOIN.
    Usa sub-query: WHERE id_autor IN (SELECT ...)
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT nome 
            FROM Autor 
            WHERE id_autor IN (
                SELECT id_autor FROM autor_livro WHERE id_livro = %s
            )
            ORDER BY nome
            """,
            [livro_id]
        )
        return dictfetchall(cursor)

# --- Views de Relatório ---

def relatorio_index_view(request):
    """Apenas renderiza a página principal (menu) de relatórios."""
    return render(request, 'relatorio/relatorio.html')

def relatorio_leitores_atrasados_view(request):
    """
    Busca empréstimos atrasados SEM JOIN.
    Estratégia: Busca na tabela Emprestimo e preenche nomes via Python.
    """
    contexto = {}
    try:
        with connection.cursor() as cursor:
            # 1. Busca dados brutos da tabela de Empréstimo
            cursor.execute(
                """
                SELECT 
                    id_emprestimo,
                    id_leitor,
                    id_exemplar,
                    dt_prevista_devolucao
                FROM Emprestimo 
                WHERE status = 'Em Andamento' 
                  AND dt_prevista_devolucao < CURRENT_DATE
                ORDER BY dt_prevista_devolucao ASC
                """
            )
            emprestimos = dictfetchall(cursor)
            
            # 2. Enriquecimento de dados (Loop Python)
            hoje = date.today()
            
            for emp in emprestimos:
                # Calcula dias de atraso no Python
                if emp['dt_prevista_devolucao']:
                    emp['dias_atraso'] = (hoje - emp['dt_prevista_devolucao']).days
                else:
                    emp['dias_atraso'] = 0

                # Busca Leitor (Nome e Telefone)
                cursor.execute("SELECT nome, telefone FROM Leitor WHERE id_leitor = %s", [emp['id_leitor']])
                row_leitor = cursor.fetchone()
                if row_leitor:
                    emp['leitor_nome'] = row_leitor[0]
                    emp['leitor_telefone'] = row_leitor[1]
                else:
                    emp['leitor_nome'] = "Desconhecido"
                    emp['leitor_telefone'] = "-"

                # Busca Exemplar (Patrimônio e ID do Livro)
                cursor.execute("SELECT numero_patrimonio, id_livro FROM Exemplar WHERE id_exemplar = %s", [emp['id_exemplar']])
                row_exemplar = cursor.fetchone()
                
                if row_exemplar:
                    emp['numero_patrimonio'] = row_exemplar[0]
                    id_livro = row_exemplar[1]
                    
                    # Busca Nome do Livro
                    cursor.execute("SELECT nome FROM Livro WHERE id_livro = %s", [id_livro])
                    row_livro = cursor.fetchone()
                    emp['livro_nome'] = row_livro[0] if row_livro else "Desconhecido"
                else:
                    emp['numero_patrimonio'] = "?"
                    emp['livro_nome'] = "?"

            contexto['emprestimos_atrasados'] = emprestimos

    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao gerar o relatório: {e}")
        contexto['emprestimos_atrasados'] = []

    return render(request, 'relatorio/leitores_atrasados.html', contexto)

def relatorio_livros_emprestados_view(request):
    """
    Busca livros emprestados SEM JOIN.
    """
    contexto = {}
    try:
        with connection.cursor() as cursor:
            # 1. Busca dados da tabela Empréstimo
            cursor.execute(
                """
                SELECT 
                    id_emprestimo,
                    id_exemplar,
                    id_leitor,
                    dt_emprestimo,
                    dt_prevista_devolucao
                FROM Emprestimo 
                WHERE status = 'Em Andamento'
                ORDER BY (
                    SELECT nome FROM Livro WHERE id_livro = (
                        SELECT id_livro FROM Exemplar WHERE id_exemplar = Emprestimo.id_exemplar
                    )
                ) ASC
                """
            )
            emprestimos = dictfetchall(cursor)
            
            hoje = date.today()

            # 2. Loop para preencher os dados relacionais
            for emp in emprestimos:
                # Lógica de Atraso
                emp['is_atrasado'] = emp['dt_prevista_devolucao'] < hoje
                
                # Busca Leitor
                cursor.execute("SELECT nome FROM Leitor WHERE id_leitor = %s", [emp['id_leitor']])
                leitor_row = cursor.fetchone()
                emp['leitor_nome'] = leitor_row[0] if leitor_row else "Desconhecido"

                # Busca Exemplar e Livro
                cursor.execute("SELECT numero_patrimonio, id_livro FROM Exemplar WHERE id_exemplar = %s", [emp['id_exemplar']])
                ex_row = cursor.fetchone()
                
                if ex_row:
                    emp['numero_patrimonio'] = ex_row[0]
                    emp['id_livro'] = ex_row[1] # Necessário para buscar autores depois
                    
                    cursor.execute("SELECT nome FROM Livro WHERE id_livro = %s", [emp['id_livro']])
                    l_row = cursor.fetchone()
                    emp['livro_nome'] = l_row[0] if l_row else "Desconhecido"
                    
                    # Busca Autores (usando nossa função auxiliar sem join)
                    emp['autores_list'] = _get_autores_para_livro(emp['id_livro'])
                else:
                    emp['numero_patrimonio'] = "-"
                    emp['livro_nome'] = "-"
                    emp['autores_list'] = []
            
            contexto['emprestimos'] = emprestimos
            
    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao gerar o relatório: {e}")
        contexto['emprestimos'] = []
    
    return render(request, 'relatorio/livros_emprestados.html', contexto)

def relatorio_historico_livro_view(request):
    """
    Histórico por livro SEM JOIN.
    """
    contexto = {}
    try:
        with connection.cursor() as cursor:
            # 1. Dropdown de Livros (Tabela Simples)
            cursor.execute("SELECT id_livro AS pk, nome FROM Livro ORDER BY nome")
            todos_livros = dictfetchall(cursor)
            contexto['todos_livros'] = todos_livros
            
            # 2. Se selecionou um livro
            livro_id_selecionado = request.GET.get('livro_id')
            if livro_id_selecionado:
                # Pega dados do livro selecionado no Python (sem query extra se possível)
                livro_selecionado_dados = next((livro for livro in todos_livros if livro['pk'] == int(livro_id_selecionado)), None)
                contexto['livro_selecionado'] = livro_selecionado_dados
                
                # 3. Busca o histórico de empréstimos
                # TRUQUE: Usamos sub-select no WHERE para filtrar pelos exemplares do livro
                cursor.execute(
                    """
                    SELECT 
                        id_exemplar,
                        id_leitor,
                        dt_emprestimo,
                        dt_devolucao,
                        status
                    FROM Emprestimo 
                    WHERE id_exemplar IN (
                        SELECT id_exemplar FROM Exemplar WHERE id_livro = %s
                    )
                    ORDER BY dt_emprestimo DESC
                    """,
                    [livro_id_selecionado]
                )
                emprestimos = dictfetchall(cursor)

                # 4. Preenche os nomes (Leitor e Patrimônio)
                for emp in emprestimos:
                    # Busca Nome Leitor
                    cursor.execute("SELECT nome FROM Leitor WHERE id_leitor = %s", [emp['id_leitor']])
                    l_row = cursor.fetchone()
                    emp['leitor_nome'] = l_row[0] if l_row else "Desconhecido"

                    # Busca Patrimônio
                    cursor.execute("SELECT numero_patrimonio FROM Exemplar WHERE id_exemplar = %s", [emp['id_exemplar']])
                    e_row = cursor.fetchone()
                    emp['numero_patrimonio'] = e_row[0] if e_row else "-"

                contexto['emprestimos'] = emprestimos
    
    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao gerar o relatório: {e}")
        contexto['todos_livros'] = []
        
    return render(request, 'relatorio/historico_livro.html', contexto)