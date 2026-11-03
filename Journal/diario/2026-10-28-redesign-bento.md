# 2026-10-28 — Redesign: Bento Grid claro na tela principal

## Objetivo

Substituir o painel escuro da tela principal por uma composição Bento Grid clara, premium e editorial, sem alterar a API, a lógica de corrida, o modo demo ou a tela de setup. O escopo foi definido como reestruturação de layout apenas em `/`.

## O que foi implementado

- `templates/index.html`: nova estrutura Bento com hero de vídeo, cronômetro, ranking, formação, pódio e telemetria; selo circular, rótulos verticais e setas SVG inline.
- `static/css/style.css`: reescrita completa com tokens de cor, tipografia, cartões, sombras, espaçamento, animações de entrada, tilt, botões magnéticos, tela cheia e breakpoints.
- `static/fonts/`: Space Grotesk e Inter variáveis, com `OFL-space-grotesk.txt` e `OFL-inter.txt`.
- `static/js/app.js`: preservação dos IDs e do polling; `soundLabel` e `fullscreenLabel` em spans próprios; `rankingTag` dinâmico; pódio sempre renderizado, com slots vazios; tilt e botões magnéticos; correção de textos corrompidos.
- `static/img/preview.png`: prévia atualizada a partir do estado final da corrida demo, em página completa.
- Documentação: README, backlog, Journal, ADR 0008 e este diário.

## Decisões de implementação

- O layout usa áreas nomeadas de grid para manter a hierarquia do vídeo e do resultado, com reorganização em coluna única no celular.
- As fontes são locais e variáveis para funcionar offline e evitar requisições externas.
- O pódio deixou de depender de uma corrida em andamento para existir: os slots vazios aparecem desde o estado idle.
- A tela cheia ficou preta e esconde `.video-badges` para evitar a duplicação de `AO VIVO`/`DEMO` com o HUD de FPS/fonte desenhado pelo backend.
- Os efeitos de tilt e magnetismo só são ativados com ponteiro fino e são removidos em `prefers-reduced-motion: reduce`.
- A tela `/setup` permanece no tema escuro e foi registrada como trabalho visual futuro.

## Verificações realizadas

- `node --check static/js/app.js` sem erros.
- `python -m compileall -q app.py src tools` sem erros.
- Flask `test_client`: `/` responde `200` e contém os novos elementos (`card--podium`, `sound-label`, `space-grotesk`, `Fase 4`).
- Playwright desktop 1440x900 e 1440x1000: estado idle e final, sem erros de console/página.
- Playwright em 1080, 900, 820, 720 e 390 px: `scrollWidth` igual à viewport, sem rolagem horizontal.
- Tela cheia: `#video-panel` entra em fullscreen, `Sair da tela cheia` aparece, os badges HTML ficam ocultos e a saída restaura o layout.
- `prefers-reduced-motion: reduce`: `[data-reveal]` visível, `transform: none`, transições e animações praticamente instantâneas.
- Corrida demo: 3 itens no ranking, 3 entradas no pódio, `#ranking-tag` em `Final`, `#podium-tag` em `3 de 3`.
- Prévia final gerada em `static/img/preview.png` com 1440 px de largura e página completa.

## Limitações atuais

- Apenas a tela principal foi redesenhada; `/setup` continua escura.
- A validação com webcam real permanece pendente; os testes visuais usaram `--demo`.
- A suíte automatizada versionada continua fora do repositório.
- Tilt e magnetismo não aparecem em telas de toque por decisão de interação.
- A prévia inclui o HUD do backend no vídeo; os badges HTML continuam visíveis no fluxo normal.

## Próximos passos

1. Aplicar os mesmos tokens visuais à tela de setup, se o escopo for aprovado.
2. Criar a suíte de testes versionada de geometria, detecção e corrida.
3. Executar o checklist de aceite com a webcam real.
4. Revisar a documentação final e publicar no GitHub.
