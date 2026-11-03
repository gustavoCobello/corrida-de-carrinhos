# Backlog — toy-car-race-vision

Atualizado em 2026-10-28. Ordem aproximada de prioridade dentro de cada bloco.

## Concluído (Fase 1)

- [x] Servidor Flask com `/`, `/video_feed`, `/api/state`, `/api/config` e `/api/health`
- [x] Thread de captura com último frame, FPS e reconexão
- [x] Shell da interface: tema escuro, área de vídeo, painel lateral e cartões de cores
- [x] Persistência em `config.local.json` com merge recursivo
- [x] Overlay da linha de chegada, ROI e HUD de FPS/fonte
- [x] Modo de demonstração sem webcam
- [x] Tratamento de câmera indisponível

## Concluído (Fase 2)

- [x] Tela de setup com stream limpo e 2 cliques para calibrar a linha
- [x] Endpoint `/api/config/line` e salvamento pela interface
- [x] Ferramenta `tools/calibrate.py` com sliders HSV e visualização das máscaras
- [x] Ajuste da ROI na tela de setup com 2 cantos
- [x] Endpoint `/api/config/roi` e salvamento da área de interesse
- [x] Endpoint `/api/config/colors` e persistência das faixas HSV
- [x] Modo de diagnóstico no calibrador com FPS, contornos e área dos blobs
- [x] Recarga automática de `config.local.json` sem reiniciar o servidor
- [x] Amostragem de cor por clique na ferramenta de calibração

## Concluído (Fase 3)

- [x] Detecção das 4 cores e classificação por maior contorno
- [x] Sorteio de 3 cores sem repetição e exibição da formação
- [x] Máquina de estados `idle -> armed -> running -> finished`
- [x] Cruzamento da linha com confirmação em frames e uma chegada por cor
- [x] Ranking, tempo de chegada e diferença para o 1º
- [x] HUD com cronômetro e status da formação
- [x] Pipeline de visão ligado ao stream, à API e ao overlay
- [x] Controles de sortear, iniciar, encerrar e resetar
- [x] Modo demo com os quatro carros cruzando dentro do segmento da linha

## Concluído (Fase 4)

- [x] Pódio animado com até 3 finalistas e slots vazios para chegadas ausentes
- [x] Som de chegada e fanfarra via WebAudio, com preferência no `localStorage`
- [x] Barra de progresso por carro, calculada pela distância normalizada até a linha
- [x] Layout responsivo final, testado em desktop e viewport móvel de 390 px
- [x] Modo tela cheia no painel de vídeo, com botão e duplo clique
- [x] Ajustes visuais da formação, do ranking e do pódio

## Concluído (Redesign da tela principal)

- [x] Layout Bento Grid claro na tela principal, com paleta off-white, lilás, menta, âmbar e preto
- [x] Tipografia self-hosted Space Grotesk/Inter, com licenças OFL no repositório
- [x] Pódio sempre visível, com slots vazios antes da corrida e tag de ranking dinâmica
- [x] Tilt 3D, botões magnéticos, selo circular e animações de entrada
- [x] Tela cheia reformulada em preto, sem duplicar os badges do vídeo
- [x] Responsividade validada em 1440, 1080, 900, 820, 720 e 390 px
- [x] Suporte a `prefers-reduced-motion`

## Próximo (Fase 5)

- [ ] Testes unitários de geometria, detecção e corrida com frames sintéticos
- [ ] Checklist de aceite com a webcam real
- [ ] Screenshots e GIF de demonstração no README
- [ ] Publicação no GitHub com tópicos e descrição

## Depois (ideias)

- [ ] Velocidade real com fita de referência (calibração de escala)
- [ ] Detecção de luz de largada para t0 automático
- [ ] Gravação das corridas e snapshots dos pódios
- [ ] Histórico persistente (SQLite) e exportação CSV
- [ ] Múltiplas baterias com ranking acumulado
- [ ] Perfis de calibração por ambiente/pista
- [ ] Marcadores ArUco como alternativa robusta
- [ ] Aplicar o mesmo sistema visual à tela de setup

## Riscos conhecidos

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| Confusão entre rosa e vermelho | Alto | Calibração HSV por perfil, ROI, ajuste de S/V, diagnóstico visual |
| Oclusão dos carros na chegada | Médio | Memória de última posição, histerese e margem na linha |
| Iluminação variável | Alto | Perfis por ambiente, alerta de baixa confiança |
| Erro humano no clique de largada | Médio | Documentar; futuro modo com luz de largada |
| Webcam instável no Windows | Médio | `CAP_DSHOW`, seleção de índice na config, reconexão |
| Falsos positivos de objetos coloridos | Médio | ROI da pista, área mínima e confirmação em vários frames |

## Dívida técnica

- Definir formato definitivo do `config.local.json` e versionamento de schema.
- Avaliar cache do JPEG anotado caso o projeto passe a servir mais de um cliente.
- Padronizar logs do servidor e mensagens de erro em PT-BR.
- Definir se o estado da corrida será apenas em memória ou persistido.

## Critérios de priorização

1. Fazer o fluxo principal funcionar de ponta a ponta.
2. Garantir corretude do ranking antes do acabamento visual.
3. Reduzir falsos positivos e perda de detecção.
4. Melhorar a experiência de apresentação (pódio, som, tela cheia).
5. Só então ampliar escopo (velocidade real, histórico, múltiplas baterias).
