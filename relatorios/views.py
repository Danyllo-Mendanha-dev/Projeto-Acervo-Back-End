from django.shortcuts import render

# Create your views here.
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
    """Função auxiliar para buscar autores de um livro específico."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT a.nome 
            FROM Autor a
            JOIN autor_livro al ON a.id_autor = al.id_autor
            WHERE al.id_livro = %s
            ORDER BY a.nome
            """,
            [livro_id]
        )
        return dictfetchall(cursor)

# --- Views de Relatório ---

def relatorio_index_view(request):
    """Apenas renderiza a página principal (menu) de relatórios."""
    return render(request, 'relatorio/relatorio.html')

def relatorio_leitores_atrasados_view(request):
    """Busca todos os empréstimos com status 'Em Andamento' e data de devolução ultrapassada."""
    contexto = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    le.nome AS leitor_nome, 
                    le.telefone AS leitor_telefone,
                    l.nome AS livro_nome,
                    e.numero_patrimonio,
                    emp.dt_prevista_devolucao,
                    (CURRENT_DATE - emp.dt_prevista_devolucao) AS dias_atraso
                FROM Emprestimo emp
                JOIN Leitor le ON emp.id_leitor = le.id_leitor
                JOIN Exemplar e ON emp.id_exemplar = e.id_exemplar
                JOIN Livro l ON e.id_livro = l.id_livro
                WHERE emp.status = 'Em Andamento' 
                  AND emp.dt_prevista_devolucao < CURRENT_DATE
                ORDER BY dias_atraso DESC
                """
            )
            contexto['emprestimos_atrasados'] = dictfetchall(cursor)
    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao gerar o relatório: {e}")
        contexto['emprestimos_atrasados'] = []

    return render(request, 'relatorio/leitores_atrasados.html', contexto)

def relatorio_livros_emprestados_view(request):
    """Busca todos os empréstimos com status 'Em Andamento' (atrasados ou não)."""
    contexto = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    emp.id_emprestimo,       -- <--- ADICIONE ESTA LINHA AQUI!
                    l.id_livro,
                    l.nome AS livro_nome,
                    e.numero_patrimonio,
                    le.nome AS leitor_nome,
                    emp.dt_emprestimo,
                    emp.dt_prevista_devolucao
                FROM Emprestimo emp
                JOIN Exemplar e ON emp.id_exemplar = e.id_exemplar
                JOIN Livro l ON e.id_livro = l.id_livro
                JOIN Leitor le ON emp.id_leitor = le.id_leitor
                WHERE emp.status = 'Em Andamento'
                ORDER BY emp.dt_prevista_devolucao ASC
                """
            )
            emprestimos = dictfetchall(cursor)
            
            # Para cada empréstimo, verificamos o status de atraso e buscamos os autores
            for emp in emprestimos:
                emp['is_atrasado'] = emp['dt_prevista_devolucao'] < date.today()
                emp['autores_list'] = _get_autores_para_livro(emp['id_livro'])
            
            contexto['emprestimos'] = emprestimos
            
    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao gerar o relatório: {e}")
        contexto['emprestimos'] = []
    
    return render(request, 'relatorio/livros_emprestados.html', contexto)

def relatorio_historico_livro_view(request):
    """
    Mostra um dropdown com todos os livros. 
    Se um livro for selecionado, mostra seu histórico de empréstimos.
    """
    contexto = {}
    try:
        with connection.cursor() as cursor:
            # 1. Busca todos os livros para o dropdown
            cursor.execute("SELECT id_livro AS pk, nome FROM Livro ORDER BY nome")
            todos_livros = dictfetchall(cursor)
            contexto['todos_livros'] = todos_livros
            
            # 2. Verifica se um livro foi selecionado via GET
            livro_id_selecionado = request.GET.get('livro_id')
            if livro_id_selecionado:
                # Encontra os dados do livro selecionado
                livro_selecionado_dados = next((livro for livro in todos_livros if livro['pk'] == int(livro_id_selecionado)), None)
                contexto['livro_selecionado'] = livro_selecionado_dados
                
                # 3. Busca o histórico de empréstimos desse livro (de todos os seus exemplares)
                cursor.execute(
                    """
                    SELECT 
                        e.numero_patrimonio,
                        le.nome AS leitor_nome,
                        emp.dt_emprestimo,
                        emp.dt_devolucao,
                        emp.status
                    FROM Emprestimo emp
                    JOIN Exemplar e ON emp.id_exemplar = e.id_exemplar
                    JOIN Leitor le ON emp.id_leitor = le.id_leitor
                    WHERE e.id_livro = %s
                    ORDER BY emp.dt_emprestimo DESC
                    """,
                    [livro_id_selecionado]
                )
                contexto['emprestimos'] = dictfetchall(cursor)
    
    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao gerar o relatório: {e}")
        contexto['todos_livros'] = []
        
    return render(request, 'relatorio/historico_livro.html', contexto)
