const tabela = document.querySelector("#productTable tbody");
const excluirSelecionadosBtn = document.getElementById("excluirSelecionadosBtn");
const produtos = JSON.parse(localStorage.getItem("produtos")) || [];

// Atualiza a exibição do botão "Excluir Selecionados" com base na seleção
function atualizarBotaoExcluirSelecionados() {
    const selecionados = document.querySelectorAll(".select-product:checked");
    excluirSelecionadosBtn.style.display = selecionados.length > 0 ? "block" : "none";
}

// Carrega os produtos na tabela
function carregarTabela() {
    tabela.innerHTML = "";

    produtos.forEach((produto, index) => {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td><input type="checkbox" class="select-product" data-index="${index}" onchange="atualizarBotaoExcluirSelecionados()"></td>
            <td>${produto.nome}</td>
            <td>${produto.marca}</td>
            <td>${produto.validade || "N/A"}</td>
            <td>${produto.codigo}</td>
            <td>${produto.quantidade}</td>
            <td>${produto.referencia}</td>
            <td>${produto.endereco || "N/A"}</td>
            <td>
                <button class="editar" onclick="confirmarAcao('editar', ${index})">Editar</button>
                <button class="excluir" onclick="confirmarAcao('excluir', ${index})">Excluir</button>
            </td>
        `;

        tabela.appendChild(row);
    });

    atualizarBotaoExcluirSelecionados();
}

// Função para confirmar a ação
function confirmarAcao(acao, index) {
    const mensagem =
        acao === "editar"
            ? "Você tem certeza que deseja editar este produto?"
            : "Você tem certeza que deseja excluir este produto?";

    if (confirm(mensagem)) {
        if (acao === "editar") {
            editarProduto(index);
        } else if (acao === "excluir") {
            excluirProduto(index);
        }
    }
}

// Redireciona para a página de cadastro com o produto a ser editado
function editarProduto(index) {
    const produto = produtos[index];
    localStorage.setItem("produtoEdicao", JSON.stringify(produto));
    localStorage.setItem("produtoEdicaoIndex", index);
    window.location.href = "Cadastro_de_produtos.html";
}

// Exclui um produto específico
function excluirProduto(index) {
    produtos.splice(index, 1);
    localStorage.setItem("produtos", JSON.stringify(produtos));
    carregarTabela();
}

// Exclui os produtos selecionados
excluirSelecionadosBtn.addEventListener("click", () => {
    const selecionados = document.querySelectorAll(".select-product:checked");

    if (selecionados.length === 0) {
        alert("Nenhum produto selecionado!");
        return;
    }

    if (confirm(`Tem certeza que deseja excluir ${selecionados.length} produto(s)?`)) {
        const indicesParaExcluir = Array.from(selecionados).map((checkbox) =>
            parseInt(checkbox.dataset.index)
        );

        indicesParaExcluir.sort((a, b) => b - a).forEach((index) => produtos.splice(index, 1));
        localStorage.setItem("produtos", JSON.stringify(produtos));
        carregarTabela();
    }
});

carregarTabela();
