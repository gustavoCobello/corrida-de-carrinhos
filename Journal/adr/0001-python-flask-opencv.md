# ADR 0001 — Python + Flask + OpenCV como base

- **Status:** Aceito
- **Data:** 2026-10-28

## Contexto

O projeto precisa acessar a webcam no Windows, processar vídeo em tempo real na CPU e servir uma interface local bonita. O ambiente já possui Python 3.10, OpenCV 5, NumPy e Flask instalados. O usuário não quer complexidade de Node/React.

## Decisão

Usar **Python** como linguagem principal, **OpenCV** para captura e visão computacional e **Flask** como servidor local. O front-end é servido pelo próprio Flask.

## Alternativas consideradas

- **Node.js + biblioteca de câmera:** exigiria dependências nativas e um segundo ecossistema; o processamento de imagem seria menos direto.
- **Aplicativo desktop (Tkinter/Qt):** mais simples de empacotar, porém com interface menos flexível e menos atraente que HTML/CSS.
- **Electron:** pesado para o escopo e contraria o desejo de simplicidade.
- **FastAPI:** também viável e já instalado, mas o streaming MJPEG e o polling são igualmente simples em Flask, que tem menor curva de entrada para este caso.

## Consequências

- Positivas: stack única, dependências já disponíveis, fácil de rodar e explicar, interface web flexível.
- Negativas: Flask de desenvolvimento não é um servidor de produção (aceitável, pois o uso é local); o processamento fica limitado à CPU.
- Reavaliar se houver necessidade de acesso remoto, múltiplas câmeras ou empacotamento executável.
