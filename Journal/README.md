# Journal — toy-car-race-vision

Índice da documentação do projeto. Tudo em português (PT-BR).

## Documentos

| Documento | Conteúdo |
| --- | --- |
| [especificação.md](especificacao.md) | Objetivo, escopo, requisitos funcionais e não funcionais, regras e critérios de aceite |
| [arquitetura.md](arquitetura.md) | Pipeline, componentes, estados da corrida, contrato da API e modelo de dados |
| [adr/](adr/) | Decisões técnicas registradas (Architecture Decision Records) |
| [diário/](diario/) | Diário de bordo datado, com contexto e próximos passos |
| [backlog.md](backlog.md) | Prioridades, ideias futuras e riscos conhecidos |

## ADRs

| Número | Decisão |
| --- | --- |
| [0001](adr/0001-python-flask-opencv.md) | Python + Flask + OpenCV como base |
| [0002](adr/0002-deteccao-hsv.md) | Detecção por cor em HSV em vez de modelo treinado |
| [0003](adr/0003-interface-vanilla-js.md) | Interface em HTML/CSS/JS puro servida pelo Flask |
| [0004](adr/0004-largada-manual.md) | Largada manual pelo botão "Iniciar" |
| [0005](adr/0005-calibracao-em-duas-etapas.md) | Calibração geográfica no navegador e calibração de cor no OpenCV |
| [0006](adr/0006-cruzamento-com-confirmacao.md) | Chegada por troca de lado com confirmação em frames |
| [0007](adr/0007-progresso-por-distancia.md) | Progresso visual pela distância normalizada até a linha |
| [0008](adr/0008-bento-grid-claro.md) | Tema claro em Bento Grid e fontes self-hosted na tela principal |

## Diário

| Data | Registro |
| --- | --- |
| 2026-10-28 | [Início do projeto](diario/2026-10-28-inicio.md) |
| 2026-10-28 | [Fase 1: captura, servidor e interface](diario/2026-10-28-fase-1.md) |
| 2026-10-28 | [Fase 2: calibração da linha, ROI e cores](diario/2026-10-28-fase-2.md) |
| 2026-10-28 | [Fase 3: detecção, cruzamento, ranking e tempos](diario/2026-10-28-fase-3.md) |
| 2026-10-28 | [Fase 4: pódio, som, progresso e tela cheia](diario/2026-10-28-fase-4.md) |
| 2026-10-28 | [Redesign: Bento Grid claro na tela principal](diario/2026-10-28-redesign-bento.md) |

## Convenções

- Documentos em PT-BR, sem emojis.
- Decisões relevantes viram um ADR com contexto, decisão e consequências.
- Cada sessão de trabalho relevante gera uma entrada datada em `diario/`.
- O backlog é revisado ao final de cada fase.
