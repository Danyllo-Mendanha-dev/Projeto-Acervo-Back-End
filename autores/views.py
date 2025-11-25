from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection, IntegrityError
from .forms import AutorForm 

# --- Helper Function ---
def dictfetchall(cursor):
    """Retorna todas as linhas de um cursor como um dict."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

# --- CRUD DE AUTOR ---

# CREATE (Cadastrar Autor)
def cadastrar_autor_view(request):
    if request.method == 'POST':
        form = AutorForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            try:
                with connection.cursor() as cursor:
                    # CORREÇÃO: Adicionamos 'biografia' ao INSERT
                    cursor.execute(
                        """
                        INSERT INTO Autor (nome, nacionalidade, biografia)
                        VALUES (%s, %s, %s)
                        """,
                        # CORREÇÃO: Adicionamos o dado da biografia
                        [dados['nome'], dados['nacionalidade'], dados['biografia']]
                    )
                messages.success(request, 'Autor cadastrado com sucesso!')
                return redirect('autores:autor_list')
            except Exception as e:
                messages.error(request, f'Ocorreu um erro ao cadastrar: {e}')
    else:
        form = AutorForm()

    return render(request, 'autor/cadastrar_autor.html', {'form': form})

# READ (Consultar Autores)
def consultar_autores_view(request):
    query = request.GET.get('q', '')
    
    with connection.cursor() as cursor:
        sql = "SELECT id_autor AS pk, nome, nacionalidade FROM Autor"
        params = []
        
        if query:
            sql += " WHERE nome ILIKE %s"
            params.append(f'%{query}%')
        else:
            sql += " ORDER BY nome"
        
        cursor.execute(sql, params)
        
        autores = dictfetchall(cursor)

    return render(request, 'autor/consultar_autor.html', {'autores': autores})

# UPDATE (Atualizar Autor)
def atualizar_autor_view(request, pk):
    with connection.cursor() as cursor:
        # CORREÇÃO: Adicionamos 'biografia' ao SELECT
        cursor.execute("SELECT id_autor, nome, nacionalidade, biografia FROM Autor WHERE id_autor = %s", [pk])
        row = cursor.fetchone()
        if not row:
            messages.error(request, 'Autor não encontrado.')
            return redirect('autores:autor_list')
        
        # CORREÇÃO: Adicionamos 'biografia' ao dicionário
        autor_data = {
            'pk': row[0],
            'nome': row[1],
            'nacionalidade': row[2],
            'biografia': row[3]  # Índice 3, conforme a imagem do seu banco
        }

    if request.method == 'POST':
        form = AutorForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            try:
                with connection.cursor() as cursor:
                    # CORREÇÃO: Adicionamos 'biografia' ao UPDATE
                    sql_query = """
                        UPDATE Autor
                        SET nome=%s, nacionalidade=%s, biografia=%s
                        WHERE id_autor = %s
                    """
                    # CORREÇÃO: Adicionamos o dado da biografia
                    params = [dados['nome'], dados['nacionalidade'], dados['biografia'], pk]
                    cursor.execute(sql_query, params)
                messages.success(request, 'Autor atualizado com sucesso!')
                return redirect('autores:autor_list')
            except Exception as e:
                messages.error(request, f'Ocorreu um erro ao atualizar: {e}')
    else:
        form = AutorForm(initial=autor_data)

    context = {
        'form': form,
        'autor': autor_data,
        'editando': True
    }
    return render(request, 'autor/cadastrar_autor.html', context)

# DELETE (Excluir Autor)
def excluir_autor_view(request, pk):
    with connection.cursor() as cursor:
        cursor.execute("SELECT nome FROM Autor WHERE id_autor = %s", [pk])
        autor = cursor.fetchone()
    
    if not autor:
        messages.error(request, 'Autor não encontrado.')
        return redirect('autores:autor_list')

    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM Autor WHERE id_autor = %s", [pk])
            messages.success(request, f'Autor "{autor[0]}" excluído com sucesso.')
            return redirect('autores:autor_list')
        except IntegrityError:
            messages.error(request, f'Não é possível excluir o autor "{autor[0]}", pois ele está associado a um ou mais livros.')
            return redirect('autores:autor_list')
        except Exception as e:
            messages.error(request, f'Ocorreu um erro ao excluir: {e}')
            return redirect('autores:autor_list')

    return render(request, 'autor/excluir_autor.html', {'autor': {'nome': autor[0]}})