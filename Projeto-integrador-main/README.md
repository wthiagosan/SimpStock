# 📦 SimpStock - Sistema de Controle de Estoque

> Projeto Integrador - Ciência da Computação

![Status](https://img.shields.io/badge/Status-Concluído-brightgreen)
![Python](https://img.shields.io/badge/Python-3.x-blue)
![Flask](https://img.shields.io/badge/Flask-2.x-green)
![HTML5](https://img.shields.io/badge/HTML5-orange)
![CSS3](https://img.shields.io/badge/CSS3-blue)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E)

## 📄 Sobre o Projeto

O **SimpStock** é uma plataforma web de gestão de estoque desenvolvida para simplificar o dia a dia de lojistas e otimizar o controle de produtos. O objetivo é facilitar o gerenciamento de entradas e saídas através de uma interface intuitiva e acessível.

O sistema opera numa arquitetura **Cliente-Servidor**, onde o Frontend consome uma API RESTful desenvolvida em Python (Flask).

---

## 🚀 Funcionalidades

### 🔒 Autenticação e Usuários
* **Cadastro e Login:** Sistema de autenticação com validação de senha.
* **Painel Administrativo:** Área exclusiva para administradores gerenciarem os usuários do sistema.
* **Proteção de Admin:** Impede a exclusão do Administrador Principal.

### 📦 Gestão de Produtos
* **Adicionar Produto:** Cadastro completo com nome, marca, validade, SKU, quantidade e localização.
* **Listagem:** Visualização de todo o inventário em formato de tabela.
* **Edição e Remoção:** Atualização de dados ou exclusão de itens (individual ou em massa).

---

## 🛠️ Tecnologias Utilizadas

### Backend (API)
* **Python 3**: Linguagem base.
* **Flask**: Micro-framework para criação das rotas da API.
* **Flask-CORS**: Para gerenciar permissões de acesso entre domínios.
* **JSON**: Utilizado como banco de dados NoSQL (baseado em arquivo) para prototipagem rápida.

### Frontend (Interface)
* **HTML5 & CSS3**: Estrutura e estilização (Responsivo).
* **JavaScript (Vanilla)**: Manipulação do DOM e consumo de API (Fetch).

---

## 📂 Estrutura do Projeto

```bash
/
├── app.py                 # Servidor Flask (Backend e API)
├── banco.json             # Banco de dados de Produtos
├── usuarios.json          # Banco de dados de Usuários
├── src/
│   ├── Admin.html         # Painel de administração
│   ├── Cadastro...html    # Formulário de produtos
│   ├── Login.html         # Tela de Login/Registro
│   ├── tabela...html      # Listagem de estoque
│   ├── Sistema_script.js  # Lógica principal do Frontend
│   └── imagens/           # Assets do projeto
```

---

### 👥 Autores
 *Projeto desenvolvido pela equipe de estudantes de Ciência da Computação:*
* **Estela Vidal**
* **Mateus de Souza**
* **Welinton Sandrin**
* **Wesley da Silva**
