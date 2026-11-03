# ADR 0005 — Calibração geográfica no navegador e calibração de cor no OpenCV

- **Status:** Aceito
- **Data:** 2026-10-28

## Contexto

A Fase 2 precisa de duas calibrações com naturezas diferentes:

- **Linha de chegada e ROI:** são geometria sobre a imagem. O usuário precisa ver o enquadramento e clicar em pontos; a persistência pode ser feita por uma API local.
- **Faixas HSV:** exigem ajuste contínuo de matiz, saturação e valor, visualização da máscara e amostragem de pixels. É uma tarefa de diagnóstico, não de posicionamento.

O servidor já mantém a webcam aberta em uma thread. Abrir a câmera em outra janela ao mesmo tempo pode falhar em drivers do Windows.

## Decisão

Separar a calibração em duas superfícies:

1. **`/setup` no navegador:** consome o stream MJPEG limpo (`/video_feed?overlay=0`), desenha a linha e a ROI em um canvas e envia coordenadas normalizadas para `/api/config/line` e `/api/config/roi`. O salvamento é explícito e há confirmação visual.
2. **`tools/calibrate.py`:** ferramenta OpenCV com janela nativa, sliders HSV, amostragem por clique, máscara ao vivo, FPS e área dos contornos. Grava apenas a cor em edição em `/api/config/colors` por meio do mesmo `ConfigStore`.

As duas superfícies gravam sobrescritas em `config.local.json`. O `ConfigStore` compara o `mtime` do arquivo e recarrega a configuração automaticamente, então a tela principal e o stream refletem a mudança sem reiniciar o servidor.

## Alternativas consideradas

- **Tudo no navegador, inclusive HSV:** reduziria a troca de contexto, mas exigiria reimplementar sliders, amostragem, morfologia e preview de máscara em JavaScript, aumentando bastante o front-end.
- **Tudo no OpenCV:** ruim para posicionar a linha e a ROI, pois exigiria cliques em uma janela nativa e não aproveitaria a interface já existente.
- **Calibrar HSV com o servidor rodando:** conflito de acesso à webcam em muitos drivers; a ferramenta deve ser usada com o servidor parado.

## Consequências

- Positivas: cada tarefa usa a interface mais adequada; a câmera é aberta por um processo de cada vez; a configuração é compartilhada e recarregada a quente; o fluxo de calibração fica simples para o usuário.
- Negativas: existem duas telas/ferramentas para aprender; a calibração de cor exige parar o servidor; a validação visual da máscara não aparece no navegador.
- Mitigações: link **Calibração** na interface principal, instruções na própria tela de setup e mensagens claras na ferramenta; o `--demo` permite testar o calibrador sem webcam.
- Reavaliar se o ajuste de cor for necessário com frequência durante a operação: nesse caso, vale estudar um preview de máscara no navegador.
