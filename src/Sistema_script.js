// ============================================================
//  SimpStock Frontend Script - v2.0 (JWT Auth, API & Live Demo)
// ============================================================

// Detecta dinamicamente a URL da API (permite URL customizada, localhost ou produção)
const API_URL = (() => {
    const custom = localStorage.getItem("custom_api_url");
    if (custom) return custom;
    const host = window.location.hostname;
    const proto = window.location.protocol;
    if (host === "localhost" || host === "127.0.0.1" || proto === "file:") {
        return "http://127.0.0.1:5000";
    }
    return "https://wthiagos.pythonanywhere.com";
})();

function isDemoMode() {
    return localStorage.getItem("token") === "demo-token-jwt-preview";
}

// Inicializa dados de demonstração caso o usuário teste via GitHub Pages sem backend ativo
function inicializarDadosDemo() {
    if (!localStorage.getItem("demo_produtos")) {
        const produtosIniciais = [
            { id: 1, usuario_id: 99, nome: "Teclado Mecânico RGB", marca: "Keychron", validade: null, codigo: "SKU-KEY-01", quantidade: 35, referencia: "REF-K2-V2", endereco: "Corredor A, Prateleira 2" },
            { id: 2, usuario_id: 99, nome: "Monitor 27'' IPS 144Hz", marca: "LG UltraGear", validade: null, codigo: "SKU-MON-27", quantidade: 14, referencia: "REF-27GN65R", endereco: "Corredor B, Prateleira 5" },
            { id: 3, usuario_id: 99, nome: "Cadeira Ergonômica Pro", marca: "Flexform", validade: null, codigo: "SKU-CAD-09", quantidade: 8, referencia: "REF-FLEX-PLUS", endereco: "Depósito Central" }
        ];
        localStorage.setItem("demo_produtos", JSON.stringify(produtosIniciais));
    }
    if (!localStorage.getItem("demo_usuarios")) {
        const usuariosIniciais = [
            { id: 1, nome: "ADM Principal", email: "admin@simpstock.com", is_admin: true, criado_em: "2026-09-09 20:00:00" },
            { id: 99, nome: "Lojista Demo", email: "demo@simpstock.com", is_admin: true, criado_em: "2026-09-09 21:00:00" },
            { id: 3, nome: "Carlos Varejo", email: "carlos@varejo.com", is_admin: false, criado_em: "2026-09-09 21:30:00" }
        ];
        localStorage.setItem("demo_usuarios", JSON.stringify(usuariosIniciais));
    }
}

// --- GESTÃO DE TOKENS E CABEÇALHOS JWT ---
function getAuthToken() {
    return localStorage.getItem("token") || "";
}

function getAuthHeaders(extraHeaders = {}) {
    const headers = {
        "Content-Type": "application/json",
        ...extraHeaders
    };
    const token = getAuthToken();
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
}

function getUsuarioId() {
    return parseInt(localStorage.getItem("usuarioId"), 10) || null;
}

function getIsAdmin() {
    return localStorage.getItem("isAdmin") === "true";
}

// --- TOASTS MODERNOS ---
function mostrarAlerta(mensagem, tipo = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${tipo}`;
    
    let icone = tipo === 'success' ? '✅ ' : tipo === 'error' ? '❌ ' : '⚠️ ';
    toast.innerText = icone + mensagem;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        toast.addEventListener('animationend', () => toast.remove());
    }, 3000);
}

function escaparHTML(str) {
    if (str === null || str === undefined) return '-';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("usuarioLogado");
    localStorage.removeItem("usuarioId");
    localStorage.removeItem("isAdmin");
    localStorage.removeItem("idProdutoEdicao");
    window.location.href = "Login.html";
}

function verificarAutenticacao() {
    const token = getAuthToken();
    if (!token) {
        mostrarAlerta("Você precisa fazer login para acessar esta página.", "warning");
        setTimeout(() => { window.location.href = "Login.html"; }, 1500);
        return false;
    }
    return true;
}

document.addEventListener("DOMContentLoaded", () => {
    const path = window.location.pathname;
    const isPublic = path.includes("Login.html") || path.includes("index.html") || path.includes("Sobre_n") || path.includes("Ajuda.html");

    // Ajusta menu da página de ajuda se logado
    const navAjuda = document.getElementById("navAjuda");
    if (navAjuda && getAuthToken()) {
        navAjuda.innerHTML = `
            <li class="nav-item"><a href="Tela_inicial.html"><strong>Voltar ao Sistema</strong></a></li>
            <li class="nav-item"><a href="#" onclick="logout(); return false;"><strong>Sair</strong></a></li>
        `;
    }

    if (!isPublic) {
        if (!verificarAutenticacao()) return;
    }

    const isAdmin = getIsAdmin();
    const btnAdmin = document.getElementById("btnAdmin");
    if (btnAdmin) btnAdmin.style.display = isAdmin ? "block" : "none";

    if (path.includes("Admin.html") && !isAdmin) {
        mostrarAlerta("Acesso negado! Apenas administradores.", "error");
        setTimeout(() => { window.location.href = "Tela_inicial.html"; }, 1500);
        return;
    }

    if (document.getElementById("formLogin")) configurarLogin();
    if (document.getElementById("formCadastro")) configurarCadastro();
    if (document.getElementById("productForm")) iniciarPaginaCadastro();
    if (document.getElementById("productTable")) iniciarPaginaTabela();
    if (document.getElementById("tabelaUsuarios")) iniciarPaginaAdmin();

    configurarOlhoSenha("toggleLogin", "senhaLogin");
    configurarOlhoSenha("toggleCadastro", "senhaCadastro");

    const btnSair = document.getElementById("btnSairNav");
    if (btnSair) {
        btnSair.addEventListener("click", (e) => { e.preventDefault(); logout(); });
    }

    const container = document.getElementById('container');
    const registerBtn = document.getElementById('register');
    const loginBtn = document.getElementById('login');
    if (registerBtn && container) registerBtn.addEventListener('click', () => container.classList.add("active"));
    if (loginBtn && container) loginBtn.addEventListener('click', () => container.classList.remove("active"));
});

function configurarOlhoSenha(iconId, inputId) {
    const icon = document.getElementById(iconId);
    const input = document.getElementById(inputId);
    if (icon && input) {
        icon.addEventListener("click", () => {
            const type = input.getAttribute("type") === "password" ? "text" : "password";
            input.setAttribute("type", type);
            icon.classList.toggle("fa-eye");
            icon.classList.toggle("fa-eye-slash");
        });
    }
}

function configurarLogin() {
    const formLogin = document.getElementById("formLogin");
    
    // Configura botão de demonstração rápida (Live Demo)
    const btnDemo = document.getElementById("btnDemoLogin");
    if (btnDemo) {
        btnDemo.addEventListener("click", () => {
            inicializarDadosDemo();
            localStorage.setItem("token", "demo-token-jwt-preview");
            localStorage.setItem("usuarioLogado", "Lojista Demo");
            localStorage.setItem("usuarioId", "99");
            localStorage.setItem("isAdmin", "true");
            mostrarAlerta("Modo Demonstração ativado! Redirecionando...", "success");
            setTimeout(() => { window.location.href = "Tela_inicial.html"; }, 800);
        });
    }

    formLogin.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("emailLogin").value.trim();
        const senha = document.getElementById("senhaLogin").value;
        try {
            const res = await fetch(`${API_URL}/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, senha })
            });
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem("token", data.token);
                localStorage.setItem("usuarioLogado", data.usuario);
                localStorage.setItem("usuarioId", data.usuario_id);
                localStorage.setItem("isAdmin", data.is_admin ? "true" : "false");
                mostrarAlerta("Login autorizado! Bem-vindo.", "success");
                setTimeout(() => { window.location.href = "Tela_inicial.html"; }, 1000);
            } else { 
                mostrarAlerta(data.message || "Email ou senha incorretos.", "error"); 
            }
        } catch (erro) { 
            mostrarAlerta("Servidor não respondeu. Use o Modo Demonstração para testar online ou execute a API localmente.", "warning"); 
        }
    });
}

function configurarCadastro() {
    document.getElementById("formCadastro").addEventListener("submit", async (e) => {
        e.preventDefault();
        const nome = document.getElementById("nomeCadastro").value.trim();
        const email = document.getElementById("emailCadastro").value.trim();
        const senha = document.getElementById("senhaCadastro").value;

        const regexSenha = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$/;
        if (!regexSenha.test(senha)) {
            mostrarAlerta("Senha inválida! Regras: Mínimo 6 caracteres, letras e números.", "warning");
            return;
        }
        try {
            const res = await fetch(`${API_URL}/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ nome, email, senha })
            });
            const data = await res.json();
            if (res.ok) {
                mostrarAlerta("Conta criada com sucesso! Faça login para continuar.", "success");
                const btnLogin = document.getElementById('login');
                if (btnLogin) setTimeout(() => { btnLogin.click(); }, 1000);
            } else { 
                mostrarAlerta(data.message || "Erro ao cadastrar.", "error"); 
            }
        } catch (erro) { 
            mostrarAlerta("Erro de conexão ao servidor.", "error"); 
        }
    });
}

async function iniciarPaginaAdmin() {
    const tbody = document.querySelector("#tabelaUsuarios tbody");
    tbody.innerHTML = "<tr><td colspan='5'>Carregando usuários...</td></tr>";

    if (isDemoMode()) {
        inicializarDadosDemo();
        const usuarios = JSON.parse(localStorage.getItem("demo_usuarios") || "[]");
        renderizarTabelaUsuarios(usuarios);
        return;
    }

    try {
        const res = await fetch(`${API_URL}/usuarios`, {
            headers: getAuthHeaders()
        });

        if (res.status === 401 || res.status === 403) {
            mostrarAlerta("Acesso negado. Sessão inválida ou sem permissão de admin.", "error");
            setTimeout(() => { logout(); }, 1500);
            return;
        }

        const usuarios = await res.json();
        renderizarTabelaUsuarios(usuarios);
    } catch (erro) { 
        tbody.innerHTML = "<tr><td colspan='5'>Erro ao conectar com o servidor.</td></tr>"; 
    }
}

function renderizarTabelaUsuarios(usuarios) {
    const tbody = document.querySelector("#tabelaUsuarios tbody");
    tbody.innerHTML = "";
    if (!Array.isArray(usuarios) || usuarios.length === 0) {
        tbody.innerHTML = "<tr><td colspan='5'>Nenhum usuário cadastrado.</td></tr>";
        return;
    }

    const currentUserId = getUsuarioId();

    usuarios.forEach(user => {
        const tipo = user.is_admin ? "<strong>ADMIN</strong>" : "Lojista";
        const btnDisabled = (user.id === 1 || user.id === currentUserId)
            ? "disabled style='opacity:0.5; cursor:not-allowed'"
            : "";
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${escaparHTML(String(user.id))}</td>
            <td>${escaparHTML(user.nome)}</td>
            <td>${escaparHTML(user.email)}</td>
            <td>${tipo}</td>
            <td><button class="excluir" onclick="deletarUsuario(${user.id})" ${btnDisabled}>Remover</button></td>
        `;
        tbody.appendChild(tr);
    });
}

window.deletarUsuario = async (id) => {
    if (confirm("Tem certeza que deseja excluir este usuário?")) {
        if (isDemoMode()) {
            let usuarios = JSON.parse(localStorage.getItem("demo_usuarios") || "[]");
            usuarios = usuarios.filter(u => u.id !== id);
            localStorage.setItem("demo_usuarios", JSON.stringify(usuarios));
            mostrarAlerta("Usuário removido no modo demonstração!", "success");
            setTimeout(() => window.location.reload(), 800);
            return;
        }

        try { 
            const res = await fetch(`${API_URL}/usuarios/${id}`, {
                method: "DELETE",
                headers: getAuthHeaders()
            });
            const data = await res.json();
            if (res.ok) {
                mostrarAlerta("Usuário removido com sucesso!", "success");
                setTimeout(() => window.location.reload(), 1000);
            } else {
                mostrarAlerta(data.message || "Erro ao deletar usuário.", "error");
            }
        } catch (erro) { 
            mostrarAlerta("Erro de conexão ao remover usuário.", "error"); 
        }
    }
};

async function iniciarPaginaCadastro() {
    const idEdicao = localStorage.getItem("idProdutoEdicao");
    if (idEdicao) {
        if (isDemoMode()) {
            const produtos = JSON.parse(localStorage.getItem("demo_produtos") || "[]");
            const produto = produtos.find(p => p.id == idEdicao);
            if (produto) preencherFormularioEdicao(produto, idEdicao);
        } else {
            try {
                const res = await fetch(`${API_URL}/produtos`, {
                    headers: getAuthHeaders()
                });

                if (res.status === 401) {
                    mostrarAlerta("Sessão expirada. Faça login novamente.", "error");
                    logout();
                    return;
                }

                const produtos = await res.json();
                const produto = produtos.find(p => p.id == idEdicao);
                if (produto) preencherFormularioEdicao(produto, idEdicao);
            } catch (erro) {
                mostrarAlerta("Erro ao carregar produto para edição.", "error");
                localStorage.removeItem("idProdutoEdicao");
            }
        }
    }

    document.getElementById("productForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const produtoData = {
            nome: document.getElementById("nome").value.trim(),
            marca: document.getElementById("marca").value.trim(),
            validade: document.getElementById("validade").value || null,
            codigo: document.getElementById("codigo").value.trim(),
            quantidade: parseInt(document.getElementById("quantidade").value, 10),
            referencia: document.getElementById("referencia").value.trim(),
            endereco: document.getElementById("endereco").value.trim() || null
        };
        const id = e.target.dataset.id;

        if (isDemoMode()) {
            let produtos = JSON.parse(localStorage.getItem("demo_produtos") || "[]");
            if (id) {
                produtos = produtos.map(p => p.id == id ? { ...p, ...produtoData } : p);
            } else {
                produtoData.id = Date.now();
                produtoData.usuario_id = 99;
                produtos.push(produtoData);
            }
            localStorage.setItem("demo_produtos", JSON.stringify(produtos));
            mostrarAlerta("Produto salvo no modo demonstração!", "success");
            setTimeout(() => { window.location.href = "tabela_principal.html"; }, 1000);
            return;
        }

        try {
            let url = `${API_URL}/produtos`;
            let method = "POST";
            if (id) { 
                url = `${url}/${id}`; 
                method = "PUT"; 
            }
            const response = await fetch(url, {
                method: method,
                headers: getAuthHeaders(),
                body: JSON.stringify(produtoData)
            });
            const data = await response.json();
            if (response.ok) { 
                mostrarAlerta(data.message || "Produto salvo com sucesso!", "success"); 
                setTimeout(() => { window.location.href = "tabela_principal.html"; }, 1500);
            } else { 
                mostrarAlerta(data.message || "Erro ao salvar produto.", "error"); 
            }
        } catch (erro) { 
            mostrarAlerta("Erro de conexão com a API.", "error"); 
        }
    });
}

function preencherFormularioEdicao(produto, idEdicao) {
    document.getElementById("nome").value = produto.nome;
    document.getElementById("marca").value = produto.marca;
    document.getElementById("validade").value = produto.validade || "";
    document.getElementById("codigo").value = produto.codigo;
    document.getElementById("quantidade").value = produto.quantidade;
    document.getElementById("referencia").value = produto.referencia || "";
    document.getElementById("endereco").value = produto.endereco || "";
    document.getElementById("productForm").dataset.id = idEdicao;
    document.querySelector("button[type='submit']").innerText = "Salvar Alterações";
    localStorage.removeItem("idProdutoEdicao");
}

async function iniciarPaginaTabela() {
    const tbody = document.querySelector("#productTable tbody");
    const btnExcluir = document.getElementById("excluirSelecionadosBtn");

    tbody.innerHTML = "<tr><td colspan='9'>Carregando produtos...</td></tr>";

    window.atualizarBotaoExcluirSelecionados = () => {
        const sel = document.querySelectorAll(".select-product:checked");
        if (btnExcluir) btnExcluir.style.display = sel.length > 0 ? "block" : "none";
    };

    if (isDemoMode()) {
        inicializarDadosDemo();
        const produtos = JSON.parse(localStorage.getItem("demo_produtos") || "[]");
        renderizarTabelaProdutos(produtos);
        configurarExclusaoEmMassa(btnExcluir);
        return;
    }

    try {
        const res = await fetch(`${API_URL}/produtos`, {
            headers: getAuthHeaders()
        });

        if (res.status === 401) {
            mostrarAlerta("Sessão expirada. Faça login novamente.", "error");
            setTimeout(() => logout(), 1500);
            return;
        }

        const produtos = await res.json();
        renderizarTabelaProdutos(produtos);
        configurarExclusaoEmMassa(btnExcluir);
    } catch (e) {
        tbody.innerHTML = "<tr><td colspan='9'>Erro ao conectar com o servidor.</td></tr>";
    }
}

function renderizarTabelaProdutos(produtos) {
    const tbody = document.querySelector("#productTable tbody");
    tbody.innerHTML = "";
    if (!Array.isArray(produtos) || produtos.length === 0) {
        tbody.innerHTML = "<tr><td colspan='9'>Nenhum produto cadastrado no estoque.</td></tr>"; 
        const contador = document.getElementById("contadorProdutos"); 
        if (contador) contador.textContent = "0 produtos encontrados";
        return;
    }

    produtos.forEach(p => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><input type="checkbox" class="select-product" data-id="${p.id}" onchange="atualizarBotaoExcluirSelecionados()"></td>
            <td>${escaparHTML(p.nome)}</td>
            <td>${escaparHTML(p.marca)}</td>
            <td>${escaparHTML(p.validade)}</td>
            <td>${escaparHTML(p.codigo)}</td>
            <td><span class="badge-qty">${escaparHTML(String(p.quantidade))}</span></td>
            <td>${escaparHTML(p.referencia)}</td>
            <td>${escaparHTML(p.endereco)}</td>
            <td>
                <button class="editar" onclick="prepararEdicao(${p.id})">Editar</button>
                <button class="excluir" onclick="deletarProduto(${p.id})">Excluir</button>
            </td>`;
        tbody.appendChild(tr);
    });

    const contador = document.getElementById("contadorProdutos"); 
    if (contador) contador.textContent = `${produtos.length} produto${produtos.length !== 1 ? "s" : ""} encontrado${produtos.length !== 1 ? "s" : ""}`; 
}

function configurarExclusaoEmMassa(btnExcluir) {
    if (!btnExcluir) return;
    btnExcluir.addEventListener("click", async () => {
        const sels = document.querySelectorAll(".select-product:checked");
        if (sels.length === 0) return;

        if (confirm(`Excluir ${sels.length} produto(s) selecionado(s)?`)) {
            if (isDemoMode()) {
                const idsParaExcluir = Array.from(sels).map(cb => parseInt(cb.dataset.id, 10));
                let produtos = JSON.parse(localStorage.getItem("demo_produtos") || "[]");
                produtos = produtos.filter(p => !idsParaExcluir.includes(p.id));
                localStorage.setItem("demo_produtos", JSON.stringify(produtos));
                mostrarAlerta("Produtos removidos!", "success");
                setTimeout(() => window.location.reload(), 800);
                return;
            }

            for (const cb of sels) {
                await fetch(`${API_URL}/produtos/${cb.dataset.id}`, { 
                    method: "DELETE",
                    headers: getAuthHeaders()
                });
            }
            mostrarAlerta("Produtos selecionados removidos!", "success");
            setTimeout(() => window.location.reload(), 1000);
        }
    });
}

window.prepararEdicao = (id) => {
    localStorage.setItem("idProdutoEdicao", id);
    window.location.href = "Cadastro_de_produtos.html";
};

window.deletarProduto = async (id) => {
    if (confirm("Tem certeza que deseja excluir este produto?")) {
        if (isDemoMode()) {
            let produtos = JSON.parse(localStorage.getItem("demo_produtos") || "[]");
            produtos = produtos.filter(p => p.id != id);
            localStorage.setItem("demo_produtos", JSON.stringify(produtos));
            mostrarAlerta("Produto excluído!", "success");
            setTimeout(() => window.location.reload(), 600);
            return;
        }

        try {
            const res = await fetch(`${API_URL}/produtos/${id}`, {
                method: "DELETE",
                headers: getAuthHeaders()
            });
            const data = await res.json();
            if (res.ok) {
                mostrarAlerta("Produto excluído com sucesso!", "success");
                setTimeout(() => window.location.reload(), 800);
            } else {
                mostrarAlerta(data.message || "Erro ao excluir produto.", "error");
            }
        } catch (e) {
            mostrarAlerta("Erro de conexão com o servidor.", "error");
        }
    }
};