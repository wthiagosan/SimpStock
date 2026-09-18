// ============================================================
//  SimpStock Frontend Script (JWT Auth, API & Live Demo)
//  Arquitetura Moderna: App Shell, Dashboard KPIs, Realtime Filters
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
            { id: 1, usuario_id: 99, nome: "Teclado Mecânico RGB Wireless", marca: "Keychron", validade: null, codigo: "SKU-KEY-01", quantidade: 35, referencia: "REF-K2-V2", endereco: "Corredor A, Prateleira 2" },
            { id: 2, usuario_id: 99, nome: "Monitor 27'' IPS 144Hz HDR", marca: "LG UltraGear", validade: null, codigo: "SKU-MON-27", quantidade: 14, referencia: "REF-27GN65R", endereco: "Corredor B, Prateleira 5" },
            { id: 3, usuario_id: 99, nome: "Cadeira Ergonômica Pro Mesh", marca: "Flexform", validade: null, codigo: "SKU-CAD-09", quantidade: 4, referencia: "REF-FLEX-PLUS", endereco: "Depósito Central" },
            { id: 4, usuario_id: 99, nome: "Mouse Gamer Sem Fio 26K DPI", marca: "Logitech G", validade: null, codigo: "SKU-MOU-PRO", quantidade: 28, referencia: "REF-GPX-SUPER", endereco: "Corredor A, Gaveta 1" },
            { id: 5, usuario_id: 99, nome: "Headset 7.1 Surround Noise Cancelling", marca: "HyperX", validade: null, codigo: "SKU-HED-001", quantidade: 0, referencia: "REF-CLOUD-II", endereco: "Corredor C, Prateleira 1" }
        ];
        localStorage.setItem("demo_produtos", JSON.stringify(produtosIniciais));
    }
    if (!localStorage.getItem("demo_usuarios")) {
        const usuariosIniciais = [
            { id: 1, nome: "Administrador Master", email: "admin@simpstock.com", is_admin: true, criado_em: "2026-09-09 20:00:00" },
            { id: 99, nome: "Lojista Demonstração", email: "demo@simpstock.com", is_admin: true, criado_em: "2026-09-09 21:00:00" },
            { id: 3, nome: "Carlos Varejo", email: "carlos@varejo.com", is_admin: false, criado_em: "2026-09-10 10:30:00" },
            { id: 4, nome: "Mariana Logística", email: "mariana@distribuidora.com", is_admin: false, criado_em: "2026-09-12 14:15:00" }
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
    }, 3200);
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
    localStorage.removeItem("usuarioNome");
    localStorage.removeItem("usuarioEmail");
    localStorage.removeItem("usuarioId");
    localStorage.removeItem("isAdmin");
    localStorage.removeItem("idProdutoEdicao");
    window.location.href = getLoginUrl();
}

function getLoginUrl() {
    const path = window.location.pathname.toLowerCase();
    if (path.endsWith("/") || path.endsWith("/simpstock") || path.endsWith("/simpstock/") || path.includes("index.html")) {
        return "src/Login.html";
    }
    return "Login.html";
}

function verificarAutenticacao() {
    const token = getAuthToken();
    if (!token) {
        mostrarAlerta("Você precisa fazer login para acessar esta página.", "warning");
        setTimeout(() => { window.location.href = getLoginUrl(); }, 1500);
        return false;
    }
    return true;
}

// --- INICIALIZAÇÃO GERAL ---
document.addEventListener("DOMContentLoaded", () => {
    const path = window.location.pathname.toLowerCase();
    const isPublic = path === ""
        || path === "/"
        || path.endsWith("/")
        || path.endsWith("/simpstock")
        || path.endsWith("/simpstock/")
        || path.includes("index.html")
        || path.includes("login.html")
        || path.includes("sobre_nos.html")
        || path.includes("sobre_n")
        || path.includes("ajuda.html");

    // Ajusta menu da página de ajuda se logado
    const navAjuda = document.getElementById("navAjuda");
    if (navAjuda && getAuthToken()) {
        navAjuda.innerHTML = `
            <li class="nav-item"><a href="../index.html">Início</a></li>
            <li class="nav-item"><a href="Tela_inicial.html"><strong>Dashboard</strong></a></li>
            <li class="nav-item"><a href="#" onclick="logout(); return false;"><strong>Sair</strong></a></li>
        `;
    }

    if (!isPublic) {
        if (!verificarAutenticacao()) return;
        inicializarPerfilSidebar();
    }

    const isAdmin = getIsAdmin();
    const adminSection = document.getElementById("adminMenuSection");
    if (adminSection) adminSection.style.display = isAdmin ? "block" : "none";

    if (path.includes("Admin.html") && !isAdmin) {
        mostrarAlerta("Acesso restrito a administradores!", "error");
        setTimeout(() => { window.location.href = "Tela_inicial.html"; }, 1500);
        return;
    }

    if (document.getElementById("formLogin")) configurarLogin();
    if (document.getElementById("formCadastro")) configurarCadastro();
    if (document.getElementById("productForm")) iniciarPaginaCadastro();
    if (document.getElementById("productTable")) iniciarPaginaTabela();
    if (document.getElementById("tabelaUsuarios")) iniciarPaginaAdmin();
    if (document.getElementById("kpiTotalProdutos") || document.getElementById("dashboardRecentTableBody")) carregarDashboardKPIs();

    configurarOlhoSenha("toggleLogin", "senhaLogin");
    configurarOlhoSenha("toggleCadastro", "senhaCadastro");

    const btnSair = document.getElementById("btnSairNav");
    if (btnSair) {
        btnSair.addEventListener("click", (e) => { e.preventDefault(); logout(); });
    }

    // Toggle para mobile
    const btnToggleSidebar = document.getElementById("btnToggleSidebar");
    if (btnToggleSidebar) {
        btnToggleSidebar.addEventListener("click", () => {
            document.getElementById("sidebar")?.classList.toggle("open");
        });
    }

    const container = document.getElementById('container');
    const registerBtn = document.getElementById('register');
    const loginBtn = document.getElementById('login');
    if (registerBtn && container) registerBtn.addEventListener('click', () => container.classList.add("active"));
    if (loginBtn && container) loginBtn.addEventListener('click', () => container.classList.remove("active"));
});

// --- PERFIL DO USUÁRIO NA SIDEBAR ---
function inicializarPerfilSidebar() {
    const nome = localStorage.getItem("usuarioNome") || localStorage.getItem("usuarioLogado") || "Lojista";
    const isAdmin = getIsAdmin();

    const elNome = document.getElementById("sidebarUserName");
    if (elNome) elNome.textContent = nome;

    const elRole = document.getElementById("sidebarUserRole");
    if (elRole) elRole.textContent = isAdmin ? "Administrador" : "Lojista";

    const elAvatar = document.getElementById("userAvatar");
    if (elAvatar) {
        const partes = nome.trim().split(/\s+/);
        const iniciais = partes.length >= 2
            ? (partes[0][0] + partes[partes.length - 1][0]).toUpperCase()
            : nome.substring(0, 2).toUpperCase();
        elAvatar.textContent = iniciais;
    }

    // Status do sistema
    const statusText = document.getElementById("systemStatusText");
    const statusDot = document.getElementById("systemStatusDot");
    if (statusText && statusDot) {
        if (isDemoMode()) {
            statusText.textContent = "Modo Demo Online";
            statusDot.style.backgroundColor = "var(--amber)";
        } else {
            statusText.textContent = "Online (API Conectada)";
            statusDot.style.backgroundColor = "var(--emerald)";
        }
    }
}

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

// --- AUTENTICAÇÃO ---
function configurarLogin() {
    const formLogin = document.getElementById("formLogin");
    
    // Botão de Demonstração Rápida (Live Demo)
    const btnDemo = document.getElementById("btnDemoLogin");
    if (btnDemo) {
        btnDemo.addEventListener("click", () => {
            inicializarDadosDemo();
            localStorage.setItem("token", "demo-token-jwt-preview");
            localStorage.setItem("usuarioLogado", "Lojista Demonstração");
            localStorage.setItem("usuarioNome", "Lojista Demonstração");
            localStorage.setItem("usuarioEmail", "demo@simpstock.com");
            localStorage.setItem("usuarioId", "99");
            localStorage.setItem("isAdmin", "true");
            mostrarAlerta("Modo Demonstração ativado! Acessando painel...", "success");
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
                localStorage.setItem("usuarioNome", data.usuario);
                localStorage.setItem("usuarioId", data.usuario_id);
                localStorage.setItem("isAdmin", data.is_admin ? "true" : "false");
                mostrarAlerta("Login autorizado com sucesso!", "success");
                setTimeout(() => { window.location.href = "Tela_inicial.html"; }, 1000);
            } else { 
                mostrarAlerta(data.message || "Email ou senha incorretos.", "error"); 
            }
        } catch (erro) { 
            mostrarAlerta("Servidor indisponível. Use o botão 'Modo Demonstração' para testar online.", "warning"); 
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
                mostrarAlerta(data.message || "Erro ao cadastrar usuário.", "error"); 
            }
        } catch (erro) { 
            mostrarAlerta("Erro de conexão ao servidor.", "error"); 
        }
    });
}

// ============================================================
//  DASHBOARD EXECUTIVO & KPIS
// ============================================================
window.carregarDashboardKPIs = async function() {
    let produtos = [];

    if (isDemoMode()) {
        inicializarDadosDemo();
        produtos = JSON.parse(localStorage.getItem("demo_produtos") || "[]");
    } else {
        try {
            const res = await fetch(`${API_URL}/produtos`, {
                headers: getAuthHeaders()
            });
            if (res.ok) {
                produtos = await res.json();
            } else if (res.status === 401) {
                logout();
                return;
            }
        } catch (e) {
            console.warn("Não foi possível carregar produtos da API, usando cache local se disponível.");
        }
    }

    // Cálculo das métricas
    const totalItens = produtos.length;
    const estoqueBaixo = produtos.filter(p => p.quantidade > 0 && p.quantidade < 5).length;
    const esgotados = produtos.filter(p => p.quantidade <= 0).length;
    const totalUnidades = produtos.reduce((acc, p) => acc + (parseInt(p.quantidade, 10) || 0), 0);

    // Atualiza KPIs no DOM
    const kpiTotal = document.getElementById("kpiTotalProdutos");
    if (kpiTotal) kpiTotal.textContent = totalItens;

    const kpiBaixo = document.getElementById("kpiEstoqueBaixo");
    if (kpiBaixo) kpiBaixo.textContent = estoqueBaixo;

    const kpiEsg = document.getElementById("kpiEsgotados");
    if (kpiEsg) kpiEsg.textContent = esgotados;

    const kpiUnid = document.getElementById("kpiTotalUnidades");
    if (kpiUnid) kpiUnid.textContent = totalUnidades.toLocaleString('pt-BR');

    // Tabela de itens recentes
    const tbody = document.getElementById("dashboardRecentTableBody");
    if (tbody) {
        tbody.innerHTML = "";
        if (produtos.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; padding: 2.5rem; color: var(--slate-400);">
                        <i class="ti ti-box" style="font-size: 2rem; color: var(--slate-300);"></i>
                        <p style="margin-top: 0.5rem; font-weight: 500;">Nenhum produto cadastrado no estoque ainda.</p>
                        <a href="Cadastro_de_produtos.html" class="btn-primary-action" style="display: inline-flex; margin-top: 1rem;">
                            <i class="ti ti-plus"></i> Cadastrar Primeiro Produto
                        </a>
                    </td>
                </tr>`;
            return;
        }

        // Mostra até 6 itens mais recentes
        const recentes = [...produtos].reverse().slice(0, 6);
        recentes.forEach(p => {
            const tr = document.createElement("tr");

            let badgeStatus = '<span class="badge badge-success"><i class="ti ti-check"></i> Em Estoque</span>';
            if (p.quantidade <= 0) {
                badgeStatus = '<span class="badge badge-danger"><i class="ti ti-circle-x"></i> Esgotado</span>';
            } else if (p.quantidade < 5) {
                badgeStatus = '<span class="badge badge-warning"><i class="ti ti-alert-triangle"></i> Baixo</span>';
            }

            tr.innerHTML = `
                <td>
                    <div class="product-cell">
                        <span class="product-title">${escaparHTML(p.nome)}</span>
                        <span class="product-sku">${escaparHTML(p.codigo)}</span>
                    </div>
                </td>
                <td>${escaparHTML(p.marca)}</td>
                <td>
                    <div class="qty-controller">
                        <button type="button" class="qty-btn" onclick="ajustarQuantidadeRapida(${p.id}, -1)" title="Diminuir 1">-</button>
                        <span class="qty-value">${escaparHTML(String(p.quantidade))}</span>
                        <button type="button" class="qty-btn" onclick="ajustarQuantidadeRapida(${p.id}, 1)" title="Aumentar 1">+</button>
                    </div>
                </td>
                <td>${badgeStatus}</td>
                <td>${escaparHTML(p.endereco || 'Depósito Geral')}</td>
                <td style="text-align: right;">
                    <div class="action-buttons" style="justify-content: flex-end;">
                        <button type="button" class="btn-icon-action" onclick="prepararEdicao(${p.id})" title="Editar Produto">
                            <i class="ti ti-pencil"></i>
                        </button>
                        <button type="button" class="btn-icon-action delete" onclick="deletarProduto(${p.id})" title="Excluir">
                            <i class="ti ti-trash"></i>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }
};

// ============================================================
//  AJUSTE RÁPIDO DE QUANTIDADE (+ / -)
// ============================================================
window.ajustarQuantidadeRapida = async function(produtoId, delta) {
    if (isDemoMode()) {
        let produtos = JSON.parse(localStorage.getItem("demo_produtos") || "[]");
        const prod = produtos.find(p => p.id == produtoId);
        if (!prod) return;

        prod.quantidade = Math.max(0, (parseInt(prod.quantidade, 10) || 0) + delta);
        localStorage.setItem("demo_produtos", JSON.stringify(produtos));
        mostrarAlerta(`Quantidade de '${prod.nome}' atualizada para ${prod.quantidade}!`, "success");

        if (document.getElementById("dashboardRecentTableBody")) carregarDashboardKPIs();
        if (document.getElementById("productTable")) {
            const row = document.querySelector(`input[data-id="${produtoId}"]`)?.closest("tr");
            if (row) {
                const valEl = row.querySelector(".qty-value");
                if (valEl) valEl.textContent = prod.quantidade;
            } else {
                iniciarPaginaTabela();
            }
        }
        return;
    }

    try {
        // Busca produto para obter dados atuais
        const resList = await fetch(`${API_URL}/produtos`, { headers: getAuthHeaders() });
        if (!resList.ok) throw new Error("Falha ao consultar item");
        const prods = await resList.json();
        const prod = prods.find(p => p.id == produtoId);
        if (!prod) return;

        const novaQtd = Math.max(0, (parseInt(prod.quantidade, 10) || 0) + delta);
        const updateRes = await fetch(`${API_URL}/produtos/${produtoId}`, {
            method: "PUT",
            headers: getAuthHeaders(),
            body: JSON.stringify({ ...prod, quantidade: novaQtd })
        });

        if (updateRes.ok) {
            mostrarAlerta(`Quantidade de '${prod.nome}' atualizada para ${novaQtd}!`, "success");
            if (document.getElementById("dashboardRecentTableBody")) carregarDashboardKPIs();
            if (document.getElementById("productTable")) iniciarPaginaTabela();
        } else {
            const err = await updateRes.json();
            mostrarAlerta(err.message || "Erro ao atualizar quantidade.", "error");
        }
    } catch (e) {
        mostrarAlerta("Erro de conexão com o servidor.", "error");
    }
};

// ============================================================
//  GESTÃO DE PRODUTOS (TABELA & FILTROS EM TEMPO REAL)
// ============================================================
let todosOsProdutos = [];
let filtroStatusAtual = 'todos';
let termoBuscaAtual = '';

async function iniciarPaginaTabela() {
    const tbody = document.querySelector("#productTable tbody");
    const btnExcluir = document.getElementById("excluirSelecionadosBtn");

    tbody.innerHTML = `
        <tr>
            <td colspan="9" style="text-align: center; padding: 3rem; color: var(--slate-400);">
                <i class="ti ti-loader" style="font-size: 1.8rem; animation: spin 1s infinite linear;"></i>
                <p style="margin-top: 0.5rem;">Carregando produtos do estoque...</p>
            </td>
        </tr>`;

    window.atualizarBotaoExcluirSelecionados = () => {
        const sel = document.querySelectorAll(".select-product:checked");
        const countSpan = document.getElementById("countSelecionados");
        if (countSpan) countSpan.textContent = sel.length;
        if (btnExcluir) btnExcluir.style.display = sel.length > 0 ? "inline-flex" : "none";
    };

    if (isDemoMode()) {
        inicializarDadosDemo();
        todosOsProdutos = JSON.parse(localStorage.getItem("demo_produtos") || "[]");
        aplicarFiltrosEBusca();
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

        todosOsProdutos = await res.json();
        aplicarFiltrosEBusca();
        configurarExclusaoEmMassa(btnExcluir);
    } catch (e) {
        tbody.innerHTML = "<tr><td colspan='9' style='text-align:center; padding: 2rem; color: var(--rose);'>Erro ao conectar com o servidor.</td></tr>";
    }
}

window.filtrarTabelaPorStatus = function(filtro) {
    filtroStatusAtual = filtro;
    aplicarFiltrosEBusca();
};

window.buscarTabelaTempoReal = function(termo) {
    termoBuscaAtual = (termo || '').toLowerCase().trim();
    aplicarFiltrosEBusca();
};

function aplicarFiltrosEBusca() {
    let filtrados = [...todosOsProdutos];

    // Filtro por Status
    if (filtroStatusAtual === 'normal') {
        filtrados = filtrados.filter(p => p.quantidade >= 5);
    } else if (filtroStatusAtual === 'baixo') {
        filtrados = filtrados.filter(p => p.quantidade > 0 && p.quantidade < 5);
    } else if (filtroStatusAtual === 'esgotado') {
        filtrados = filtrados.filter(p => p.quantidade <= 0);
    }

    // Busca por Texto (nome, marca, SKU, ref, endereço)
    if (termoBuscaAtual) {
        filtrados = filtrados.filter(p => {
            const nome = (p.nome || '').toLowerCase();
            const marca = (p.marca || '').toLowerCase();
            const sku = (p.codigo || '').toLowerCase();
            const ref = (p.referencia || '').toLowerCase();
            const end = (p.endereco || '').toLowerCase();
            return nome.includes(termoBuscaAtual) ||
                   marca.includes(termoBuscaAtual) ||
                   sku.includes(termoBuscaAtual) ||
                   ref.includes(termoBuscaAtual) ||
                   end.includes(termoBuscaAtual);
        });
    }

    renderizarTabelaProdutos(filtrados);
}

function renderizarTabelaProdutos(produtos) {
    const tbody = document.querySelector("#productTable tbody");
    tbody.innerHTML = "";

    if (!Array.isArray(produtos) || produtos.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" style="text-align: center; padding: 3rem; color: var(--slate-400);">
                    <i class="ti ti-search-off" style="font-size: 2rem; color: var(--slate-300);"></i>
                    <p style="margin-top: 0.5rem; font-weight: 500;">Nenhum produto encontrado com os filtros atuais.</p>
                </td>
            </tr>`;
        const contador = document.getElementById("contadorProdutos"); 
        if (contador) contador.textContent = "0 produtos encontrados";
        return;
    }

    produtos.forEach(p => {
        let badgeStatus = '<span class="badge badge-success"><i class="ti ti-check"></i> Normal</span>';
        if (p.quantidade <= 0) {
            badgeStatus = '<span class="badge badge-danger"><i class="ti ti-circle-x"></i> Esgotado</span>';
        } else if (p.quantidade < 5) {
            badgeStatus = '<span class="badge badge-warning"><i class="ti ti-alert-triangle"></i> Baixo</span>';
        }

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td style="text-align: center;">
                <input type="checkbox" class="select-product" data-id="${p.id}" onchange="atualizarBotaoExcluirSelecionados()">
            </td>
            <td>
                <div class="product-cell">
                    <span class="product-title">${escaparHTML(p.nome)}</span>
                    <span class="product-sku">${escaparHTML(p.codigo)}</span>
                </div>
            </td>
            <td>${escaparHTML(p.marca)}</td>
            <td>
                <div class="qty-controller">
                    <button type="button" class="qty-btn" onclick="ajustarQuantidadeRapida(${p.id}, -1)" title="Diminuir">-</button>
                    <span class="qty-value">${escaparHTML(String(p.quantidade))}</span>
                    <button type="button" class="qty-btn" onclick="ajustarQuantidadeRapida(${p.id}, 1)" title="Aumentar">+</button>
                </div>
            </td>
            <td>${badgeStatus}</td>
            <td><code>${escaparHTML(p.referencia)}</code></td>
            <td>${escaparHTML(p.endereco || '-')}</td>
            <td>${p.validade ? escaparHTML(p.validade) : '-'}</td>
            <td style="text-align: right;">
                <div class="action-buttons" style="justify-content: flex-end;">
                    <button type="button" class="btn-icon-action" onclick="prepararEdicao(${p.id})" title="Editar Produto">
                        <i class="ti ti-pencil"></i>
                    </button>
                    <button type="button" class="btn-icon-action delete" onclick="deletarProduto(${p.id})" title="Excluir Produto">
                        <i class="ti ti-trash"></i>
                    </button>
                </div>
            </td>`;
        tbody.appendChild(tr);
    });

    const contador = document.getElementById("contadorProdutos"); 
    if (contador) contador.textContent = `${produtos.length} produto${produtos.length !== 1 ? "s" : ""} encontrado${produtos.length !== 1 ? "s" : ""}`; 
}

function configurarExclusaoEmMassa(btnExcluir) {
    if (!btnExcluir) return;
    btnExcluir.onclick = async () => {
        const sels = document.querySelectorAll(".select-product:checked");
        if (sels.length === 0) return;

        const count = sels.length;
        if (confirm(`Tem certeza que deseja excluir os ${count} produto(s) selecionado(s)? Esta ação não pode ser desfeita.`)) {
            if (isDemoMode()) {
                const idsParaExcluir = Array.from(sels).map(cb => parseInt(cb.dataset.id, 10));
                todosOsProdutos = todosOsProdutos.filter(p => !idsParaExcluir.includes(p.id));
                localStorage.setItem("demo_produtos", JSON.stringify(todosOsProdutos));
                mostrarAlerta(`${count} produto(s) removido(s) com sucesso!`, "success");
                aplicarFiltrosEBusca();
                window.atualizarBotaoExcluirSelecionados();
                return;
            }

            for (const cb of sels) {
                await fetch(`${API_URL}/produtos/${cb.dataset.id}`, { 
                    method: "DELETE",
                    headers: getAuthHeaders()
                });
            }
            mostrarAlerta(`${count} produto(s) removido(s) com sucesso!`, "success");
            iniciarPaginaTabela();
        }
    };
}

window.prepararEdicao = (id) => {
    localStorage.setItem("idProdutoEdicao", id);
    window.location.href = "Cadastro_de_produtos.html";
};

window.deletarProduto = async (id) => {
    if (confirm("Tem certeza que deseja excluir este produto do estoque?")) {
        if (isDemoMode()) {
            todosOsProdutos = todosOsProdutos.filter(p => p.id != id);
            localStorage.setItem("demo_produtos", JSON.stringify(todosOsProdutos));
            mostrarAlerta("Produto excluído do estoque!", "success");
            aplicarFiltrosEBusca();
            if (document.getElementById("dashboardRecentTableBody")) carregarDashboardKPIs();
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
                if (document.getElementById("dashboardRecentTableBody")) carregarDashboardKPIs();
                if (document.getElementById("productTable")) iniciarPaginaTabela();
            } else {
                mostrarAlerta(data.message || "Erro ao excluir produto.", "error");
            }
        } catch (e) {
            mostrarAlerta("Erro de conexão com o servidor.", "error");
        }
    }
};

// ============================================================
//  CADASTRO & EDIÇÃO DE PRODUTOS
// ============================================================
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
            mostrarAlerta("Produto salvo no modo demonstração com sucesso!", "success");
            setTimeout(() => { window.location.href = "tabela_principal.html"; }, 900);
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
                setTimeout(() => { window.location.href = "tabela_principal.html"; }, 1000);
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

    const btnSubmit = document.querySelector("button[type='submit']");
    if (btnSubmit) btnSubmit.innerHTML = `<i class="ti ti-check"></i> Salvar Alterações`;

    const titleEl = document.querySelector(".form-header h1");
    if (titleEl) titleEl.textContent = `Editar Produto: ${produto.nome}`;

    localStorage.removeItem("idProdutoEdicao");
}

// ============================================================
//  PAINEL ADMINISTRATIVO (GESTÃO DE USUÁRIOS)
// ============================================================
async function iniciarPaginaAdmin() {
    const tbody = document.querySelector("#tabelaUsuarios tbody");
    tbody.innerHTML = `
        <tr>
            <td colspan="6" style="text-align: center; padding: 2.5rem; color: var(--slate-400);">
                <i class="ti ti-loader" style="font-size: 1.5rem; animation: spin 1s infinite linear;"></i>
                <p style="margin-top: 0.5rem;">Consultando banco de usuários...</p>
            </td>
        </tr>`;

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
            mostrarAlerta("Acesso negado. Sessão sem privilégios de administrador.", "error");
            setTimeout(() => { logout(); }, 1500);
            return;
        }

        const usuarios = await res.json();
        renderizarTabelaUsuarios(usuarios);
    } catch (erro) { 
        tbody.innerHTML = "<tr><td colspan='6' style='text-align:center; padding:2rem; color: var(--rose);'>Erro ao conectar com o servidor.</td></tr>"; 
    }
}

function renderizarTabelaUsuarios(usuarios) {
    const tbody = document.querySelector("#tabelaUsuarios tbody");
    tbody.innerHTML = "";

    const contador = document.getElementById("contadorUsuarios");
    if (contador) contador.textContent = `${usuarios.length} cadastrados`;

    if (!Array.isArray(usuarios) || usuarios.length === 0) {
        tbody.innerHTML = "<tr><td colspan='6' style='text-align: center; padding: 2rem; color: var(--slate-400);'>Nenhum usuário cadastrado.</td></tr>";
        return;
    }

    const currentUserId = getUsuarioId();

    usuarios.forEach(user => {
        const tipo = user.is_admin 
            ? `<span class="badge badge-purple"><i class="ti ti-shield-check"></i> Administrador</span>` 
            : `<span class="badge badge-success"><i class="ti ti-user"></i> Lojista</span>`;

        const isProtected = (user.id === 1 || user.id === currentUserId);
        const btnDisabled = isProtected
            ? "disabled style='opacity:0.4; cursor:not-allowed; border-color: var(--slate-200);'"
            : "";
        const titleHelp = isProtected ? "Conta protegida contra exclusão" : "Remover usuário";

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><code>#${escaparHTML(String(user.id))}</code></td>
            <td><strong>${escaparHTML(user.nome)}</strong></td>
            <td>${escaparHTML(user.email)}</td>
            <td>${tipo}</td>
            <td>${escaparHTML(user.criado_em || '2026-09-09')}</td>
            <td style="text-align: right;">
                <button type="button" class="btn-icon-action delete" onclick="deletarUsuario(${user.id})" ${btnDisabled} title="${titleHelp}">
                    <i class="ti ti-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

window.deletarUsuario = async (id) => {
    if (confirm("Tem certeza que deseja excluir esta conta de usuário?")) {
        if (isDemoMode()) {
            let usuarios = JSON.parse(localStorage.getItem("demo_usuarios") || "[]");
            usuarios = usuarios.filter(u => u.id !== id);
            localStorage.setItem("demo_usuarios", JSON.stringify(usuarios));
            mostrarAlerta("Usuário removido no modo demonstração!", "success");
            iniciarPaginaAdmin();
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
                iniciarPaginaAdmin();
            } else {
                mostrarAlerta(data.message || "Erro ao deletar usuário.", "error");
            }
        } catch (erro) { 
            mostrarAlerta("Erro de conexão ao remover usuário.", "error"); 
        }
    }
};