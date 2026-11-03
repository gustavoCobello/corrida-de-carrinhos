# ADR 0008 — Tema claro em Bento Grid e fontes self-hosted na tela principal

- **Status:** Aceito
- **Data:** 2026-10-28

## Contexto

A Fase 4 entregou a interface funcional em um tema escuro de painel técnico. A próxima prioridade deixou de ser a suíte de testes e passou a ser uma revisão visual da tela principal, com direção de Bento Grid claro, tipografia editorial, cartões com profundidade e microinterações.

O projeto continua sem build de front-end, sem Node em runtime e sem dependência de internet. A interface precisa preservar os IDs consumidos por `static/js/app.js`, o contrato da API e toda a lógica de corrida. A tela `/setup` não faz parte deste escopo e pode continuar no tema escuro.

## Decisão

1. Redesenhar apenas `templates/index.html` e `static/css/style.css`, mantendo `app.py`, `src/` e a tela de setup sem alterações funcionais.
2. Adotar um Bento Grid com áreas nomeadas: hero de vídeo em destaque, cronômetro, ranking, formação, pódio e telemetria da câmera.
3. Usar a paleta off-white `#F4F4F6`, lilás `#8B8EE5`/`#7F84DC`, menta `#9AE5D3`, âmbar `#FCD06B`, carvão `#3B3B3B` e preto `#0D0D0D`, com contraste alto e cartões de raio generoso.
4. Servir Space Grotesk e Inter como fontes variáveis locais em `static/fonts/`, com os textos de licença OFL versionados no repositório, em vez de usar CDN.
5. Manter HTML, CSS e JavaScript puro; as animações usam CSS e a API de Web Animations/transform, sem nova dependência.
6. Aplicar tilt 3D e botões magnéticos somente em dispositivos com `(pointer: fine)` e desativar movimento quando `prefers-reduced-motion: reduce` estiver ativo.
7. Manter o pódio sempre visível, com slots vazios antes da corrida, e atualizar `#ranking-tag` conforme o estado real da prova.
8. Em tela cheia, usar fundo preto e ocultar os badges HTML do vídeo para não duplicar o HUD de FPS/fonte desenhado pelo backend.

## Alternativas consideradas

- **Apenas ajustar o tema escuro:** menor esforço, mas não atenderia ao pedido de reestruturação visual e Bento Grid.
- **Redesenhar também `/setup`:** deixaria o produto consistente, porém ampliaria o escopo e o risco antes da validação funcional.
- **Adotar um framework de UI:** aceleraria componentes, mas contraria a restrição de HTML/CSS/JS puro e adicionaria build/runtime.
- **Carregar fontes via CDN:** simplificaria o download, mas quebraria a operação offline e a independência de rede.
- **Animar todos os cartões no hover:** chamativo, porém pioraria a legibilidade e o desempenho em telas de toque; a decisão foi limitar os efeitos a ponteiros finos.

## Consequências

- Positivas: a tela principal ganha identidade visual própria, mantém a leitura rápida do vídeo e do ranking, continua offline e preserva todo o contrato funcional.
- Negativas: existe uma diferença visual temporária entre a tela principal clara e o setup escuro; o CSS cresceu em tokens, breakpoints e estados de interação.
- Mitigações: o sistema visual foi concentrado em variáveis CSS, a tela de setup foi explicitamente deixada para uma etapa posterior e o movimento é progressivo e opcional.
- Reavaliar: se o setup for redesenhado, o mesmo conjunto de tokens e fontes pode ser promovido a um arquivo compartilhado.
