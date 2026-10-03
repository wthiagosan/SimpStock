// ============================================================
//  SimpStock Frontend Script (Plataforma Comercial SaaS)
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
    const token = localStorage.getItem("token") || "";
    return token.startsWith("demo-token-") || localStorage.getItem("offline_mode") === "true";
}

// Inicializa dados de demonstração interativos caso o usuário teste a plataforma online
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
            { id: 1, nome: "Administrador Master", email: "admin@simpstock.com", senha: "admin", is_admin: true, criado_em: "2026-09-09 20:00:00" },
            { id: 99, nome: "Lojista Demonstração", email: "demo@simpstock.com", senha: "demo", is_admin: true, criado_em: "2026-09-09 21:00:00" },
            { id: 3, nome: "Carlos Varejo", email: "carlos@varejo.com", senha: "123", is_admin: false, criado_em: "2026-09-10 10:30:00" },
            { id: 4, nome: "Mariana Logística", email: "mariana@distribuidora.com", senha: "123", is_admin: false, criado_em: "2026-09-12 14:15:00" }
        ];
        localStorage.setItem("demo_usuarios", JSON.stringify(usuariosIniciais));
    }
}

// --- GESTÃO DE SESSÃO E CABEÇALHOS DE AUTENTICAÇÃO ---
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
    const orgId = localStorage.getItem("activeOrgId");
    if (orgId) {
        headers["X-Organization-Id"] = String(orgId);
    }
    return headers;
}

function getUsuarioId() {
    return parseInt(localStorage.getItem("usuarioId"), 10) || null;
}

function getIsAdmin() {
    return localStorage.getItem("isAdmin") === "true";
}

function getIsSuperadmin() {
    return localStorage.getItem("isSuperadmin") === "true";
}

// --- TOASTS MODERNOS (ALTO CONTRASTE) ---
function mostrarAlerta(mensagem, tipo = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${tipo}`;
    
    let iconeHtml = '';
    if (tipo === 'success') {
        iconeHtml = '<i class="ti ti-circle-check" style="font-size: 1.3rem; color: #10b981; flex-shrink: 0;"></i>';
    } else if (tipo === 'error') {
        iconeHtml = '<i class="ti ti-circle-x" style="font-size: 1.3rem; color: #ef4444; flex-shrink: 0;"></i>';
    } else if (tipo === 'warning') {
        iconeHtml = '<i class="ti ti-alert-triangle" style="font-size: 1.3rem; color: #f59e0b; flex-shrink: 0;"></i>';
    } else {
        iconeHtml = '<i class="ti ti-info-circle" style="font-size: 1.3rem; color: #3b82f6; flex-shrink: 0;"></i>';
    }
    
    toast.innerHTML = `${iconeHtml} <span style="flex: 1;">${escaparHTML(mensagem)}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 350);
    }, 3500);
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
    localStorage.removeItem("offline_mode");
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

// --- AJUSTA LINKS PÚBLICOS QUANDO O USUÁRIO JÁ ESTÁ AUTENTICADO ---
function ajustarNavegacaoPublica() {
    const token = getAuthToken();
    if (!token) return;

    const path = window.location.pathname.toLowerCase();
    const isInsideSrc = path.includes("/src/") || path.includes("\\src\\");
    const targetDashboard = isInsideSrc ? "Tela_inicial.html" : "src/Tela_inicial.html";

    // 1. Atualiza botões da barra de navegação pública (index, sobre, ajuda)
    const btnLoginNav = document.querySelector(".nav-btn-login");
    if (btnLoginNav) {
        btnLoginNav.href = targetDashboard;
        btnLoginNav.innerHTML = '<i class="ti ti-layout-dashboard"></i> Ir para o Painel';
        btnLoginNav.style.background = "linear-gradient(135deg, #10b981, #059669)";

        // Adiciona botão Sair ao lado se ainda não existir
        const navMenu = btnLoginNav.closest(".nav-menu");
        if (navMenu && !document.getElementById("btnNavSairDinamico")) {
            const liSair = document.createElement("li");
            liSair.className = "nav-item";
            liSair.id = "btnNavSairDinamico";
            liSair.innerHTML = `<a href="#" onclick="logout(); return false;" style="color: var(--slate-300); display: inline-flex; align-items: center; gap: 5px; font-weight: 500;"><i class="ti ti-logout"></i> Sair</a>`;
            navMenu.appendChild(liSair);
        }
    }
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

    // Se estiver na tela de Login e já possuir sessão ativa, redireciona para o Painel
    if (path.includes("login.html") && getAuthToken() && !window.location.search.includes("trocar=true")) {
        window.location.replace("Tela_inicial.html");
        return;
    }

    // Ajusta navegação de páginas públicas se o usuário estiver com sessão ativa
    ajustarNavegacaoPublica();

    if (!isPublic) {
        if (!verificarAutenticacao()) return;
        inicializarPerfilSidebar();
    }

    const isAdmin = getIsAdmin();
    const isSuper = getIsSuperadmin();
    const adminSection = document.getElementById("adminMenuSection");
    if (adminSection) adminSection.style.display = (isAdmin || isSuper) ? "block" : "none";

    const superadminSection = document.getElementById("superadminMenuSection");
    if (superadminSection) superadminSection.style.display = isSuper ? "block" : "none";

    if (!isPublic) {
        carregarContextoOrganizacoes();
    }

    if (path.includes("Admin.html") && !isAdmin && !isSuper) {
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
    if (!formLogin) return;
    
    // Botão de Demonstração Rápida (Live Demo)
    const btnDemo = document.getElementById("btnDemoLogin");
    if (btnDemo) {
        btnDemo.addEventListener("click", () => {
            inicializarDadosDemo();
            localStorage.setItem("token", "demo-token-session-preview");
            localStorage.setItem("usuarioLogado", "Lojista Demonstração");
            localStorage.setItem("usuarioNome", "Lojista Demonstração");
            localStorage.setItem("usuarioEmail", "demo@simpstock.com");
            localStorage.setItem("usuarioId", "99");
            localStorage.setItem("isAdmin", "true");
            localStorage.setItem("offline_mode", "true");
            mostrarAlerta("Modo Demonstração ativado! Acessando painel...", "success");
            setTimeout(() => { window.location.href = "Tela_inicial.html"; }, 800);
        });
    }

    formLogin.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("emailLogin").value.trim();
        const senha = document.getElementById("senhaLogin").value;

        // Tenta autenticação via API caso haja backend ativo
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
                localStorage.setItem("isSuperadmin", data.is_superadmin ? "true" : "false");
                if (data.organizacao_ativa) {
                    localStorage.setItem("activeOrgId", data.organizacao_ativa.id);
                    localStorage.setItem("activeOrgNome", data.organizacao_ativa.nome);
                }
                localStorage.removeItem("offline_mode");
                mostrarAlerta("Login autorizado com sucesso!", "success");
                setTimeout(() => { window.location.href = "Tela_inicial.html"; }, 900);
                return;
            } else { 
                mostrarAlerta(data.message || "Email ou senha incorretos.", "error"); 
                return;
            }
        } catch (erro) { 
            // Fallback transparente para Demonstração Online / Navegador
            inicializarDadosDemo();
            let usuarios = JSON.parse(localStorage.getItem("demo_usuarios") || "[]");
            const usuario = usuarios.find(u => u.email.toLowerCase() === email.toLowerCase());

            if (!usuario) {
                mostrarAlerta("E-mail não cadastrado. Crie uma conta ou use o Modo Demonstração.", "error");
                return;
            }

            const senhaValida = !usuario.senha 
                || usuario.senha === senha 
                || (usuario.email.toLowerCase() === "demo@simpstock.com")
                || (usuario.email.toLowerCase() === "admin@simpstock.com" && (senha === "admin" || senha === "admin123"));

            if (!senhaValida) {
                mostrarAlerta("Senha incorreta. Verifique suas credenciais.", "error");
                return;
            }

            localStorage.setItem("token", `demo-token-session-${usuario.id}`);
            localStorage.setItem("usuarioLogado", usuario.nome);
            localStorage.setItem("usuarioNome", usuario.nome);
            localStorage.setItem("usuarioEmail", usuario.email);
            localStorage.setItem("usuarioId", String(usuario.id));
            localStorage.setItem("isAdmin", usuario.is_admin ? "true" : "false");
            localStorage.setItem("offline_mode", "true");

            mostrarAlerta(`Bem-vindo, ${usuario.nome}! Acessando painel...`, "success");
            setTimeout(() => { window.location.href = "Tela_inicial.html"; }, 800);
        }
    });
}

function configurarCadastro() {
    const formCadastro = document.getElementById("formCadastro");
    if (!formCadastro) return;

    formCadastro.addEventListener("submit", async (e) => {
        e.preventDefault();
        const nome = document.getElementById("nomeCadastro").value.trim();
        const email = document.getElementById("emailCadastro").value.trim();
        const senha = document.getElementById("senhaCadastro").value;

        const regexSenha = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$/;
        if (!regexSenha.test(senha)) {
            mostrarAlerta("Senha inválida! Regras: Mínimo 6 caracteres, com letras e números.", "warning");
            return;
        }

        // Tenta cadastrar via API caso haja backend ativo
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
                if (btnLogin) {
                    setTimeout(() => { 
                        btnLogin.click(); 
                        const elEmail = document.getElementById("emailLogin");
                        if (elEmail) elEmail.value = email;
                    }, 1000);
                }
                return;
            } else { 
                mostrarAlerta(data.message || "Erro ao cadastrar usuário.", "error"); 
                return;
            }
        } catch (erro) { 
            // Fallback transparente para Demonstração Online / Navegador
            inicializarDadosDemo();
            let usuarios = JSON.parse(localStorage.getItem("demo_usuarios") || "[]");
            const emailJaExiste = usuarios.some(u => u.email.toLowerCase() === email.toLowerCase());
            
            if (emailJaExiste) {
                mostrarAlerta("Este e-mail já está cadastrado no sistema!", "warning");
                return;
            }

            const novoUsuario = {
                id: Date.now(),
                nome: nome,
                email: email,
                senha: senha,
                is_admin: false,
                criado_em: new Date().toISOString().slice(0, 19).replace('T', ' ')
            };
            usuarios.push(novoUsuario);
            localStorage.setItem("demo_usuarios", JSON.stringify(usuarios));

            mostrarAlerta("Conta cadastrada com sucesso! Faça login para acessar.", "success");
            
            const btnLogin = document.getElementById('login');
            const container = document.getElementById('container');
            if (container) container.classList.remove('active');
            if (btnLogin) btnLogin.click();

            const elEmail = document.getElementById("emailLogin");
            if (elEmail) elEmail.value = email;
            const elSenha = document.getElementById("senhaLogin");
            if (elSenha) {
                elSenha.value = "";
                elSenha.focus();
            }
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
    const valorTotalEstoque = produtos.reduce((acc, p) => acc + ((parseInt(p.quantidade, 10) || 0) * (parseFloat(p.custo_unitario) || 0.0)), 0);

    // Atualiza KPIs no DOM
    const kpiTotal = document.getElementById("kpiTotalProdutos");
    if (kpiTotal) kpiTotal.textContent = totalItens;

    const kpiBaixo = document.getElementById("kpiEstoqueBaixo");
    if (kpiBaixo) kpiBaixo.textContent = estoqueBaixo;

    const kpiEsg = document.getElementById("kpiEsgotados");
    if (kpiEsg) kpiEsg.textContent = esgotados;

    const kpiUnid = document.getElementById("kpiTotalUnidades");
    if (kpiUnid) kpiUnid.textContent = totalUnidades.toLocaleString('pt-BR');

    const kpiVal = document.getElementById("kpiValorTotalEstoque");
    if (kpiVal) kpiVal.textContent = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valorTotalEstoque);

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
    const row = document.querySelector(`input[data-id="${produtoId}"]`)?.closest("tr");
    const valEl = row ? row.querySelector(".qty-value") : null;
    const prod = (typeof todosOsProdutos !== 'undefined' ? todosOsProdutos : []).find(p => p.id == produtoId);

    const qtdAnterior = prod ? prod.quantidade : (valEl ? parseInt(valEl.textContent, 10) : 0);
    const novaQtd = Math.max(0, qtdAnterior + delta);

    if (delta < 0 && qtdAnterior <= 0) {
        mostrarAlerta("Não é possível reduzir estoque zerado.", "warning");
        return;
    }

    // UPDATE OTIMISTA IMEDIATO NO DOM (0ms de latência percebida)
    if (valEl) valEl.textContent = novaQtd;
    if (prod) prod.quantidade = novaQtd;

    // Atualiza status badge otimista se aplicável
    if (row) {
        const badgeEl = row.querySelector(".badge");
        if (badgeEl) {
            if (novaQtd <= 0) {
                badgeEl.className = "badge badge-danger";
                badgeEl.innerHTML = '<i class="ti ti-circle-x"></i> Esgotado';
            } else if (novaQtd < 5) {
                badgeEl.className = "badge badge-warning";
                badgeEl.innerHTML = '<i class="ti ti-alert-triangle"></i> Baixo';
            } else {
                badgeEl.className = "badge badge-success";
                badgeEl.innerHTML = '<i class="ti ti-check"></i> Normal';
            }
        }
    }

    if (isDemoMode()) {
        let produtos = JSON.parse(localStorage.getItem("demo_produtos") || "[]");
        const pDemo = produtos.find(p => p.id == produtoId);
        if (pDemo) {
            pDemo.quantidade = novaQtd;
            localStorage.setItem("demo_produtos", JSON.stringify(produtos));
        }
        mostrarAlerta(`Quantidade atualizada para ${novaQtd}!`, "success");
        if (document.getElementById("dashboardRecentTableBody") || document.getElementById("kpiTotalProdutos")) carregarDashboardKPIs();
        return;
    }

    try {
        const tipo = delta > 0 ? "entrada" : "saida";
        const qtdAbs = Math.abs(delta);
        const updateRes = await fetch(`${API_URL}/produtos/${produtoId}/movimentar`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({
                tipo: tipo,
                quantidade: qtdAbs,
                motivo: delta > 0 ? "Entrada rápida via interface" : "Saída rápida via interface"
            })
        });

        if (updateRes.ok) {
            const resData = await updateRes.json();
            mostrarAlerta(resData.message || `Estoque atualizado com sucesso!`, "success");
            if (document.getElementById("dashboardRecentTableBody") || document.getElementById("kpiTotalProdutos")) carregarDashboardKPIs();
        } else {
            // ROLLBACK OTIMISTA EM CASO DE ERRO DE CONCORRÊNCIA OU SALDO
            const err = await updateRes.json();
            if (valEl) valEl.textContent = qtdAnterior;
            if (prod) prod.quantidade = qtdAnterior;
            mostrarAlerta(err.message || "Erro ao movimentar estoque.", "error");
        }
    } catch (e) {
        // ROLLBACK OTIMISTA POR FALHA DE REDE
        if (valEl) valEl.textContent = qtdAnterior;
        if (prod) prod.quantidade = qtdAnterior;
        mostrarAlerta("Erro de conexão ao sincronizar estoque.", "error");
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

    renderizarSkeletonsTabela(tbody, 10, 5);

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
        tbody.innerHTML = "<tr><td colspan='10' style='text-align:center; padding: 2rem; color: var(--rose);'>Erro ao conectar com o servidor.</td></tr>";
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
                <td colspan="10" style="text-align: center; padding: 3rem; color: var(--slate-400);">
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
        } else if (p.quantidade < (p.estoque_minimo || 5)) {
            badgeStatus = '<span class="badge badge-warning"><i class="ti ti-alert-triangle"></i> Baixo</span>';
        }

        const custoUnit = parseFloat(p.custo_unitario) || 0.0;
        const totalVal = Math.round((p.quantidade * custoUnit) * 100) / 100;
        const totalFormatado = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totalVal);
        const custoFormatado = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(custoUnit);

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
            <td>
                <div><strong>${totalFormatado}</strong></div>
                <small style="color: var(--slate-400); font-size: 0.72rem;">${custoFormatado}/un</small>
            </td>
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
                produtoData.usuario_id = getUsuarioId() || 99;
                produtos.push(produtoData);
            }
            localStorage.setItem("demo_produtos", JSON.stringify(produtos));
            mostrarAlerta("Produto salvo com sucesso!", "success");
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

// ============================================================
//  ENTERPRISE MULTI-TENANCY & SUPERADMIN PLATFORM FUNCTIONS
// ============================================================

window.renderizarSkeletonsTabela = function(tbody, colunas = 9, linhas = 5) {
    if (!tbody) return;
    let html = "";
    for (let i = 0; i < linhas; i++) {
        html += `<tr>
            <td style="text-align: center;"><div class="skeleton-shimmer" style="width: 16px; height: 16px;"></div></td>
            <td><div class="skeleton-shimmer skeleton-title" style="margin-bottom: 4px;"></div><div class="skeleton-shimmer skeleton-text" style="width: 40%;"></div></td>
            <td><div class="skeleton-shimmer skeleton-text" style="width: 70%;"></div></td>
            <td><div class="skeleton-shimmer skeleton-text" style="width: 50%;"></div></td>
            <td><div class="skeleton-shimmer skeleton-badge"></div></td>
            <td><div class="skeleton-shimmer skeleton-text" style="width: 60%;"></div></td>
            <td><div class="skeleton-shimmer skeleton-text" style="width: 65%;"></div></td>
            <td><div class="skeleton-shimmer skeleton-text" style="width: 50%;"></div></td>
            <td style="text-align: right;"><div class="skeleton-shimmer" style="width: 55px; height: 28px;"></div></td>
        </tr>`;
    }
    tbody.innerHTML = html;
};

window.carregarContextoOrganizacoes = async function() {
    const selector = document.getElementById("orgContextSelector");
    const banner = document.getElementById("impersonationBanner");
    const bannerName = document.getElementById("impersonatedOrgNameBanner");

    const impersonatedBy = localStorage.getItem("impersonatedBy");
    const activeOrgNome = localStorage.getItem("activeOrgNome") || "Empresa Cliente";
    if (impersonatedBy && banner) {
        banner.style.display = "flex";
        if (bannerName) bannerName.textContent = activeOrgNome;
    }

    if (!selector) return;

    if (isDemoMode()) {
        selector.innerHTML = '<option value="1">SimpStock Matriz (Demo)</option>';
        return;
    }

    try {
        const res = await fetch(`${API_URL}/organizations/my`, {
            headers: getAuthHeaders()
        });
        if (res.ok) {
            const data = await res.json();
            const orgs = data.organizations || [];
            if (orgs.length > 0) {
                selector.innerHTML = "";
                const currentOrgId = localStorage.getItem("activeOrgId") || String(data.active_organization_id || orgs[0].id);
                orgs.forEach(o => {
                    const opt = document.createElement("option");
                    opt.value = o.id;
                    opt.textContent = `${o.nome} (${(o.plano || 'PRO').toUpperCase()})`;
                    if (String(o.id) === String(currentOrgId)) {
                        opt.selected = true;
                    }
                    selector.appendChild(opt);
                });
            }
        }
    } catch (e) {
        console.warn("Falha ao carregar organizações:", e);
    }
};

window.trocarOrganizacaoContexto = async function(orgId) {
    if (isDemoMode()) {
        mostrarAlerta("Troca de organização simulada no modo demonstração!", "success");
        return;
    }

    try {
        const res = await fetch(`${API_URL}/organizations/switch`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({ organization_id: parseInt(orgId, 10) })
        });
        const data = await res.json();
        if (res.ok) {
            localStorage.setItem("token", data.token);
            localStorage.setItem("activeOrgId", data.organization.id);
            localStorage.setItem("activeOrgNome", data.organization.nome);
            mostrarAlerta(`Ambiente alternado para '${data.organization.nome}'!`, "success");
            setTimeout(() => {
                window.location.reload();
            }, 600);
        } else {
            mostrarAlerta(data.message || "Não foi possível alternar de organização.", "error");
        }
    } catch (e) {
        mostrarAlerta("Erro de conexão ao alternar organização.", "error");
    }
};

window.encerrarImpersonacao = function() {
    const originalToken = localStorage.getItem("original_superadmin_token");
    if (originalToken) {
        localStorage.setItem("token", originalToken);
        localStorage.removeItem("original_superadmin_token");
        localStorage.removeItem("impersonatedBy");
        mostrarAlerta("Sessão de suporte encerrada. Retornando ao Superadmin...", "success");
        setTimeout(() => {
            window.location.href = "Superadmin.html";
        }, 800);
    } else {
        localStorage.removeItem("impersonatedBy");
        window.location.reload();
    }
};

window.verificarAcessoSuperadmin = function() {
    if (!verificarAutenticacao()) return;
    const isSuper = getIsSuperadmin();
    const isAdmin = getIsAdmin();
    const userId = getUsuarioId();
    if (!isSuper && userId !== 1 && !isAdmin) {
        mostrarAlerta("Acesso restrito a Superadministradores da Plataforma!", "error");
        setTimeout(() => { window.location.href = "Tela_inicial.html"; }, 1500);
    }
};

window.carregarOverviewSuperadmin = async function() {
    try {
        const res = await fetch(`${API_URL}/superadmin/overview`, { headers: getAuthHeaders() });
        if (res.ok) {
            const data = await res.json();
            const ov = data.overview;
            const elEmpresas = document.getElementById("kpiTotalEmpresas");
            if (elEmpresas) elEmpresas.textContent = ov.total_organizations;
            const elAtivas = document.getElementById("kpiEmpresasAtivas");
            if (elAtivas) elAtivas.textContent = `${ov.active_organizations} ativas na nuvem`;
            const elUsers = document.getElementById("kpiTotalUsuariosGlobais");
            if (elUsers) elUsers.textContent = ov.total_users;
            const elSkus = document.getElementById("kpiTotalSkusGlobais");
            if (elSkus) elSkus.textContent = ov.total_products;
            const elItens = document.getElementById("kpiTotalItensGlobais");
            if (elItens) elItens.textContent = `${ov.total_inventory_items} unidades físicas`;
            const elVal = document.getElementById("kpiValorEstoqueGlobal");
            if (elVal) elVal.textContent = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(ov.total_inventory_value);
        }
    } catch (e) {
        console.warn("Erro ao carregar overview do superadmin:", e);
    }
};

let listaOrganizacoesSuperadmin = [];

window.carregarOrganizacoesSuperadmin = async function() {
    const tbody = document.getElementById("tabelaOrganizacoesBody");
    if (!tbody) return;
    renderizarSkeletonsTabela(tbody, 9, 4);

    try {
        const res = await fetch(`${API_URL}/superadmin/organizations`, { headers: getAuthHeaders() });
        if (res.ok) {
            listaOrganizacoesSuperadmin = await res.json();
            renderizarTabelaOrganizacoes(listaOrganizacoesSuperadmin);
        } else {
            tbody.innerHTML = "<tr><td colspan='9' style='text-align: center; color: var(--rose); padding: 2rem;'>Erro ao carregar organizações.</td></tr>";
        }
    } catch (e) {
        tbody.innerHTML = "<tr><td colspan='9' style='text-align: center; color: var(--rose); padding: 2rem;'>Erro de conexão com o servidor.</td></tr>";
    }
};

function renderizarTabelaOrganizacoes(orgs) {
    const tbody = document.getElementById("tabelaOrganizacoesBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!Array.isArray(orgs) || orgs.length === 0) {
        tbody.innerHTML = "<tr><td colspan='9' style='text-align: center; padding: 2.5rem; color: var(--slate-400);'>Nenhuma organização encontrada.</td></tr>";
        return;
    }

    orgs.forEach(o => {
        const statusBadge = o.ativo 
            ? '<span class="badge badge-success"><i class="ti ti-circle-check"></i> Ativa</span>'
            : '<span class="badge badge-danger"><i class="ti ti-circle-x"></i> Inativa</span>';

        const valorFormatado = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(o.valor_estoque || 0);

        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><code>#${escaparHTML(String(o.id))}</code></td>
            <td><strong>${escaparHTML(o.nome)}</strong></td>
            <td><code>${escaparHTML(o.slug)}</code></td>
            <td><span class="badge-plan ${escaparHTML(o.plano)}">${escaparHTML(o.plano)}</span></td>
            <td>${statusBadge}</td>
            <td>${o.total_usuarios || 0}</td>
            <td>${o.total_produtos || 0}</td>
            <td><strong>${valorFormatado}</strong></td>
            <td style="text-align: right;">
                <button type="button" class="btn-primary-action" onclick="abrirModalImpersonar(${o.id}, '${escaparHTML(o.nome)}')" style="font-size: 0.75rem; padding: 4px 10px; background: #dc2626; border-color: #dc2626;" title="Acessar painel como esta empresa com registro de auditoria">
                    <i class="ti ti-user-check"></i>
                    <span>Log in as</span>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

window.filtrarTabelaOrganizacoes = function() {
    const termo = (document.getElementById("filtroOrganizacaoInput")?.value || "").toLowerCase().trim();
    if (!termo) {
        renderizarTabelaOrganizacoes(listaOrganizacoesSuperadmin);
        return;
    }
    const filtradas = listaOrganizacoesSuperadmin.filter(o =>
        (o.nome || "").toLowerCase().includes(termo) || (o.slug || "").toLowerCase().includes(termo)
    );
    renderizarTabelaOrganizacoes(filtradas);
};

window.abrirModalImpersonar = function(orgId, orgNome) {
    const modal = document.getElementById("modalImpersonar");
    const elId = document.getElementById("impersonateOrgId");
    const elNome = document.getElementById("impersonateOrgNome");
    const elMotivo = document.getElementById("impersonateMotivo");
    if (elId) elId.value = orgId;
    if (elNome) elNome.textContent = orgNome;
    if (elMotivo) elMotivo.value = "";
    if (modal) modal.style.display = "flex";
};

window.fecharModalImpersonar = function() {
    const modal = document.getElementById("modalImpersonar");
    if (modal) modal.style.display = "none";
};

window.confirmarImpersonacao = async function() {
    const orgId = document.getElementById("impersonateOrgId")?.value;
    const motivo = document.getElementById("impersonateMotivo")?.value.trim();

    if (!motivo || motivo.length < 5) {
        mostrarAlerta("Justificativa obrigatória (mínimo 5 caracteres) para auditoria!", "warning");
        return;
    }

    try {
        const res = await fetch(`${API_URL}/superadmin/impersonate`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({ target_org_id: parseInt(orgId, 10), reason: motivo })
        });
        const data = await res.json();
        if (res.ok) {
            const tokenAtual = getAuthToken();
            localStorage.setItem("original_superadmin_token", tokenAtual);
            localStorage.setItem("token", data.token);
            localStorage.setItem("impersonatedBy", data.impersonated_by.id);
            localStorage.setItem("activeOrgId", data.organization.id);
            localStorage.setItem("activeOrgNome", data.organization.nome);

            mostrarAlerta(`Sessão de suporte iniciada na organização '${data.organization.nome}'!`, "success");
            setTimeout(() => {
                window.location.href = "Tela_inicial.html";
            }, 800);
        } else {
            mostrarAlerta(data.message || "Falha ao iniciar impersonação.", "error");
        }
    } catch (e) {
        mostrarAlerta("Erro de conexão ao solicitar impersonação.", "error");
    }
};

window.abrirModalNovaOrganizacao = function() {
    const modal = document.getElementById("modalNovaOrg");
    if (modal) modal.style.display = "flex";
};

window.fecharModalNovaOrg = function() {
    const modal = document.getElementById("modalNovaOrg");
    if (modal) modal.style.display = "none";
};

window.salvarNovaOrganizacao = async function(e) {
    e.preventDefault();
    const nome = document.getElementById("novaOrgNome")?.value.trim();
    const cnpj = document.getElementById("novaOrgCnpj")?.value.trim();
    const plano = document.getElementById("novaOrgPlano")?.value;

    try {
        const res = await fetch(`${API_URL}/superadmin/organizations`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({ nome, cnpj_ou_documento: cnpj, plano })
        });
        const data = await res.json();
        if (res.ok) {
            mostrarAlerta(`Organização '${nome}' provisionada com sucesso!`, "success");
            fecharModalNovaOrg();
            carregarOrganizacoesSuperadmin();
            carregarOverviewSuperadmin();
        } else {
            mostrarAlerta(data.message || "Erro ao criar organização.", "error");
        }
    } catch (err) {
        mostrarAlerta("Erro de conexão ao criar organização.", "error");
    }
};

window.carregarAuditoriaSuperadmin = async function() {
    const tbody = document.getElementById("tabelaAuditoriaBody");
    if (!tbody) return;

    try {
        const res = await fetch(`${API_URL}/superadmin/audit-logs?limit=25`, { headers: getAuthHeaders() });
        if (res.ok) {
            const logs = await res.json();
            tbody.innerHTML = "";
            if (logs.length === 0) {
                tbody.innerHTML = "<tr><td colspan='6' style='text-align: center; padding: 2rem; color: var(--slate-400);'>Nenhum registro de auditoria.</td></tr>";
                return;
            }
            logs.forEach(l => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><small style="color: var(--slate-500);">${escaparHTML(l.criado_em)}</small></td>
                    <td><code>${escaparHTML(l.acao)}</code></td>
                    <td><strong>${escaparHTML(l.usuario_nome)}</strong> <small style="color: var(--slate-400);">(${escaparHTML(l.usuario_email)})</small></td>
                    <td><span class="badge badge-blue">${escaparHTML(l.organization_nome || 'Global')}</span></td>
                    <td><code>${escaparHTML(l.ip_address || '-')}</code></td>
                    <td>${escaparHTML(l.detalhes || '-')}</td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        tbody.innerHTML = "<tr><td colspan='6' style='text-align: center; color: var(--rose); padding: 1.5rem;'>Erro ao carregar auditoria.</td></tr>";
    }
};

// ============================================================
//  SUPORTE TÉCNICO / PEDIR AJUDA
// ============================================================
window.abrirModalSuporte = function() {
    const modal = document.getElementById("modalSuporte");
    if (!modal) return;

    const nome = localStorage.getItem("usuarioNome") || localStorage.getItem("usuarioLogado") || "Usuário";
    const email = localStorage.getItem("usuarioEmail") || "";
    const orgSelector = document.getElementById("orgContextSelector");
    const activeOrgNome = localStorage.getItem("activeOrgNome") || (orgSelector ? orgSelector.options[orgSelector.selectedIndex]?.text : null) || "SimpStock Matriz";

    const elUser = document.getElementById("suporteUsuarioInfo");
    if (elUser) {
        elUser.textContent = email ? `${nome} (${email})` : nome;
    }

    const elOrg = document.getElementById("suporteOrgInfo");
    if (elOrg) {
        elOrg.textContent = activeOrgNome;
    }

    const elMsg = document.getElementById("suporteMensagem");
    if (elMsg) elMsg.value = "";

    modal.style.display = "flex";
};

window.fecharModalSuporte = function() {
    const modal = document.getElementById("modalSuporte");
    if (modal) modal.style.display = "none";
};

window.enviarSolicitacaoSuporte = async function(e) {
    if (e && e.preventDefault) e.preventDefault();

    const tipo = document.getElementById("suporteTipo")?.value || "duvida";
    const mensagem = document.getElementById("suporteMensagem")?.value?.trim() || "";
    const btnSubmit = document.getElementById("btnEnviarSuporte");

    if (!mensagem) {
        mostrarAlerta("Por favor, descreva sua solicitação detalhadamente.", "warning");
        return;
    }

    if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.innerHTML = '<i class="ti ti-loader" style="animation: spin 1s infinite linear;"></i> Enviando...';
    }

    try {
        const res = await fetch(`${API_URL}/api/support`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({ tipo, mensagem })
        });
        const data = await res.json();
        if (res.ok) {
            fecharModalSuporte();
            mostrarAlerta(data.message || `Chamado de suporte #${data.ticket?.id || ''} registrado com sucesso!`, "success");
            const elMsg = document.getElementById("suporteMensagem");
            if (elMsg) elMsg.value = "";
        } else {
            mostrarAlerta(data.message || "Erro ao registrar chamado de suporte.", "error");
        }
    } catch (err) {
        mostrarAlerta("Falha de conexão ao enviar chamado de suporte.", "error");
    } finally {
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = '<i class="ti ti-send"></i> Enviar Solicitação';
        }
    }
};