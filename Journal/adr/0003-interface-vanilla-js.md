# ADR 0003 — Interface em HTML/CSS/JS puro servida pelo Flask

- **Status:** Aceito
- **Data:** 2026-10-28

## Contexto

A interface precisa ser visualmente agradável, rodar no notebook e ser simples de manter. Não há requisitos de SPA, roteamento complexo ou estado compartilhado entre muitos usuários.

## Decisão

Usar **HTML, CSS e JavaScript puro**, sem Node, React ou build. O Flask serve os templates e os arquivos estáticos. O vídeo chega por **MJPEG** (`/video_feed`) e o estado por **polling JSON** (`/api/state` a cada 200 ms).

## Alternativas consideradas

- **React/Vite:** melhor para aplicações grandes, mas adiciona toolchain, build e dependências sem ganho real aqui.
- **WebSocket:** menor latência, porém mais complexo no servidor e desnecessário para atualizações a 5 Hz.
- **Server-Sent Events:** viável, mas o polling é mais simples de depurar e reiniciar.

## Consequências

- Positivas: zero build, um único processo, fácil de publicar e entender; o navegador cuida da renderização do HUD.
- Negativas: sem componentização formal; exige disciplina para não virar um arquivo único gigante (separar CSS/JS e manter funções pequenas).
- O polling limita a taxa de atualização do HUD, o que é adequado para cronômetro e ranking.
