from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection, IntegrityError
from .forms import LivroForm

# --- Helper Function ---
def dictfetchall(cursor):
    """Retorna todas as linhas de um cursor como um dict."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

# --- CRUD DE LIVRO ---

# CREATE (Cadastrar Livro)
def cadastrar_livro_view(request):
    if request.method == 'POST':
        form = LivroForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            try:
                with connection.cursor() as cursor:
                    # 1. Insere o livro na tabela principal e obtém o ID
                    cursor.execute(
                        """
                        INSERT INTO Livro (nome, genero, isbn, qtde_exemplares, status)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id_livro 
                        """,
                        [dados['nome'], dados['genero'], dados['isbn'], dados['qtde_exemplares'], dados['status']]
                    )
                    id_livro_novo = cursor.fetchone()[0]
                    
                    # 2. Insere as associações na tabela autor_livro com os nomes de coluna corretos
                    ids_autores = dados.get('autores', [])
                    for id_autor_loop in ids_autores: # Renomeado para evitar conflito de nome
                        # !!! CORREÇÃO AQUI nos nomes das colunas !!!
                        cursor.execute(
                            """
                            INSERT INTO autor_livro (id_livro, id_autor) 
                            VALUES (%s, %s)
                            """,
                            [id_livro_novo, id_autor_loop]
                        )
                        
                messages.success(request, 'Livro cadastrado com sucesso!')
                return redirect('livros:livro_list')
            except Exception as e:
                messages.error(request, f'Ocorreu um erro ao cadastrar: {e}')
    else:
        form = LivroForm()

    return render(request, 'livro/cadastrar_livro.html', {'form': form, 'editando': False})

# READ (Consultar Livros)
def consultar_livros_view(request):
    query = request.GET.get('q', '')
    
    with connection.cursor() as cursor:
        # AQUI ESTÁ A MUDANÇA:
        # Usamos sub-selects para contar o estoque real, igual fizemos no Acervo
        sql = """
            SELECT 
                l.id_livro AS pk, 
                l.nome, 
                l.genero, 
                l.status,
                
                -- Conta total de exemplares físicos
                (SELECT COUNT(*) FROM Exemplar e WHERE e.id_livro = l.id_livro) as total_fisico,
                
                -- Conta quantos estão emprestados
                (SELECT COUNT(*) FROM Emprestimo emp 
                 JOIN Exemplar e ON emp.id_exemplar = e.id_exemplar 
                 WHERE e.id_livro = l.id_livro AND emp.status = 'Em Andamento') as total_emprestado
            
            FROM Livro l
        """
        
        params = []
        
        if query:
            sql += """
                LEFT JOIN autor_livro al ON l.id_livro = al.id_livro 
                LEFT JOIN Autor a ON al.id_autor = a.id_autor
                WHERE l.nome ILIKE %s OR l.isbn ILIKE %s OR a.nome ILIKE %s
                GROUP BY l.id_livro
            """
            params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
        else:
            sql += " ORDER BY l.nome"
            
        cursor.execute(sql, params)
        livros = dictfetchall(cursor)

        # Processamento Python
        for livro in livros:
            # 1. Calcula disponibilidade
            total = livro['total_fisico'] or 0
            emprestados = livro['total_emprestado'] or 0
            livro['disponiveis'] = total - emprestados
            
            # 2. Busca Autores
            with connection.cursor() as autor_cursor:
                autor_cursor.execute(
                    """
                    SELECT a.nome 
                    FROM Autor a
                    JOIN autor_livro al ON a.id_autor = al.id_autor 
                    WHERE al.id_livro = %s
                    """,
                    [livro['pk']]
                )
                livro['autores_list'] = dictfetchall(autor_cursor)

    return render(request, 'livro/consultar_livro.html', {'livros': livros})

# UPDATE (Atualizar Livro)
def atualizar_livro_view(request, pk):
    with connection.cursor() as cursor:
        # 1. Busca os dados do livro
        cursor.execute("SELECT id_livro, nome, genero, isbn, qtde_exemplares, status FROM Livro WHERE id_livro = %s", [pk])
        livro_row = cursor.fetchone()
        if not livro_row:
            messages.error(request, 'Livro não encontrado.')
            return redirect('livros:livro_list')
        
        livro_data = {
            'pk': livro_row[0], 'nome': livro_row[1], 'genero': livro_row[2], 
            'isbn': livro_row[3], 'qtde_exemplares': livro_row[4], 'status': livro_row[5]
        }
        
        # 2. Busca os IDs dos autores já selecionados na tabela autor_livro
         # !!! CORREÇÃO AQUI no nome da coluna !!!
        cursor.execute("SELECT id_autor FROM autor_livro WHERE id_livro = %s", [pk])
        livro_data['autores'] = [row[0] for row in cursor.fetchall()]


    if request.method == 'POST':
        form = LivroForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            try:
                with connection.cursor() as cursor:
                    # 1. Atualiza a tabela principal 'Livro'
                    cursor.execute(
                        """
                        UPDATE Livro
                        SET nome=%s, genero=%s, isbn=%s, qtde_exemplares=%s, status=%s
                        WHERE id_livro = %s
                        """,
                        [dados['nome'], dados['genero'], dados['isbn'], dados['qtde_exemplares'], dados['status'], pk]
                    )
                    
                    # 2. Remove todas as associações de autores antigas da tabela autor_livro
                     # !!! CORREÇÃO AQUI no nome da coluna !!!
                    cursor.execute("DELETE FROM autor_livro WHERE id_livro = %s", [pk])
                    
                    # 3. Re-insere as novas associações de autores na tabela autor_livro
                    ids_autores = dados.get('autores', [])
                    for id_autor_loop in ids_autores: # Renomeado para evitar conflito
                         # !!! CORREÇÃO AQUI nos nomes das colunas !!!
                        cursor.execute(
                            """
                            INSERT INTO autor_livro (id_livro, id_autor)
                            VALUES (%s, %s)
                            """,
                            [pk, id_autor_loop]
                        )
                        
                messages.success(request, 'Livro atualizado com sucesso!')
                return redirect('livros:livro_list')
            except Exception as e:
                messages.error(request, f'Ocorreu um erro ao atualizar: {e}')
    else:
        form = LivroForm(initial=livro_data)

    context = {
        'form': form,
        'livro': livro_data,
        'editando': True
    }
    return render(request, 'livro/cadastrar_livro.html', context)

# DELETE (Excluir Livro)
def excluir_livro_view(request, pk):
    with connection.cursor() as cursor:
        cursor.execute("SELECT nome FROM Livro WHERE id_livro = %s", [pk])
        livro = cursor.fetchone()
    
    if not livro:
        messages.error(request, 'Livro não encontrado.')
        return redirect('livros:livro_list')

    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                # Deletamos as associações primeiro da tabela autor_livro
                 # !!! CORREÇÃO AQUI no nome da coluna !!!
                cursor.execute("DELETE FROM autor_livro WHERE id_livro = %s", [pk])
                # Depois o livro
                cursor.execute("DELETE FROM Livro WHERE id_livro = %s", [pk])
            
            messages.success(request, f'Obra "{livro[0]}" excluída com sucesso.')
            return redirect('livros:livro_list')
        except IntegrityError: 
            messages.error(request, f'Não é possível excluir a obra "{livro[0]}", pois ela possui exemplares associados.')
            return redirect('livros:livro_list')
        except Exception as e:
            messages.error(request, f'Ocorreu um erro ao excluir: {e}')
            return redirect('livros:livro_list')

    return render(request, 'livro/excluir_livro.html', {'livro': {'nome': livro[0]}})