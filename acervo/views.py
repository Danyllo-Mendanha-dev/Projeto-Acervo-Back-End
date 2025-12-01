from django.shortcuts import render
from django.contrib import messages
from django.db import connection

# --- Helper Function ---
def dictfetchall(cursor):
    """Retorna todas as linhas de um cursor como um dict."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def _get_autores_para_livro(livro_id):
    """Busca autores de um livro específico SEM JOIN."""
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

# --- View Principal do Acervo ---

def acervo_view(request):
    """
    Busca e exibe todos os livros com disponibilidade calculada.
    SEM JOIN (usando sub-queries e Python).
    """
    query = request.GET.get('q', '')
    contexto = {'query': query}
    
    try:
        with connection.cursor() as cursor:
            # 1. Busca os Livros (Tabela Principal)
            sql = "SELECT id_livro AS pk, nome, genero, isbn FROM Livro"
            params = []
            
            if query:
                # Filtro de busca SEM JOIN
                sql += """
                    WHERE nome ILIKE %s 
                    OR genero ILIKE %s
                    OR id_livro IN (
                        SELECT id_livro FROM autor_livro 
                        WHERE id_autor IN (SELECT id_autor FROM Autor WHERE nome ILIKE %s)
                    )
                """
                params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
            
            sql += " ORDER BY nome"
            
            cursor.execute(sql, params)
            livros = dictfetchall(cursor)
            
            # 2. Processamento (Enriquecimento dos dados)
            for livro in livros:
                livro_id = livro['pk']

                # A) Conta TOTAL de exemplares físicos
                cursor.execute("SELECT COUNT(*) FROM Exemplar WHERE id_livro = %s", [livro_id])
                total_exemplares = cursor.fetchone()[0]
                livro['total_exemplares'] = total_exemplares

                # B) Conta quantos estão EMPRESTADOS (Em Andamento)
                # Sub-query: Conta na tabela Emprestimo onde o exemplar pertence a este livro
                cursor.execute(
                    """
                    SELECT COUNT(*) 
                    FROM Emprestimo 
                    WHERE status = 'Em Andamento'
                    AND id_exemplar IN (SELECT id_exemplar FROM Exemplar WHERE id_livro = %s)
                    """, 
                    [livro_id]
                )
                qtd_emprestados = cursor.fetchone()[0]
                livro['qtd_emprestados'] = qtd_emprestados
                
                # C) Cálculo Matemático da Disponibilidade
                # Se tenho 5 livros e 2 estão emprestados -> 3 disponíveis
                livro['exemplares_disponiveis'] = total_exemplares - qtd_emprestados
                
                # Força zero se der negativo (segurança)
                if livro['exemplares_disponiveis'] < 0:
                    livro['exemplares_disponiveis'] = 0

                # D) Busca lista de autores
                livro['autores_list'] = _get_autores_para_livro(livro_id)
            
            contexto['livros'] = livros

    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao consultar o acervo: {e}")
        contexto['livros'] = []

    return render(request, 'acervo/acervo.html', contexto)