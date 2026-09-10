# 📐 SIMPSTOCK BLUEPRINT & TECHNICAL SPECIFICATION

Este documento formaliza as decisões de design, modelos conceituais de dados, arquitetura defensiva e contratos de API implementados no **SimpStock**.

---

## 1. Modelo Relacional de Dados (SQLite)

```sql
-- Tabela de Usuários e Autenticação
CREATE TABLE usuarios (
    id        INTEGER      PRIMARY KEY AUTOINCREMENT,
    nome      VARCHAR(100) NOT NULL,
    email     VARCHAR(150) NOT NULL UNIQUE,
    senha     VARCHAR(255) NOT NULL,
    is_admin  BOOLEAN      NOT NULL DEFAULT 0,
    criado_em TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Produtos (Inventário)
CREATE TABLE produtos (
    id            INTEGER      PRIMARY KEY AUTOINCREMENT,
    usuario_id    INTEGER      NOT NULL,
    nome          VARCHAR(150) NOT NULL,
    marca         VARCHAR(100) NOT NULL,
    validade      DATE         NULL,
    codigo        VARCHAR(80)  NOT NULL UNIQUE,
    quantidade    INTEGER      NOT NULL DEFAULT 0,
    referencia    VARCHAR(80)  NULL,
    endereco      VARCHAR(200) NULL,
    criado_em     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Tabela de Auditoria de Estoque
CREATE TABLE movimentacoes (
    id         INTEGER      PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER      NOT NULL,
    usuario_id INTEGER      NOT NULL,
    tipo       VARCHAR(10)  NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    quantidade INTEGER      NOT NULL,
    motivo     VARCHAR(255) NULL,
    criado_em  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (produto_id) REFERENCES produtos (id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE RESTRICT ON UPDATE CASCADE
);
```

---

## 2. Padrões de Segurança Aplicados

### Token Payload (JWT Specification)
- Algoritmo de Assinatura: `HMAC-SHA256 (HS256)`
- Claims incluídas:
  - `sub`: ID do usuário
  - `user_id`: ID do usuário
  - `nome`: Nome do usuário
  - `email`: Endereço de e-mail do usuário
  - `is_admin`: Flag booleana de privilégio
  - `iat`: Timestamp UTC de emissão
  - `exp`: Timestamp UTC de expiração (configurável, padrão 24 horas)

### Proteção de Integridade
1. **Regra de Não-Exclusão do Administrador Principal:**
   O usuário com `id = 1` é imutável em relação à exclusão, prevenindo que um administrador remova a chave mestra de recuperação do ambiente.
2. **Prevenção de Auto-Exclusão de Admin:**
   Um administrador não pode disparar uma requisição de exclusão sobre si mesmo para evitar desautorização acidental sem transferência prévia de responsabilidade.
3. **Auditoria Transacional Imutável:**
   A criação de produtos e cada modificação na quantidade de estoque gera obrigatoriamente um registro na tabela `movimentacoes`.

---

## 3. Guia de Contribuição e Ciclo de Vida do Código

1. Todo novo endpoint deve ser registrado via **Flask Blueprint**.
2. Todas as rotas que manipulam dados devem exigir o decorador `@token_required` ou `@admin_required`.
3. Todo código adicionado deve ser acompanhado por testes automatizados em `tests/` executáveis via `pytest`.