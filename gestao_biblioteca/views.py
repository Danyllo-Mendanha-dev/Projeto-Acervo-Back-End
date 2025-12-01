from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection # Para executar SQL bruto
# from django.contrib.auth.hashers import make_password

def login_view(request):
    # Verifica se o formulário foi submetido
    if request.method == 'POST':
        # Captura os dados enviados pelo HTML
        email = request.POST.get('email')
        senha = request.POST.get('senha')

        # Abre conexão para executar SQL nativo
        with connection.cursor() as cursor:
            # Executa a query com parâmetros (previne SQL Injection)
            cursor.execute(
                "SELECT id_funcionario, nome FROM Funcionario WHERE email = %s AND senha = %s", 
                [email, senha]
            )
            # Retorna o registro encontrado (ou None)
            funcionario = cursor.fetchone()

        # Verifica se a credencial é válida
        if funcionario:
            # Salva dados na sessão (mantém o login ativo)
            request.session['funcionario_logado_id'] = funcionario[0]
            request.session['funcionario_logado_nome'] = funcionario[1]
            return redirect('home')
        else:
            # Login falhou: define mensagem de erro e recarrega
            messages.error(request, 'Email ou senha inválidos.')
            return redirect('login')

    # Renderiza a página inicial de login (GET)
    return render(request, 'login.html')


# View simples para a página de dashboard
def home_view(request):
    # Verifica se o usuário está logado
    if 'funcionario_logado_id' not in request.session:
        return redirect('login')
        
    nome_funcionario = request.session.get('funcionario_logado_nome')
    
    # Conexão para buscar os indicadores
    with connection.cursor() as cursor:
        # 1. Total de Empréstimos Ativos
        cursor.execute("SELECT COUNT(*) FROM Emprestimo WHERE status = 'Em Andamento'")
        total_emprestimos = cursor.fetchone()[0]

        # 2. Total de Obras (Títulos únicos)
        cursor.execute("SELECT COUNT(*) FROM Livro")
        total_obras = cursor.fetchone()[0]

        # 3. Total de Exemplares (Livros físicos)
        cursor.execute("SELECT COUNT(*) FROM Exemplar")
        total_exemplares = cursor.fetchone()[0]

        # 4. Leitores Cadastrados
        cursor.execute("SELECT COUNT(*) FROM Leitor")
        total_leitores = cursor.fetchone()[0]

    context = {
        'nome': nome_funcionario,
        'total_emprestimos': total_emprestimos,
        'total_obras': total_obras,
        'total_exemplares': total_exemplares,
        'total_leitores': total_leitores,
    }

    # Renderiza a página inicial de dashboard
    return render(request, 'home.html', context)

def logout_view(request):
    # Limpa a sessão para fazer o logout
    request.session.flush()
    messages.success(request, 'Você saiu da sua conta com sucesso.')
    return redirect('login')

def acervo_view(request):
    """
    Esta view apenas exibe a página pública do acervo.
    No futuro, você pode adicionar lógica aqui para buscar os livros do banco.
    """
    return render(request, 'acervo.html')

# --- VIEWS PARA OS FORMULÁRIOS DE CADASTRO ---

def cadastrar_emprestimo_view(request):
    # Lógica para processar o formulário virá aqui depois (quando for POST)
    return render(request, 'emprestimo/cadastrar_emprestimo.html')

def cadastrar_exemplar_view(request):
    # Lógica para processar o formulário virá aqui depois
    return render(request, 'exemplar/cadastrar_exemplar.html')

def cadastrar_livro_view(request):
    # Lógica para processar o formulário virá aqui depois
    return render(request, 'livro/cadastrar_livro.html')

def cadastrar_autor_view(request):
    # Lógica para processar o formulário virá aqui depois
    return render(request, 'autor/cadastrar_autor.html')
# Em gestao_biblioteca/views.py

# ... (suas views de login, cadastro, etc., ficam aqui em cima) ...

# --- VIEWS PARA AS PÁGINAS DE CONSULTA / LISTAGEM ---

def consultar_autores_view(request):
    # Futuramente, buscar todos os autores.
    return render(request, 'autor/consultar_autor.html')

def consultar_livros_view(request):
    # Futuramente, buscar todos os livros.
    return render(request, 'livro/consultar_livro.html')

def consultar_exemplares_view(request):
    # Futuramente, buscar todos os exemplares.
    return render(request, 'exemplar/consultar_exemplar.html')

def consultar_emprestimos_view(request):
    # View para a lista de empréstimos, que também está no menu.
    return render(request, 'emprestimo/consultar_emprestimos.html')
    
def relatorio_index_view(request):
    """
    Esta view renderiza a página principal de relatórios.
    """
    # Certifique-se que o nome do template está correto.
    return render(request, 'relatorio/relatorio.html')