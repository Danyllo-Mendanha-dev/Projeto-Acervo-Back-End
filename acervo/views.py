from django.shortcuts import render
from django.contrib import messages
from django.db import connection

# --- Helper Function ---
def dictfetchall(cursor):
    """Retorna todas as linhas de um cursor como um dict."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def _get_autores_para_livro(livro_id):
    """Busca autores de um livro específico."""
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

# --- View Principal do Acervo ---

def acervo_view(request): # Note: Use o nome exato que está no seu urls.py
    """
    Busca e exibe todos os livros, calculando matematicamente a disponibilidade.
    Fórmula: Disponíveis = Total de Exemplares - Empréstimos Ativos
    """
    query = request.GET.get('q', '')
    contexto = {'query': query}
    
    try:
        with connection.cursor() as cursor:
            # 1. Query Otimizada com Sub-selects
            # Isso evita erros de contagem quando o livro tem múltiplos autores
            sql = """
                SELECT 
                    l.id_livro AS pk,
                    l.nome,
                    l.genero,
                    l.isbn,
                    
                    -- Sub-query 1: Conta quantos exemplares físicos existem
                    (SELECT COUNT(*) 
                     FROM Exemplar e 
                     WHERE e.id_livro = l.id_livro) AS total_exemplares,

                    -- Sub-query 2: Conta quantos estão emprestados AGORA
                    (SELECT COUNT(*) 
                     FROM Emprestimo emp 
                     JOIN Exemplar e ON emp.id_exemplar = e.id_exemplar 
                     WHERE e.id_livro = l.id_livro 
                     AND emp.status = 'Em Andamento') AS qtd_emprestados

                FROM Livro l 
                """
            
            params = []
            
            # 2. Filtros de Busca
            if query:
                sql += """
                    LEFT JOIN autor_livro al ON l.id_livro = al.id_livro 
                    LEFT JOIN Autor a ON al.id_autor = a.id_autor
                    WHERE l.nome ILIKE %s OR a.nome ILIKE %s OR l.genero ILIKE %s
                    GROUP BY l.id_livro
                """
                params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
            
            sql += " ORDER BY l.nome"
            
            cursor.execute(sql, params)
            livros = dictfetchall(cursor)
            
            # 3. Processamento no Python (Cálculo Real)
            for livro in livros:
                # Garante que não venha None do banco
                total = livro['total_exemplares'] or 0
                emprestados = livro['qtd_emprestados'] or 0
                
                # A MÁGICA: Subtração simples e infalível
                livro['exemplares_disponiveis'] = total - emprestados
                
                # Se der negativo por erro de banco, força zero
                if livro['exemplares_disponiveis'] < 0:
                    livro['exemplares_disponiveis'] = 0

                # Busca a lista de autores para exibir no card
                livro['autores_list'] = _get_autores_para_livro(livro['pk'])
            
            contexto['livros'] = livros

    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao consultar o acervo: {e}")
        contexto['livros'] = []

    return render(request, 'acervo/acervo.html', contexto)