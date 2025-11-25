from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection

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

# --- View Principal do Acervo ---

def acervo_view(request):
    """
    Busca e exibe todos os livros com informações de disponibilidade 
    e autores, com filtro de busca.
    """
    query = request.GET.get('q', '')
    contexto = {'query': query}
    
    try:
        with connection.cursor() as cursor:
            # 1. Query base para buscar livros e contagem de exemplares
            # Esta query é complexa:
            # - Conta o total de exemplares (total_exemplares)
            # - Conta apenas os exemplares disponíveis
            #   (disponiveis = que não estão em um empréstimo 'Em Andamento')
            sql = """
                SELECT 
                    l.id_livro AS pk,
                    l.nome,
                    l.genero,
                    l.isbn,
                    COUNT(DISTINCT e.id_exemplar) AS total_exemplares,
                    COUNT(DISTINCT CASE 
                        WHEN emp.status IS NULL THEN e.id_exemplar 
                        ELSE NULL 
                    END) AS exemplares_disponiveis
                FROM Livro l
                LEFT JOIN Exemplar e ON l.id_livro = e.id_livro
                LEFT JOIN Emprestimo emp ON e.id_exemplar = emp.id_exemplar AND emp.status = 'Em Andamento'
            """
            
            params = []
            sql_where = ""
            
            # 2. Adiciona JOINs e WHERE apenas se houver busca
            if query:
                sql += """
                    LEFT JOIN autor_livro al ON l.id_livro = al.id_livro
                    LEFT JOIN Autor a ON al.id_autor = a.id_autor
                """
                sql_where = " WHERE l.nome ILIKE %s OR a.nome ILIKE %s"
                params.extend([f'%{query}%', f'%{query}%'])
            
            sql += sql_where
            sql += " GROUP BY l.id_livro, l.nome, l.genero, l.isbn ORDER BY l.nome"
            
            cursor.execute(sql, params)
            livros = dictfetchall(cursor)
            
            # 3. Para cada livro, busca sua lista de autores
            for livro in livros:
                livro['autores_list'] = _get_autores_para_livro(livro['pk'])
            
            contexto['livros'] = livros

    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao consultar o acervo: {e}")
        contexto['livros'] = []

    return render(request, 'acervo/acervo.html', contexto)
