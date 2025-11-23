const API_URL = "https://mateus774v2.pythonanywhere.com";

document.addEventListener("DOMContentLoaded", () => {
    const path = window.location.pathname;
    const isPublic = path.includes("Login.html") || path.includes("index.html") || path.includes("Sobre_nós") || path.includes("Ajuda.html");
    
    if (!isPublic) verificarAutenticacao();

    // --- LÓGICA ADMIN ---
    const isAdmin = localStorage.getItem("isAdmin") === "true";
    
    const btnAdmin = document.getElementById("btnAdmin");
    if (btnAdmin) {
        btnAdmin.style.display = isAdmin ? "block" : "none";
    }

    if (path.includes("Admin.html") && !isAdmin) {
        alert("Acesso negado! Apenas administradores.");
        window.location.href = "Tela_inicial.html";
    }

    // Inicializadores de Página
    if (document.getElementById("formLogin")) configurarLogin();
    if (document.getElementById("formCadastro")) configurarCadastro();
    if (document.getElementById("productForm")) iniciarPaginaCadastro();
    if (document.getElementById("productTable")) iniciarPaginaTabela();
    if (document.getElementById("tabelaUsuarios")) iniciarPaginaAdmin();
    
    // Botões de Olho (Senha)
    configurarOlhoSenha("toggleLogin", "senhaLogin");
    configurarOlhoSenha("toggleCadastro", "senhaCadastro");

    // Logout
    const btnSair = document.querySelector('a[href="index.html"]'); 
    if (btnSair && !isPublic) {
        btnSair.addEventListener("click", (e) => { e.preventDefault(); logout(); });
    }

    // Animação do Painel de Login/Cadastro
    const container = document.getElementById('container');
    const registerBtn = document.getElementById('register'); 
    const loginBtn = document.getElementById('login');      
    if (registerBtn && container) registerBtn.addEventListener('click', () => container.classList.add("active"));
    if (loginBtn && container) loginBtn.addEventListener('click', () => container.classList.remove("active"));
});

// --- FUNÇÕES GERAIS ---
function verificarAutenticacao() {
    if (!localStorage.getItem("usuarioLogado")) {
        alert("Você precisa fazer login.");
        window.location.href = "Login.html";
    }
}

function logout() {
    localStorage.removeItem("usuarioLogado");
    localStorage.removeItem("isAdmin");
    window.location.href = "Login.html";
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

// --- LOGIN E CADASTRO ---
function configurarLogin() {
    document.getElementById("formLogin").addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("emailLogin").value;
        const senha = document.getElementById("senhaLogin").value;
        try {
            const res = await fetch(`${API_URL}/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, senha })
            });
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem("usuarioLogado", data.usuario);
                localStorage.setItem("isAdmin", data.is_admin);
                window.location.href = "Tela_inicial.html";
            } else { alert(data.message); }
        } catch (erro) { alert("Erro de conexão."); }
    });
}

function configurarCadastro() {
    document.getElementById("formCadastro").addEventListener("submit", async (e) => {
        e.preventDefault();
        const nome = document.getElementById("nomeCadastro").value;
        const email = document.getElementById("emailCadastro").value;
        const senha = document.getElementById("senhaCadastro").value;

        const regexSenha = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{6,}$/;
        if (!regexSenha.test(senha)) {
            alert("Senha inválida! Regras:\n- Mínimo 6 caracteres\n- Letras e Números apenas\n- SEM caracteres especiais");
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
                alert("Conta criada! Faça login.");
                const btnLogin = document.getElementById('login');
                if(btnLogin) btnLogin.click(); 
            } else { alert(data.message); }
        } catch (erro) { alert("Erro ao cadastrar."); }
    });
}

// --- ADMINISTRAÇÃO ---
async function iniciarPaginaAdmin() {
    const tbody = document.querySelector("#tabelaUsuarios tbody");
    try {
        const res = await fetch(`${API_URL}/usuarios`);
        const usuarios = await res.json();
        tbody.innerHTML = "";
        if (usuarios.length === 0) { tbody.innerHTML = "<tr><td colspan='5'>Nenhum usuário.</td></tr>"; return; }
        usuarios.forEach(user => {
            const tipo = user.is_admin ? "<strong>ADMIN</strong>" : "Comum";
            const btnDisabled = user.id === 1 ? "disabled style='opacity:0.5; cursor:not-allowed'" : "";
            const tr = document.createElement("tr");
            tr.innerHTML = `<td>${user.id}</td><td>${user.nome}</td><td>${user.email}</td><td>${tipo}</td>
                <td><button class="excluir" onclick="deletarUsuario(${user.id})" ${btnDisabled}>Remover</button></td>`;
            tbody.appendChild(tr);
        });
    } catch (erro) { tbody.innerHTML = "<tr><td colspan='5'>Erro ao carregar.</td></tr>"; }
}

window.deletarUsuario = async (id) => {
    if (confirm("Excluir usuário?")) {
        try { await fetch(`${API_URL}/usuarios/${id}`, { method: "DELETE" }); window.location.reload(); }
        catch (erro) { alert("Erro."); }
    }
}

// --- PRODUTOS (Cadastro e Tabela) ---
async function iniciarPaginaCadastro() {
    const idEdicao = localStorage.getItem("idProdutoEdicao");
    if (idEdicao) {
        try {
            const res = await fetch(`${API_URL}/produtos`);
            const produtos = await res.json();
            const produto = produtos.find(p => p.id == idEdicao);
            if (produto) {
                document.getElementById("nome").value = produto.nome;
                document.getElementById("marca").value = produto.marca;
                document.getElementById("validade").value = produto.validade || "";
                document.getElementById("codigo").value = produto.codigo;
                document.getElementById("quantidade").value = produto.quantidade;
                document.getElementById("referencia").value = produto.referencia;
                document.getElementById("endereco").value = produto.endereco || "";
                document.getElementById("productForm").dataset.id = idEdicao;
                document.querySelector("button[type='submit']").innerText = "Salvar Alterações";
            }
        } catch (erro) { console.error(erro); }
        localStorage.removeItem("idProdutoEdicao");
    }
    document.getElementById("productForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const produtoData = {
            nome: document.getElementById("nome").value,
            marca: document.getElementById("marca").value,
            validade: document.getElementById("validade").value,
            codigo: document.getElementById("codigo").value,
            quantidade: document.getElementById("quantidade").value,
            referencia: document.getElementById("referencia").value,
            endereco: document.getElementById("endereco").value
        };
        const id = e.target.dataset.id;
        try {
            let url = `${API_URL}/produtos`; let method = "POST";
            if (id) { url = `${url}/${id}`; method = "PUT"; }
            const response = await fetch(url, { method: method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(produtoData) });
            if (response.ok) { alert("Salvo!"); window.location.href = "tabela_principal.html"; } else { alert("Erro."); }
        } catch (erro) { alert("Erro API."); }
    });
}

async function iniciarPaginaTabela() {
    const tbody = document.querySelector("#productTable tbody");
    const btnExcluir = document.getElementById("excluirSelecionadosBtn");
    window.atualizarBotaoExcluirSelecionados = () => {
        const sel = document.querySelectorAll(".select-product:checked");
        if (btnExcluir) btnExcluir.style.display = sel.length > 0 ? "block" : "none";
    };
    try {
        const res = await fetch(`${API_URL}/produtos`);
        const produtos = await res.json();
        tbody.innerHTML = "";
        if (produtos.length === 0) tbody.innerHTML = "<tr><td colspan='9'>Vazio.</td></tr>";
        produtos.forEach(p => {
            tbody.innerHTML += `<tr>
                <td><input type="checkbox" class="select-product" data-id="${p.id}" onchange="atualizarBotaoExcluirSelecionados()"></td>
                <td>${p.nome}</td><td>${p.marca}</td><td>${p.validade || "-"}</td>
                <td>${p.codigo}</td><td>${p.quantidade}</td><td>${p.referencia}</td><td>${p.endereco || "-"}</td>
                <td><button class="editar" onclick="prepararEdicao(${p.id})">Editar</button>
                    <button class="excluir" onclick="deletarProduto(${p.id})">Excluir</button></td>
            </tr>`;
        });
    } catch (e) { tbody.innerHTML = "<tr><td colspan='9'>Erro servidor.</td></tr>"; }
    if (btnExcluir) btnExcluir.addEventListener("click", async () => {
        if (confirm("Excluir selecionados?")) {
            const sels = document.querySelectorAll(".select-product:checked");
            for (const cb of sels) await fetch(`${API_URL}/produtos/${cb.dataset.id}`, { method: "DELETE" });
            window.location.reload();
        }
    });
}
window.prepararEdicao = (id) => { localStorage.setItem("idProdutoEdicao", id); window.location.href = "Cadastro_de_produtos.html"; }

window.deletarProduto = async (id) => { if (confirm("Excluir?")) { await fetch(`${API_URL}/produtos/${id}`, { method: "DELETE" }); window.location.reload(); } }
