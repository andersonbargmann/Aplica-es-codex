# Portal de Links

Página estática em HTML e CSS para organizar ícones e links de acesso rápido sobre um fundo azul inspirado na identidade visual enviada.

## Como editar os links

Abra o arquivo `index.html` e altere os blocos com a classe `link-card`:

```html
<a class="link-card" href="https://exemplo.com" target="_blank" rel="noopener noreferrer">
  <span class="card-icon" aria-hidden="true">🌐</span>
  <span class="card-text">
    <strong>Nome do site</strong>
    <small>Descrição curta</small>
  </span>
</a>
```

- `href`: endereço do site.
- `card-icon`: emoji, letra, símbolo ou ícone que deseja exibir.
- `strong`: nome principal do link.
- `small`: descrição curta.

Para criar outro card, copie e cole um bloco `<a class="link-card">` completo dentro de `links-grid`.

## Como abrir

Basta abrir o arquivo `index.html` no navegador. Se preferir, execute um servidor local:

```bash
python3 -m http.server 8000
```

Depois acesse `http://localhost:8000`.
