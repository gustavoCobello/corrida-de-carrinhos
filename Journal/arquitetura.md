# Arquitetura — toy-car-race-vision

## 1. Visão geral

```text
+-----------+     +------------------+     +-------------------+     +------------------+
|  Webcam   | --> | Thread de captura| --> | Detecção (HSV)    | --> | Estado da corrida|
| (OpenCV)  |     | último frame     |     | máscaras/contornos|     | ranking e tempos |
+-----------+     +------------------+     +-------------------+     +------------------+
                                                    |                          |
                                                    v                          v
                                        +----------------------+    +----------------------+
                                        | Overlay no vídeo     |    | API JSON /api/state  |
                                        | caixas e linha       |    | polling do navegador |
                                        +----------------------+    +----------------------+
                                                    |                          |
                                                    v                          v
                                        +----------------------+    +----------------------+
                                        | MJPEG /video_feed    |    | HUD HTML/CSS/JS      |
                                        +----------------------+    +----------------------+
```

O servidor Flask entrega a página, o stream MJPEG e o estado da corrida. Não há WebSocket: o navegador consulta `/api/state` a cada 200 ms, o que é suficiente para o HUD e mantém a implementação simples.

## 2. Componentes

| Componente | Responsabilidade |
| --- | --- |
| `app.py` | Cria o app Flask, registra rotas, serve o MJPEG, instancia o pipeline e inicia/encerra a câmera |
| `src/camera.py` | Abre a webcam em thread, mantém o último frame, chama o callback de processamento e implementa o modo demo |
| `src/overlay.py` | Desenha a linha quadriculada, a ROI, as detecções e o HUD de corrida/FPS/fonte no vídeo |
| `src/config.py` | Carrega `config.example.json`, aplica `config.local.json`, valida e persiste |
| `src/detection.py` | Aplica máscaras HSV, morfologia, contornos, área mínima e classifica cores |
| `src/geometry.py` | Distância assinada até a linha, pertinência ao segmento e teste de cruzamento |
| `src/race.py` | Sorteio, máquina de estados, registro de chegadas, ranking, tempos e progresso normalizado |
| `src/pipeline.py` | Processa frames, recarrega a configuração e publica snapshots de corrida/detecções |
| `templates/index.html` | Interface principal em Bento Grid (vídeo, formação, ranking, pódio e controles) |
| `templates/setup.html` | Calibração da linha e da ROI sobre o vídeo, ainda no tema escuro |
| `static/css/style.css` e `static/js/app.js` | Estilo e lógica do HUD, progresso, pódio, som, tilt, tela cheia e movimento reduzido |
| `static/css/setup.css` e `static/js/setup.js` | Estilo, cliques, canvas e persistência da calibração |
| `static/fonts/` | Space Grotesk e Inter variáveis, self-hosted, com licenças OFL |
| `tools/calibrate.py` | Ferramenta de ajuste fino das faixas HSV com sliders do OpenCV |

## 3. Pipeline de detecção

1. **Captura:** frame BGR da webcam, redimensionado para a resolução de processamento (`960x540` por padrão).
2. **ROI:** recorte da área da pista definida na configuração; tudo fora dela é ignorado.
3. **Conversão:** BGR para HSV.
4. **Máscaras:** uma ou mais faixas HSV por cor (vermelho usa duas faixas por cruzar o matiz 0/179).
5. **Limpeza:** abertura e fechamento morfológicos para remover ruído e preencher buracos.
6. **Contornos:** seleciona o maior contorno válido de cada cor acima de `min_area_px`.
7. **Classificação:** como cada cor existe no máximo uma vez na corrida, o maior blob de cada cor é o carro daquela cor.
8. **Referência lateral:** guarda o último ponto de cada carro. Se ele desaparecer e reaparecer, o salto é validado antes de atualizar a referência, sem inventar uma chegada.
9. **Cruzamento:** compara o lado da linha entre frames consecutivos; confirma a chegada quando o lado muda e o ponto de cruzamento está dentro do segmento.
10. **Saída:** centroide, caixa, cor e instante de chegada alimentam o estado da corrida e o overlay.

## 4. Geometria da linha e cruzamento

A linha é definida por dois pontos normalizados `p1` e `p2` (0 a 1), convertidos para pixels na resolução de processamento. Para um centroide `p`:

```text
lado(p) = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
```

- `lado` positivo e negativo indicam lados opostos da reta.
- A chegada é confirmada quando `lado` muda de sinal entre dois frames.
- O ponto de cruzamento deve estar dentro do segmento, com margem de tolerância nas pontas.
- Exige-se `confirm_frames` frames consecutivos do novo lado para evitar oscilação do centroide.
- Cada cor registra chegada no máximo uma vez por corrida.
- A distância perpendicular normalizada é `distancia = |lado| / comprimento_da_linha`.
- O progresso visual é `1 - distancia / max(start_distance, 0.02)`, limitado a 0–1, e vira `1.0` na chegada.
- `start_distance` é a distância da primeira detecção daquela cor depois da largada; o progresso serve para a apresentação e não altera o ranking.

## 5. Máquina de estados da corrida

| Estado | Significado | Transições |
| --- | --- | --- |
| `idle` | Sem corrida ativa | `arm` após sortear 3 cores |
| `armed` | Formação definida, aguardando largada | `start` pelo botão; novo sorteio; `reset` |
| `running` | Cronômetro ativo desde t0 | `finish` automático quando os 3 carros chegam, `finish` manual ou `reset` |
| `finished` | Ranking e tempos disponíveis | `reset` ou `arm` para nova bateria |

- `start` grava `started_at`, zera os tempos e reinicia o progresso dos carros.
- Cada chegada grava `crossed_at` e entra no ranking por ordem crescente.
- `reset` limpa tempos, lineup, progresso e volta para `idle`.
- Se um carro não for detectado, a corrida pode ser encerrada manualmente; os carros sem chegada ficam como `missed`.
- O sorteio pode receber uma lista explícita de cores (usada em testes); sem lista, escolhe 3 cores válidas aleatoriamente.

## 6. Modelo de dados (estado da corrida)

```json
{
  "race": {
    "status": "running",
    "started_at": "2026-10-28T14:32:10.512",
    "lineup": ["vermelho", "azul", "rosa"],
    "cars": [
      {
        "color": "vermelho",
        "label": "Vermelho",
        "status": "finished",
        "first_seen_at": "2026-10-28T14:32:11.004",
        "crossed_at": "2026-10-28T14:32:12.730",
        "elapsed_ms": 2218,
        "position": 1,
        "delta_ms": 0,
        "progress": 1.0
      }
    ]
  },
  "detections": [
    {
      "color": "azul",
      "label": "Azul",
      "bbox": [590, 380, 44, 76],
      "cx": 612,
      "cy": 418,
      "nx": 0.6375,
      "ny": 0.7741,
      "area": 1830,
      "confidence": 0.92
    }
  ],
  "config": {
    "line": { "p1": [0.15, 0.75], "p2": [0.85, 0.75] }
  }
}
```

## 7. Contrato da API

| Método | Rota | Descrição |
| --- | --- | --- |
| GET | `/` | Interface principal |
| GET | `/setup` | Tela de calibração e diagnóstico |
| GET | `/video_feed` | Stream MJPEG com overlay; `?overlay=0` entrega a imagem limpa |
| GET | `/api/state` | Estado atual da corrida, detecções e configuração pública |
| POST | `/api/race/arm` | Sorteia 3 cores e arma a corrida |
| POST | `/api/race/start` | Marca t0 e inicia a corrida |
| POST | `/api/race/reset` | Limpa a corrida |
| POST | `/api/race/finish` | Encerra manualmente uma corrida em andamento |
| GET | `/api/config` | Configuração efetiva |
| POST | `/api/config/line` | Salva a linha calibrada (2 pontos normalizados) |
| POST | `/api/config/roi` | Salva a área de interesse (`x`, `y`, `w`, `h` normalizados) |
| POST | `/api/config/colors` | Salva faixas HSV ajustadas |
| GET | `/api/setup/frame` | Frame único em JPEG para diagnóstico |
| GET | `/api/health` | Verificação rápida do servidor e do estado da câmera |

Respostas de erro usam JSON com `{"error": "mensagem"}` e código HTTP adequado.

## 8. Threading e performance

- Uma única thread abre a câmera e mantém `latest_frame` protegido por lock. Evita abrir a webcam duas vezes (o que falha em muitos drivers).
- A detecção roda no mesmo laço da captura, por callback, na resolução de processamento, e publica um `RaceManager` protegido por lock.
- O stream MJPEG lê o último frame publicado e desenha o overlay com o snapshot mais recente de detecções e corrida; a codificação JPEG acontece no gerador do stream.
- Com um cliente o custo é baixo; se houver vários, o próximo passo é cachear o JPEG anotado por frame.
- O overlay é desenhado em uma cópia do frame para não contaminar a detecção.
- A interface usa polling de 200 ms; o vídeo é independente e roda a 25–30 fps.
- O progresso, o ranking e o pódio usam o mesmo snapshot; o pódio só é reconstruído quando a assinatura de posições, cores e tempos muda.
- O som de chegada é sintetizado com `OscillatorNode` no navegador, sem arquivos de áudio; o contexto é desbloqueado por um gesto do usuário e a preferência fica em `localStorage`.
- A tela cheia chama `requestFullscreen()` no painel de vídeo e aceita botão ou duplo clique.
- No Windows, abrir a câmera com `cv2.CAP_DSHOW` melhora a compatibilidade.

## 9. Configuração

- `config.example.json` é versionado e traz os valores padrão.
- `config.local.json` contém a calibração do usuário e é ignorado pelo git.
- O carregamento faz merge recursivo: valores locais sobrescrevem apenas as chaves informadas e preservam o restante dos padrões.
- Coordenadas da linha e da ROI são normalizadas (0 a 1), independentes da resolução.
- `ConfigStore` compara o `mtime` de `config.local.json` a cada `snapshot()` e recarrega as sobrescritas automaticamente.
- A gravação é atômica: escreve um arquivo temporário e substitui o original, reduzindo o risco de configuração corrompida.
- A tela `/setup` trabalha com coordenadas normalizadas e desenha a prévia em um canvas sobre o stream limpo.
- A calibração de cor fica em uma ferramenta OpenCV separada, pois exige sliders e uma janela nativa; ela grava apenas a cor em edição.

## 10. Tratamento de falhas

- Câmera indisponível: interface mostra aviso e o servidor continua ativo para permitir reconfigurar o índice.
- Configuração inválida: usa padrões e registra aviso no log.
- Perda de detecção: a referência lateral é mantida até a próxima detecção; saltos grandes são ignorados e a chegada exige confirmação em `confirm_frames`.
- Cliente desconectado: o stream encerra sem derrubar a captura.

## 11. Segurança e privacidade

- Servidor escuta apenas em `127.0.0.1`.
- Nenhuma imagem é enviada para a internet.
- Nada é gravado em disco por padrão; capturas, se habilitadas no futuro, ficam em pasta ignorada.

## 12. Estratégia de testes

- **Unitários (`unittest`):** geometria da linha, lado, pertinência ao segmento e detecção de cruzamento.
- **Sintéticos:** frames gerados com blobs coloridos para validar máscaras e classificação.
- **Integração manual:** checklist dos critérios de aceite com a webcam real.
- **Diagnóstico:** `tools/calibrate.py` mostra máscaras, FPS e área dos contornos; a tela de setup mostra FPS, resolução e a geometria calibrada.

## 13. Status da implementação (Fase 4)

- Implementado: `app.py`, `config.py`, `camera.py`, `overlay.py`, `geometry.py`, `detection.py`, `race.py`, `pipeline.py`, interface principal, tela de setup, `tools/calibrate.py` e modo demo.
- Endpoints ativos: `/`, `/setup`, `/video_feed`, `/api/state`, `/api/config`, `/api/config/line`, `/api/config/roi`, `/api/config/colors`, `/api/race/arm`, `/api/race/start`, `/api/race/finish`, `/api/race/reset`, `/api/setup/frame` e `/api/health`.
- Corrida: sorteio de 3 cores, estados `idle/armed/running/finished`, confirmação de cruzamento em `confirm_frames`, ranking com tempo e diferença para o 1º, progresso visual por carro e encerramento manual.
- Interface: Bento Grid claro na tela principal, cronômetro, formação com estados e progresso das cores, ranking dinâmico, pódio sempre visível com até 3 finalistas, som WebAudio com controle de ligar/desligar, tela cheia preta, layout responsivo e toast de erro.
- Redesign: fontes self-hosted, selo circular, tilt em ponteiro fino, botões magnéticos e respeito a `prefers-reduced-motion`; `/setup` segue no tema escuro.
- Pendente: aplicar o sistema visual ao setup, criar testes automatizados versionados, executar o checklist de aceite com a webcam real, gerar screenshots/GIF de demonstração e publicar no GitHub.
