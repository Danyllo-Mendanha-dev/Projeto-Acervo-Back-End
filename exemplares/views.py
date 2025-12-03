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
                    # INSERT Simples: Grava a FK (id_livro) diretamente na tabela Exemplar
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
            # 1. Busca Inicial (Apenas dados do Exemplar)
            # Note que não trazemos o nome do livro aqui, apenas o ID.
            sql = """
                SELECT e.id_exemplar AS pk, e.numero_patrimonio, e.localizacao, e.id_livro 
                FROM Exemplar e
            """
            params = []
            
            if query:
                # 2. Filtragem via Subquery (Substitui o JOIN no WHERE)
                # Buscamos o ID do livro em uma subconsulta para filtrar o exemplar
                sql += """
                    WHERE e.numero_patrimonio::text ILIKE %s 
                    OR e.id_livro IN (SELECT id_livro FROM Livro WHERE nome ILIKE %s)
                """
                params.extend([f'%{query}%', f'%{query}%'])
            
            # Ordenação via Subquery no ORDER BY
            sql += " ORDER BY (SELECT nome FROM Livro WHERE id_livro = e.id_livro), e.numero_patrimonio"

            cursor.execute(sql, params)
            exemplares = dictfetchall(cursor)

            # 3. "Hidratação" Manual dos Dados (Substitui o JOIN no SELECT)
            # Para cada exemplar, fazemos uma query extra para buscar o nome do livro.
            # Conhecido como padrão "N+1", usado aqui para fins didáticos de separação de responsabilidade.
            for exemplar in exemplares:
                cursor.execute("SELECT nome FROM Livro WHERE id_livro = %s", [exemplar['id_livro']])
                row = cursor.fetchone()
                exemplar['livro_nome'] = row[0] if row else "Livro Desconhecido"

        return render(request, 'exemplar/consultar_exemplar.html', {'exemplares': exemplares})
    
    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao consultar os exemplares: {e}")
        return redirect('home')

# UPDATE (Atualizar Exemplar - SEM JOIN)
def atualizar_exemplar_view(request, pk):
    with connection.cursor() as cursor:
        # 1. Recupera dados do Exemplar
        cursor.execute("SELECT id_exemplar, id_livro, numero_patrimonio, localizacao, dt_aquisicao, dt_publicacao, edicao FROM Exemplar WHERE id_exemplar = %s", [pk])
        row = cursor.fetchone()
        if not row:
            messages.error(request, 'Exemplar não encontrado.')
            return redirect('exemplares:exemplar_list')
        
        # --- CORREÇÃO DE DATAS AQUI ---
        # Formata 'dt_aquisicao' (índice 4)
        dt_aquisicao_banco = row[4]
        dt_aquisicao_fmt = dt_aquisicao_banco.strftime('%d/%m/%Y') if dt_aquisicao_banco else None

        # Formata 'dt_publicacao' (índice 5)
        # Atenção: dt_publicacao pode ser apenas um ano (YYYY) ou data completa dependendo do seu banco. 
        # Se for DATE, usamos strftime. Se for INTEGER, deixamos como está.
        # Assumindo que é DATE conforme seu formulário:
        dt_publicacao_banco = row[5]
        dt_publicacao_fmt = dt_publicacao_banco.strftime('%d/%m/%Y') if dt_publicacao_banco else None
        # ------------------------------

        # 2. Query Separada para recuperar o Nome do Livro
        id_livro_atual = row[1]
        cursor.execute("SELECT nome FROM Livro WHERE id_livro = %s", [id_livro_atual])
        livro_row = cursor.fetchone()
        nome_livro = livro_row[0] if livro_row else "Desconhecido"

        exemplar_data = {
            'pk': row[0], 
            'livro': row[1], 
            'numero_patrimonio': row[2],
            'localizacao': row[3], 
            'dt_aquisicao': dt_aquisicao_fmt,   # Usa a data formatada
            'dt_publicacao': dt_publicacao_fmt, # Usa a data formatada
            'edicao': row[6], 
            'livro_nome': nome_livro
        }

    if request.method == 'POST':
        form = ExemplarForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            try:
                with connection.cursor() as cursor:
                    # UPDATE padrão
                    cursor.execute(
                        """
                        UPDATE Exemplar
                        SET id_livro=%s, numero_patrimonio=%s, localizacao=%s, dt_aquisicao=%s, dt_publicacao=%s, edicao=%s
                        WHERE id_exemplar = %s
                        """,
                        [dados['livro'], dados['numero_patrimonio'], dados['localizacao'], dados['dt_aquisicao'], dados['dt_publicacao'], dados['edicao'], pk]
                    )
                messages.success(request, 'Exemplar atualizado com sucesso!')
                return redirect('exemplares:exemplar_list')
            except Exception as e:
                messages.error(request, f'Ocorreu um erro ao atualizar: {e}')
    else:
        form = ExemplarForm(initial=exemplar_data)

    context = {'form': form, 'exemplar': exemplar_data, 'editando': True}
    return render(request, 'exemplar/cadastrar_exemplar.html', context)
# DELETE (Excluir Exemplar - SEM JOIN)
def excluir_exemplar_view(request, pk):
    # 1. Busca dados para montar a mensagem de confirmação
    with connection.cursor() as cursor:
        cursor.execute("SELECT numero_patrimonio, id_livro FROM Exemplar WHERE id_exemplar = %s", [pk])
        exemplar_row = cursor.fetchone()
    
    if not exemplar_row:
        messages.error(request, 'Exemplar não encontrado.')
        return redirect('exemplares:exemplar_list')
    
    # 2. Busca nome do livro separadamente
    with connection.cursor() as cursor:
        cursor.execute("SELECT nome FROM Livro WHERE id_livro = %s", [exemplar_row[1]])
        livro_row = cursor.fetchone()
        nome_livro = livro_row[0] if livro_row else "Desconhecido"

    exemplar_data = {'numero_patrimonio': exemplar_row[0], 'livro_nome': nome_livro}

    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                # Tenta Exclusão Física
                cursor.execute("DELETE FROM Exemplar WHERE id_exemplar = %s", [pk])
            
            messages.success(request, f'Exemplar "{exemplar_data["numero_patrimonio"]}" excluído com sucesso.')
            return redirect('exemplares:exemplar_list')
            
        except IntegrityError:
            # Captura erro se o exemplar estiver em um Empréstimo ativo
            messages.error(request, f'Não é possível excluir este exemplar do livro "{exemplar_data["livro_nome"]}", pois ele está associado a um empréstimo.')
            return redirect('exemplares:exemplar_list')
            
        except Exception as e:
            messages.error(request, f'Ocorreu um erro ao excluir: {e}')
            return redirect('exemplares:exemplar_list')

    return render(request, 'exemplar/excluir_exemplar.html', {'exemplar': exemplar_data})