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
                    # 1. Insere o livro
                    cursor.execute(
                        """
                        INSERT INTO Livro (nome, genero, isbn, qtde_exemplares, status)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id_livro 
                        """,
                        [dados['nome'], dados['genero'], dados['isbn'], dados['qtde_exemplares'], dados['status']]
                    )
                    id_livro_novo = cursor.fetchone()[0]
                    
                    # 2. Insere autores (loop simples, sem join)
                    ids_autores = dados.get('autores', [])
                    for id_autor_loop in ids_autores:
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
        # 1. Busca os livros (Tabela principal apenas)
        sql = "SELECT id_livro AS pk, nome, isbn, genero, status FROM Livro"
        params = []
        
        if query:
            # Filtro simples na tabela Livro
            sql += " WHERE nome ILIKE %s OR isbn ILIKE %s"
            params.extend([f'%{query}%', f'%{query}%'])
        
        sql += " ORDER BY nome"
        
        cursor.execute(sql, params)
        livros = dictfetchall(cursor)

        # 2. Loop para buscar dados relacionados (O "JOIN manual" via Python)
        for livro in livros:
            livro_id = livro['pk']

            # A) Conta total de exemplares físicos
            cursor.execute("SELECT COUNT(*) FROM Exemplar WHERE id_livro = %s", [livro_id])
            total_fisico = cursor.fetchone()[0]
            livro['total_fisico'] = total_fisico

            # B) Conta quantos estão emprestados 
            # (Precisamos saber quais exemplares deste livro estão em emprestimos ativos)
            # Fazemos sub-query ou filtro direto
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM Emprestimo 
                WHERE status = 'Em Andamento' 
                AND id_exemplar IN (SELECT id_exemplar FROM Exemplar WHERE id_livro = %s)
                """, 
                [livro_id]
            )
            total_emprestado = cursor.fetchone()[0]
            
            # C) Calcula disponibilidade
            livro['disponiveis'] = total_fisico - total_emprestado

            # D) Busca os Autores (Sem JOIN)
            # Primeiro: pega os IDs dos autores na tabela de ligação
            cursor.execute("SELECT id_autor FROM autor_livro WHERE id_livro = %s", [livro_id])
            rows_autores = cursor.fetchall()
            ids_autores = [r[0] for r in rows_autores]
            
            autores_list = []
            if ids_autores:
                # Segundo: para cada ID, busca o nome na tabela Autor
                # (Poderíamos usar IN, mas um loop simples também resolve se quiser evitar SQL complexo)
                # Vamos usar IN para ser um pouco mais otimizado, mas sem JOIN
                placeholders = ','.join(['%s'] * len(ids_autores))
                cursor.execute(f"SELECT nome FROM Autor WHERE id_autor IN ({placeholders})", ids_autores)
                autores_list = dictfetchall(cursor)
            
            livro['autores_list'] = autores_list

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
        
        # 2. Busca os IDs dos autores (Select simples na tabela de ligação)
        cursor.execute("SELECT id_autor FROM autor_livro WHERE id_livro = %s", [pk])
        livro_data['autores'] = [row[0] for row in cursor.fetchall()]


    if request.method == 'POST':
        form = LivroForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            try:
                with connection.cursor() as cursor:
                    # 1. Atualiza Livro
                    cursor.execute(
                        """
                        UPDATE Livro
                        SET nome=%s, genero=%s, isbn=%s, qtde_exemplares=%s, status=%s
                        WHERE id_livro = %s
                        """,
                        [dados['nome'], dados['genero'], dados['isbn'], dados['qtde_exemplares'], dados['status'], pk]
                    )
                    
                    # 2. Atualiza Autores (Remove tudo e insere de novo)
                    cursor.execute("DELETE FROM autor_livro WHERE id_livro = %s", [pk])
                    
                    ids_autores = dados.get('autores', [])
                    for id_autor_loop in ids_autores:
                        cursor.execute(
                            "INSERT INTO autor_livro (id_livro, id_autor) VALUES (%s, %s)",
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
    # 1. Busca prévia para confirmação visual
    with connection.cursor() as cursor:
        cursor.execute("SELECT nome FROM Livro WHERE id_livro = %s", [pk])
        livro = cursor.fetchone()
    
    if not livro:
        messages.error(request, 'Livro não encontrado.')
        return redirect('livros:livro_list')

    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                # 2. LIMPEZA MANUAL DA TABELA ASSOCIATIVA (N:M)
                # Como Livro tem relação N:M com Autor, precisamos deletar 
                # o vínculo na tabela 'autor_livro' ANTES de deletar o livro.
                cursor.execute("DELETE FROM autor_livro WHERE id_livro = %s", [pk])
                
                # 3. EXCLUSÃO DA ENTIDADE PRINCIPAL
                # Agora que a tabela de ligação está limpa, podemos apagar o livro.
                cursor.execute("DELETE FROM Livro WHERE id_livro = %s", [pk])
            
            messages.success(request, f'Obra "{livro[0]}" excluída com sucesso.')
            return redirect('livros:livro_list')
            
        except IntegrityError: 
            # 4. VALIDAÇÃO DE INTEGRIDADE (1:N)
            # Se existirem exemplares (cópias físicas) na tabela Exemplar,
            # o banco impede o delete do Livro (Foreign Key) e caímos aqui.
            messages.error(request, f'Não é possível excluir a obra "{livro[0]}", pois ela possui exemplares associados.')
            return redirect('livros:livro_list')
            
        except Exception as e:
            messages.error(request, f'Ocorreu um erro ao excluir: {e}')
            return redirect('livros:livro_list')

    return render(request, 'livro/excluir_livro.html', {'livro': {'nome': livro[0]}})