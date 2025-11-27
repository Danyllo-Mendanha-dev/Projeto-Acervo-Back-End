from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection, IntegrityError
from .forms import ExemplarForm

# --- Helper Function ---
def dictfetchall(cursor):
    """Retorna todas as linhas de um cursor como um dict."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

# --- CRUD DE EXEMPLAR ---

# CREATE (Cadastrar Exemplar)
def cadastrar_exemplar_view(request):
    if request.method == 'POST':
        form = ExemplarForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            try:
                with connection.cursor() as cursor:
                    # CORREÇÃO: Usando 'id_livro' e os campos novos. Removido 'status'.
                    cursor.execute(
                        """
                        INSERT INTO Exemplar (id_livro, numero_patrimonio, localizacao, dt_aquisicao, dt_publicacao, edicao)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        [dados['livro'], dados['numero_patrimonio'], dados['localizacao'], dados['dt_aquisicao'], dados['dt_publicacao'], dados['edicao']]
                    )
                messages.success(request, 'Exemplar cadastrado com sucesso!')
                return redirect('exemplares:exemplar_list')
            except Exception as e:
                messages.error(request, f'Ocorreu um erro ao cadastrar: {e}')
    else:
        form = ExemplarForm()

    return render(request, 'exemplar/cadastrar_exemplar.html', {'form': form, 'editando': False})

# READ (Consultar Exemplares)
def consultar_exemplares_view(request):
    query = request.GET.get('q', '')
    
    try:
        with connection.cursor() as cursor:
            # CORREÇÃO: Removido 'e.status' do SELECT. Usando 'e.id_livro'.
            sql = """
                SELECT 
                    e.id_exemplar AS pk,
                    e.numero_patrimonio,
                    e.localizacao,
                    l.nome AS livro_nome 
                FROM Exemplar e
                JOIN Livro l ON e.id_livro = l.id_livro
            """
            params = []
            
            if query:
                # Convertendo numero_patrimonio (integer) para texto para o ILIKE
                sql += " WHERE l.nome ILIKE %s OR e.numero_patrimonio::text ILIKE %s"
                params.extend([f'%{query}%', f'%{query}%'])
            else:
                sql += " ORDER BY l.nome, e.numero_patrimonio"

            cursor.execute(sql, params)
            exemplares = dictfetchall(cursor)

        return render(request, 'exemplar/consultar_exemplar.html', {'exemplares': exemplares})
    
    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao consultar os exemplares: {e}")
        return redirect('home')

# UPDATE (Atualizar Exemplar)
def atualizar_exemplar_view(request, pk):
    with connection.cursor() as cursor:
        # CORREÇÃO: Buscando os campos corretos. Usando 'e.id_livro'.
        cursor.execute(
            """
            SELECT e.id_exemplar, e.id_livro, e.numero_patrimonio, e.localizacao, 
                   e.dt_aquisicao, e.dt_publicacao, e.edicao, l.nome AS livro_nome
            FROM Exemplar e
            JOIN Livro l ON e.id_livro = l.id_livro
            WHERE e.id_exemplar = %s
            """, 
            [pk]
        )
        row = cursor.fetchone()
        if not row:
            messages.error(request, 'Exemplar não encontrado.')
            return redirect('exemplares:exemplar_list')
        
        # CORREÇÃO: Mapeamento correto dos campos.
        exemplar_data = {
            'pk': row[0],
            'livro': row[1],
            'numero_patrimonio': row[2],
            'localizacao': row[3],
            'dt_aquisicao': row[4],
            'dt_publicacao': row[5],
            'edicao': row[6],
            'livro_nome': row[7] # Usado no título da página
        }

    if request.method == 'POST':
        form = ExemplarForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            try:
                with connection.cursor() as cursor:
                    # CORREÇÃO: Query de UPDATE com os campos corretos.
                    cursor.execute(
                        """
                        UPDATE Exemplar
                        SET id_livro=%s, numero_patrimonio=%s, localizacao=%s, 
                            dt_aquisicao=%s, dt_publicacao=%s, edicao=%s
                        WHERE id_exemplar = %s
                        """,
                        [dados['livro'], dados['numero_patrimonio'], dados['localizacao'], 
                         dados['dt_aquisicao'], dados['dt_publicacao'], dados['edicao'], pk]
                    )
                messages.success(request, 'Exemplar atualizado com sucesso!')
                return redirect('exemplares:exemplar_list')
            except Exception as e:
                messages.error(request, f'Ocorreu um erro ao atualizar: {e}')
    else:
        form = ExemplarForm(initial=exemplar_data)

    context = {
        'form': form,
        'exemplar': exemplar_data,
        'editando': True
    }
    return render(request, 'exemplar/cadastrar_exemplar.html', context)

# DELETE (Excluir Exemplar)
def excluir_exemplar_view(request, pk):
    with connection.cursor() as cursor:
        # Busca o patrimônio e o nome do livro associado
        cursor.execute(
            """
            SELECT e.numero_patrimonio, l.nome
            FROM Exemplar e
            JOIN Livro l ON e.id_livro = l.id_livro
            WHERE e.id_exemplar = %s
            """,
            [pk]
        )
        exemplar_row = cursor.fetchone()
    
    if not exemplar_row:
        messages.error(request, 'Exemplar não encontrado.')
        return redirect('exemplares:exemplar_list')
    
    exemplar_data = {
        'numero_patrimonio': exemplar_row[0],
        'livro_nome': exemplar_row[1]  # <-- Aqui guardamos o nome do livro
    }

    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM Exemplar WHERE id_exemplar = %s", [pk])
            
            # Mensagem de sucesso usa o patrimônio (pois foi ele que sumiu)
            messages.success(request, f'Exemplar "{exemplar_data["numero_patrimonio"]}" excluído com sucesso.')
            return redirect('exemplares:exemplar_list')
            
        except IntegrityError:
            # CORREÇÃO AQUI: Usamos exemplar_data["livro_nome"] na mensagem de erro
            messages.error(request, f'Não é possível excluir este exemplar do livro "{exemplar_data["livro_nome"]}", pois ele está associado a um empréstimo.')
            return redirect('exemplares:exemplar_list')
            
        except Exception as e:
            messages.error(request, f'Ocorreu um erro ao excluir: {e}')
            return redirect('exemplares:exemplar_list')

    return render(request, 'exemplar/excluir_exemplar.html', {'exemplar': exemplar_data})